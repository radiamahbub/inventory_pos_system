"""Shared base class for API tests (file name avoids test auto-discovery)."""

from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import Role, User
from categories.models import Category
from products.models import Product


class BaseAPITestCase(APITestCase):
    password = "StrongPass123!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin1", password=cls.password, role=Role.ADMIN)
        cls.cashier = User.objects.create_user("cashier1", password=cls.password, role=Role.CASHIER)
        cls.category = Category.objects.create(name="General")

    def as_admin(self):
        self.client.force_authenticate(self.admin)

    def as_cashier(self):
        self.client.force_authenticate(self.cashier)

    def make_product(self, sku="SKU-1", name="Item", cost="50.00", price="80.00", stock=0, min_stock=5, **kw):
        product = Product.objects.create(
            name=name,
            sku=sku,
            category=self.category,
            purchase_price=Decimal(cost),
            selling_price=Decimal(price),
            min_stock_level=min_stock,
            **kw,
        )
        if stock:
            from inventory.models import MovementType
            from inventory.services import apply_stock_change

            apply_stock_change(
                product=product, quantity_change=stock, movement_type=MovementType.OPENING, user=self.admin
            )
            product.refresh_from_db()
        return product
