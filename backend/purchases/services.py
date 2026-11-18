import uuid
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from config.utils import ZERO, money
from inventory.models import MovementType
from inventory.services import apply_stock_change
from products.models import Product

from .models import Purchase, PurchaseItem


@transaction.atomic
def create_purchase(*, supplier, purchase_date, note, items, user):
    """
    একটি purchase তৈরি করে এবং প্রতিটি product-এর stock বাড়ায়।
    পুরোটাই একটি transaction: কোনো ধাপে সমস্যা হলে কিছুই save হয় না।
    মোট দাম server-এ হিসাব হয়; client-এর পাঠানো কোনো total ব্যবহার করা হয় না।
    product-এর purchase_price আপডেট হয় weighted average cost অনুযায়ী (profit হিসাবের জন্য)।
    """
    purchase = Purchase.objects.create(
        reference_no=f"TMP-{uuid.uuid4().hex}",
        supplier=supplier,
        purchase_date=purchase_date,
        note=note,
        total_amount=ZERO,
        created_by=user,
    )
    # unique reference: তারিখ + primary key
    purchase.reference_no = f"PUR-{purchase.purchase_date:%Y%m%d}-{purchase.pk:06d}"

    total = ZERO
    for item in items:
        product = Product.objects.get(pk=item["product"].pk)
        if not product.is_active:
            raise ValidationError({"items": [f"Product '{product.name}' is inactive and cannot be purchased."]})

        quantity = item["quantity"]
        unit_price = money(item["unit_price"])
        line_total = money(unit_price * quantity)

        PurchaseItem.objects.create(
            purchase=purchase, product=product, quantity=quantity, unit_price=unit_price, line_total=line_total
        )

        # Weighted average cost
        old_stock = product.stock_quantity
        new_cost = (product.purchase_price * old_stock + unit_price * quantity) / Decimal(old_stock + quantity)
        product.purchase_price = money(new_cost)
        product.save(update_fields=["purchase_price", "updated_at"])

        apply_stock_change(
            product=product,
            quantity_change=quantity,
            movement_type=MovementType.PURCHASE,
            user=user,
            reference=purchase.reference_no,
            note=f"Purchase from {supplier.name}",
        )
        total += line_total

    purchase.total_amount = total
    purchase.save(update_fields=["reference_no", "total_amount"])
    return purchase
