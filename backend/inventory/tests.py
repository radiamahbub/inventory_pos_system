from config.base_test import BaseAPITestCase
from inventory.models import MovementType, StockMovement


class InventoryTests(BaseAPITestCase):
    def adjust(self, product, change, reason="Stock count"):
        return self.client.post(
            "/api/inventory/adjust/",
            {"product": product.pk, "quantity_change": change, "reason": reason},
            format="json",
        )

    def test_admin_can_increase_and_decrease_stock(self):
        p = self.make_product(stock=10)
        self.as_admin()
        r = self.adjust(p, 5, "Found extra boxes")
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data["quantity_before"], r.data["quantity_after"]), (10, 15))
        self.assertEqual(r.data["movement_type"], "adjustment")
        r = self.adjust(p, -4, "Damaged")
        self.assertEqual(r.status_code, 201)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 11)

    def test_adjustment_cannot_make_stock_negative(self):
        p = self.make_product(stock=3)
        self.as_admin()
        r = self.adjust(p, -4)
        self.assertEqual(r.status_code, 400)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 3)
        self.assertEqual(StockMovement.objects.filter(movement_type=MovementType.ADJUSTMENT).count(), 0)

    def test_adjustment_validation(self):
        p = self.make_product(stock=3)
        self.as_admin()
        self.assertEqual(self.adjust(p, 0).status_code, 400)
        self.assertEqual(self.adjust(p, 1, reason="   ").status_code, 400)
        r = self.client.post("/api/inventory/adjust/", {"product": p.pk, "quantity_change": 1}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cashier_cannot_adjust_or_see_movements(self):
        p = self.make_product(stock=3)
        self.as_cashier()
        self.assertEqual(self.adjust(p, 1).status_code, 403)
        self.assertEqual(self.client.get("/api/inventory/movements/").status_code, 403)

    def test_cashier_can_view_current_stock(self):
        self.make_product(sku="A", name="A", stock=2, min_stock=5)
        self.make_product(sku="B", name="B", stock=20, min_stock=5)
        self.as_cashier()
        r = self.client.get("/api/inventory/stock/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        low = self.client.get("/api/inventory/stock/low-stock/")
        self.assertEqual([x["name"] for x in low.data["results"]], ["A"])
        self.assertEqual(len(self.client.get("/api/inventory/stock/?low_stock=true").data["results"]), 1)

    def test_movement_history_is_complete_and_filterable(self):
        p = self.make_product(stock=10)  # opening +10
        self.as_admin()
        self.adjust(p, -2)
        r = self.client.get(f"/api/inventory/movements/?product={p.pk}")
        self.assertEqual(r.data["count"], 2)
        types = [m["movement_type"] for m in r.data["results"]]
        self.assertEqual(types, ["adjustment", "opening"])  # newest first
        r = self.client.get("/api/inventory/movements/?movement_type=opening")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(self.client.get("/api/inventory/movements/?start_date=bad").status_code, 400)

    def test_history_is_read_only(self):
        p = self.make_product(stock=1)
        movement = StockMovement.objects.get()
        self.as_admin()
        self.assertEqual(self.client.post("/api/inventory/movements/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/inventory/movements/{movement.pk}/").status_code, 405)

    def test_full_flow_purchase_then_sale_leaves_correct_history(self):
        from suppliers.models import Supplier

        p = self.make_product(stock=0)
        supplier = Supplier.objects.create(name="S")
        self.as_admin()
        self.client.post(
            "/api/purchases/",
            {"supplier": supplier.pk, "items": [{"product": p.pk, "quantity": 10, "unit_price": "40.00"}]},
            format="json",
        )
        self.client.post(
            "/api/sales/", {"payment_method": "cash", "items": [{"product": p.pk, "quantity": 4}]}, format="json"
        )
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 6)
        changes = list(StockMovement.objects.filter(product=p).order_by("id").values_list("quantity_change", flat=True))
        self.assertEqual(changes, [10, -4])
