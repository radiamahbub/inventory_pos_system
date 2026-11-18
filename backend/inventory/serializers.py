from rest_framework import serializers

from products.models import Product

from .models import StockMovement


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id", "product", "product_name", "product_sku", "movement_type", "movement_type_display",
            "quantity_change", "quantity_before", "quantity_after", "reference", "note",
            "created_by", "created_by_username", "created_at",
        ]
        read_only_fields = fields


class StockItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "category", "category_name",
            "stock_quantity", "min_stock_level", "is_low_stock", "is_active",
        ]
        read_only_fields = fields


class StockAdjustmentSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity_change = serializers.IntegerField(
        help_text="Positive to add stock, negative to remove stock. Cannot be zero."
    )
    reason = serializers.CharField(max_length=255, help_text="Why is the stock being adjusted?")

    def validate_quantity_change(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity change cannot be zero.")
        return value

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A reason is required.")
        return value
