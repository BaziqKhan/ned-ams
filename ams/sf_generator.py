from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

class StockFormGenerator:
    def __init__(self,register_name = None,data={},stock_data={}):
        self.output_filename = "Stock_Form.pdf"
        self.width, self.height = (800, 1008)
        self.styles = getSampleStyleSheet()
        self.BOTTOM_MARGIN = 0  # bottom margin to stop drawing before page end
        
        self.data = data
        self.stock_data = stock_data
        
        
        # create the PDF canvas
        self.buffer = BytesIO()
        c = canvas.Canvas(self.buffer, pagesize=(800, 1008))
        c.setFont("Helvetica-Bold", 25)
        c.drawCentredString(self.width/2, self.height/2, f"{register_name}")
        c.showPage()
        self.page_header(c)
        self.draw_item_table(c)
        c.save()
        
         # Reset buffer position to beginning for reading
        self.buffer.seek(0)
        
    def get_pdf(self):
        """Return the PDF buffer"""
        return self.buffer
    # ----------------------------
    # Header for each page
    # ----------------------------
    def page_header(self, c):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.width - 768, self.height - 20, "F/SOP/SD 01/52/01")
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(
            self.width / 2, self.height - 40,
            "NED UNIVERSITY OF ENGINEERING AND TECHNOLOGY, KARACHI"
        )
        c.setFont("Times-Italic", 14)
        c.drawCentredString(
            self.width / 2, self.height - 60,
            "DESCRIPTION OF ITEM ________________________________________________________"
        )
        c.drawString(
            self.width - 500, self.height - 60,
            f"{self.data['description_of_item']}"
        )

        c.setLineWidth(1)
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.lightblue)
        c.rect(x=self.width - 748, y=self.height - 67, width=56.8, height=20, fill=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(self.width - 718, self.height - 60, "/250")
        # c.drawString(self.width - 700, self.height - 60, f"{self.data['page_no']}")

    # ----------------------------
    # Main table with auto pagination
    # ----------------------------
    def draw_item_table(self, c):
        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        # Header paragraph style
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            alignment=1,  # center
            leading=10,
            wordWrap="LTR",
        )

        # Define table headers
        header = [
            [
                Paragraph("Date<br/>Received/<br/>Issued", header_style),
                Paragraph(
                    "Voucher/<br/>Cash Memo/<br/>Requisition/<br/>Purchase Order No.",
                    header_style,
                ),
                Paragraph("PARTICULARS", header_style),
                Paragraph("Accounting / Measuring Unit", header_style),
                Paragraph("Unit Price", header_style),
                Paragraph("Total Cost<br/>(with Taxes)", header_style),
                Paragraph("QUANTITY", header_style),
                "", "",
                Paragraph("Remarks /<br/>Initials of Authorized Persons", header_style),
            ],
            [
                "", "", "", "", "", "",
                Paragraph("Received", header_style),
                Paragraph("Issued", header_style),
                Paragraph("Balance", header_style),
                "",
            ],
        ]

        # Generate some example data
        rows = []
        for i in range(len(self.stock_data['date_of_entry'])):
            rows.append([
                self.stock_data['date_of_entry'][i],
                Paragraph(
                    self.stock_data['voucher_no'][i],
                    normal,
                ),
                Paragraph(
                    self.stock_data['particulars'][i],
                    normal,
                ),
                self.stock_data['acct_unit'][i],
                self.stock_data['unit_price'][i],
                self.stock_data['total_cost'][i],
                self.stock_data['recieved_quantity'][i],
                self.stock_data['issued_quantity'][i],
                self.stock_data['balance'][i],
                Paragraph(
                    self.stock_data['remarks'][i],
                    normal,
                ),
            ])

        # Define table column widths
        col_widths = [
            0.8 * inch,
            1.3 * inch,
            2.3 * inch,
            0.9 * inch,
            0.95 * inch,
            0.95 * inch,
            0.8 * inch,
            0.8 * inch,
            0.8 * inch,
            1.5 * inch,
        ]

        # Table style
        table_style = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("ALIGN", (0, 2), (-1, -1), "CENTER"),
            ("SPAN", (0, 0), (0, 1)),
            ("SPAN", (1, 0), (1, 1)),
            ("SPAN", (2, 0), (2, 1)),
            ("SPAN", (3, 0), (3, 1)),
            ("SPAN", (4, 0), (4, 1)),
            ("SPAN", (5, 0), (5, 1)),
            ("SPAN", (6, 0), (8, 0)),
            ("SPAN", (9, 0), (9, 1)),
            ("BACKGROUND", (0, 0), (-1, 1), colors.white),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])

        # Pagination setup
        x_margin = 1
        y_start = self.height - 80
        current_y = y_start

        chunk = header[:]  # start with header
        for row in rows:
            temp = Table(chunk + [row], colWidths=col_widths)
            temp.setStyle(table_style)
            _, h = temp.wrap(self.width, self.height)

            # Check if next row fits on current page
            if current_y - h < self.BOTTOM_MARGIN:
                # Draw current chunk
                temp = Table(chunk, colWidths=col_widths)
                temp.setStyle(table_style)
                _, h_chunk = temp.wrap(self.width, self.height)
                temp.drawOn(c, x_margin, current_y - h_chunk)

                # New page
                c.showPage()
                self.page_header(c)
                current_y = y_start
                chunk = header[:] + [row]  # start new chunk with header + current row
            else:
                chunk.append(row)

        # Draw any remaining rows
        if chunk:
            temp = Table(chunk, colWidths=col_widths)
            temp.setStyle(table_style)
            _, h_chunk = temp.wrap(self.width, self.height)
            temp.drawOn(c, x_margin, current_y - h_chunk)


# Run the generator
if __name__ == "__main__":
    StockFormGenerator()
