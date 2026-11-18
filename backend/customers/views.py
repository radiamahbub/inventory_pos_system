from django.db.models import Sum
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.utils import ZERO, money, parse_bool
from sales.models import Sale

from .models import Customer
from .permissions import CustomerPermission
from .serializers import (
    CustomerPaymentCreateSerializer,
    CustomerPaymentSerializer,
    CustomerSerializer,
    LedgerSerializer,
)
from .services import build_ledger, collect_payment, customer_balance, with_balance


@extend_schema_view(
    list=extend_schema(
        tags=["Customers"],
        parameters=[OpenApiParameter("has_due", bool, description="true = only customers who owe money")],
    ),
    retrieve=extend_schema(tags=["Customers"]),
    create=extend_schema(tags=["Customers"]),
    update=extend_schema(tags=["Customers"]),
    partial_update=extend_schema(tags=["Customers"]),
    destroy=extend_schema(tags=["Customers"], description="Admin only. Fails with 409 if the customer has sales."),
)
class CustomerViewSet(viewsets.ModelViewSet):
    """Admin and Cashier: create/read/update. Delete: Admin only."""

    queryset = Customer.objects.all().order_by("name")
    serializer_class = CustomerSerializer
    permission_classes = [CustomerPermission]
    search_fields = ["name", "phone", "email"]
    ordering_fields = ["name", "created_at", "balance"]

    def get_queryset(self):
        qs = with_balance(super().get_queryset())
        if parse_bool(self.request.query_params.get("has_due"), "has_due"):
            qs = qs.filter(balance__gt=0)
        return qs

    @extend_schema(
        tags=["Customers"],
        summary="Customer ledger (statement) with running balance",
        description="Sales, payments made at sale, returns and later due collections in date order. "
        "Positive balance = the customer owes the shop.",
        responses=LedgerSerializer,
    )
    @action(detail=True, methods=["get"], url_path="ledger")
    def ledger(self, request, pk=None):
        customer = self.get_object()
        entries = build_ledger(customer)
        sales = Sale.objects.filter(customer=customer).aggregate(t=Sum("grand_total"))["t"] or ZERO
        returned = Sale.objects.filter(customer=customer).aggregate(t=Sum("returned_total"))["t"] or ZERO
        balance = customer_balance(customer)
        customer.balance = balance
        data = {
            "customer": customer,
            "total_sales": money(sales - returned),  # net of returns
            "total_received": money(sales - returned - balance),
            "balance": balance,
            "entries": entries,
        }
        return Response(LedgerSerializer(data, context={"request": request}).data)

    @extend_schema(
        tags=["Customers"],
        summary="List due collections / collect a payment from this customer",
        request=CustomerPaymentCreateSerializer,
        responses={200: CustomerPaymentSerializer(many=True), 201: CustomerPaymentSerializer},
        examples=[
            OpenApiExample(
                "Collect payment",
                value={"amount": "500.00", "payment_method": "cash", "note": "Paid in shop"},
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="payments")
    def payments(self, request, pk=None):
        customer = self.get_object()
        if request.method == "GET":
            qs = customer.payments.select_related("created_by")
            page = self.paginate_queryset(qs)
            return self.get_paginated_response(CustomerPaymentSerializer(page, many=True).data)

        serializer = CustomerPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = collect_payment(
            customer=customer,
            amount=data["amount"],
            payment_method=data["payment_method"],
            note=data.get("note", ""),
            user=request.user,
        )
        return Response(CustomerPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
