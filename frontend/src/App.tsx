import { Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute, RoleRoute } from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import PosPage from './pages/PosPage';
import SalesPage from './pages/SalesPage';
import InvoicePage from './pages/InvoicePage';
import ReturnsPage from './pages/ReturnsPage';
import ReceiptPage from './pages/ReceiptPage';
import ProductsPage from './pages/ProductsPage';
import CategoriesPage from './pages/CategoriesPage';
import InventoryPage from './pages/InventoryPage';
import CustomersPage from './pages/CustomersPage';
import CustomerLedgerPage from './pages/CustomerLedgerPage';
import SuppliersPage from './pages/SuppliersPage';
import PurchasesPage from './pages/PurchasesPage';
import NewPurchasePage from './pages/NewPurchasePage';
import ReportsPage from './pages/ReportsPage';
import UsersPage from './pages/UsersPage';
import ProfilePage from './pages/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="pos" element={<PosPage />} />
        <Route path="sales" element={<SalesPage />} />
        <Route path="sales/:id" element={<InvoicePage />} />
        <Route path="sales/:id/receipt" element={<ReceiptPage />} />
        <Route path="returns" element={<ReturnsPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="customers" element={<CustomersPage />} />
        <Route path="customers/:id/ledger" element={<CustomerLedgerPage />} />
        <Route path="suppliers" element={<SuppliersPage />} />
        <Route path="profile" element={<ProfilePage />} />

        {/* শুধু Admin */}
        <Route
          path="purchases"
          element={
            <RoleRoute roles={['admin']}>
              <PurchasesPage />
            </RoleRoute>
          }
        />
        <Route
          path="purchases/new"
          element={
            <RoleRoute roles={['admin']}>
              <NewPurchasePage />
            </RoleRoute>
          }
        />
        <Route
          path="reports"
          element={
            <RoleRoute roles={['admin']}>
              <ReportsPage />
            </RoleRoute>
          }
        />
        <Route
          path="users"
          element={
            <RoleRoute roles={['admin']}>
              <UsersPage />
            </RoleRoute>
          }
        />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
