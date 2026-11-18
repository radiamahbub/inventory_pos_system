# Inventory POS — Frontend

React 18 + TypeScript + Vite + Tailwind CSS single-page app for the Django backend in `../backend`.

## Quick start
```bash
cd frontend
cp .env.example .env     # optional
npm install
npm run dev              # http://localhost:5173
```
Start the backend first (`python manage.py runserver`, port 8000). Sign in with your superuser (Admin) or any Cashier created from **Users**.

## Scripts
| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run typecheck` | TypeScript type-check only |
| `npm run build` | Type-check + production build in `dist/` |
| `npm run preview` | Serve the production build locally |

## Environment
| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:8000/api` | Backend API base URL |

## Project structure
```
src/
├── api/client.ts          Axios instance, token storage, automatic refresh on 401
├── context/AuthContext    login / logout / current user / isAdmin
├── hooks/                 useFetch, usePagedList (filter-aware pagination), useDebounce
├── components/
│   ├── layout/            AppLayout, Sidebar, Topbar, nav config (role-aware)
│   ├── ui/                Modal, ConfirmDialog, DataTable, Pagination, Card/StatCard, Form helpers, ProductSearch, feedback components
│   ├── ResourcePage.tsx   Generic CRUD page (used by Categories, Suppliers, Customers, Users)
│   └── ProtectedRoute.tsx ProtectedRoute + RoleRoute
├── pages/                 Login, Dashboard, POS, Sales, Invoice, Products, Categories, Inventory,
│                          Customers, Suppliers, Purchases, NewPurchase, Reports, Users, Profile, NotFound
├── types/                 API response types
└── utils/                 formatting (৳, dates in Asia/Dhaka), DRF error parser, chart helpers
```

## Design notes
- Tailwind with a custom `brand` (indigo) palette; reusable component classes (`btn`, `input`, `card`, `th`, `td`) live in `src/index.css`.
- Responsive: sidebar becomes a slide-in drawer on small screens; tables scroll horizontally; POS cart stacks under the product grid on narrow screens.
- Invoices print cleanly (`window.print()`; navigation is hidden with Tailwind `print:` variants).

## Manual test checklist
1. **Login** — wrong password shows an error; correct login lands on the dashboard; refreshing the page keeps you signed in.
1a. **Register** — open `/register`, create an account → redirected to login with an "awaiting approval" notice; signing in fails until the Admin approves it (*Users → Approve* or the dashboard banner); then it works and the user is a Cashier. Try a weak password / mismatched confirmation / existing username to see field errors.
1b. **Sign out** — use the *Sign out* button at the bottom of the sidebar (or the top-right menu).
2. **Admin setup** — add a category, a supplier and a product (with opening stock); create a Cashier from *Users*.
3. **Purchase** — *Purchases → New purchase*; confirm the product's stock increased and the cost price updated.
4. **POS** — sell 2 items with a discount; invoice opens; stock decreases; try selling more than the stock → error message.
5. **Cashier** — sign in as the Cashier: no Purchases / Reports / Users in the menu; `/reports` shows *Access denied*; only own sales are visible; the Products table has no *Cost* column (and the API no longer sends `purchase_price`).
6. **Inventory** — adjust stock with a reason; the *Movement history* tab shows the entry; negative stock is rejected.
7. **Reports** — daily / monthly / yearly numbers match the sales you created; low-stock tab lists products at or below minimum.
8. **Logout** — signing out returns to the login page and protected URLs redirect to login.
