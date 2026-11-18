from config.base_test import BaseAPITestCase
from suppliers.models import Supplier


class SupplierTests(BaseAPITestCase):
    data = {
        "name": "ABC Traders", "contact_person": "Karim", "phone": "+8801711000000",
        "email": "abc@example.com", "address": "Dhaka",
    }

    def test_admin_crud(self):
        self.as_admin()
        r = self.client.post("/api/suppliers/", self.data, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        self.assertEqual(self.client.patch(f"/api/suppliers/{pk}/", {"phone": "01711000001"}, format="json").status_code, 200)
        self.assertEqual(self.client.get(f"/api/suppliers/{pk}/").data["phone"], "01711000001")
        self.assertEqual(self.client.delete(f"/api/suppliers/{pk}/").status_code, 204)

    def test_validation(self):
        self.as_admin()
        self.assertEqual(self.client.post("/api/suppliers/", {**self.data, "phone": "abc"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/suppliers/", {**self.data, "email": "bad"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/suppliers/", {**self.data, "name": " "}, format="json").status_code, 400)

    def test_cashier_read_only(self):
        s = Supplier.objects.create(name="S1")
        self.as_cashier()
        self.assertEqual(self.client.get("/api/suppliers/").status_code, 200)
        self.assertEqual(self.client.post("/api/suppliers/", self.data, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/suppliers/{s.pk}/").status_code, 403)

    def test_search(self):
        Supplier.objects.create(name="Alpha", contact_person="Rahim")
        Supplier.objects.create(name="Beta", contact_person="Karim")
        self.as_admin()
        r = self.client.get("/api/suppliers/?search=karim")
        self.assertEqual([s["name"] for s in r.data["results"]], ["Beta"])
