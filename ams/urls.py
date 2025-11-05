from rest_framework_nested import routers
from .views import (
    InspectionCertificateViewSet,
    InspectionItemViewSet,
    StockEntryViewSet,
    StockRegisterViewSet,
    IssueRequisitionViewSet,
    IssueItemViewSet
)

# Main router
router = routers.DefaultRouter()
router.register(r"inspection-certificates", InspectionCertificateViewSet, basename="inspectioncertificate")
router.register(r"stock-registers", StockRegisterViewSet, basename="stockregister")
router.register(r"issue-requisitions",IssueRequisitionViewSet,basename='issue-requisition')

# Nested router for items under certificates
cert_items_router = routers.NestedDefaultRouter(router, r"inspection-certificates", lookup="inspectioncertificate")
cert_items_router.register(r"items", InspectionItemViewSet, basename="inspectioncertificate-items")

# ✅ New nested route for QR codes under each inspection item
item_qr_router = routers.NestedDefaultRouter(cert_items_router, r"items", lookup="inspectionitem")

# Stock entries nested under stock registers
stock_entry_router = routers.NestedDefaultRouter(router, r"stock-registers", lookup="stockregister")
stock_entry_router.register(r"entries", StockEntryViewSet, basename="stockregister-entries")

issue_items_router = routers.NestedDefaultRouter(router,r"issue-requisitions",lookup="issuerequisitions")
issue_items_router.register(r"issueitems",IssueItemViewSet,basename="issue-items")

urlpatterns = [
    *router.urls,
    *cert_items_router.urls,
    *item_qr_router.urls,  # ✅ include the deeper nested router
    *stock_entry_router.urls,
]
