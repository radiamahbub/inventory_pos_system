import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, ShoppingCart } from 'lucide-react';
import { Card, PageHeader } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Feedback';
import { SearchInput } from '@/components/ui/Form';
import { Pagination } from '@/components/ui/Pagination';
import { useAuth } from '@/context/AuthContext';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagedList } from '@/hooks/useFetch';
import type { PaymentMethod, Sale } from '@/types';
import { fmtDateTime, money } from '@/utils/format';

export const PAYMENT_TONE: Record<PaymentMethod, 'green' | 'blue' | 'indigo'> = {
  cash: 'green',
  card: 'blue',
  mobile_banking: 'indigo',
};

export default function SalesPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [payment, setPayment] = useState('');
  const [returnStatus, setReturnStatus] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const debounced = useDebounce(search);

  const list = usePagedList<Sale>('/sales/', {
    search: debounced,
    payment_method: payment,
    return_status: returnStatus,
    payment_status: paymentStatus,
    start_date: start,
    end_date: end,
    ordering: '-sale_date',
  });

  const columns: Column<Sale>[] = [
    {
      key: 'invoice',
      header: 'Invoice',
      render: (s) => (
        <Link to={`/sales/${s.id}`} className="font-semibold text-brand-600 hover:underline" onClick={(e) => e.stopPropagation()}>
          {s.invoice_number}
        </Link>
      ),
    },
    { key: 'date', header: 'Date', render: (s) => <span className="whitespace-nowrap">{fmtDateTime(s.sale_date)}</span> },
    { key: 'customer', header: 'Customer', render: (s) => s.customer_name ?? <span className="text-slate-400">Walk-in</span> },
    { key: 'items', header: 'Items', align: 'right', render: (s) => s.item_count ?? '—' },
    { key: 'payment', header: 'Payment', render: (s) => <Badge tone={PAYMENT_TONE[s.payment_method]}>{s.payment_method_display}</Badge> },
    {
      key: 'total',
      header: 'Total',
      align: 'right',
      render: (s) => (
        <div className="flex flex-col items-end gap-1">
          <span className="font-semibold text-slate-900">{money(s.grand_total)}</span>
          {Number(s.due_amount) > 0 && <Badge tone="amber">Due {money(s.due_amount)}</Badge>}
          {s.return_status !== 'none' && (
            <Badge tone={s.return_status === 'full' ? 'red' : 'amber'}>
              {s.return_status === 'full' ? 'Returned' : `Returned ${money(s.returned_total)}`}
            </Badge>
          )}
        </div>
      ),
    },
  ];
  if (isAdmin) columns.push({ key: 'by', header: 'Cashier', render: (s) => s.created_by_username });
  columns.push({
    key: 'view',
    header: '',
    align: 'right',
    render: (s) => (
      <Link to={`/sales/${s.id}`} className="btn-icon" title="View invoice" onClick={(e) => e.stopPropagation()}>
        <Eye className="h-4 w-4" />
      </Link>
    ),
  });

  return (
    <>
      <PageHeader
        title="Sales"
        subtitle={isAdmin ? 'All sales and invoices.' : 'Your sales and invoices.'}
        actions={
          <Link to="/pos" className="btn btn-primary">
            <ShoppingCart className="h-4 w-4" /> New sale
          </Link>
        }
      />
      <Card bodyClassName="p-0">
        <div className="grid gap-3 border-b border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <SearchInput value={search} onChange={setSearch} placeholder="Invoice no. or customer…" />
          <select className="input" value={payment} onChange={(e) => setPayment(e.target.value)}>
            <option value="">All payment methods</option>
            <option value="cash">Cash</option>
            <option value="card">Card</option>
            <option value="mobile_banking">Mobile Banking</option>
          </select>
          <select className="input" value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)}>
            <option value="">All (paid or due)</option>
            <option value="paid">Fully paid</option>
            <option value="due">Has due</option>
            <option value="partial">Partly paid</option>
            <option value="unpaid">Unpaid</option>
          </select>
          <select className="input" value={returnStatus} onChange={(e) => setReturnStatus(e.target.value)}>
            <option value="">All (returned or not)</option>
            <option value="none">Not returned</option>
            <option value="partial">Partially returned</option>
            <option value="full">Fully returned</option>
          </select>
          <input type="date" className="input" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} aria-label="From date" />
          <input type="date" className="input" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} aria-label="To date" />
        </div>
        <DataTable
          columns={columns}
          rows={list.data?.results ?? []}
          rowKey={(s) => s.id}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          onRowClick={(s) => navigate(`/sales/${s.id}`)}
          emptyTitle="No sales found"
          emptyDescription="Sales created from the POS screen will appear here."
        />
        <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
      </Card>
    </>
  );
}
