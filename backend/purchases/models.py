from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Purchase(models.Model):
    reference_no = models.CharField(max_length=40, unique=True, editable=False)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchases")
    purchase_date = models.DateField(default=timezone.localdate)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchase_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="purchase_total_gte_0"),
        ]

    def __str__(self):
        return self.reference_no


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="purchase_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="purchaseitem_quantity_gt_0"),
            models.CheckConstraint(condition=Q(unit_price__gt=0), name="purchaseitem_unit_price_gt_0"),
        ]

    def __str__(self):
        return f"{self.product_id} x {self.quantity}"
