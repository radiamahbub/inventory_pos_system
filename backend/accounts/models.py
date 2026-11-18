from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    CASHIER = "cashier", "Cashier"


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # createsuperuser দিয়ে বানানো ইউজার সবসময় Admin role পাবে
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user with a role (Admin or Cashier)."""

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CASHIER)

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
