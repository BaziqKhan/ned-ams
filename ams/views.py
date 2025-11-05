from io import BytesIO
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.http import HttpResponse

from .models import InspectionCertificate, InspectionItem,StockEntry,StockRegister,IssueRequisiton,IssueItem
from .serializers import (InspectionCertificateSerializer, InspectionItemSerializer,StockRegisterSerializer,StockEntrySerializer
,IssueItemSerializer,IssueRequisitionSerializer)
from .generator import InspectionCertificateGenerator
from .sf_generator import StockFormGenerator
import os
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class InspectionCertificateViewSet(viewsets.ModelViewSet):
    """
    CRUD for InspectionCertificate.
    """
    queryset = InspectionCertificate.objects.all().order_by('-created_at')
    serializer_class = InspectionCertificateSerializer

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        """
        Generate and return the Inspection Certificate PDF directly using buffer
        """
        certificate = self.get_object()
        
        # Item and rejection details
        items = InspectionItem.objects.filter(inspection=certificate)
        stock_registers = [f'{item.stock_register.register_type} - {item.stock_register.store.name}' 
                          for item in items if item.stock_register]
        stock_registers = list(set(stock_registers))  # Unique values
        
        # Prepare certificate data
        data = {
            "contract_no": certificate.contract.contract_no,
            "date": certificate.contract.contract_date.strftime('%Y-%m-%d'),
            "contractor_name": certificate.contract.contractor.name,
            "contractor_address": certificate.contract.contractor.address or "",
            "indenter": certificate.indent.indenter.name,
            "indent_no": certificate.indent.indent_no,
            "consignee": certificate.consignee.name,
            "department": certificate.department.name if certificate.department else "",
            "date_of_delivery": certificate.date_of_delivery.strftime('%Y-%m-%d') if certificate.date_of_delivery else "",
            "delivery_status": certificate.delivery_status or "",
            "date_of_inspection": "",
            "stock_register_no": stock_registers,
            "dead_stock_register_no": "",
        }

        item_data = {
            "descriptions": [f'{item.item.name}, {item.item.specifications}' if item.item else "" for item in items],
            "acct_unit": [item.acct_unit or "" for item in items],
            "t_quantity": [item.tendered_quantity for item in items],
            "r_quantity": [item.rejected_quantity for item in items],
            "a_quantity": [item.accepted_quantity for item in items],
        }

        # Filter items with rejected reasons
        rejected_items = [item for item in items if item.rejected_reason]
        rejected_item_data = {
            "item_no": [i + 1 for i in range(len(rejected_items))],
            "reasons": [item.rejected_reason or "" for item in rejected_items],
        }
        
        # Define output path - save to forms/inspection_certificates/
        filename = f"inspection_certificate_{certificate.id}.pdf"
        output_dir = os.path.join(settings.BASE_DIR, 'forms', 'inspection_certificates')
        output_path = os.path.join(output_dir, filename)

        # Generate PDF in buffer
        generator = InspectionCertificateGenerator(
            logo_path="ams/ned_logo.png",
            data=data,
            item_data=item_data,
            rejected_item_data=rejected_item_data
        )

        # Get the PDF buffer and return as response
        pdf_buffer = generator.get_pdf()
        
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response


class InspectionItemViewSet(viewsets.ModelViewSet):
    """
    CRUD for InspectionItem.
    Supports both nested and standalone access.
    """
    queryset = InspectionItem.objects.all().order_by('-created_at')
    serializer_class = InspectionItemSerializer

    def get_queryset(self):
        """
        Filter by inspection if nested route is used.
        """
        qs = super().get_queryset()
        inspection_pk = self.kwargs.get("inspectioncertificate_pk")
        if inspection_pk:
            qs = qs.filter(inspection_id=inspection_pk)
        return qs

    def perform_create(self, serializer):
        """
        Auto-assign inspection when nested under it.
        """
        inspection_pk = self.kwargs.get("inspectioncertificate_pk")
        if inspection_pk:
            inspection = get_object_or_404(InspectionCertificate, pk=inspection_pk)
            # FIXED: use 'inspection' parameter instead of 'certificate'
            serializer.save(inspection=inspection)
        else:
            serializer.save()
    @action(detail=True, methods=["get"], url_path="qr-codes")
    def generate_qr_codes_pdf(self, request, *args, **kwargs):
        """
        Generate or load all QR codes of this inspection item and return them in a single PDF page.
        """
        inspection_item = self.get_object()
        item_instances = inspection_item.item_instances.all()

        if not item_instances.exists():
            return Response({"detail": "No item instances found for this inspection item."}, status=404)

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        width, height = A4
        margin_x, margin_y = 50, 100
        qr_size = 150
        x, y = margin_x, height - margin_y
        per_row = 3
        counter = 0

        for instance in item_instances:
            if not instance.qr_code:
                continue

            qr_path = instance.qr_code.path

            # --- Draw QR ---
            p.drawImage(qr_path, x, y - qr_size, qr_size, qr_size)

            # --- Text section (aligned nicely below QR) ---
            text_y = y - qr_size - 15
            p.setFont("Helvetica", 10)
            p.drawString(x, text_y, f"Item: {instance.item.name}")
            p.drawString(x, text_y - 12, f"Status: {instance.status}")

            location_name = getattr(instance.current_location, "name", "Unknown Location")
            p.drawString(x, text_y - 24, f"Location: {location_name}")

            # --- Layout control ---
            counter += 1
            x += qr_size + 40

            if counter % per_row == 0:
                x = margin_x
                y -= qr_size + 80  # move down for next row

            # Move to next page if needed
            if y < margin_y + qr_size:
                p.showPage()
                y = height - margin_y
                x = margin_x

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="qr_codes_item_{inspection_item.id}.pdf"'
        return response
            

class StockRegisterViewSet(viewsets.ModelViewSet):
    queryset = StockRegister.objects.all().order_by('id')
    serializer_class = StockRegisterSerializer
    
    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        """
        Generate and return the Inspection Certificate PDF directly using buffer
        """
        register = self.get_object()

        
        # Item and rejection details
        entries = StockEntry.objects.filter(stock_register=register)
        
        # Prepare certificate data
        data = {
            'description_of_item': [f'{entry.item.name} - {entry.item.specifications}' for entry in entries],
            
        }
        stock_data = {
            'date_of_entry': [entry.date_of_entry.strftime('%Y-%m-%d') for entry in entries],
            'voucher_no': [f'{entry.voucher_no}' for entry in entries],
            'particulars': [f'{entry.item.name},{entry.item.specifications}' for entry in entries],
            'acct_unit': [''],
            'unit_price': [str(entry.unit_price) if entry.unit_price else '' for entry in entries],
            'total_cost': [str((entry.unit_price) * entry.quantity_in) if entry.unit_price else '' for entry in entries], 
            'recieved_quantity': [entry.quantity_in for entry in entries],
            'issued_quantity': [entry.quantity_out for entry in entries],
            'balance': [entry.balance for entry in entries],
            'remarks': [entry.remarks or '' for entry in entries],
        }

        
        # Define output path - save to forms/inspection_certificates/
        filename = f"{register.register_type} - {register.store.name}.pdf"
        output_dir = os.path.join(settings.BASE_DIR, 'forms', 'stock_registers')
        output_path = os.path.join(output_dir, filename)

        # Generate PDF in buffer
        generator = StockFormGenerator(
            register_name=f"{register.register_type} - {register.store.name}",
            data=data,
            stock_data=stock_data
        )

        # Get the PDF buffer and return as response
        pdf_buffer = generator.get_pdf()
        
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
class StockEntryViewSet(viewsets.ModelViewSet):

    #queryset = StockEntry.objects.all().order_by('-created_at')
    serializer_class = StockEntrySerializer
    
    def get_queryset(self):
        stock_register_id = self.kwargs['stockregister_pk']
        return StockEntry.objects.filter(stock_register_id=stock_register_id)
    
    def perform_create(self, serializer):
        stock_register_id = self.kwargs['stockregister_pk']
        stock_register = StockRegister.objects.get(pk=stock_register_id)

        serializer.save(stockregister=stock_register)
        
        
class IssueRequisitionViewSet(viewsets.ModelViewSet):
    """
    Handles all CRUD for Issue Requisitions
    """
    queryset = IssueRequisiton.objects.all().order_by('-created_at')
    serializer_class = IssueRequisitionSerializer
    filterset_fields = {
        'status': ['exact'],
        'department': ['exact'],
        'issue_date': ['gte', 'lte', 'exact'],
    }
    search_fields = ['requisiton_no', 'purpose', 'issued_by', 'received_by']


class IssueItemViewSet(viewsets.ModelViewSet):
    """
    Handles all CRUD for Issue Items (nested under Issue Requisition)
    """
    serializer_class = IssueItemSerializer
    filterset_fields = ['major_head', 'store_post_reference']

    def get_queryset(self):
        issue_requisition_id = self.kwargs.get('issue-requisition_pk')
        return IssueItem.objects.filter(issue_id=issue_requisition_id)