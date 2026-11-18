# API DOCUMENTATION

Interactive docs (backend on port 8000): **Swagger** `/api/docs/` · **ReDoc** `/api/redoc/` · **OpenAPI schema** `/api/schema/` (all public).
Browsable API root: `/api/`.

## Authentication
1. `POST /api/auth/login/` with `{"username": "...", "password": "..."}`
2. Send `Authorization: Bearer <access>` on every other request.
3. Access token lives 30 minutes; refresh with `POST /api/auth/refresh/`. Refresh tokens rotate and old ones are blacklisted.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" \
  -d '{"username":"admin1","password":"StrongPass123!"}'
```
Response:
```json
{"access": "<jwt>", "refresh": "<jwt>", "user": {"id": 1, "username": "admin1", "role": "admin", "...": "..."}}
```

## Common behaviour
- List endpoints are paginated: `{"count", "next", "previous", "results"}`. Use `?page=2&page_size=50` (max 100).
- Most lists support `?search=...` and `?ordering=field` / `?ordering=-field`.
- Money fields are returned as strings with two decimals (e.g. `"1030.00"`).
- Dates: `YYYY-MM-DD`. Invalid filter values return `400`.

## Endpoints

### Auth
| Method | URL | Who | Description |
|---|---|---|---|
| POST | /api/auth/register/ | public (rate limited) | Self-register. Always creates a **Cashier**; `role` in the body is ignored. Body: `username`, `first_name`, `last_name?`, `email?`, `password`, `confirm_password`. Returns 201 `{detail, requires_approval, user}`; 403 if registration is disabled |
| GET | /api/auth/registration-status/ | public | `{"enabled": bool, "requires_approval": bool}` — lets the UI hide the Register link |
| POST | /api/auth/login/ | public | Get access + refresh token and user info (inactive / not-yet-approved accounts get 401) |
| POST | /api/auth/refresh/ | public (needs refresh token) | New access token (refresh token rotates) |
| POST | /api/auth/logout/ | public (needs refresh token) | Blacklist refresh token. Body `{"refresh": "..."}` → 205 |
| GET | /api/auth/me/ | any user | Current user |
| POST | /api/auth/change-password/ | any user | `{"old_password","new_password"}` |

### Users (Admin only)
| Method | URL | Description |
|---|---|---|
| GET / POST | /api/users/ | List (`?role=admin|cashier`, `?is_active=true`, `?search=`) / create (`username`, `password`, `role`, ...) |
| GET / PUT / PATCH / DELETE | /api/users/{id}/ | Retrieve / update (optional `password` resets it) / delete |

Approving a self-registered account = `PATCH /api/users/{id}/` with `{"is_active": true}`.

Rules: cannot delete or demote yourself, at least one active Admin must remain, users with history are deactivated instead of deleted.

### Categories — Admin write, Cashier read
`GET/POST /api/categories/` · `GET/PUT/PATCH/DELETE /api/categories/{id}/` — `name` unique (case-insensitive). Delete returns 409 if products use it.

### Products — Admin write, Cashier read
`GET/POST /api/products/` · `GET/PUT/PATCH/DELETE /api/products/{id}/` · `GET /api/products/low-stock/`

> `purchase_price` (cost) is **only returned to Admin users** — it is removed from every product response for Cashiers.

Create example:
```json
{"name": "Rice 5kg", "sku": "rice-5", "category": 1, "purchase_price": "300.00",
 "selling_price": "350.00", "min_stock_level": 5, "initial_stock": 20}
```
- `sku` is unique and stored upper-case. `stock_quantity` is read-only: change it only by purchase, sale or inventory adjustment. `initial_stock` (create only) records an *opening* movement.
- Filters: `?search=` (name, SKU, category, description), `?category=ID`, `?low_stock=true`, `?in_stock=true|false`, `?is_active=true`, `?min_price=`, `?max_price=`, `?ordering=`.
- `is_low_stock` is true when `stock_quantity <= min_stock_level`.

### Suppliers — Admin write, Cashier read
`GET/POST /api/suppliers/` · `GET/PUT/PATCH/DELETE /api/suppliers/{id}/` — fields: `name`, `contact_person`, `phone`, `email`, `address`.

### Customers — Admin and Cashier (delete: Admin only)
`GET/POST /api/customers/` · `GET/PUT/PATCH/DELETE /api/customers/{id}/` — fields: `name`, `phone`, `email`, `address`.

#### PDF invoice and 80 mm receipt
| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/sales/{id}/invoice-pdf/` | A4 invoice (`application/pdf`) with items, discount, returns, paid and due |
| GET | `/api/sales/{id}/receipt-pdf/` | 80 mm wide thermal receipt PDF (height fits the content) |
| GET | `/api/shop/` | Shop `name`, `address`, `phone`, `footer` (from the backend environment) |

Cashiers can only open PDFs of their own sales (others give `404`). Needs `pip install reportlab` (`503` if missing). Set `SHOP_NAME`, `SHOP_ADDRESS`, `SHOP_PHONE`, `SHOP_RECEIPT_FOOTER` in the environment (see `.env.example`). Built-in PDF fonts cannot draw Bengali letters or ৳, so PDFs print amounts as "Tk 1,250.00"; to print Bengali text set `PDF_FONT_REGULAR` / `PDF_FONT_BOLD` to a Bengali-capable `.ttf` file.

#### Due sales and customer ledger
| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/sales/` | New optional field `paid_amount`. Omit = paid in full. Lower than the total = **due (credit) sale**; a `customer` is then required (`400` otherwise). Cannot be negative or above the total. |
| GET | `/api/sales/?payment_status=` | `paid`, `due` (any unpaid balance), `partial`, `unpaid` |
| GET | `/api/customers/` | Each customer has `balance` (what they owe; `0.00` = nothing). `?has_due=true` lists only customers who owe money. |
| GET | `/api/customers/{id}/ledger/` | Statement: sales, amount paid at sale, returns and later collections in date order, with a running `balance`, plus `total_sales`, `total_received`, `balance`. |
| GET | `/api/customers/{id}/payments/` | Paginated list of collections |
| POST | `/api/customers/{id}/payments/` | Collect due. Body `{"amount":"500.00","payment_method":"cash","note":""}`. Applied to the **oldest unpaid invoices first**. `400` if there is no due or the amount is more than the due. |

Sale fields added: `paid_amount`, `collected_amount`, `total_paid`, `due_amount`, `payment_status` (`paid | partial | unpaid`).
Balance = sum over the customer's sales of `grand_total − paid_amount − collected_amount − (returned_total − refunded_total)`.
Reports: the payment-method breakdown now counts only money actually received at the sale. Dashboard has `total_due` and `customers_with_due`.

#### Returns on due sales
For a return the server compares what the customer has paid with the value of the goods they keep. If they paid more, the difference is refunded (`refund_amount`); the rest cancels part of their unpaid balance (`due_adjusted`). `total_amount = refund_amount + due_adjusted`.

### Purchases — Admin only (create / read only)
`GET/POST /api/purchases/` · `GET /api/purchases/{id}/` · filters `?supplier=`, `?start_date=`, `?end_date=`, `?search=`

Request:
```json
{"supplier": 1, "purchase_date": "2026-11-13", "note": "Monthly restock",
 "items": [{"product": 1, "quantity": 20, "unit_price": "45.00"}]}
```
Response (201): `reference_no` (`PUR-20261113-000001`), `total_amount` (calculated by the server), `items[]`. Stock increases automatically and the product cost becomes the weighted average.

### Sales / POS — Admin and Cashier (create / read only)
`GET/POST /api/sales/` · `GET /api/sales/{id}/` (invoice) · filters `?customer=`, `?payment_method=cash|card|mobile_banking`, `?start_date=`, `?end_date=`, `?search=` (invoice no., customer). Cashiers only see their own sales.

Request:
```json
{"customer": 1, "payment_method": "cash", "discount": "50.00",
 "items": [{"product": 1, "quantity": 2}, {"product": 3, "quantity": 1}]}
```
Response (201): `invoice_number` (`INV-20261113-000001`), `subtotal`, `discount`, `grand_total`, `items[]` with the price used. `customer` is optional.

Errors (400): `{"items": ["Insufficient stock for 'Rice 5kg': available 1, requested 2."]}`, `{"discount": "Discount cannot be greater than the subtotal."}`

### Sales returns / refunds — Admin and Cashier (Cashier: own sales only)
| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/sales/{id}/returns/` | Return items of an invoice. Body: `{"items":[{"sale_item":12,"quantity":1}], "reason":"Damaged", "refund_method":"cash"}` (`reason`, `refund_method` optional; method defaults to the original payment method). Returns **201** with the return. |
| GET | `/api/returns/` | List returns. Filters: `sale`, `start_date`, `end_date`, `search` (return no., invoice, customer, reason) |
| GET | `/api/returns/{id}/` | Return details with items |

Rules
- Full or partial, repeatable until every item is returned. Item quantity cannot exceed what is still returnable (`400`).
- Stock goes back in (stock movement type `return`, reference = `RET-YYYYMMDD-000001`).
- Refund = value of returned goods. The invoice discount is spread across the items, so one item is worth `unit_price × grand_total ÷ subtotal`; the total refunded can never exceed the invoice grand total.
- All-or-nothing (one DB transaction). A Cashier can only return their own sales (others give `404`).
- `GET /api/sales/{id}/` now also returns `returned_total`, `net_total`, `return_status` (`none | partial | full`), `returns[]`, and per item `returned_quantity` / `returnable_quantity`. `GET /api/sales/?return_status=` filters.
- Reports: `returns_total` and `net_sales` added. `grand_total` stays the gross sales of the period; returns made in the period are subtracted, and the cost of returned goods is taken out of `cost_of_goods_sold`, so `estimated_profit` stays correct.

### Inventory
| Method | URL | Who | Description |
|---|---|---|---|
| GET | /api/inventory/stock/ | Admin, Cashier | Current stock (`?low_stock=true`, `?category=`, `?search=`) |
| GET | /api/inventory/stock/{id}/ | Admin, Cashier | Stock of one product |
| GET | /api/inventory/stock/low-stock/ | Admin, Cashier | Products at/below minimum level |
| GET | /api/inventory/movements/ | Admin | History (`?product=`, `?movement_type=opening|purchase|sale|adjustment`, `?start_date=`, `?end_date=`) |
| POST | /api/inventory/adjust/ | Admin | `{"product": 1, "quantity_change": -3, "reason": "Damaged"}` — cannot make stock negative |

### Reports — Admin only
| URL | Query | Description |
|---|---|---|
| GET /api/reports/sales/daily/ | `date` (default today) | Totals, profit, payment-method breakdown |
| GET /api/reports/sales/monthly/ | `year`, `month` | Totals, profit, per-day totals |
| GET /api/reports/sales/yearly/ | `year` | Totals, profit, per-month totals |
| GET /api/reports/summary/ | `start_date`, `end_date` | Total sales, total purchases, estimated profit |
| GET /api/reports/low-stock/ | – | Low-stock products with `shortage` |

Estimated profit = total sales after discount − cost of goods sold (cost snapshot saved on each sale item).

### Dashboard — Admin only
`GET /api/dashboard/` → `total_products`, `total_categories`, `total_customers`, `total_suppliers`, `today_sales`, `monthly_sales`, `low_stock_count`, `low_stock_products` (10), `recent_sales` (5).

### Other
`GET /api/health/` (public) → `{"status": "ok", ...}`

## Notes for frontend developers
- Base URL is configured in `frontend/.env` (`VITE_API_URL`, default `http://127.0.0.1:8000/api`).
- Always send decimal values as strings with two decimals (`"45.00"`). Responses return money as strings too.
- Boolean query filters must be `true` / `false` (strings); the frontend omits a filter instead of sending an empty value.
- Dropdowns (categories, suppliers, customers) request `?page_size=100`, the maximum allowed page size.
- On `400` read field errors from the JSON body (`{"sku": ["..."]}`); on `409` show `detail` (record cannot be deleted).
- CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` (Vite dev server).
