# PROGRESS

## Backend — ✅ Complete (Phases 1–10) · Frontend — ✅ Complete (Phases F1–F8)

### Completed
- **Phase 1** — Monorepo layout (`backend/`, `frontend/`), Django project `config`, 10 apps, settings (SQLite, DRF, Simple JWT + blacklist, CORS, drf-spectacular)
- **Phase 2** — Custom `User` with `role` (Admin / Cashier), JWT login / refresh / logout (blacklist), `me`, change-password, Admin-only user management, role permissions
- **Phase 3** — Category and Product APIs (unique name / SKU, search, filters, low-stock detection)
- **Phase 4** — Supplier and Customer APIs
- **Phase 5** — Purchases: multi-item, server-side totals, automatic stock increase, weighted-average cost, history
- **Phase 6** — POS sales: multi-item, server-side prices and totals, discount, payment method, unique invoice number, automatic stock decrease, no overselling
- **Phase 7** — Inventory: current stock, stock-movement history, Admin adjustment, low-stock list, no negative stock (service + DB constraints)
- **Phase 8** — Reports (daily / monthly / yearly sales, total sales, total purchases, estimated profit, low-stock) and Dashboard
- **Phase 9** — Swagger / ReDoc / OpenAPI schema with examples (schema validates with zero warnings), 93 automated tests, security review
- **Phase 10** — Final verification: `check`, `makemigrations --check`, full test suite, schema validation and a real end-to-end run (login → product → purchase → sale → reports → logout)

### Frontend — Completed
- **Phase F1** — Vite + React + TypeScript + Tailwind setup, API client with JWT + automatic refresh, `AuthContext`, protected / role-based routes, **Login page**
- **Phase F2** — App layout: responsive sidebar (role-aware menu), top bar with user menu, shared UI kit (modal, confirm dialog, data table, pagination, badges, empty / error / loading states)
- **Phase F3** — Professional **Dashboard**: KPI cards, monthly sales area chart, payment-method donut, low-stock alerts, recent sales, quick actions (Admin) + shift overview (Cashier)
- **Phase F4** — Catalog: Products (filters, stock badges, create / edit / delete), Categories
- **Phase F5** — **POS screen**: product grid with search and category filter, cart, customer, discount, payment method, server-side validation errors, success dialog
- **Phase F6** — Sales list with filters, **printable invoice** page
- **Phase F7** — Suppliers, Customers, Users (Admin), Purchases (list, details, multi-item new purchase), Inventory (current stock, movement history, stock adjustment)
- **Phase F8** — Reports (daily / monthly / yearly with charts, financial summary, low stock), Profile & change password, 404 page, documentation

### Auth & Role-based access — Phase A1 ✅
- **Register:** public `POST /api/auth/register/` (always Cashier, strong-password validation, case-insensitive unique username, rate limited) + `GET /api/auth/registration-status/`; env switches `SELF_REGISTRATION_ENABLED` / `SELF_REGISTRATION_AUTO_APPROVE`
- **Approval flow:** new accounts are inactive until an Admin approves them (Users page *Approve* button, *Pending approval* badge, dashboard banner)
- **Frontend:** `/register` page (password strength meter, show/hide, per-field server errors), shared auth layout, Login shows *Create an account* only when enabled and a success notice after registering
- **Sidebar:** user card + **Sign out** button (Topbar menu keeps Sign out too)
- **RBAC audit & fixes:** every backend view already had an explicit permission class; added — product `purchase_price` (cost) hidden from Cashier API responses, role/status re-sync when the tab regains focus, Users page status filter + approve action
- **New backend tests (not yet run — Django is not available in the sandbox where this was written; run `python manage.py test`):** 10 registration tests, 2 cost-price visibility tests

### Frontend — Verification note
- All source files pass TypeScript syntax parsing and every import resolves to an existing file.
- Run `python manage.py test` (backend) and `npm install && npm run build` (frontend) on your machine to run the full type-check and production build, then follow the manual test checklist in `frontend/README.md`.

### Phase 1 (daily shop work) — Sales return / refund ✅
- **Backend:** `SaleReturn` / `SaleReturnItem` models, `POST /api/sales/{id}/returns/`, `GET /api/returns/`, new stock movement type `return`, returns reflected in reports (net sales and profit), migrations `inventory 0002`, `sales 0002`
- **Frontend:** *Return items* on the invoice page (quantity per item, refund method, reason), returns history on the invoice, new **Returns** page, return badges and filter on Sales, returns shown in Reports
- **Tests:** `sales/test_returns.py` (16 tests) — not run in the sandbox where this was written (Django unavailable); run `python manage.py test`
### Phase 1 — Due sale + customer ledger ✅
- **Backend:** `paid_amount` on sales (due / credit sale needs a customer), `CustomerPayment` (collections, applied oldest invoice first), customer `balance`, `GET /customers/{id}/ledger/`, `POST /customers/{id}/payments/`, `?has_due=` and `?payment_status=` filters, returns now split into refund vs. due cancelled, dashboard `total_due`, migrations `sales 0003`, `customers 0002` (old sales are marked fully paid)
- **Frontend:** *Amount received* + due in POS, due badges on Sales and invoice, **Due** column and filter on Customers, new **Customer ledger** page with *Collect payment* and print, due banner on the Dashboard
- **Tests:** `sales/test_due_sales.py` — not run in the sandbox (Django unavailable); run `python manage.py test`
### Phase 1 — PDF invoice + 80 mm receipt ✅
- **Backend:** ReportLab PDFs (`GET /sales/{id}/invoice-pdf/` A4, `/receipt-pdf/` 80 mm), `GET /api/shop/`, shop details via env (`SHOP_*`), optional Bengali font (`PDF_FONT_*`), `reportlab` added to requirements
- **Frontend:** *A4 PDF* and *80mm receipt* buttons on the invoice, new browser-print **Receipt page** (`/sales/:id/receipt`, `@page` 80mm; `?print=1` opens the print dialog), POS *Print receipt* button, shop name / address / footer on the invoice
- **Tests:** `sales/test_pdf.py` — not run in the sandbox; the two PDF builders were smoke-tested and checked visually
- **Still to do from this phase:** barcode scan in POS, CSV product import / export

### Pending (optional ideas)
- Product images, automated frontend tests (Vitest + Testing Library), Docker / deployment configuration
