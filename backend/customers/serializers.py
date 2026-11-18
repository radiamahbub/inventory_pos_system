from rest_framework import serializers
from decimal import Decimal

from config.utils import money
from sales.models import PaymentMethod

from .models import Customer, CustomerPayment
from .services import customer_balance


class CustomerSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField(help_text="Amount the customer owes the shop (0 = nothing due)")

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "address", "balance", "created_at", "updated_at"]
        read_only_fields = ["id", "balance", "created_at", "updated_at"]

    def get_balance(self, obj):
        value = getattr(obj, "balance", None)  # annotated in list/detail queries
        if value is None:
            value = customer_balance(obj)
        return f"{money(value):.2f}"

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value


class CustomerPaymentSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = CustomerPayment
        fields = [
            "id", "reference", "customer", "amount", "payment_method", "payment_method_display",
            "payment_date", "note", "created_by", "created_by_username",
        ]
        read_only_fields = fields


class CustomerPaymentCreateSerializer(serializers.Serializer):
    # amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01")) # Radia refined decimal value
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class LedgerEntrySerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    type = serializers.ChoiceField(choices=["sale", "payment_at_sale", "return", "collection"])
    reference = serializers.CharField()
    sale_id = serializers.IntegerField(allow_null=True)
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=16, decimal_places=2)
    credit = serializers.DecimalField(max_digits=16, decimal_places=2)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2)


class LedgerSerializer(serializers.Serializer):
    customer = CustomerSerializer()
    total_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_received = serializers.DecimalField(max_digits=16, decimal_places=2)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2)
    entries = LedgerEntrySerializer(many=True)
