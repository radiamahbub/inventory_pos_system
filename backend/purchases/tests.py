from decimal import Decimal

from config.base_test import BaseAPITestCase
from inventory.models import MovementType, StockMovement
from purchases.models import Purchase
from suppliers.models import Supplier


class PurchaseTests(BaseAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.supplier = Supplier.objects.create(name="ABC Traders")

    def post(self, items, **extra):
        body = {"supplier": self.supplier.pk, "items": items}
        body.update(extra)
        return self.client.post("/api/purchases/", body, format="json")

    def test_purchase_increases_stock_and_records_movement(self):
        p1 = self.make_product(sku="P1", name="One", stock=10)
        p2 = self.make_product(sku="P2", name="Two", stock=0)
        self.as_admin()
        r = self.post(
            [
                {"product": p1.pk, "quantity": 20, "unit_price": "50.00"},
                {"product": p2.pk, "quantity": 5, "unit_price": "100.00"},
            ]
        )
        self.assertEqual(r.status_code, 201, r.data)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.stock_quantity, 30)
        self.assertEqual(p2.stock_quantity, 5)
        self.assertEqual(Decimal(r.data["total_amount"]), Decimal("1500.00"))
        self.assertEqual(len(r.data["items"]), 2)
        movement = StockMovement.objects.get(product=p1, movement_type=MovementType.PURCHASE)
        self.assertEqual(movement.quantity_change, 20)
        self.assertEqual((movement.quantity_before, movement.quantity_after), (10, 30))
        self.assertEqual(movement.reference, r.data["reference_no"])

    def test_total_is_calculated_by_server_not_client(self):
        p = self.make_product()
        self.as_admin()
        r = self.post([{"product": p.pk, "quantity": 3, "unit_price": "10.00"}], total_amount="1.00")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Decimal(r.data["total_amount"]), Decimal("30.00"))

    def test_reference_numbers_are_unique(self):
        p = self.make_product()
        self.as_admin()
        a = self.post([{"product": p.pk, "quantity": 1, "unit_price": "10"}]).data["reference_no"]
        b = self.post([{"product": p.pk, "quantity": 1, "unit_price": "10"}]).data["reference_no"]
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("PUR-"))

    def test_weighted_average_cost_updates_product_cost(self):
        p = self.make_product(cost="50.00", stock=10)
        self.as_admin()
        self.post([{"product": p.pk, "quantity": 10, "unit_price": "70.00"}])
        p.refresh_from_db()
        self.assertEqual(p.purchase_price, Decimal("60.00"))
        self.assertEqual(p.stock_quantity, 20)

    def test_validation_errors(self):
        p = self.make_product()
        self.as_admin()
        self.assertEqual(self.post([]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 0, "unit_price": "10"}]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1, "unit_price": "-5"}]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1, "unit_price": "0"}]).status_code, 400)
        self.assertEqual(self.post([{"product": 9999, "quantity": 1, "unit_price": "5"}]).status_code, 400)
        dup = self.post(
            [{"product": p.pk, "quantity": 1, "unit_price": "5"}, {"product": p.pk, "quantity": 2, "unit_price": "5"}]
        )
        self.assertEqual(dup.status_code, 400)
        bad_supplier = self.client.post(
            "/api/purchases/", {"supplier": 9999, "items": [{"product": p.pk, "quantity": 1, "unit_price": "5"}]}, format="json"
        )
        self.assertEqual(bad_supplier.status_code, 400)
        future = self.post([{"product": p.pk, "quantity": 1, "unit_price": "5"}], purchase_date="2999-01-01")
        self.assertEqual(future.status_code, 400)
        self.assertEqual(Purchase.objects.count(), 0)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 0)

    def test_failure_rolls_back_everything(self):
        good = self.make_product(sku="G", name="Good", stock=4)
        bad = self.make_product(sku="B", name="Bad", stock=4, is_active=False)
        self.as_admin()
        r = self.post(
            [{"product": good.pk, "quantity": 10, "unit_price": "5"}, {"product": bad.pk, "quantity": 1, "unit_price": "5"}]
        )
        self.assertEqual(r.status_code, 400)
        good.refresh_from_db()
        self.assertEqual(good.stock_quantity, 4)  # unchanged
        self.assertEqual(Purchase.objects.count(), 0)
        self.assertEqual(StockMovement.objects.filter(movement_type=MovementType.PURCHASE).count(), 0)

    def test_cashier_cannot_use_purchases(self):
        p = self.make_product()
        self.as_cashier()
        self.assertEqual(self.client.get("/api/purchases/").status_code, 403)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1, "unit_price": "5"}]).status_code, 403)

    def test_history_list_filter_and_detail(self):
        p = self.make_product()
        other = Supplier.objects.create(name="Other")
        self.as_admin()
        a = self.post([{"product": p.pk, "quantity": 1, "unit_price": "10"}], purchase_date="2026-01-10").data
        self.client.post(
            "/api/purchases/",
            {"supplier": other.pk, "purchase_date": "2026-02-10", "items": [{"product": p.pk, "quantity": 2, "unit_price": "10"}]},
            format="json",
        )
        self.assertEqual(self.client.get("/api/purchases/").data["count"], 2)
        r = self.client.get(f"/api/purchases/?supplier={self.supplier.pk}")
        self.assertEqual([x["id"] for x in r.data["results"]], [a["id"]])
        r = self.client.get("/api/purchases/?start_date=2026-02-01&end_date=2026-02-28")
        self.assertEqual(r.data["count"], 1)
        detail = self.client.get(f"/api/purchases/{a['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["items"][0]["quantity"], 1)

    def test_purchases_cannot_be_edited_or_deleted(self):
        p = self.make_product()
        self.as_admin()
        pk = self.post([{"product": p.pk, "quantity": 1, "unit_price": "10"}]).data["id"]
        self.assertEqual(self.client.patch(f"/api/purchases/{pk}/", {"note": "x"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/purchases/{pk}/").status_code, 405)
