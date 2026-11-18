from rest_framework import serializers

from inventory.serializers import StockItemSerializer


class SalesSummarySerializer(serializers.Serializer):
    sales_count = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=16, decimal_places=2)
    discount = serializers.DecimalField(max_digits=16, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    returns_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    cost_of_goods_sold = serializers.DecimalField(max_digits=16, decimal_places=2)
    estimated_profit = serializers.DecimalField(max_digits=16, decimal_places=2)


class PaymentBreakdownSerializer(serializers.Serializer):
    payment_method = serializers.CharField()
    count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=16, decimal_places=2)


class DailySalesReportSerializer(SalesSummarySerializer):
    date = serializers.DateField()
    payment_methods = PaymentBreakdownSerializer(many=True)


class DayTotalSerializer(serializers.Serializer):
    day = serializers.IntegerField()
    sales_count = serializers.IntegerField()
    grand_total = serializers.DecimalField(max_digits=16, decimal_places=2)


class MonthlySalesReportSerializer(SalesSummarySerializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    daily = DayTotalSerializer(many=True)


class MonthTotalSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    sales_count = serializers.IntegerField()
    grand_total = serializers.DecimalField(max_digits=16, decimal_places=2)


class YearlySalesReportSerializer(SalesSummarySerializer):
    year = serializers.IntegerField()
    monthly = MonthTotalSerializer(many=True)


class FinancialSummarySerializer(serializers.Serializer):
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    sales_count = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    returns_total = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    purchases_count = serializers.IntegerField()
    total_purchases = serializers.DecimalField(max_digits=16, decimal_places=2)
    cost_of_goods_sold = serializers.DecimalField(max_digits=16, decimal_places=2)
    estimated_profit = serializers.DecimalField(max_digits=16, decimal_places=2)


class LowStockItemSerializer(StockItemSerializer):
    shortage = serializers.IntegerField(help_text="min_stock_level - stock_quantity (never below 0)")

    class Meta(StockItemSerializer.Meta):
        fields = StockItemSerializer.Meta.fields + ["shortage"]
        read_only_fields = fields


class LowStockReportSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = LowStockItemSerializer(many=True)
