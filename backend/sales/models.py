from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Q
from django.utils import timezone


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    CARD = "card", "Card"
    MOBILE_BANKING = "mobile_banking", "Mobile Banking"


ZERO = Decimal("0.00")


def due_expression():
    """
    Unpaid amount of a sale as a database expression:
    grand_total - paid at sale - collected later - (returned value - refunded cash)
    """
    return ExpressionWrapper(
        F("grand_total") - F("paid_amount") - F("collected_amount") - (F("returned_total") - F("refunded_total")),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )


class ReturnStatus(models.TextChoices):
    NONE = "none", "Not returned"
    PARTIAL = "partial", "Partially returned"
    FULL = "full", "Fully returned"


class Sale(models.Model):
    invoice_number = models.CharField(max_length=40, unique=True, editable=False)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, null=True, blank=True, related_name="sales"
    )
    sale_date = models.DateTimeField(default=timezone.now, db_index=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    note = models.CharField(max_length=255, blank=True)
    # --- Due sale bookkeeping (maintained only by services) ---
    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Amount received at the time of sale"
    )
    collected_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Due collected later (customer payments)"
    )
    # --- Returns bookkeeping (maintained only by sales.services.create_sale_return) ---
    returned_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Value of goods returned so far"
    )
    refunded_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Money given back to the customer so far"
    )
    return_status = models.CharField(
        max_length=10, choices=ReturnStatus.choices, default=ReturnStatus.NONE, db_index=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="sale_subtotal_gte_0"),
            models.CheckConstraint(condition=Q(discount__gte=0), name="sale_discount_gte_0"),
            models.CheckConstraint(condition=Q(grand_total__gte=0), name="sale_grand_total_gte_0"),
            models.CheckConstraint(condition=Q(discount__lte=F("subtotal")), name="sale_discount_lte_subtotal"),
            models.CheckConstraint(condition=Q(paid_amount__gte=0), name="sale_paid_amount_gte_0"),
            models.CheckConstraint(condition=Q(paid_amount__lte=F("grand_total")), name="sale_paid_lte_grand_total"),
            models.CheckConstraint(condition=Q(collected_amount__gte=0), name="sale_collected_amount_gte_0"),
            models.CheckConstraint(condition=Q(refunded_total__gte=0), name="sale_refunded_total_gte_0"),
            models.CheckConstraint(condition=Q(refunded_total__lte=F("returned_total")), name="sale_refunded_lte_returned"),
            models.CheckConstraint(condition=Q(returned_total__gte=0), name="sale_returned_total_gte_0"),
            models.CheckConstraint(condition=Q(returned_total__lte=F("grand_total")), name="sale_returned_lte_grand_total"),
        ]

    def __str__(self):
        return self.invoice_number

    @property
    def net_total(self):
        return self.grand_total - self.returned_total

    @property
    def total_paid(self):
        return self.paid_amount + self.collected_amount

    @property
    def due_adjusted(self):
        """Part of the returned value that only cancelled an unpaid balance (no money moved)."""
        return self.returned_total - self.refunded_total

    @property
    def due_amount(self):
        return max(ZERO, self.grand_total - self.total_paid - self.due_adjusted)

    @property
    def payment_status(self):
        if self.due_amount <= 0:
            return "paid"
        return "partial" if self.total_paid > 0 else "unpaid"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    returned_quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Selling price at the time of sale")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cost price at the time of sale")
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="saleitem_quantity_gt_0"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="saleitem_unit_price_gte_0"),
            models.CheckConstraint(
                condition=Q(returned_quantity__lte=F("quantity")), name="saleitem_returned_lte_quantity"
            ),
        ]

    def __str__(self):
        return f"{self.product_id} x {self.quantity}"

    @property
    def returnable_quantity(self):
        return self.quantity - self.returned_quantity


class SaleReturn(models.Model):
    """A sales return / refund against one invoice (an invoice can have several partial returns)."""

    return_number = models.CharField(max_length=40, unique=True, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="returns")
    return_date = models.DateTimeField(default=timezone.now, db_index=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Value of the returned goods")
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Money given back to the customer")
    due_adjusted = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Part that reduced the customer's unpaid balance instead"
    )
    refund_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sale_returns")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-return_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="salereturn_total_gte_0"),
            models.CheckConstraint(condition=Q(refund_amount__gte=0), name="salereturn_refund_gte_0"),
            models.CheckConstraint(condition=Q(due_adjusted__gte=0), name="salereturn_due_adjusted_gte_0"),
            models.CheckConstraint(
                condition=Q(total_amount=F("refund_amount") + F("due_adjusted")),
                name="salereturn_total_equals_refund_plus_due_adjusted",
            ),
        ]

    def __str__(self):
        return self.return_number


class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name="return_items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="return_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Selling price after the invoice discount is spread over the items"
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cost snapshot (for profit reversal)")
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="salereturnitem_quantity_gt_0"),
        ]

    def __str__(self):
        return f"{self.product_id} x {self.quantity}"
