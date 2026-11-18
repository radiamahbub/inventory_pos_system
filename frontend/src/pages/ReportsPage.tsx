import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertTriangle, Banknote, Percent, Receipt, ShoppingBag, TrendingUp, Undo2, Wallet } from 'lucide-react';
import { api } from '@/api/client';
import { Card, PageHeader, StatCard } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge, ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { Field } from '@/components/ui/Form';
import { useFetch } from '@/hooks/useFetch';
import type { DailyReport, FinancialSummary, LowStockItem, LowStockReport, MonthlyReport, SalesSummary, YearlyReport } from '@/types';
import { CHART_COLORS, fillDaily, fillMonthly } from '@/utils/charts';
import { MONTHS, PAYMENT_LABEL, compactMoney, money, todayISO } from '@/utils/format';

type Tab = 'sales' | 'summary' | 'low-stock';
type Mode = 'daily' | 'monthly' | 'yearly';

const tooltipStyle = { borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 12 };

function SummaryCards({ s }: { s: SalesSummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <StatCard label="Orders" value={s.sales_count} icon={ShoppingBag} tone="sky" />
      <StatCard label="Gross sales" value={money(s.subtotal)} hint="Before discount" icon={Receipt} tone="indigo" />
      <StatCard label="Discounts given" value={money(s.discount)} icon={Percent} tone="amber" />
      <StatCard label="Sales (after discount)" value={money(s.grand_total)} hint="Before returns" icon={Wallet} tone="violet" />
      <StatCard label="Returns / refunds" value={money(s.returns_total)} hint="Refunded to customers" icon={Undo2} tone="amber" />
      <StatCard label="Net sales" value={money(s.net_sales)} hint="Sales − returns" icon={Wallet} tone="indigo" />
      <StatCard label="Cost of goods sold" value={money(s.cost_of_goods_sold)} icon={Banknote} tone="rose" />
      <StatCard label="Estimated profit" value={money(s.estimated_profit)} hint="Net sales − cost of goods sold" icon={TrendingUp} tone="emerald" />
    </div>
  );
}

function BarsCard({ title, data, xLabel }: { title: string; data: { label: string; total: number }[]; xLabel: string }) {
  return (
    <Card title={title}>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#64748b' }} interval={0} />
            <YAxis tickLine={false} axisLine={false} width={52} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => compactMoney(Number(v))} />
            <Tooltip formatter={(value) => money(Number(value))} labelFormatter={(l) => `${xLabel} ${l}`} contentStyle={tooltipStyle} cursor={{ fill: '#f1f5f9' }} />
            <Bar dataKey="total" name="Sales" fill="#4f46e5" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function SalesReportTab() {
  const now = todayISO();
  const [mode, setMode] = useState<Mode>('daily');
  const [date, setDate] = useState(now);
  const [year, setYear] = useState(Number(now.slice(0, 4)));
  const [month, setMonth] = useState(Number(now.slice(5, 7)));

  const { data, loading, error, reload } = useFetch<DailyReport | MonthlyReport | YearlyReport>(async () => {
    if (mode === 'daily') return (await api.get<DailyReport>('/reports/sales/daily/', { params: { date } })).data;
    if (mode === 'monthly') return (await api.get<MonthlyReport>('/reports/sales/monthly/', { params: { year, month } })).data;
    return (await api.get<YearlyReport>('/reports/sales/yearly/', { params: { year } })).data;
  }, [mode, date, year, month]);

  const years = Array.from({ length: 6 }, (_, i) => Number(now.slice(0, 4)) - i);

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
            {(['daily', 'monthly', 'yearly'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium capitalize transition ${
                  mode === m ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {mode === 'daily' && (
            <Field label="Date" className="lg:w-48">
              <input type="date" className="input" value={date} max={now} onChange={(e) => e.target.value && setDate(e.target.value)} />
            </Field>
          )}
          {mode === 'monthly' && (
            <>
              <Field label="Month" className="lg:w-44">
                <select className="input" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
                  {MONTHS.map((m, i) => (
                    <option key={m} value={i + 1}>
                      {m}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Year" className="lg:w-32">
                <select className="input" value={year} onChange={(e) => setYear(Number(e.target.value))}>
                  {years.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </Field>
            </>
          )}
          {mode === 'yearly' && (
            <Field label="Year" className="lg:w-32">
              <select className="input" value={year} onChange={(e) => setYear(Number(e.target.value))}>
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </Card>

      {loading && !data && <PageLoader label="Loading report…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}

      {data && !error && (
        <>
          <SummaryCards s={data} />

          {'payment_methods' in data && (
            <Card title="Payment method breakdown">
              {data.payment_methods.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">No sales on this date.</p>
              ) : (
                <div className="grid items-center gap-6 md:grid-cols-2">
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.payment_methods.map((p) => ({ name: PAYMENT_LABEL[p.payment_method] ?? p.payment_method, value: Number(p.total) }))}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={3}
                          stroke="none"
                        >
                          {data.payment_methods.map((_, i) => (
                            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => money(Number(value))} contentStyle={tooltipStyle} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="divide-y divide-slate-100 text-sm">
                    {data.payment_methods.map((p, i) => (
                      <li key={p.payment_method} className="flex items-center justify-between py-3">
                        <span className="flex items-center gap-2 text-slate-700">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                          {PAYMENT_LABEL[p.payment_method] ?? p.payment_method}
                          <span className="text-xs text-slate-400">· {p.count} sale(s)</span>
                        </span>
                        <span className="font-semibold text-slate-900">{money(p.total)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {'daily' in data && <BarsCard title={`Daily sales — ${MONTHS[data.month - 1]} ${data.year}`} data={fillDaily(data.year, data.month, data.daily)} xLabel="Day" />}
          {'monthly' in data && <BarsCard title={`Monthly sales — ${data.year}`} data={fillMonthly(data.monthly)} xLabel="" />}
        </>
      )}
    </div>
  );
}

function SummaryTab() {
  const now = todayISO();
  const [start, setStart] = useState(`${now.slice(0, 8)}01`);
  const [end, setEnd] = useState(now);

  const { data, loading, error, reload } = useFetch<FinancialSummary>(async () => {
    const { data } = await api.get<FinancialSummary>('/reports/summary/', { params: { start_date: start || undefined, end_date: end || undefined } });
    return data;
  }, [start, end]);

  return (
    <div className="space-y-6">
      <Card>
        <div className="grid gap-4 sm:grid-cols-2 lg:max-w-xl">
          <Field label="From date">
            <input type="date" className="input" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field label="To date">
            <input type="date" className="input" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} />
          </Field>
        </div>
      </Card>

      {loading && !data && <PageLoader label="Loading summary…" />}
      {error && <ErrorBanner message={error} onRetry={reload} />}
      {data && !error && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard label="Total sales" value={money(data.total_sales)} hint={`${data.sales_count} sale(s)`} icon={Wallet} tone="indigo" />
          <StatCard label="Returns / refunds" value={money(data.returns_total)} hint={`Net sales ${money(data.net_sales)}`} icon={Undo2} tone="amber" />
          <StatCard label="Total purchases" value={money(data.total_purchases)} hint={`${data.purchases_count} purchase(s)`} icon={ShoppingBag} tone="sky" />
          <StatCard label="Cost of goods sold" value={money(data.cost_of_goods_sold)} icon={Banknote} tone="rose" />
          <StatCard label="Estimated profit" value={money(data.estimated_profit)} hint="Net sales − cost of goods sold" icon={TrendingUp} tone="emerald" />
        </div>
      )}
    </div>
  );
}

function LowStockTab() {
  const { data, loading, error, reload } = useFetch<LowStockReport>(async () => {
    const { data } = await api.get<LowStockReport>('/reports/low-stock/');
    return data;
  }, []);

  const columns: Column<LowStockItem>[] = [
    {
      key: 'product',
      header: 'Product',
      render: (p) => (
        <div>
          <p className="font-medium text-slate-900">{p.name}</p>
          <p className="text-xs text-slate-500">SKU: {p.sku}</p>
        </div>
      ),
    },
    { key: 'category', header: 'Category', render: (p) => <Badge tone="slate">{p.category_name}</Badge> },
    { key: 'stock', header: 'In stock', align: 'right', render: (p) => <span className="font-semibold">{p.stock_quantity}</span> },
    { key: 'min', header: 'Min. level', align: 'right', render: (p) => p.min_stock_level },
    { key: 'short', header: 'Shortage', align: 'right', render: (p) => <Badge tone={p.stock_quantity === 0 ? 'red' : 'amber'}>{p.shortage}</Badge> },
  ];

  return (
    <Card
      title={`Products at or below minimum level${data ? ` (${data.count})` : ''}`}
      bodyClassName="p-0"
      action={<AlertTriangle className="h-4 w-4 text-amber-500" />}
    >
      <DataTable
        columns={columns}
        rows={data?.results ?? []}
        rowKey={(p) => p.id}
        loading={loading}
        error={error}
        onRetry={reload}
        emptyTitle="No low-stock products"
        emptyDescription="All products are above their minimum stock level."
      />
    </Card>
  );
}

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>('sales');
  const tabs: { id: Tab; label: string }[] = [
    { id: 'sales', label: 'Sales reports' },
    { id: 'summary', label: 'Financial summary' },
    { id: 'low-stock', label: 'Low stock' },
  ];

  return (
    <>
      <PageHeader title="Reports" subtitle="Sales performance, profit and stock insights." />
      <div className="mb-6 inline-flex flex-wrap rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              tab === t.id ? 'bg-brand-600 text-white shadow' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'sales' && <SalesReportTab />}
      {tab === 'summary' && <SummaryTab />}
      {tab === 'low-stock' && <LowStockTab />}
    </>
  );
}
