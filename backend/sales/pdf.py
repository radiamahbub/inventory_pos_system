"""PDF invoice (A4) and 80 mm thermal receipt, generated with ReportLab.

Fonts: the built-in Helvetica cannot draw Bengali letters or the ৳ sign, so by default amounts are printed
as "Tk 1,250.00". To print Bengali product names / ৳, point PDF_FONT_REGULAR (and optionally PDF_FONT_BOLD)
to a Unicode .ttf file that contains Bengali glyphs (for example Noto Sans Bengali) in the environment.
"""

import os
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONTS = None


def _fonts():
    """(regular, bold, currency prefix). Registers the optional Unicode font once."""
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    regular, bold, prefix = "Helvetica", "Helvetica-Bold", "Tk "
    reg_path = getattr(settings, "PDF_FONT_REGULAR", "")
    if reg_path and os.path.exists(reg_path):
        try:
            pdfmetrics.registerFont(TTFont("ShopFont", reg_path))
            regular = bold = "ShopFont"
            bold_path = getattr(settings, "PDF_FONT_BOLD", "")
            if bold_path and os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("ShopFont-Bold", bold_path))
                bold = "ShopFont-Bold"
            prefix = "৳ "
        except Exception:  # bad font file -> fall back to Helvetica
            regular, bold, prefix = "Helvetica", "Helvetica-Bold", "Tk "
    _FONTS = (regular, bold, prefix)
    return _FONTS


def _money(value):
    return f"{_fonts()[2]}{value:,.2f}"


def _when(dt):
    return timezone.localtime(dt).strftime("%d %b %Y, %H:%M")


def _lines(sale):
    """Rows to show below the items: label, amount (only the relevant ones)."""
    rows = [("Subtotal", _money(sale.subtotal))]
    if sale.discount > 0:
        rows.append(("Discount", "- " + _money(sale.discount)))
    rows.append(("Total", _money(sale.grand_total)))
    if sale.returned_total > 0:
        rows.append(("Returned", "- " + _money(sale.returned_total)))
        rows.append(("Net total", _money(sale.net_total)))
    rows.append(("Paid", _money(sale.total_paid - sale.refunded_total)))
    if sale.due_amount > 0:
        rows.append(("DUE", _money(sale.due_amount)))
    return rows


# --------------------------------------------------------------------------------------- A4 invoice
def build_invoice_pdf(sale, items, shop):
    regular, bold, _ = _fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Invoice {sale.invoice_number}",
    )
    small = ParagraphStyle("small", fontName=regular, fontSize=9, leading=12, textColor=colors.HexColor("#475569"))
    normal = ParagraphStyle("normal", fontName=regular, fontSize=10, leading=13)
    title = ParagraphStyle("title", fontName=bold, fontSize=18, leading=22)
    right = ParagraphStyle("right", parent=normal, alignment=2)

    shop_lines = [escape(x) for x in (shop["address"], shop["phone"]) if x]
    head = Table(
        [[
            [Paragraph(escape(shop["name"]), title)] + [Paragraph(x, small) for x in shop_lines],
            [Paragraph("INVOICE", ParagraphStyle("inv", parent=title, alignment=2, fontSize=14)),
             Paragraph(escape(sale.invoice_number), right)],
        ]],
        colWidths=[105 * mm, 69 * mm],
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    customer = sale.customer.name if sale.customer else "Walk-in customer"
    if sale.customer and sale.customer.phone:
        customer += f" ({sale.customer.phone})"
    meta = Table(
        [
            [Paragraph("<b>Billed to</b>", small), Paragraph("<b>Date</b>", small), Paragraph("<b>Payment / Cashier</b>", small)],
            [Paragraph(escape(customer), normal), Paragraph(_when(sale.sale_date), normal),
             Paragraph(f"{escape(sale.get_payment_method_display())} / {escape(sale.created_by.username)}", normal)],
        ],
        colWidths=[70 * mm, 45 * mm, 59 * mm],
    )
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))

    data = [["#", "Item", "Qty", "Unit price", "Amount"]]
    for i, it in enumerate(items, start=1):
        name = Paragraph(f"{escape(it.product.name)}<br/><font size=8 color='#64748b'>{escape(it.product.sku)}</font>", normal)
        qty = str(it.quantity) + (f" (ret. {it.returned_quantity})" if it.returned_quantity else "")
        data.append([str(i), name, qty, _money(it.unit_price), _money(it.line_total)])
    table = Table(data, colWidths=[10 * mm, 80 * mm, 26 * mm, 29 * mm, 29 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), bold), ("FONTNAME", (0, 1), (-1, -1), regular),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#cbd5e1")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    totals_rows = _lines(sale)
    totals = Table(totals_rows, colWidths=[40 * mm, 40 * mm], hAlign="RIGHT")
    last_total = [i for i, r in enumerate(totals_rows) if r[0] in ("Total", "Net total")][-1]
    style = [("FONTNAME", (0, 0), (-1, -1), regular), ("FONTSIZE", (0, 0), (-1, -1), 10), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
             ("FONTNAME", (0, last_total), (-1, last_total), bold), ("LINEABOVE", (0, last_total), (-1, last_total), 0.8, colors.HexColor("#94a3b8"))]
    if totals_rows[-1][0] == "DUE":
        style += [("FONTNAME", (0, -1), (-1, -1), bold), ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#b91c1c"))]
    totals.setStyle(TableStyle(style))

    story = [head, Spacer(1, 8 * mm), meta, Spacer(1, 6 * mm), table, Spacer(1, 5 * mm), totals]
    if sale.note:
        story += [Spacer(1, 5 * mm), Paragraph(f"<b>Note:</b> {escape(sale.note)}", normal)]
    story += [Spacer(1, 12 * mm), Paragraph(escape(shop["footer"]), ParagraphStyle("foot", parent=small, alignment=1))]
    doc.build(story)
    return buf.getvalue()


# --------------------------------------------------------------------------------------- 80 mm receipt
def build_receipt_pdf(sale, items, shop):
    """Narrow thermal-printer receipt; the page height is calculated from the content."""
    regular, bold, _ = _fonts()
    width = 80 * mm
    margin = 4 * mm
    usable = width - 2 * margin

    ops = []  # ("text", str, font, size, align) | ("pair", left, right, font, size) | ("rule",) | ("gap", pts)

    def text(value, font=regular, size=8, align="l"):
        for line in simpleSplit(value, font, size, usable) or [""]:
            ops.append(("text", line, font, size, align))

    def pair(left, right, font=regular, size=8):
        ops.append(("pair", left, right, font, size))

    text(shop["name"], bold, 12, "c")
    if shop["address"]:
        text(shop["address"], regular, 7.5, "c")
    if shop["phone"]:
        text(shop["phone"], regular, 7.5, "c")
    ops.append(("gap", 3))
    ops.append(("rule",))
    text(f"Invoice: {sale.invoice_number}", bold, 8)
    text(_when(sale.sale_date), regular, 8)
    text(f"Customer: {sale.customer.name if sale.customer else 'Walk-in'}", regular, 8)
    text(f"Cashier: {sale.created_by.username}", regular, 8)
    ops.append(("rule",))
    for it in items:
        text(it.product.name, bold, 8)
        qty = f"{it.quantity} x {_money(it.unit_price)}"
        if it.returned_quantity:
            qty += f"  (returned {it.returned_quantity})"
        pair(qty, _money(it.line_total))
    ops.append(("rule",))
    for label, amount in _lines(sale):
        strong = label in ("Total", "Net total", "DUE")
        pair(label, amount, bold if strong else regular, 10 if label in ("Total", "DUE") else 8)
    ops.append(("rule",))
    text(f"Payment: {sale.get_payment_method_display()}", regular, 8)
    if sale.note:
        text(f"Note: {sale.note}", regular, 7.5)
    ops.append(("gap", 4))
    text(shop["footer"], regular, 8, "c")

    def height_of(op):
        kind = op[0]
        if kind == "text":
            return op[3] * 1.3
        if kind == "pair":
            return op[4] * 1.4
        if kind == "rule":
            return 7
        return op[1]

    total_height = 2 * margin + sum(height_of(o) for o in ops)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, total_height))
    c.setTitle(f"Receipt {sale.invoice_number}")
    y = total_height - margin
    for op in ops:
        h = height_of(op)
        y -= h
        base = y + h * 0.25
        if op[0] == "text":
            _, value, font, size, align = op
            c.setFont(font, size)
            if align == "c":
                c.drawCentredString(width / 2, base, value)
            elif align == "r":
                c.drawRightString(width - margin, base, value)
            else:
                c.drawString(margin, base, value)
        elif op[0] == "pair":
            _, left, right, font, size = op
            c.setFont(font, size)
            c.drawString(margin, base, left)
            c.drawRightString(width - margin, base, right)
        elif op[0] == "rule":
            c.setDash(1, 2)
            c.line(margin, y + h / 2, width - margin, y + h / 2)
            c.setDash()
    c.showPage()
    c.save()
    return buf.getvalue()
