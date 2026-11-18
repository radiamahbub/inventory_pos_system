from django.conf import settings
from django.db import models
from django.db.models import F, Q


class MovementType(models.TextChoices):
    OPENING = "opening", "Opening stock"
    PURCHASE = "purchase", "Purchase (stock in)"
    SALE = "sale", "Sale (stock out)"
    RETURN = "return", "Sales return (stock in)"
    ADJUSTMENT = "adjustment", "Admin adjustment"


class StockMovement(models.Model):
    """প্রতিটি stock পরিবর্তনের স্থায়ী রেকর্ড (কখনো edit/delete হয় না)।"""

    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="stock_movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.IntegerField(help_text="Positive = stock in, negative = stock out")
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    reference = models.CharField(max_length=50, blank=True, help_text="Invoice / purchase reference number")
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(quantity_change=0), name="stockmovement_change_not_zero"),
            models.CheckConstraint(
                condition=Q(quantity_after=F("quantity_before") + F("quantity_change")),
                name="stockmovement_after_equals_before_plus_change",
            ),
        ]

    def __str__(self):
        return f"{self.product_id} {self.movement_type} {self.quantity_change:+d}"
