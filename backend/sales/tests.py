from decimal import Decimal

from config.base_test import BaseAPITestCase
from customers.models import Customer
from inventory.models import MovementType, StockMovement
from sales.models import Sale, SaleItem


class SaleTests(BaseAPITestCase):
    def post(self, items, **extra):
        body = {"payment_method": "cash", "items": items}
        body.update(extra)
        return self.client.post("/api/sales/", body, format="json")

    def test_sale_decreases_stock_and_calculates_totals(self):
        p1 = self.make_product(sku="P1", name="One", cost="50.00", price="80.00", stock=10)
        p2 = self.make_product(sku="P2", name="Two", cost="20.00", price="30.50", stock=4)
        self.as_cashier()
        r = self.post([{"product": p1.pk, "quantity": 3}, {"product": p2.pk, "quantity": 2}], discount="10.00")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["subtotal"]), Decimal("301.00"))  # 240 + 61
        self.assertEqual(Decimal(r.data["discount"]), Decimal("10.00"))
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("291.00"))
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual((p1.stock_quantity, p2.stock_quantity), (7, 2))
        movement = StockMovement.objects.get(product=p1, movement_type=MovementType.SALE)
        self.assertEqual((movement.quantity_change, movement.quantity_before, movement.quantity_after), (-3, 10, 7))
        self.assertEqual(movement.reference, r.data["invoice_number"])
        self.assertEqual(movement.created_by, self.cashier)

    def test_client_cannot_set_price_or_totals(self):
        p = self.make_product(price="80.00", stock=5)
        self.as_cashier()
        r = self.post(
            [{"product": p.pk, "quantity": 1, "unit_price": "1.00", "line_total": "1.00"}],
            subtotal="1.00", grand_total="1.00",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("80.00"))
        self.assertEqual(Decimal(r.data["items"][0]["unit_price"]), Decimal("80.00"))

    def test_cost_snapshot_saved_on_items(self):
        p = self.make_product(cost="42.00", price="80.00", stock=5)
        self.as_cashier()
        self.post([{"product": p.pk, "quantity": 2}])
        item = SaleItem.objects.get()
        self.assertEqual(item.unit_cost, Decimal("42.00"))
        self.assertEqual(item.unit_price, Decimal("80.00"))

    def test_cannot_sell_more_than_stock(self):
        p = self.make_product(name="Rice", stock=2)
        self.as_cashier()
        r = self.post([{"product": p.pk, "quantity": 3}])
        self.assertEqual(r.status_code, 400)
        self.assertIn("Insufficient stock", r.data["items"][0])
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 2)
        self.assertEqual(Sale.objects.count(), 0)

    def test_can_sell_exact_remaining_stock_and_stock_never_negative(self):
        p = self.make_product(stock=3)
        self.as_cashier()
        self.assertEqual(self.post([{"product": p.pk, "quantity": 3}]).status_code, 201)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 0)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}]).status_code, 400)

    def test_multi_item_failure_rolls_back_all(self):
        ok = self.make_product(sku="OK", name="Ok", stock=10)
        low = self.make_product(sku="LOW", name="Low", stock=1)
        self.as_cashier()
        r = self.post([{"product": ok.pk, "quantity": 5}, {"product": low.pk, "quantity": 2}])
        self.assertEqual(r.status_code, 400)
        ok.refresh_from_db()
        self.assertEqual(ok.stock_quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.filter(movement_type=MovementType.SALE).count(), 0)

    def test_discount_cannot_exceed_subtotal_or_be_negative(self):
        p = self.make_product(price="100.00", stock=5)
        self.as_cashier()
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}], discount="100.01").status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}], discount="-1").status_code, 400)
        ok = self.post([{"product": p.pk, "quantity": 1}], discount="100.00")
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(Decimal(ok.data["grand_total"]), Decimal("0.00"))

    def test_invoice_numbers_are_unique(self):
        p = self.make_product(stock=10)
        self.as_cashier()
        numbers = {self.post([{"product": p.pk, "quantity": 1}]).data["invoice_number"] for _ in range(5)}
        self.assertEqual(len(numbers), 5)
        self.assertTrue(all(n.startswith("INV-") for n in numbers))

    def test_validation_errors(self):
        p = self.make_product(stock=5, name="Off")
        inactive = self.make_product(sku="X", name="Inactive", stock=5, is_active=False)
        self.as_cashier()
        self.assertEqual(self.post([]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 0}]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": -1}]).status_code, 400)
        self.assertEqual(self.post([{"product": 9999, "quantity": 1}]).status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}], payment_method="bitcoin").status_code, 400)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}], customer=9999).status_code, 400)
        dup = self.post([{"product": p.pk, "quantity": 1}, {"product": p.pk, "quantity": 1}])
        self.assertEqual(dup.status_code, 400)
        self.assertEqual(self.post([{"product": inactive.pk, "quantity": 1}]).status_code, 400)
        self.assertEqual(Sale.objects.count(), 0)

    def test_all_payment_methods_and_optional_customer(self):
        p = self.make_product(stock=10)
        customer = Customer.objects.create(name="Buyer")
        self.as_cashier()
        for method in ("cash", "card", "mobile_banking"):
            r = self.post([{"product": p.pk, "quantity": 1}], payment_method=method)
            self.assertEqual(r.status_code, 201)
            self.assertIsNone(r.data["customer"])
        r = self.post([{"product": p.pk, "quantity": 1}], customer=customer.pk)
        self.assertEqual(r.data["customer_name"], "Buyer")

    def test_unauthenticated_cannot_sell(self):
        p = self.make_product(stock=5)
        self.assertEqual(self.post([{"product": p.pk, "quantity": 1}]).status_code, 401)

    def test_cashier_sees_only_own_sales_admin_sees_all(self):
        p = self.make_product(stock=20)
        self.as_cashier()
        mine = self.post([{"product": p.pk, "quantity": 1}]).data["id"]
        self.as_admin()
        theirs = self.post([{"product": p.pk, "quantity": 1}]).data["id"]
        self.assertEqual(self.client.get("/api/sales/").data["count"], 2)
        self.as_cashier()
        r = self.client.get("/api/sales/")
        self.assertEqual([s["id"] for s in r.data["results"]], [mine])
        self.assertEqual(self.client.get(f"/api/sales/{theirs}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/sales/{mine}/").status_code, 200)

    def test_sales_cannot_be_edited_or_deleted(self):
        p = self.make_product(stock=5)
        self.as_admin()
        pk = self.post([{"product": p.pk, "quantity": 1}]).data["id"]
        self.assertEqual(self.client.patch(f"/api/sales/{pk}/", {"discount": "1"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/sales/{pk}/").status_code, 405)

    def test_list_filters_and_search(self):
        p = self.make_product(stock=20)
        customer = Customer.objects.create(name="Zed Buyer")
        self.as_admin()
        a = self.post([{"product": p.pk, "quantity": 1}], payment_method="card", customer=customer.pk).data
        self.post([{"product": p.pk, "quantity": 1}], payment_method="cash")
        self.assertEqual(self.client.get("/api/sales/?payment_method=card").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/sales/?customer={customer.pk}").data["count"], 1)
        self.assertEqual(self.client.get("/api/sales/?search=zed").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/sales/?search={a['invoice_number']}").data["count"], 1)
        self.assertEqual(self.client.get("/api/sales/?start_date=2999-01-01").data["count"], 0)
        self.assertEqual(self.client.get("/api/sales/?start_date=bad").status_code, 400)

    def test_database_blocks_negative_stock(self):
        from django.db import IntegrityError, transaction
        from products.models import Product

        p = self.make_product(stock=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=p.pk).update(stock_quantity=-1)
