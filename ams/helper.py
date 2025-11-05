import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generate_item_qr_code(inspection_id, store_name, register_type, location_name, status):
    """
    Generate a QR code image for an item based on its inspection, store, location, and status.
    Returns a Django ContentFile suitable for saving to an ImageField.
    """

    # Build the text / data to encode
    qr_data = (
        f"Inspection ID: {inspection_id}\n"
        f"Store: {store_name} ({register_type})\n"
        f"Location: {location_name}\n"
        f"Status: {status}"
    )

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,  # controls size; 1 = 21x21
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create an image from the QR code
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to in-memory file
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Return a ContentFile to attach to Django ImageField
    filename = f"qr_inspection_{inspection_id}.png"
    return ContentFile(buffer.getvalue(), name=filename)
