import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye } from 'lucide-react';
import { Card, PageHeader } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Feedback';
import { SearchInput } from '@/components/ui/Form';
import { Pagination } from '@/components/ui/Pagination';
import { useAuth } from '@/context/AuthContext';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagedList } from '@/hooks/useFetch';
import type { SaleReturn } from '@/types';
import { fmtDateTime, money } from '@/utils/format';

export default function ReturnsPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const debounced = useDebounce(search);

  const list = usePagedList<SaleReturn>('/returns/', {
    search: debounced,
    start_date: start,
    end_date: end,
    ordering: '-return_date',
  });

  const columns: Column<SaleReturn>[] = [
    { key: 'no', header: 'Return', render: (r) => <span className="font-semibold text-slate-900">{r.return_number}</span> },
    {
      key: 'invoice',
      header: 'Invoice',
      render: (r) => (
        <Link to={`/sales/${r.sale}`} className="font-medium text-brand-600 hover:underline" onClick={(e) => e.stopPropagation()}>
          {r.invoice_number}
        </Link>
      ),
    },
    { key: 'date', header: 'Date', render: (r) => <span className="whitespace-nowrap">{fmtDateTime(r.return_date)}</span> },
    { key: 'customer', header: 'Customer', render: (r) => r.customer_name ?? <span className="text-slate-400">Walk-in</span> },
    { key: 'items', header: 'Items', align: 'right', render: (r) => r.item_count ?? '—' },
    {
      key: 'method',
      header: 'Settled as',
      render: (r) => (
        <div className="flex flex-col gap-1">
          {Number(r.refund_amount) > 0 && <Badge tone="slate">{`${money(r.refund_amount)} via ${r.refund_method_display}`}</Badge>}
          {Number(r.due_adjusted) > 0 && <Badge tone="amber">{`${money(r.due_adjusted)} off due`}</Badge>}
        </div>
      ),
    },
    { key: 'reason', header: 'Reason', className: 'max-w-xs truncate', render: (r) => r.reason || <span className="text-slate-400">—</span> },
    { key: 'total', header: 'Value', align: 'right', render: (r) => <span className="font-semibold text-red-600">{money(r.total_amount)}</span> },
  ];
  if (isAdmin) columns.push({ key: 'by', header: 'By', render: (r) => r.created_by_username });
  columns.push({
    key: 'view',
    header: '',
    align: 'right',
    render: (r) => (
      <Link to={`/sales/${r.sale}`} className="btn-icon" title="Open invoice" onClick={(e) => e.stopPropagation()}>
        <Eye className="h-4 w-4" />
      </Link>
    ),
  });

  return (
    <>
      <PageHeader
        title="Sales returns"
        subtitle="Refunds and returned items. To return something, open the invoice from Sales and press “Return items”."
      />
      <Card bodyClassName="p-0">
        <div className="grid gap-3 border-b border-slate-100 p-4 sm:grid-cols-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Return no., invoice or customer…" />
          <input type="date" className="input" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} aria-label="From date" />
          <input type="date" className="input" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} aria-label="To date" />
        </div>
        <DataTable
          columns={columns}
          rows={list.data?.results ?? []}
          rowKey={(r) => r.id}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          onRowClick={(r) => navigate(`/sales/${r.sale}`)}
          emptyTitle="No returns yet"
          emptyDescription="Returns you process from an invoice will appear here."
        />
        <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
      </Card>
    </>
  );
}
