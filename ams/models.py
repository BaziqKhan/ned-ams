from django.db import models

# === Helper Enums ===

class RegisterType(models.TextChoices):
    CONSUMABLE = 'CONSUMABLE', 'Consumable'
    DEADSTOCK = 'DEADSTOCK', 'Deadstock'
    EQUIPMENT = 'EQUIPMENT', 'Equipment'


class ItemStatus(models.TextChoices):
    IN_STOCK = 'IN_STOCK', 'In Stock'
    ISSUED = 'ISSUED', 'Issued'
    UNDER_REPAIR = 'UNDER_REPAIR', 'Under Repair'
    DISPOSED = 'DISPOSED', 'Disposed'
    LOST = 'LOST', 'Lost'
    
class IssueStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    ISSUED = 'ISSUED', 'Issued'
    RECEIVED = 'RECEIVED', 'Received'
    CANCELLED = 'CANCELLED', 'Cancelled'

    


class StockEntryType(models.TextChoices):
    RECIEVED = 'RECIEVED', 'Recieved'
    ISSUE = 'ISSUE', 'Issue'
    ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'


# === Category ===
class Category(models.Model):
    name = models.CharField(max_length=255)
    depreciation_rate = models.DecimalField(max_digits=6, decimal_places=3, default=0)

    def __str__(self):
        return self.name


# === Item ===
class Item(models.Model):
    name = models.CharField(max_length=255)
    specifications = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=255)
    responsible_person = models.CharField(max_length=255, blank=True, null=True)
    parent_location = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sublocations'
    )

    @property
    def is_department(self):
        return self.parent_location is None

    def __str__(self):
        if self.parent_location:
            return f"{self.name} ({self.parent_location.name})"
        return self.name



# === Store ===
class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='stores')

    def __str__(self):
        return self.name


# === StockRegister ===
class StockRegister(models.Model):
    register_type = models.CharField(max_length=20, choices=RegisterType.choices)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stock_registers')
    
    def __str__(self):
        return f"{self.register_type} Register - {self.store.name}"

class Contractor(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
class Contract(models.Model):
    contract_no = models.CharField(max_length=128, unique=True)
    contract_date = models.DateField()
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE)

    def __str__(self):
        return f"Contract {self.contract_no} - {self.contractor.name}"
class Indenter(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class Indent(models.Model):
    indent_no = models.CharField(max_length=128, unique=True)
    indenter = models.ForeignKey(Indenter, on_delete=models.CASCADE)

    def __str__(self):
        return f"Indent {self.indent_no} - {self.indenter.name}"
class Consignee(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
# === InspectionCertificate (header) ===
class InspectionCertificate(models.Model):
    issued_on = models.DateField(blank=True, null=True)
    issued_to = models.CharField(max_length=255, blank=True, null=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    indent = models.ForeignKey(Indent, on_delete=models.CASCADE)
    consignee = models.ForeignKey(Consignee, on_delete=models.CASCADE)
    department = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='inspection_certificates')
    date_of_delivery = models.DateField(blank=True, null=True)
    delivery_status = models.CharField(max_length=16, blank=True, null=True)
    #date_of_inspection = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inspection {self.id} - {self.contract.contract_no or 'No Contract'}"


# === InspectionItem (lines) ===
class InspectionItem(models.Model):
    inspection = models.ForeignKey(InspectionCertificate, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, related_name='inspection_items')
    acct_unit = models.CharField(max_length=64, blank=True, null=True)
    tendered_quantity = models.IntegerField(default=0)
    rejected_quantity = models.IntegerField(default=0)
    accepted_quantity = models.IntegerField(default=0)
    rejected_reason = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    stock_register = models.ForeignKey(StockRegister, on_delete=models.SET_NULL, null=True, related_name='inspection_items')
    created_at = models.DateTimeField(auto_now_add=True)
    generate_qr_code = models.BooleanField(default=False)

    def __str__(self):
        return f"InspectionItem {self.id} - {self.item.name if self.item else 'Unknown Item'}"


# === ItemInstance (each physical piece) ===
class ItemInstance(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='instances')
    inspection = models.ForeignKey(InspectionCertificate, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_instances')
    inspection_item = models.ForeignKey(InspectionItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_instances')
    current_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_instances')
    current_store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_instances')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.IN_STOCK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name} [{self.qr_code or 'No QR'}]"


# === IssueTransaction (issue / transfer document) ===
class IssueRequisiton(models.Model):
    requisiton_no = models.CharField(max_length=64)
    issue_date = models.DateField(blank=True, null=True)
    purpose = models.CharField(max_length=255,null=True)
    department = models.ForeignKey(Location,on_delete=models.CASCADE)
    issued_by = models.CharField(max_length=255, blank=True, null=True)
    received_by = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=IssueStatus.choices,default=IssueStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Issue {self.issue_no or self.id} ({self.status})"


# === IssueItem (lines in an issue) ===
class IssueItem(models.Model):
    issue = models.ForeignKey(IssueRequisiton, on_delete=models.CASCADE, related_name='items')
    item_instance = models.ForeignKey(ItemInstance, on_delete=models.SET_NULL, null=True, related_name='issue_items')
    acct_unit = models.CharField(max_length=255,null=True)
    quantity_required = models.IntegerField(default=1)
    quantity_recieved = models.IntegerField(default=1)
    major_head = models.CharField(max_length=255,null=True)
    store_post_reference = models.CharField(max_length=300,null=True)

    def __str__(self):
        return f"IssueItem {self.id} - {self.item_instance or 'Unassigned'}"


# === StockEntries (movement journal) ===
class StockEntry(models.Model):
    stock_register = models.ForeignKey(StockRegister, on_delete=models.CASCADE, related_name='entries')
    date_of_entry = models.DateField(auto_now_add=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='stock_entries')
    inspection = models.ForeignKey(InspectionCertificate, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_entries')
    #issue = models.ForeignKey(Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_entries')
    voucher_no = models.CharField(max_length=128, blank=True, null=True)
    entry_type = models.CharField(max_length=20, choices=StockEntryType.choices)
    quantity_in = models.IntegerField(default=0)
    quantity_out = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    balance = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entry_type} - Register {self.stock_register_id}"
