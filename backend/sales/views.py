from django.db.models import Count
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import Role
from accounts.permissions import IsAdminOrCashier
from config.shop import shop_info
from config.utils import parse_date, parse_int

from .models import PaymentMethod, ReturnStatus, Sale, SaleReturn, due_expression
from .serializers import (
    SaleCreateSerializer,
    SaleListSerializer,
    SaleReturnCreateSerializer,
    SaleReturnListSerializer,
    SaleReturnSerializer,
    SaleSerializer,
)
from .services import create_sale, create_sale_return


@extend_schema_view(
    list=extend_schema(
        tags=["Sales"],
        summary="Sales history (Cashier sees only own sales; Admin sees all)",
        parameters=[
            OpenApiParameter("customer", int, description="Filter by customer id"),
            OpenApiParameter("payment_method", str, description="cash | card | mobile_banking"),
            OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("payment_status", str, description="paid | due (any unpaid balance) | partial | unpaid"),
            OpenApiParameter("return_status", str, description="none | partial | full"),
        ],
    ),
    retrieve=extend_schema(tags=["Sales"], summary="Invoice details (includes its returns)"),
)
class SaleViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    POS sales. Admin and Cashier can create sales.
    Sales are create/read only (no edit or delete) so invoices and stock history stay trustworthy.
    """

    queryset = (
        Sale.objects.select_related("customer", "created_by")
        .annotate(item_count=Count("items"))
        .order_by("-sale_date", "-id")
    )
    permission_classes = [IsAdminOrCashier]
    search_fields = ["invoice_number", "customer__name", "customer__phone"]
    ordering_fields = ["sale_date", "grand_total", "id"]

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        if self.action == "list":
            return SaleListSerializer
        return SaleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return qs.none()
        user = self.request.user
        if user.role == Role.CASHIER:
            qs = qs.filter(created_by=user)
        if self.action == "retrieve":
            qs = qs.prefetch_related("items__product", "returns__items__product", "returns__created_by")

        p = self.request.query_params
        customer = parse_int(p.get("customer"), "customer")
        if customer is not None:
            qs = qs.filter(customer_id=customer)
        method = p.get("payment_method")
        if method:
            if method not in PaymentMethod.values:
                return qs.none()
            qs = qs.filter(payment_method=method)
        status_filter = p.get("payment_status")
        if status_filter:
            qs = qs.annotate(_due=due_expression())
            if status_filter == "paid":
                qs = qs.filter(_due__lte=0)
            elif status_filter == "due":
                qs = qs.filter(_due__gt=0)
            elif status_filter == "partial":
                qs = qs.filter(_due__gt=0, paid_amount__gt=0)
            elif status_filter == "unpaid":
                qs = qs.filter(_due__gt=0, paid_amount=0, collected_amount=0)
            else:
                return qs.none()
        return_status = p.get("return_status")
        if return_status:
            if return_status not in ReturnStatus.values:
                return qs.none()
            qs = qs.filter(return_status=return_status)
        start = parse_date(p.get("start_date"), "start_date")
        if start:
            qs = qs.filter(sale_date__date__gte=start)
        end = parse_date(p.get("end_date"), "end_date")
        if end:
            qs = qs.filter(sale_date__date__lte=end)
        return qs

    @extend_schema(
        tags=["Sales"],
        summary="Create a sale (stock decreases automatically)",
        description=(
            "Only `product` and `quantity` are sent per item. Prices, subtotal and grand total are calculated "
            "by the server. Fails with 400 if any product has insufficient stock. Send `paid_amount` lower than the total "
            "to record a due (credit) sale - a customer is then required."
        ),
        request=SaleCreateSerializer,
        responses={201: SaleSerializer},
        examples=[
            OpenApiExample(
                "Sale request",
                value={
                    "customer": 1,
                    "payment_method": "cash",
                    "discount": "50.00",
                    "paid_amount": "500.00",
                    "items": [{"product": 1, "quantity": 2}, {"product": 3, "quantity": 1}],
                },
                request_only=True,
            ),
            OpenApiExample(
                "Insufficient stock (400)",
                value={"items": ["Insufficient stock for 'Rice 5kg': available 1, requested 2."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sale = create_sale(
            customer=data.get("customer"),
            items=data["items"],
            discount=data.get("discount", 0),
            paid_amount=data.get("paid_amount"),
            payment_method=data["payment_method"],
            note=data.get("note", ""),
            user=request.user,
        )
        sale = (
            Sale.objects.select_related("customer", "created_by").prefetch_related("items__product").get(pk=sale.pk)
        )
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Returns"],
        summary="Return items of this invoice (stock goes back in, money is refunded)",
        description=(
            "Full or partial, repeatable. Send `sale_item` ids from the invoice and the quantity to return. "
            "The server works out the money: what the customer already paid beyond the value of the goods they keep is "
            "refunded; the rest simply cancels part of their unpaid balance. Cashiers can only return their own sales."
        ),
        request=SaleReturnCreateSerializer,
        responses={201: SaleReturnSerializer},
        examples=[
            OpenApiExample(
                "Return request",
                value={"items": [{"sale_item": 12, "quantity": 1}], "reason": "Damaged", "refund_method": "cash"},
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="returns")
    def returns(self, request, pk=None):
        sale = self.get_object()
        serializer = SaleReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sale_return = create_sale_return(
            sale=sale, items=data["items"], reason=data.get("reason", ""),
            refund_method=data.get("refund_method", ""), user=request.user,
        )
        sale_return = (
            SaleReturn.objects.select_related("sale__customer", "created_by")
            .prefetch_related("items__product").get(pk=sale_return.pk)
        )
        return Response(SaleReturnSerializer(sale_return).data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------ PDFs
    def _pdf(self, kind):
        try:
            from . import pdf
        except ImportError:
            return Response(
                {"detail": "PDF support is not installed on the server. Run: pip install reportlab"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        sale = self.get_object()  # cashiers can only reach their own sales
        items = list(sale.items.select_related("product").order_by("id"))
        builder = pdf.build_invoice_pdf if kind == "invoice" else pdf.build_receipt_pdf
        response = HttpResponse(builder(sale, items, shop_info()), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{sale.invoice_number}-{kind}.pdf"'
        return response

    @extend_schema(
        tags=["Sales"], summary="A4 invoice as PDF", responses={(200, "application/pdf"): OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=["get"], url_path="invoice-pdf")
    def invoice_pdf(self, request, pk=None):
        return self._pdf("invoice")

    @extend_schema(
        tags=["Sales"], summary="80 mm thermal receipt as PDF", responses={(200, "application/pdf"): OpenApiTypes.BINARY}
    )
    @action(detail=True, methods=["get"], url_path="receipt-pdf")
    def receipt_pdf(self, request, pk=None):
        return self._pdf("receipt")


@extend_schema_view(
    list=extend_schema(
        tags=["Returns"],
        summary="Sales returns (Cashier sees returns of own sales; Admin sees all)",
        parameters=[
            OpenApiParameter("sale", int, description="Filter by invoice id"),
            OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
        ],
    ),
    retrieve=extend_schema(tags=["Returns"], summary="Return details"),
)
class SaleReturnViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only list of returns. Create one with POST /api/sales/{id}/returns/."""

    queryset = (
        SaleReturn.objects.select_related("sale__customer", "created_by")
        .annotate(item_count=Count("items"))
        .order_by("-return_date", "-id")
    )
    permission_classes = [IsAdminOrCashier]
    search_fields = ["return_number", "sale__invoice_number", "sale__customer__name", "reason"]
    ordering_fields = ["return_date", "total_amount", "id"]

    def get_serializer_class(self):
        return SaleReturnListSerializer if self.action == "list" else SaleReturnSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return qs.none()
        if self.request.user.role == Role.CASHIER:
            qs = qs.filter(sale__created_by=self.request.user)
        if self.action == "retrieve":
            qs = qs.prefetch_related("items__product")
        p = self.request.query_params
        sale_id = parse_int(p.get("sale"), "sale")
        if sale_id is not None:
            qs = qs.filter(sale_id=sale_id)
        start = parse_date(p.get("start_date"), "start_date")
        if start:
            qs = qs.filter(return_date__date__gte=start)
        end = parse_date(p.get("end_date"), "end_date")
        if end:
            qs = qs.filter(return_date__date__lte=end)
        return qs
