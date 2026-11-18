from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrCashier, IsAdminRole
from config.utils import parse_bool, parse_date, parse_int
from products.models import Product, low_stock_filter

from .models import MovementType, StockMovement
from .serializers import StockAdjustmentSerializer, StockItemSerializer, StockMovementSerializer
from .services import apply_stock_change


@extend_schema_view(
    list=extend_schema(
        tags=["Inventory"],
        summary="Current stock of all products",
        parameters=[
            OpenApiParameter("low_stock", bool, description="true = only low-stock products"),
            OpenApiParameter("category", int, description="Filter by category id"),
        ],
    ),
    retrieve=extend_schema(tags=["Inventory"], summary="Current stock of one product"),
)
class CurrentStockViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin and Cashier: read-only current stock."""

    queryset = Product.objects.select_related("category").order_by("name")
    serializer_class = StockItemSerializer
    permission_classes = [IsAdminOrCashier]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "stock_quantity"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if parse_bool(p.get("low_stock"), "low_stock"):
            qs = qs.filter(low_stock_filter())
        category = parse_int(p.get("category"), "category")
        if category is not None:
            qs = qs.filter(category_id=category)
        return qs

    @extend_schema(tags=["Inventory"], summary="Products at or below minimum stock level")
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(low_stock_filter())).order_by("stock_quantity", "name")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        tags=["Inventory"],
        summary="Stock movement history (Admin only)",
        parameters=[
            OpenApiParameter("product", int, description="Filter by product id"),
            OpenApiParameter("movement_type", str, description="opening | purchase | sale | return | adjustment"),
            OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
        ],
    ),
    retrieve=extend_schema(tags=["Inventory"]),
)
class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("product", "created_by")
    serializer_class = StockMovementSerializer
    permission_classes = [IsAdminRole]
    search_fields = ["product__name", "product__sku", "reference", "note"]
    ordering_fields = ["created_at", "quantity_change"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        product = parse_int(p.get("product"), "product")
        if product is not None:
            qs = qs.filter(product_id=product)
        movement_type = p.get("movement_type")
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        start = parse_date(p.get("start_date"), "start_date")
        if start:
            qs = qs.filter(created_at__date__gte=start)
        end = parse_date(p.get("end_date"), "end_date")
        if end:
            qs = qs.filter(created_at__date__lte=end)
        return qs


class StockAdjustmentView(APIView):
    permission_classes = [IsAdminRole]
    serializer_class = StockAdjustmentSerializer

    @extend_schema(
        tags=["Inventory"],
        summary="Adjust stock manually (Admin only)",
        description="Positive `quantity_change` adds stock, negative removes it. Stock can never go below zero.",
        request=StockAdjustmentSerializer,
        responses={201: StockMovementSerializer},
        examples=[
            OpenApiExample(
                "Remove 3 damaged items",
                value={"product": 1, "quantity_change": -3, "reason": "Damaged during storage"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            movement = apply_stock_change(
                product=data["product"],
                quantity_change=data["quantity_change"],
                movement_type=MovementType.ADJUSTMENT,
                user=request.user,
                note=data["reason"],
            )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)
