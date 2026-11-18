import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from products.models import Product
from suppliers.models import Supplier

from .models import Purchase, PurchaseItem


class PurchaseItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class PurchaseCreateSerializer(serializers.Serializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    purchase_date = serializers.DateField(required=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    items = PurchaseItemInputSerializer(many=True, allow_empty=False)

    def validate_purchase_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Purchase date cannot be in the future.")
        return value

    def validate_items(self, items):
        seen = set()
        for item in items:
            pid = item["product"].pk
            if pid in seen:
                raise serializers.ValidationError(
                    f"Product '{item['product'].name}' appears more than once. Combine the quantities into one line."
                )
            seen.add(pid)
        return items


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ["id", "product", "product_name", "product_sku", "quantity", "unit_price", "line_total"]
        read_only_fields = fields


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id", "reference_no", "supplier", "supplier_name", "purchase_date", "total_amount",
            "note", "created_by", "created_by_username", "created_at", "items",
        ]
        read_only_fields = fields


class PurchaseListSerializer(PurchaseSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta(PurchaseSerializer.Meta):
        fields = [f for f in PurchaseSerializer.Meta.fields if f != "items"] + ["item_count"]
        read_only_fields = fields
