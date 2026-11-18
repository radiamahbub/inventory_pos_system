"""
Stock পরিবর্তনের একমাত্র জায়গা।
Purchase, Sale এবং Admin adjustment — সবাই এই function ব্যবহার করে,
ফলে stock কখনো negative হয় না এবং প্রতিটি পরিবর্তনের রেকর্ড থাকে।
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from products.models import Product

from .models import StockMovement


def apply_stock_change(*, product, quantity_change, movement_type, user=None, reference="", note=""):
    if quantity_change == 0:
        raise ValidationError({"quantity_change": "Quantity change cannot be zero."})

    with transaction.atomic():
        qs = Product.objects.filter(pk=product.pk)
        if quantity_change < 0:
            # শর্তসহ atomic update: stock যথেষ্ট না থাকলে কোনো row বদলায় না
            updated = qs.filter(stock_quantity__gte=-quantity_change).update(
                stock_quantity=F("stock_quantity") + quantity_change, updated_at=timezone.now()
            )
            if not updated:
                available = qs.values_list("stock_quantity", flat=True).first()
                raise ValidationError(
                    {
                        "detail": f"Insufficient stock for '{product.name}': "
                        f"available {available}, requested {-quantity_change}."
                    }
                )
        else:
            qs.update(stock_quantity=F("stock_quantity") + quantity_change, updated_at=timezone.now())

        product.refresh_from_db(fields=["stock_quantity", "updated_at"])
        after = product.stock_quantity
        return StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity_change=quantity_change,
            quantity_before=after - quantity_change,
            quantity_after=after,
            reference=reference,
            note=note,
            created_by=user,
        )
