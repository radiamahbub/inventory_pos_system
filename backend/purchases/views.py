from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from config.utils import parse_date, parse_int

from .models import Purchase
from .serializers import PurchaseCreateSerializer, PurchaseListSerializer, PurchaseSerializer
from .services import create_purchase


@extend_schema_view(
    list=extend_schema(
        tags=["Purchases"],
        summary="Purchase history",
        parameters=[
            OpenApiParameter("supplier", int, description="Filter by supplier id"),
            OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
        ],
    ),
    retrieve=extend_schema(tags=["Purchases"]),
)
class PurchaseViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Admin only. Purchases are create/read only (no edit or delete) to keep stock history trustworthy.
    """

    queryset = (
        Purchase.objects.select_related("supplier", "created_by")
        .annotate(item_count=Count("items"))
        .order_by("-purchase_date", "-id")
    )
    permission_classes = [IsAdminRole]
    search_fields = ["reference_no", "supplier__name", "note"]
    ordering_fields = ["purchase_date", "total_amount", "id"]

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseCreateSerializer
        if self.action == "list":
            return PurchaseListSerializer
        return PurchaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related("items__product")
        p = self.request.query_params
        supplier = parse_int(p.get("supplier"), "supplier")
        if supplier is not None:
            qs = qs.filter(supplier_id=supplier)
        start = parse_date(p.get("start_date"), "start_date")
        if start:
            qs = qs.filter(purchase_date__gte=start)
        end = parse_date(p.get("end_date"), "end_date")
        if end:
            qs = qs.filter(purchase_date__lte=end)
        return qs

    @extend_schema(
        tags=["Purchases"],
        summary="Create a purchase (stock increases automatically)",
        request=PurchaseCreateSerializer,
        responses={201: PurchaseSerializer},
        examples=[
            OpenApiExample(
                "Purchase request",
                value={
                    "supplier": 1,
                    "purchase_date": "2026-11-13",
                    "note": "Monthly restock",
                    "items": [
                        {"product": 1, "quantity": 20, "unit_price": "45.00"},
                        {"product": 2, "quantity": 10, "unit_price": "120.50"},
                    ],
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = PurchaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        purchase = create_purchase(
            supplier=data["supplier"],
            purchase_date=data.get("purchase_date") or timezone.localdate(),
            note=data.get("note", ""),
            items=data["items"],
            user=request.user,
        )
        purchase = Purchase.objects.prefetch_related("items__product").select_related("supplier", "created_by").get(
            pk=purchase.pk
        )
        return Response(PurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)
