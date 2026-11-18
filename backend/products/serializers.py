from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from accounts.models import Role

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    # purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0) # Rafeu
    purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0")) #Radia
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    initial_stock = serializers.IntegerField(
        write_only=True, required=False, min_value=0, default=0,
        help_text="Optional, on create only. Recorded as an 'opening' stock movement.",
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "category", "category_name",
            "purchase_price", "selling_price", "stock_quantity", "min_stock_level",
            "description", "is_active", "is_low_stock", "initial_stock",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "stock_quantity", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Cost price ব্যবসার গোপন তথ্য — Cashier API response-এও পাবে না
        request = self.context.get("request")
        if request is not None and getattr(request.user, "role", None) != Role.ADMIN:
            data.pop("purchase_price", None)
        return data

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_sku(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("SKU cannot be blank.")
        qs = Product.objects.filter(sku__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate(self, attrs):
        if self.instance is not None and attrs.get("initial_stock"):
            raise serializers.ValidationError(
                {"initial_stock": "Use the inventory adjustment API to change stock of an existing product."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from inventory.models import MovementType
        from inventory.services import apply_stock_change

        initial_stock = validated_data.pop("initial_stock", 0)
        product = Product.objects.create(**validated_data)
        if initial_stock > 0:
            apply_stock_change(
                product=product,
                quantity_change=initial_stock,
                movement_type=MovementType.OPENING,
                user=self.context["request"].user,
                note="Opening stock",
            )
        return product

    def update(self, instance, validated_data):
        validated_data.pop("initial_stock", None)
        return super().update(instance, validated_data)
