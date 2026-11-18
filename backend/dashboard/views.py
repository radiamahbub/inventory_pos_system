from django.db.models import Count, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from categories.models import Category
from customers.models import Customer
from customers.services import with_balance
from products.models import Product, low_stock_filter
from config.utils import money
from reports.services import sales_for_date_range, total_sales_amount
from sales.models import Sale, due_expression
from suppliers.models import Supplier

from .serializers import DashboardSerializer


class DashboardView(APIView):
    permission_classes = [IsAdminRole]
    serializer_class = DashboardSerializer

    @extend_schema(tags=["Dashboard"], summary="Dashboard summary (Admin only)", responses=DashboardSerializer)
    def get(self, request):
        today = timezone.localdate()
        month_start = today.replace(day=1)

        today_qs = sales_for_date_range(today, today)
        month_qs = sales_for_date_range(month_start, today)
        low_stock_qs = Product.objects.select_related("category").filter(low_stock_filter())

        owing = with_balance(Customer.objects.all()).filter(balance__gt=0)
        data = {
            "total_products": Product.objects.count(),
            "total_categories": Category.objects.count(),
            "total_customers": Customer.objects.count(),
            "total_suppliers": Supplier.objects.count(),
            "today_sales": {"sales_count": today_qs.count(), "total": total_sales_amount(today_qs)},
            "monthly_sales": {"sales_count": month_qs.count(), "total": total_sales_amount(month_qs)},
            "total_due": money(Sale.objects.aggregate(t=Sum(due_expression()))["t"] or 0),
            "customers_with_due": owing.count(),
            "low_stock_count": low_stock_qs.count(),
            "low_stock_products": low_stock_qs.order_by("stock_quantity", "name")[:10],
            "recent_sales": Sale.objects.select_related("customer", "created_by")
            .annotate(item_count=Count("items"))
            .order_by("-sale_date", "-id")[:5],
        }
        return Response(DashboardSerializer(data).data)
