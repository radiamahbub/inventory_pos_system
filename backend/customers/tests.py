from config.base_test import BaseAPITestCase
from customers.models import Customer


class CustomerTests(BaseAPITestCase):
    data = {"name": "Rahim Uddin", "phone": "01911000000", "email": "r@example.com", "address": "Mirpur"}

    def test_admin_crud(self):
        self.as_admin()
        r = self.client.post("/api/customers/", self.data, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        self.assertEqual(self.client.patch(f"/api/customers/{pk}/", {"name": "Rahim U."}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/customers/{pk}/").status_code, 204)

    def test_cashier_can_create_and_update_but_not_delete(self):
        self.as_cashier()
        r = self.client.post("/api/customers/", self.data, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        self.assertEqual(self.client.patch(f"/api/customers/{pk}/", {"address": "Uttara"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/customers/{pk}/").status_code, 403)

    def test_unauthenticated_blocked(self):
        self.assertEqual(self.client.get("/api/customers/").status_code, 401)

    def test_validation_and_search(self):
        Customer.objects.create(name="Walk Alpha", phone="01800000000")
        self.as_admin()
        self.assertEqual(self.client.post("/api/customers/", {**self.data, "phone": "x"}, format="json").status_code, 400)
        r = self.client.get("/api/customers/?search=0180")
        self.assertEqual(len(r.data["results"]), 1)

    def test_cannot_delete_customer_with_sales(self):
        product = self.make_product(stock=5)
        self.as_admin()
        customer = Customer.objects.create(name="Buyer")
        sale = self.client.post(
            "/api/sales/",
            {"customer": customer.pk, "payment_method": "cash", "items": [{"product": product.pk, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(sale.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/customers/{customer.pk}/").status_code, 409)
