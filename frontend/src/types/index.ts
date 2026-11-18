export type Role = 'admin' | 'cashier';
/** Django DecimalField গুলো API থেকে string হিসেবে আসে (যেমন "1030.00") */
export type Money = string;

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Category {
  id: number;
  name: string;
  description: string;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  category: number;
  category_name: string;
  /** শুধু Admin-এর response-এ থাকে; Cashier পায় না */
  purchase_price?: Money;
  selling_price: Money;
  stock_quantity: number;
  min_stock_level: number;
  description: string;
  is_active: boolean;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  email: string;
  address: string;
  /** কাস্টমার দোকানকে কত বাকি দেবে ("0.00" = বাকি নেই) */
  balance: Money;
  created_at: string;
  updated_at: string;
}

export type PaymentMethod = 'cash' | 'card' | 'mobile_banking';

export interface SaleItem {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  returned_quantity: number;
  returnable_quantity: number;
  unit_price: Money;
  line_total: Money;
}

export type PaymentStatus = 'paid' | 'partial' | 'unpaid';
export type ReturnStatus = 'none' | 'partial' | 'full';

export interface SaleReturnItem {
  id: number;
  sale_item: number;
  product: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  /** ইনভয়েসের ডিসকাউন্ট ভাগ করার পর প্রতি পিসের ফেরতের দাম */
  unit_price: Money;
  line_total: Money;
}

export interface SaleReturn {
  id: number;
  return_number: string;
  sale: number;
  invoice_number: string;
  customer_name: string | null;
  return_date: string;
  total_amount: Money;
  /** কাস্টমারকে ফেরত দেওয়া টাকা */
  refund_amount: Money;
  /** যে অংশ কাস্টমারের বাকি কমিয়েছে (টাকা ফেরত যায়নি) */
  due_adjusted: Money;
  refund_method: PaymentMethod | '';
  refund_method_display: string;
  reason: string;
  created_by: number;
  created_by_username: string;
  items?: SaleReturnItem[];
  item_count?: number;
}

export interface Sale {
  id: number;
  invoice_number: string;
  customer: number | null;
  customer_name: string | null;
  sale_date: string;
  subtotal: Money;
  discount: Money;
  grand_total: Money;
  payment_method: PaymentMethod;
  payment_method_display: string;
  paid_amount: Money;
  collected_amount: Money;
  total_paid: Money;
  due_amount: Money;
  payment_status: PaymentStatus;
  returned_total: Money;
  refunded_total: Money;
  net_total: Money;
  return_status: ReturnStatus;
  note: string;
  created_by: number;
  created_by_username: string;
  items?: SaleItem[];
  returns?: SaleReturn[];
  item_count?: number;
}

export interface PurchaseItem {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: Money;
  line_total: Money;
}

export interface Purchase {
  id: number;
  reference_no: string;
  supplier: number;
  supplier_name: string;
  purchase_date: string;
  total_amount: Money;
  note: string;
  created_by: number;
  created_by_username: string;
  created_at: string;
  items?: PurchaseItem[];
  item_count?: number;
}

export interface CustomerPayment {
  id: number;
  reference: string;
  customer: number;
  amount: Money;
  payment_method: PaymentMethod;
  payment_method_display: string;
  payment_date: string;
  note: string;
  created_by_username: string;
}

export interface LedgerEntry {
  date: string;
  type: 'sale' | 'payment_at_sale' | 'return' | 'collection';
  reference: string;
  sale_id: number | null;
  description: string;
  debit: Money;
  credit: Money;
  balance: Money;
}

export interface CustomerLedger {
  customer: Customer;
  total_sales: Money;
  total_received: Money;
  balance: Money;
  entries: LedgerEntry[];
}

export interface ShopInfo {
  name: string;
  address: string;
  phone: string;
  footer: string;
}

export type MovementType = 'opening' | 'purchase' | 'sale' | 'return' | 'adjustment';

export interface StockItem {
  id: number;
  name: string;
  sku: string;
  category: number;
  category_name: string;
  stock_quantity: number;
  min_stock_level: number;
  is_low_stock: boolean;
  is_active: boolean;
}

export interface StockMovement {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  movement_type: MovementType;
  movement_type_display: string;
  quantity_change: number;
  quantity_before: number;
  quantity_after: number;
  reference: string;
  note: string;
  created_by: number | null;
  created_by_username: string | null;
  created_at: string;
}

/* ---------- Reports / Dashboard ---------- */
export interface SalesSummary {
  sales_count: number;
  subtotal: Money;
  discount: Money;
  grand_total: Money;
  returns_total: Money;
  net_sales: Money;
  cost_of_goods_sold: Money;
  estimated_profit: Money;
}
export interface PaymentBreakdown {
  payment_method: string;
  count: number;
  total: Money;
}
export interface DailyReport extends SalesSummary {
  date: string;
  payment_methods: PaymentBreakdown[];
}
export interface MonthlyReport extends SalesSummary {
  year: number;
  month: number;
  daily: { day: number; sales_count: number; grand_total: Money }[];
}
export interface YearlyReport extends SalesSummary {
  year: number;
  monthly: { month: number; sales_count: number; grand_total: Money }[];
}
export interface FinancialSummary {
  start_date: string | null;
  end_date: string | null;
  sales_count: number;
  total_sales: Money;
  returns_total: Money;
  net_sales: Money;
  purchases_count: number;
  total_purchases: Money;
  cost_of_goods_sold: Money;
  estimated_profit: Money;
}
export interface LowStockItem extends StockItem {
  shortage: number;
}
export interface LowStockReport {
  count: number;
  results: LowStockItem[];
}
export interface DashboardData {
  total_products: number;
  total_categories: number;
  total_customers: number;
  total_suppliers: number;
  today_sales: { sales_count: number; total: Money };
  monthly_sales: { sales_count: number; total: Money };
  total_due: Money;
  customers_with_due: number;
  low_stock_count: number;
  low_stock_products: StockItem[];
  recent_sales: Sale[];
}
