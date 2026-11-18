from decimal import Decimal

from categories.models import Category
from config.base_test import BaseAPITestCase
from inventory.models import MovementType, StockMovement
from products.models import Product


class ProductTests(BaseAPITestCase):
    def payload(self, **kw):
        data = {
            "name": "Rice 5kg", "sku": "rice-5", "category": self.category.pk,
            "purchase_price": "300.00", "selling_price": "350.00", "min_stock_level": 5,
        }
        data.update(kw)
        return data

    def test_admin_creates_product_sku_is_normalised(self):
        self.as_admin()
        r = self.client.post("/api/products/", self.payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["sku"], "RICE-5")
        self.assertEqual(r.data["stock_quantity"], 0)
        self.assertEqual(r.data["category_name"], "General")

    def test_initial_stock_creates_opening_movement(self):
        self.as_admin()
        r = self.client.post("/api/products/", self.payload(initial_stock=12), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["stock_quantity"], 12)
        movement = StockMovement.objects.get(product_id=r.data["id"])
        self.assertEqual(movement.movement_type, MovementType.OPENING)
        self.assertEqual(movement.quantity_after, 12)

    def test_sku_must_be_unique_case_insensitive(self):
        self.as_admin()
        self.client.post("/api/products/", self.payload(), format="json")
        r = self.client.post("/api/products/", self.payload(sku="RICE-5", name="Other"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("sku", r.data)

    def test_negative_or_zero_prices_rejected(self):
        self.as_admin()
        r = self.client.post("/api/products/", self.payload(purchase_price="-1"), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/products/", self.payload(selling_price="0"), format="json")
        self.assertEqual(r.status_code, 400)

    def test_stock_cannot_be_edited_directly(self):
        product = self.make_product(stock=10)
        self.as_admin()
        r = self.client.patch(f"/api/products/{product.pk}/", {"stock_quantity": 999}, format="json")
        self.assertEqual(r.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 10)

    def test_initial_stock_rejected_on_update(self):
        product = self.make_product()
        self.as_admin()
        r = self.client.patch(f"/api/products/{product.pk}/", {"initial_stock": 5}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cashier_can_read_but_not_write(self):
        product = self.make_product()
        self.as_cashier()
        self.assertEqual(self.client.get("/api/products/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/products/{product.pk}/").status_code, 200)
        self.assertEqual(self.client.post("/api/products/", self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/products/{product.pk}/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/products/{product.pk}/").status_code, 403)

    def test_search_by_name_sku_and_category(self):
        self.make_product(sku="A-1", name="Green Tea")
        other = Category.objects.create(name="Snacks")
        Product.objects.create(
            name="Chips", sku="B-2", category=other, purchase_price=Decimal("10"), selling_price=Decimal("20")
        )
        self.as_admin()
        names = lambda q: [p["name"] for p in self.client.get(f"/api/products/?search={q}").data["results"]]
        self.assertEqual(names("tea"), ["Green Tea"])
        self.assertEqual(names("b-2"), ["Chips"])
        self.assertEqual(names("snacks"), ["Chips"])

    def test_filter_by_category_and_price(self):
        self.make_product(sku="A-1", name="Cheap", price="10.00")
        self.make_product(sku="A-2", name="Pricey", price="500.00")
        self.as_admin()
        r = self.client.get(f"/api/products/?category={self.category.pk}&min_price=100")
        self.assertEqual([p["name"] for p in r.data["results"]], ["Pricey"])
        r = self.client.get("/api/products/?max_price=100")
        self.assertEqual([p["name"] for p in r.data["results"]], ["Cheap"])

    def test_invalid_filter_values_return_400(self):
        self.as_admin()
        self.assertEqual(self.client.get("/api/products/?category=abc").status_code, 400)
        self.assertEqual(self.client.get("/api/products/?low_stock=maybe").status_code, 400)
        self.assertEqual(self.client.get("/api/products/?min_price=abc").status_code, 400)

    def test_low_stock_detection(self):
        self.make_product(sku="L-1", name="Low", stock=3, min_stock=5)
        self.make_product(sku="L-2", name="Equal", stock=5, min_stock=5)
        self.make_product(sku="L-3", name="Fine", stock=50, min_stock=5)
        self.as_cashier()
        r = self.client.get("/api/products/?low_stock=true")
        self.assertEqual(sorted(p["name"] for p in r.data["results"]), ["Equal", "Low"])
        self.assertTrue(all(p["is_low_stock"] for p in r.data["results"]))
        r = self.client.get("/api/products/low-stock/")
        self.assertEqual(r.data["count"], 2)

    def test_in_stock_filter(self):
        self.make_product(sku="S-1", name="Has", stock=4)
        self.make_product(sku="S-2", name="None", stock=0)
        self.as_admin()
        self.assertEqual([p["name"] for p in self.client.get("/api/products/?in_stock=true").data["results"]], ["Has"])
        self.assertEqual([p["name"] for p in self.client.get("/api/products/?in_stock=false").data["results"]], ["None"])

    def test_delete_unused_product_ok_but_used_product_blocked(self):
        unused = self.make_product(sku="U-1", name="Unused")
        used = self.make_product(sku="U-2", name="Used", stock=5)  # has stock movement history
        self.as_admin()
        self.assertEqual(self.client.delete(f"/api/products/{unused.pk}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/products/{used.pk}/").status_code, 409)

    def test_db_constraint_blocks_negative_price(self):
        from django.db import IntegrityError, transaction

        product = self.make_product()
        product.selling_price = Decimal("-5")
        with self.assertRaises(IntegrityError), transaction.atomic():
            product.save()


class ProductCostVisibilityTests(BaseAPITestCase):
    """Cost (purchase) price শুধু Admin দেখতে পাবে।"""

    def test_admin_sees_purchase_price(self):
        product = self.make_product(cost="50.00", price="80.00")
        self.as_admin()
        detail = self.client.get(f"/api/products/{product.pk}/")
        self.assertEqual(detail.data["purchase_price"], "50.00")
        listing = self.client.get("/api/products/")
        self.assertIn("purchase_price", listing.data["results"][0])

    def test_cashier_never_receives_purchase_price(self):
        product = self.make_product(cost="50.00", price="80.00")
        self.as_cashier()
        detail = self.client.get(f"/api/products/{product.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("purchase_price", detail.data)
        self.assertEqual(detail.data["selling_price"], "80.00")
        listing = self.client.get("/api/products/")
        self.assertNotIn("purchase_price", listing.data["results"][0])
