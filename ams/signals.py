from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InspectionItem, StockEntry, StockEntryType,ItemInstance,ItemStatus
from .helper import generate_item_qr_code

@receiver(post_save, sender=InspectionItem)
def create_stock_entry_on_inspection_item(sender, instance, created, **kwargs):
    """
    When a new InspectionItem is created, automatically create a StockEntry
    in the relevant StockRegister to reflect received stock.
    """
    if not created:
        return  # Only act on creation, not updates

    # Skip if no stock register assigned
    if not instance.stock_register:
        return

    # Skip if accepted_quantity is 0 (nothing to record)
    if instance.accepted_quantity <= 0:
        return

    # Create the StockEntry record
    StockEntry.objects.create(
        date_of_entry=instance.created_at.date(),
        voucher_no=f'{instance.inspection.contract.contract_no}, {instance.inspection.contract.contract_date}',
        stock_register=instance.stock_register,
        item=instance.item,
        inspection=instance.inspection,
        entry_type=StockEntryType.RECIEVED,  # enum from your model
        quantity_in=instance.accepted_quantity,
        unit_price=instance.unit_price,
        remarks=f"Auto entry for InspectionItem {instance.id}",
        
    )
    if instance.generate_qr_code is False:
        return
    
    for i in range(instance.accepted_quantity):
        qr_code = generate_item_qr_code(
            instance.inspection.id, 
            instance.stock_register.store.name, 
            instance.stock_register.register_type,
            instance.stock_register.store.location.name,
            ItemStatus.IN_STOCK
        )
        ItemInstance.objects.create(
            item = instance.item,
            inspection = instance.inspection,
            inspection_item = instance,
            current_location = instance.stock_register.store.location,
            current_store = instance.stock_register.store,
            qr_code = qr_code,
            status = ItemStatus.IN_STOCK,
            created_at = instance.created_at,
            updated_at = instance.created_at,
        )
