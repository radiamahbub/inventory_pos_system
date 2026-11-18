"""Customer balance, collections and ledger.

Balance = what the customer still owes the shop = sum of the `due` of all their sales.
(See sales.models.due_expression: grand total - paid at sale - collected later - unpaid part cancelled by returns.)
Collections are allocated to the oldest unpaid invoices first, so every invoice shows its own status.
"""

import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from config.utils import ZERO, money
from sales.models import Sale, SaleReturn, due_expression

from .models import Customer, CustomerPayment

DEC = DecimalField(max_digits=16, decimal_places=2)


def with_balance(queryset):
    """Annotate customers with `balance` (one query, no N+1)."""
    per_customer = (
        Sale.objects.filter(customer=OuterRef("pk"))
        .order_by()
        .values("customer")
        .annotate(total=Sum(due_expression()))
        .values("total")[:1]
    )
    return queryset.annotate(
        balance=Coalesce(Subquery(per_customer, output_field=DEC), Value(Decimal("0.00")), output_field=DEC)
    )


def customer_balance(customer):
    agg = Sale.objects.filter(customer=customer).aggregate(
        total=Coalesce(Sum(due_expression()), Value(Decimal("0.00")), output_field=DEC)
    )
    return money(agg["total"])


@transaction.atomic
def collect_payment(*, customer, amount, payment_method, note, user):
    amount = money(amount)
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    balance = customer_balance(customer)
    if balance <= 0:
        raise ValidationError({"amount": "This customer has no outstanding due."})
    if amount > balance:
        raise ValidationError({"amount": f"Amount is more than the outstanding due ({balance})."})

    remaining = amount
    for sale in Sale.objects.select_for_update().filter(customer=customer).order_by("sale_date", "id"):
        outstanding = sale.due_amount
        if outstanding <= 0:
            continue
        allocated = min(outstanding, remaining)
        Sale.objects.filter(pk=sale.pk).update(collected_amount=F("collected_amount") + allocated)
        remaining -= allocated
        if remaining <= 0:
            break

    payment = CustomerPayment.objects.create(
        customer=customer,
        reference=f"TMP-{uuid.uuid4().hex}",
        amount=amount,
        payment_method=payment_method,
        note=note,
        created_by=user,
    )
    local_date = timezone.localtime(payment.payment_date)
    payment.reference = f"PAY-{local_date:%Y%m%d}-{payment.pk:06d}"
    payment.save(update_fields=["reference"])
    return payment


def build_ledger(customer):
    """Chronological statement with a running balance (positive = customer owes the shop)."""
    events = []  # (datetime, order, entry dict)
    for sale in Sale.objects.filter(customer=customer):
        events.append((sale.sale_date, 0, sale.pk, {
            "type": "sale", "reference": sale.invoice_number, "sale_id": sale.pk,
            "description": "Sale", "debit": sale.grand_total, "credit": ZERO,
        }))
        if sale.paid_amount > 0:
            events.append((sale.sale_date, 1, sale.pk, {
                "type": "payment_at_sale", "reference": sale.invoice_number, "sale_id": sale.pk,
                "description": f"Paid at sale ({sale.get_payment_method_display()})",
                "debit": ZERO, "credit": sale.paid_amount,
            }))
    for ret in SaleReturn.objects.filter(sale__customer=customer).select_related("sale"):
        note = f"Return against {ret.sale.invoice_number}"
        if ret.refund_amount > 0:
            note += f" - {ret.refund_amount:,.2f} refunded"
        events.append((ret.return_date, 2, ret.pk, {
            "type": "return", "reference": ret.return_number, "sale_id": ret.sale_id,
            "description": note, "debit": ZERO, "credit": ret.due_adjusted,
        }))
    for pay in CustomerPayment.objects.filter(customer=customer):
        events.append((pay.payment_date, 3, pay.pk, {
            "type": "collection", "reference": pay.reference, "sale_id": None,
            "description": f"Due collected ({pay.get_payment_method_display()})" + (f" - {pay.note}" if pay.note else ""),
            "debit": ZERO, "credit": pay.amount,
        }))

    events.sort(key=lambda e: (e[0], e[1], e[2]))
    balance = ZERO
    entries = []
    for when, _order, _pk, entry in events:
        balance += entry["debit"] - entry["credit"]
        entries.append({"date": when, **entry, "balance": balance})
    return entries
