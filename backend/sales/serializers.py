from rest_framework import serializers
from decimal import Decimal

from customers.models import Customer
from products.models import Product

from .models import PaymentMethod, Sale, SaleItem, SaleReturn, SaleReturnItem


class SaleItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class SaleCreateSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    # discount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, required=False, default=0) #Rafeu
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")) #Radia
    paid_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True, default=None,
        help_text="Money received now. Omit for full payment. Less than the total = due sale (customer required).",
    )
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    items = SaleItemInputSerializer(many=True, allow_empty=False)

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


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    returnable_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id", "product", "product_name", "product_sku", "quantity", "returned_quantity",
            "returnable_quantity", "unit_price", "line_total",
        ]
        read_only_fields = fields


class SaleReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = SaleReturnItem
        fields = ["id", "sale_item", "product", "product_name", "product_sku", "quantity", "unit_price", "line_total"]
        read_only_fields = fields


class SaleReturnSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="sale.invoice_number", read_only=True)
    customer_name = serializers.CharField(source="sale.customer.name", read_only=True, default=None)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    refund_method_display = serializers.CharField(source="get_refund_method_display", read_only=True)
    items = SaleReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = SaleReturn
        fields = [
            "id", "return_number", "sale", "invoice_number", "customer_name", "return_date",
            "total_amount", "refund_amount", "due_adjusted", "refund_method", "refund_method_display",
            "reason", "created_by", "created_by_username", "items",
        ]
        read_only_fields = fields


class SaleReturnListSerializer(SaleReturnSerializer):
    item_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(SaleReturnSerializer.Meta):
        fields = [f for f in SaleReturnSerializer.Meta.fields if f != "items"] + ["item_count"]
        read_only_fields = fields


class SaleReturnItemInputSerializer(serializers.Serializer):
    sale_item = serializers.PrimaryKeyRelatedField(queryset=SaleItem.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class SaleReturnCreateSerializer(serializers.Serializer):
    items = SaleReturnItemInputSerializer(many=True, allow_empty=False)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    refund_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, required=False, allow_blank=True, default="",
        help_text="How the refund is paid. Defaults to the original payment method.",
    )


class SaleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)
    returns = SaleReturnSerializer(many=True, read_only=True)
    total_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    net_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    payment_status = serializers.CharField(read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "invoice_number", "customer", "customer_name", "sale_date",
            "subtotal", "discount", "grand_total", "payment_method", "payment_method_display",
            "paid_amount", "collected_amount", "total_paid", "due_amount", "payment_status",
            "returned_total", "refunded_total", "net_total", "return_status",
            "note", "created_by", "created_by_username", "items", "returns",
        ]
        read_only_fields = fields


class SaleListSerializer(SaleSerializer):
    item_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(SaleSerializer.Meta):
        fields = [f for f in SaleSerializer.Meta.fields if f not in ("items", "returns")] + ["item_count"]
        read_only_fields = fields
