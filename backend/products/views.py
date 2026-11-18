from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action

from accounts.permissions import IsAdminOrReadOnly
from config.utils import parse_bool, parse_decimal, parse_int

from .models import Product, low_stock_filter
from .serializers import ProductSerializer

LIST_PARAMS = [
    OpenApiParameter("category", int, description="Filter by category id"),
    OpenApiParameter("low_stock", bool, description="true = stock <= minimum level"),
    OpenApiParameter("in_stock", bool, description="true = stock > 0, false = out of stock"),
    OpenApiParameter("is_active", bool, description="Filter by active status"),
    OpenApiParameter("min_price", float, description="Minimum selling price"),
    OpenApiParameter("max_price", float, description="Maximum selling price"),
]


@extend_schema_view(
    list=extend_schema(tags=["Products"], parameters=LIST_PARAMS),
    retrieve=extend_schema(tags=["Products"]),
    create=extend_schema(tags=["Products"]),
    update=extend_schema(tags=["Products"]),
    partial_update=extend_schema(tags=["Products"]),
    destroy=extend_schema(
        tags=["Products"],
        description="Fails with 409 if the product is used in purchases/sales/stock history. Deactivate instead.",
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    """Admin: full CRUD. Cashier: read-only. Search by name, SKU, category, description."""

    queryset = Product.objects.select_related("category").order_by("name")
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name", "sku", "category__name", "description"]
    ordering_fields = ["name", "sku", "selling_price", "purchase_price", "stock_quantity", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params

        category = parse_int(p.get("category"), "category")
        if category is not None:
            qs = qs.filter(category_id=category)

        if parse_bool(p.get("low_stock"), "low_stock"):
            qs = qs.filter(low_stock_filter())

        in_stock = parse_bool(p.get("in_stock"), "in_stock")
        if in_stock is True:
            qs = qs.filter(stock_quantity__gt=0)
        elif in_stock is False:
            qs = qs.filter(stock_quantity=0)

        is_active = parse_bool(p.get("is_active"), "is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        min_price = parse_decimal(p.get("min_price"), "min_price")
        if min_price is not None:
            qs = qs.filter(selling_price__gte=min_price)
        max_price = parse_decimal(p.get("max_price"), "max_price")
        if max_price is not None:
            qs = qs.filter(selling_price__lte=max_price)
        return qs

    @extend_schema(tags=["Products"], summary="Low-stock products")
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(low_stock_filter())).order_by("stock_quantity", "name")
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
