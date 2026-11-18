from rest_framework import serializers

from inventory.serializers import StockItemSerializer
from sales.serializers import SaleListSerializer


class SalesTotalSerializer(serializers.Serializer):
    sales_count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=16, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    total_suppliers = serializers.IntegerField()
    today_sales = SalesTotalSerializer()
    monthly_sales = SalesTotalSerializer()
    total_due = serializers.DecimalField(max_digits=16, decimal_places=2, help_text="Money customers still owe")
    customers_with_due = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    low_stock_products = StockItemSerializer(many=True)
    recent_sales = SaleListSerializer(many=True)
