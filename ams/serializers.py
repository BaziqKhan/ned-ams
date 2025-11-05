from rest_framework import serializers
from .models import (
    InspectionCertificate,
    InspectionItem,
    Item,
    StockEntry,
    StockRegister,
    Location,
    Contractor,
    Contract,
    Indenter,
    Indent,
    Consignee,
    StockEntry,
    Store,
    IssueItem,
    IssueRequisiton
)
from rest_framework.reverse import reverse
from datetime import date

class InspectionItemSerializer(serializers.ModelSerializer):
    # Show item and stock_register as primary keys by default; you can change to nested serializers if desired.
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), required=False, allow_null=True)
    stock_register = serializers.PrimaryKeyRelatedField(queryset=StockRegister.objects.all(), required=False, allow_null=True)
    inspection = serializers.PrimaryKeyRelatedField(read_only=True)  # set by view when created via nested endpoint

    class Meta:
        model = InspectionItem
        fields = [
            "id",
            "inspection",
            "item",
            "acct_unit",
            "tendered_quantity",
            "rejected_quantity",
            "accepted_quantity",
            "rejected_reason",
            "unit_price",
            "gst_rate",
            "stock_register",
            "created_at",
            "generate_qr_code",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        # add cross-field validations here if needed
        if data.get("tendered_quantity", 0) < 0:
            raise serializers.ValidationError("tendered_quantity cannot be negative.")
        return data



class InspectionCertificateSerializer(serializers.ModelSerializer):
    # nested read-only items
    items = InspectionItemSerializer(many=True, read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(parent_location__isnull=True)
    )
    # READ-ONLY foreign key fields (for PDF generation and GET requests)
    contract = serializers.PrimaryKeyRelatedField(read_only=True)
    indent = serializers.PrimaryKeyRelatedField(read_only=True)
    consignee = serializers.PrimaryKeyRelatedField(read_only=True)
    
    # Foreign key fields to type directly
    contractor_name = serializers.CharField(write_only=True)
    contractor_address = serializers.CharField(write_only=True, allow_blank=True, required=False)
    contract_no = serializers.CharField(write_only=True)
    contract_date = serializers.DateField(write_only=True, required=False)

    indenter_name = serializers.CharField(write_only=True)
    indent_no = serializers.CharField(write_only=True)

    consignee_name = serializers.CharField(write_only=True)
    
    pdf_url = serializers.SerializerMethodField(method_name="get_pdf_url")
    

    class Meta:
        model = InspectionCertificate
        fields = [
            "id",
            "issued_on",
            "issued_to",
            # READ-ONLY foreign keys (for accessing existing data)
            "contract",
            "indent",
            "consignee",
            
            "contractor_name",
            "contractor_address",
            "contract_no",
            "contract_date",
            "indenter_name",
            "indent_no",
            "consignee_name",
            "department",
            "date_of_delivery",
            "delivery_status",
            "created_at",
            "updated_at",
            "items",
            'pdf_url',
        ]
        read_only_fields = ["id", "created_at", "updated_at","contract","indent","consignee"]
    
    def create(self, validated_data):
        # --- Contractor + Contract ---
        contractor_name = validated_data.pop("contractor_name")
        contractor_address = validated_data.pop("contractor_address", "")
        contract_no = validated_data.pop("contract_no")
        contract_date = validated_data.pop("contract_date", date.today())

        contractor, _ = Contractor.objects.get_or_create(
            name=contractor_name,
            defaults={"address": contractor_address},
        )
        if contractor_address and not contractor.address:
            contractor.address = contractor_address
            contractor.save()

        contract, _ = Contract.objects.get_or_create(
            contract_no=contract_no,
            defaults={"contract_date": contract_date, "contractor": contractor},
        )

        # --- Indenter + Indent ---
        indenter_name = validated_data.pop("indenter_name")
        indent_no = validated_data.pop("indent_no")

        indenter, _ = Indenter.objects.get_or_create(name=indenter_name)
        indent, _ = Indent.objects.get_or_create(
            indent_no=indent_no,
            defaults={"indenter": indenter},
        )

        # --- Consignee ---
        consignee_name = validated_data.pop("consignee_name")
        consignee, _ = Consignee.objects.get_or_create(name=consignee_name)

        # --- Create certificate ---
        certificate = InspectionCertificate.objects.create(
            contract=contract,
            indent=indent,
            consignee=consignee,
            **validated_data,
        )
        return certificate
        
    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if request:
            return reverse(
                "inspectioncertificate-download-pdf",
                kwargs={"pk": obj.pk},
                request=request
            )
        return None
class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "location",
        ]
        read_only_fields = ["id"]

class StockRegisterSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField(method_name="get_pdf_url")
    store = serializers.SerializerMethodField(method_name="get_store")
    class Meta:
        model = StockRegister
        fields = [
            "id",
            "register_type",
            "store",
            'pdf_url',
        ]
        read_only_fields = ["id"]
    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if request:
            return reverse(
                "stockregister-download-pdf",
                kwargs={"pk": obj.pk},
                request=request
            )
        return None
    def get_store(self, obj):
        serializer = StoreSerializer(obj.store, context=self.context)
        return serializer.data['name']
class StockEntrySerializer(serializers.ModelSerializer):
    # Show human-readable related info in responses
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_category = serializers.CharField(source='item.category.name', read_only=True)
    store_name = serializers.CharField(source='stockregister.store.name', read_only=True) 
    #stock_register = serializers.PrimaryKeyRelatedField(queryset=StockRegister.objects.all())

    class Meta:
        model = StockEntry
        fields = [
            "id",
            "stock_register",
            "item",
            "item_name",
            "item_category",
            "entry_type",
            "voucher_no",
            "date_of_entry",
            "quantity_in",
            "quantity_out",
            "balance",
            "remarks",
            "store_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at",'stock_register']
        

class IssueItemSerializer(serializers.ModelSerializer):
    item_instance_name = serializers.CharField(source='item_instance.item.name', read_only=True)
    item_instance_id = serializers.IntegerField(source='item_instance.id', read_only=True)

    class Meta:
        model = IssueItem
        fields = '__all__'


class IssueRequisitionSerializer(serializers.ModelSerializer):
    items = IssueItemSerializer(many=True, read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(parent_location__isnull=True)
    )

    class Meta:
        model = IssueRequisiton
        fields = '__all__'