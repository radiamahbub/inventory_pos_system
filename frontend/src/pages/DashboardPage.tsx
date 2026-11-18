import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertTriangle,
  ArrowRight,
  ClipboardList,
  UserCheck,
  Package,
  PackagePlus,
  Receipt,
  ShoppingCart,
  Tags,
  TrendingUp,
  Truck,
  Users,
  Wallet,
} from 'lucide-react';
import { api } from '@/api/client';
import { Card, StatCard } from '@/components/ui/Card';
import { Badge, ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { useAuth } from '@/context/AuthContext';
import { useFetch } from '@/hooks/useFetch';
import type { DailyReport, DashboardData, MonthlyReport, Paginated, Sale, StockItem, User } from '@/types';
import { CHART_COLORS, fillDaily } from '@/utils/charts';
import { PAYMENT_LABEL, compactMoney, fmtDateTime, fullName, greeting, money, todayISO } from '@/utils/format';
import { PAYMENT_TONE } from './SalesPage';

function QuickLink({ to, icon: Icon, label }: { to: string; icon: typeof Package; label: string }) {
  return (
    <Link to={to} className="btn btn-secondary">
      <Icon className="h-4 w-4 text-brand-600" /> {label}
    </Link>
  );
}

function RecentSales({ sales }: { sales: Sale[] }) {
  return (
    <Card
      title="Recent sales"
      bodyClassName="p-0"
      action={
        <Link to="/sales" className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline">
          View all <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      {sales.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-slate-500">No sales yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {sales.map((s) => (
            <li key={s.id}>
              <Link to={`/sales/${s.id}`} className="flex items-center justify-between gap-3 px-5 py-3 transition hover:bg-slate-50">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">{s.invoice_number}</p>
                  <p className="truncate text-xs text-slate-500">
                    {s.customer_name ?? 'Walk-in'} · {fmtDateTime(s.sale_date)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Badge tone={PAYMENT_TONE[s.payment_method]}>{s.payment_method_display}</Badge>
                  <span className="text-sm font-semibold text-slate-900">{money(s.grand_total)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function LowStockList({ items, total }: { items: StockItem[]; total: number }) {
  return (
    <Card
      title={`Low stock alerts${total ? ` (${total})` : ''}`}
      bodyClassName="p-0"
      action={
        <Link to="/inventory" className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline">
          Inventory <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      }
    >
      {items.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-slate-500">All products are well stocked 🎉</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{p.name}</p>
                <p className="text-xs text-slate-500">
                  {p.sku} · Min {p.min_stock_level}
                </p>
              </div>
              <Badge tone={p.stock_quantity === 0 ? 'red' : 'amber'}>
                {p.stock_quantity === 0 ? 'Out of stock' : `${p.stock_quantity} left`}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Admin dashboard                                                     */
/* ------------------------------------------------------------------ */
function AdminDashboard() {
  const today = todayISO();
  const year = Number(today.slice(0, 4));
  const month = Number(today.slice(5, 7));

  const { data, loading, error, reload } = useFetch(async () => {
    const [dash, monthly, daily, inactive] = await Promise.all([
      api.get<DashboardData>('/dashboard/'),
      api.get<MonthlyReport>('/reports/sales/monthly/', { params: { year, month } }),
      api.get<DailyReport>('/reports/sales/daily/', { params: { date: today } }),
      // self-register করা, approval-এর অপেক্ষায় থাকা অ্যাকাউন্ট (ব্যর্থ হলেও dashboard চলবে)
      api
        .get<Paginated<User>>('/users/', { params: { is_active: 'false', page_size: 100 } })
        .then((r) => r.data.results.filter((u) => !u.last_login).length)
        .catch(() => 0),
    ]);
    return { dash: dash.data, monthly: monthly.data, daily: daily.data, pending: inactive };
  }, [today]);

  if (loading && !data) return <PageLoader label="Loading dashboard…" />;
  if (error || !data) return <ErrorBanner message={error ?? 'Could not load the dashboard.'} onRetry={reload} />;

  const { dash, monthly, daily, pending } = data;
  const chartData = fillDaily(monthly.year, monthly.month, monthly.daily);
  const pieData = daily.payment_methods
    .map((p) => ({ name: PAYMENT_LABEL[p.payment_method] ?? p.payment_method, value: Number(p.total) }))
    .filter((p) => p.value > 0);
  const pieTotal = pieData.reduce((s, p) => s + p.value, 0);

  return (
    <div className="space-y-6">
      {pending > 0 && (
        <Link
          to="/users?status=inactive"
          className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-900 transition hover:bg-amber-100"
        >
          <span className="flex items-center gap-3">
            <UserCheck className="h-5 w-5 text-amber-600" />
            <span>
              <strong>{pending}</strong> new account{pending > 1 ? 's are' : ' is'} waiting for your approval.
            </span>
          </span>
          <span className="flex items-center gap-1 font-medium">
            Review <ArrowRight className="h-4 w-4" />
          </span>
        </Link>
      )}
      {Number(dash.total_due) > 0 && (
        <Link
          to="/customers?due=1"
          className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 transition hover:bg-amber-100"
        >
          <span className="flex items-center gap-2">
            <Users className="h-4 w-4 shrink-0" />
            <span>
              Customers owe you <strong>{money(dash.total_due)}</strong> ({dash.customers_with_due} customer
              {dash.customers_with_due > 1 ? 's' : ''}).
            </span>
          </span>
          <span className="flex items-center gap-1 font-medium">
            View dues <ArrowRight className="h-4 w-4" />
          </span>
        </Link>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's sales" value={money(dash.today_sales.total)} hint={`${dash.today_sales.sales_count} order(s) today`} icon={Wallet} tone="indigo" />
        <StatCard label="This month's sales" value={money(dash.monthly_sales.total)} hint={`${dash.monthly_sales.sales_count} order(s) this month`} icon={Receipt} tone="sky" />
        <StatCard label="Est. profit (month)" value={money(monthly.estimated_profit)} hint={`Cost of goods ${money(monthly.cost_of_goods_sold)}`} icon={TrendingUp} tone="emerald" />
        <StatCard
          label="Low stock items"
          value={dash.low_stock_count}
          hint={dash.low_stock_count > 0 ? 'Needs restocking' : 'Everything is stocked'}
          icon={AlertTriangle}
          tone={dash.low_stock_count > 0 ? 'rose' : 'amber'}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Products', value: dash.total_products, icon: Package, to: '/products', tone: 'text-brand-600 bg-brand-50' },
          { label: 'Categories', value: dash.total_categories, icon: Tags, to: '/categories', tone: 'text-violet-600 bg-violet-50' },
          { label: 'Customers', value: dash.total_customers, icon: Users, to: '/customers', tone: 'text-sky-600 bg-sky-50' },
          { label: 'Suppliers', value: dash.total_suppliers, icon: Truck, to: '/suppliers', tone: 'text-amber-600 bg-amber-50' },
        ].map((t) => (
          <Link key={t.label} to={t.to} className="card flex items-center gap-4 p-4 transition hover:border-brand-300 hover:shadow-md">
            <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${t.tone}`}>
              <t.icon className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-xl font-bold text-slate-900">{t.value}</span>
              <span className="block text-xs text-slate-500">{t.label}</span>
            </span>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Sales this month" className="lg:col-span-2" action={<span className="text-xs text-slate-500">{money(monthly.grand_total)} total</span>}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#4f46e5" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} interval="preserveStartEnd" />
                <YAxis tickLine={false} axisLine={false} width={52} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => compactMoney(Number(v))} />
                <Tooltip
                  formatter={(value) => money(Number(value))}
                  labelFormatter={(label) => `Day ${label}`}
                  contentStyle={{ borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 12 }}
                />
                <Area type="monotone" dataKey="total" name="Sales" stroke="#4f46e5" strokeWidth={2.5} fill="url(#salesFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Today's payment methods">
          {pieData.length === 0 ? (
            <div className="flex h-72 flex-col items-center justify-center text-center text-sm text-slate-400">
              <Wallet className="mb-2 h-8 w-8" />
              No sales recorded today
            </div>
          ) : (
            <>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={3} stroke="none">
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => money(Number(value))} contentStyle={{ borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-2 space-y-2 text-sm">
                {pieData.map((p, i) => (
                  <li key={p.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-slate-600">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                      {p.name}
                    </span>
                    <span className="font-medium text-slate-900">
                      {money(p.value)} <span className="text-xs text-slate-400">({Math.round((p.value / pieTotal) * 100)}%)</span>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentSales sales={dash.recent_sales} />
        <LowStockList items={dash.low_stock_products} total={dash.low_stock_count} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Cashier dashboard                                                   */
/* ------------------------------------------------------------------ */
function CashierDashboard() {
  const today = todayISO();
  const { data, loading, error, reload } = useFetch(async () => {
    const [sales, low] = await Promise.all([
      api.get<Paginated<Sale>>('/sales/', { params: { start_date: today, end_date: today, page_size: 100, ordering: '-sale_date' } }),
      api.get<Paginated<StockItem>>('/inventory/stock/low-stock/', { params: { page_size: 8 } }),
    ]);
    return { sales: sales.data, low: low.data };
  }, [today]);

  if (loading && !data) return <PageLoader label="Loading…" />;
  if (error || !data) return <ErrorBanner message={error ?? 'Could not load data.'} onRetry={reload} />;

  const total = data.sales.results.reduce((s, x) => s + Number(x.grand_total), 0);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="My sales today" value={money(total)} hint={`${data.sales.count} order(s)`} icon={Wallet} tone="indigo" />
        <StatCard label="Low stock items" value={data.low.count} hint="Tell your manager to restock" icon={AlertTriangle} tone={data.low.count > 0 ? 'rose' : 'emerald'} />
        <Link
          to="/pos"
          className="card flex items-center justify-between gap-4 bg-gradient-to-br from-brand-600 to-brand-800 p-5 text-white transition hover:shadow-lg"
        >
          <span>
            <span className="block text-sm text-brand-100">Ready to sell?</span>
            <span className="mt-1 block text-xl font-bold">Start a new sale</span>
          </span>
          <ShoppingCart className="h-9 w-9 text-brand-200" />
        </Link>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <RecentSales sales={data.sales.results.slice(0, 6)} />
        <LowStockList items={data.low.results} total={data.low.count} />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, isAdmin } = useAuth();
  if (!user) return null;

  return (
    <>
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {greeting()}, {fullName(user)} 👋
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {isAdmin ? "Here's what's happening in your business today." : 'Here is your shift overview.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <QuickLink to="/pos" icon={ShoppingCart} label="New sale" />
          {isAdmin && <QuickLink to="/products" icon={PackagePlus} label="Add product" />}
          {isAdmin && <QuickLink to="/purchases/new" icon={ClipboardList} label="New purchase" />}
        </div>
      </div>
      {isAdmin ? <AdminDashboard /> : <CashierDashboard />}
    </>
  );
}
