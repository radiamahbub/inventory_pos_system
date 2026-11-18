import calendar
import datetime

from django.db.models import Count
from django.db.models.functions import ExtractDay, ExtractMonth
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from config.utils import money, parse_date, parse_int
from products.models import Product, low_stock_filter

from . import services
from .serializers import (
    DailySalesReportSerializer,
    FinancialSummarySerializer,
    LowStockReportSerializer,
    MonthlySalesReportSerializer,
    YearlySalesReportSerializer,
)


def _year(value):
    year = parse_int(value, "year")
    if year is None:
        return timezone.localdate().year
    if not 2000 <= year <= 2100:
        raise ValidationError({"year": "Year must be between 2000 and 2100."})
    return year


class BaseReportView(APIView):
    """সব report শুধু Admin-এর জন্য (profit ও purchase তথ্য সংবেদনশীল)।"""

    permission_classes = [IsAdminRole]


class DailySalesReportView(BaseReportView):
    serializer_class = DailySalesReportSerializer

    @extend_schema(
        tags=["Reports"],
        summary="Daily sales report",
        parameters=[OpenApiParameter("date", str, description="YYYY-MM-DD (default: today)")],
        responses=DailySalesReportSerializer,
    )
    def get(self, request):
        day = parse_date(request.query_params.get("date"), "date") or timezone.localdate()
        qs = services.sales_for_date_range(day, day)
        returns = services.returns_for_date_range(day, day)
        data = {"date": day, **services.sales_summary(qs, returns), "payment_methods": services.payment_breakdown(qs)}
        return Response(DailySalesReportSerializer(data).data)


class MonthlySalesReportView(BaseReportView):
    serializer_class = MonthlySalesReportSerializer

    @extend_schema(
        tags=["Reports"],
        summary="Monthly sales report",
        parameters=[
            OpenApiParameter("year", int, description="Default: current year"),
            OpenApiParameter("month", int, description="1-12 (default: current month)"),
        ],
        responses=MonthlySalesReportSerializer,
    )
    def get(self, request):
        today = timezone.localdate()
        year = _year(request.query_params.get("year"))
        month = parse_int(request.query_params.get("month"), "month") or today.month
        if not 1 <= month <= 12:
            raise ValidationError({"month": "Month must be between 1 and 12."})
        start = datetime.date(year, month, 1)
        end = datetime.date(year, month, calendar.monthrange(year, month)[1])
        qs = services.sales_for_date_range(start, end)
        returns = services.returns_for_date_range(start, end)
        rows = (
            qs.order_by()
            .annotate(day=ExtractDay("sale_date"))
            .values("day")
            .annotate(sales_count=Count("id"), grand_total=services._sum("grand_total"))
            .order_by("day")
        )
        daily = [
            {"day": r["day"], "sales_count": r["sales_count"], "grand_total": money(r["grand_total"])} for r in rows
        ]
        data = {"year": year, "month": month, **services.sales_summary(qs, returns), "daily": daily}
        return Response(MonthlySalesReportSerializer(data).data)


class YearlySalesReportView(BaseReportView):
    serializer_class = YearlySalesReportSerializer

    @extend_schema(
        tags=["Reports"],
        summary="Yearly sales report",
        parameters=[OpenApiParameter("year", int, description="Default: current year")],
        responses=YearlySalesReportSerializer,
    )
    def get(self, request):
        year = _year(request.query_params.get("year"))
        year_start, year_end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
        qs = services.sales_for_date_range(year_start, year_end)
        returns = services.returns_for_date_range(year_start, year_end)
        rows = (
            qs.order_by()
            .annotate(month=ExtractMonth("sale_date"))
            .values("month")
            .annotate(sales_count=Count("id"), grand_total=services._sum("grand_total"))
            .order_by("month")
        )
        monthly = [
            {"month": r["month"], "sales_count": r["sales_count"], "grand_total": money(r["grand_total"])}
            for r in rows
        ]
        data = {"year": year, **services.sales_summary(qs, returns), "monthly": monthly}
        return Response(YearlySalesReportSerializer(data).data)


class FinancialSummaryView(BaseReportView):
    serializer_class = FinancialSummarySerializer

    @extend_schema(
        tags=["Reports"],
        summary="Total sales, total purchases and estimated profit",
        description=(
            "Estimated profit = net sales (sales after discount minus returns) - cost of goods sold (returned goods taken out). "
            "Cost uses the weighted-average cost saved on each sale item at the time of sale."
        ),
        parameters=[
            OpenApiParameter("start_date", str, description="YYYY-MM-DD (optional)"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD (optional)"),
        ],
        responses=FinancialSummarySerializer,
    )
    def get(self, request):
        start = parse_date(request.query_params.get("start_date"), "start_date")
        end = parse_date(request.query_params.get("end_date"), "end_date")
        if start and end and start > end:
            raise ValidationError({"end_date": "end_date cannot be before start_date."})
        sales = services.sales_for_date_range(start, end)
        summary = services.sales_summary(sales, services.returns_for_date_range(start, end))
        purchases_count, purchases_total = services.total_purchases(services.purchases_for_date_range(start, end))
        data = {
            "start_date": start,
            "end_date": end,
            "sales_count": summary["sales_count"],
            "total_sales": summary["grand_total"],
            "returns_total": summary["returns_total"],
            "net_sales": summary["net_sales"],
            "purchases_count": purchases_count,
            "total_purchases": purchases_total,
            "cost_of_goods_sold": summary["cost_of_goods_sold"],
            "estimated_profit": summary["estimated_profit"],
        }
        return Response(FinancialSummarySerializer(data).data)


class LowStockReportView(BaseReportView):
    serializer_class = LowStockReportSerializer

    @extend_schema(tags=["Reports"], summary="Low-stock report", responses=LowStockReportSerializer)
    def get(self, request):
        products = list(
            Product.objects.select_related("category").filter(low_stock_filter()).order_by("stock_quantity", "name")
        )
        for p in products:
            p.shortage = max(p.min_stock_level - p.stock_quantity, 0)
        return Response(LowStockReportSerializer({"count": len(products), "results": products}).data)
