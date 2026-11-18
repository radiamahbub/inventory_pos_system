from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from config.validators import phone_validator
from sales.models import PaymentMethod


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CustomerPayment(models.Model):
    """Money collected from a customer against their unpaid (due) balance."""

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=40, unique=True, editable=False)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    payment_date = models.DateTimeField(default=timezone.now, db_index=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="customer_payments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="customerpayment_amount_gt_0"),
        ]

    def __str__(self):
        return self.reference
