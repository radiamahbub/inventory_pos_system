from django.db import models
from django.db.models import F, Q


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey("categories.Category", on_delete=models.PROTECT, related_name="products")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    # stock সরাসরি edit করা যায় না; শুধু purchase / sale / inventory adjustment দিয়ে বদলায়
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(purchase_price__gte=0), name="product_purchase_price_gte_0"),
            models.CheckConstraint(condition=Q(selling_price__gte=0), name="product_selling_price_gte_0"),
        ]

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level

    def __str__(self):
        return f"{self.name} ({self.sku})"


def low_stock_filter():
    """stock <= minimum level"""
    return Q(stock_quantity__lte=F("min_stock_level"))
