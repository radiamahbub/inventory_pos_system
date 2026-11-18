import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from config.utils import ZERO, money
from inventory.models import MovementType
from inventory.services import apply_stock_change
from products.models import Product

from .models import ReturnStatus, Sale, SaleItem, SaleReturn, SaleReturnItem


@transaction.atomic
def create_sale(*, customer, items, discount, payment_method, note, user, paid_amount=None):
    """
    Creates a sale and decreases stock.
    - prices come from the product (client-sent prices are never trusted)
    - subtotal / grand total are calculated on the server
    - cannot sell more than the stock
    - `paid_amount` (optional): money received now. Default = full payment. A lower amount makes it a
      due (credit) sale, which needs a customer so the balance can be tracked in the ledger.
    - any failure rolls the whole transaction back
    """
    discount = money(discount)

    lines = []
    subtotal = ZERO
    problems = []
    for item in items:
        product = Product.objects.get(pk=item["product"].pk)
        quantity = item["quantity"]
        if not product.is_active:
            problems.append(f"Product '{product.name}' is inactive and cannot be sold.")
            continue
        if quantity > product.stock_quantity:
            problems.append(
                f"Insufficient stock for '{product.name}': available {product.stock_quantity}, requested {quantity}."
            )
            continue
        line_total = money(product.selling_price * quantity)
        subtotal += line_total
        lines.append((product, quantity, product.selling_price, product.purchase_price, line_total))

    if problems:
        raise ValidationError({"items": problems})
    if discount > subtotal:
        raise ValidationError({"discount": "Discount cannot be greater than the subtotal."})

    grand_total = subtotal - discount
    paid = grand_total if paid_amount is None else money(paid_amount)
    if paid < 0:
        raise ValidationError({"paid_amount": "Paid amount cannot be negative."})
    if paid > grand_total:
        raise ValidationError({"paid_amount": "Paid amount cannot be greater than the total."})
    if paid < grand_total and customer is None:
        raise ValidationError({"customer": "Select a customer for a sale with a due balance."})

    sale = Sale.objects.create(
        invoice_number=f"TMP-{uuid.uuid4().hex}",
        customer=customer,
        subtotal=subtotal,
        discount=discount,
        grand_total=grand_total,
        paid_amount=paid,
        payment_method=payment_method,
        note=note,
        created_by=user,
    )
    local_date = timezone.localtime(sale.sale_date)
    sale.invoice_number = f"INV-{local_date:%Y%m%d}-{sale.pk:06d}"
    sale.save(update_fields=["invoice_number"])

    for product, quantity, unit_price, unit_cost, line_total in lines:
        SaleItem.objects.create(
            sale=sale, product=product, quantity=quantity,
            unit_price=unit_price, unit_cost=unit_cost, line_total=line_total,
        )
        apply_stock_change(
            product=product,
            quantity_change=-quantity,
            movement_type=MovementType.SALE,
            user=user,
            reference=sale.invoice_number,
            note="Sale",
        )
    return sale


@transaction.atomic
def create_sale_return(*, sale, items, reason, refund_method, user):
    """
    Returns goods from one invoice (full or partial, can be repeated).

    Money rules
    - The invoice discount is spread over the items, so a returned item is worth
      unit_price * grand_total / subtotal (never more than the customer really paid for it).
    - kept   = grand_total - returned value after this return
    - paid   = paid at sale + collected later
    - If the customer paid more than the goods they keep, the difference is REFUNDED (cash/card/mobile).
    - Anything not refunded simply cancels part of the customer's unpaid balance (`due_adjusted`).
    - Stock goes back in and a `return` stock movement is recorded.
    """
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    sale_items = {si.pk: si for si in SaleItem.objects.select_for_update().filter(sale=sale).select_related("product")}

    seen = set()
    problems = []
    lines = []
    for entry in items:
        sale_item = sale_items.get(entry["sale_item"].pk)
        quantity = entry["quantity"]
        if sale_item is None:
            problems.append(f"Item #{entry['sale_item'].pk} does not belong to invoice {sale.invoice_number}.")
            continue
        if sale_item.pk in seen:
            problems.append(f"'{sale_item.product.name}' appears more than once. Combine the quantities.")
            continue
        seen.add(sale_item.pk)
        remaining = sale_item.quantity - sale_item.returned_quantity
        if quantity > remaining:
            problems.append(
                f"Cannot return {quantity} of '{sale_item.product.name}': only {remaining} left to return."
            )
            continue
        if sale.subtotal > 0:
            unit_value = money(sale_item.unit_price * sale.grand_total / sale.subtotal)
            line_total = money(sale_item.unit_price * quantity * sale.grand_total / sale.subtotal)
        else:
            unit_value, line_total = ZERO, ZERO
        lines.append({"sale_item": sale_item, "quantity": quantity, "unit_value": unit_value, "line_total": line_total})

    if problems:
        raise ValidationError({"items": problems})

    total = sum((l["line_total"] for l in lines), ZERO)
    available = sale.grand_total - sale.returned_total
    if total > available:
        # rounding guard: never return more value than the invoice has left
        excess = total - available
        biggest = max(lines, key=lambda l: l["line_total"])
        biggest["line_total"] -= excess
        total = available

    kept = sale.grand_total - (sale.returned_total + total)
    refundable_cumulative = max(ZERO, sale.total_paid - kept)
    refund = min(total, max(ZERO, refundable_cumulative - sale.refunded_total))
    due_adjusted = total - refund
    method = (refund_method or sale.payment_method) if refund > 0 else ""

    sale_return = SaleReturn.objects.create(
        return_number=f"TMP-{uuid.uuid4().hex}",
        sale=sale,
        total_amount=total,
        refund_amount=refund,
        due_adjusted=due_adjusted,
        refund_method=method,
        reason=reason,
        created_by=user,
    )
    local_date = timezone.localtime(sale_return.return_date)
    sale_return.return_number = f"RET-{local_date:%Y%m%d}-{sale_return.pk:06d}"
    sale_return.save(update_fields=["return_number"])

    for line in lines:
        sale_item = line["sale_item"]
        SaleReturnItem.objects.create(
            sale_return=sale_return,
            sale_item=sale_item,
            product=sale_item.product,
            quantity=line["quantity"],
            unit_price=line["unit_value"],
            unit_cost=sale_item.unit_cost,
            line_total=line["line_total"],
        )
        SaleItem.objects.filter(pk=sale_item.pk).update(returned_quantity=F("returned_quantity") + line["quantity"])
        sale_item.returned_quantity += line["quantity"]
        apply_stock_change(
            product=sale_item.product,
            quantity_change=line["quantity"],
            movement_type=MovementType.RETURN,
            user=user,
            reference=sale_return.return_number,
            note=f"Return of {sale.invoice_number}",
        )

    fully_returned = all(si.returned_quantity >= si.quantity for si in sale_items.values())
    Sale.objects.filter(pk=sale.pk).update(
        returned_total=F("returned_total") + total,
        refunded_total=F("refunded_total") + refund,
        return_status=ReturnStatus.FULL if fully_returned else ReturnStatus.PARTIAL,
    )
    return sale_return
