import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { api } from '@/api/client';
import { Card, PageHeader } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { SearchInput } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { Pagination } from '@/components/ui/Pagination';
import { useDebounce } from '@/hooks/useDebounce';
import { useFetch, usePagedList } from '@/hooks/useFetch';
import type { Paginated, Purchase, Supplier } from '@/types';
import { fmtDate, fmtDateTime, money } from '@/utils/format';

function PurchaseDetail({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, loading, error } = useFetch<Purchase | null>(async () => {
    if (id === null) return null;
    const { data } = await api.get<Purchase>(`/purchases/${id}/`);
    return data;
  }, [id]);

  return (
    <Modal open={id !== null} onClose={onClose} title={data ? `Purchase ${data.reference_no}` : 'Purchase details'} size="lg">
      {loading && <PageLoader />}
      {error && <ErrorBanner message={error} />}
      {!loading && data && (
        <div className="space-y-5">
          <dl className="grid gap-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Supplier</dt>
              <dd className="mt-1 font-medium text-slate-900">{data.supplier_name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Purchase date</dt>
              <dd className="mt-1 font-medium text-slate-900">{fmtDate(data.purchase_date)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Recorded by</dt>
              <dd className="mt-1 font-medium text-slate-900">
                {data.created_by_username}
                <span className="block text-xs font-normal text-slate-500">{fmtDateTime(data.created_at)}</span>
              </dd>
            </div>
          </dl>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="th">Product</th>
                  <th className="th text-right">Qty</th>
                  <th className="th text-right">Unit price</th>
                  <th className="th text-right">Line total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data.items ?? []).map((it) => (
                  <tr key={it.id}>
                    <td className="td">
                      <p className="font-medium text-slate-900">{it.product_name}</p>
                      <p className="text-xs text-slate-500">{it.product_sku}</p>
                    </td>
                    <td className="td text-right">{it.quantity}</td>
                    <td className="td text-right">{money(it.unit_price)}</td>
                    <td className="td text-right font-medium text-slate-900">{money(it.line_total)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-50">
                  <td colSpan={3} className="td text-right font-semibold text-slate-700">
                    Total
                  </td>
                  <td className="td text-right text-base font-bold text-slate-900">{money(data.total_amount)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          {data.note && (
            <p className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <span className="font-medium text-slate-700">Note:</span> {data.note}
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}

export default function PurchasesPage() {
  const [search, setSearch] = useState('');
  const [supplier, setSupplier] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [detailId, setDetailId] = useState<number | null>(null);
  const debounced = useDebounce(search);

  useEffect(() => {
    api
      .get<Paginated<Supplier>>('/suppliers/', { params: { page_size: 100 } })
      .then(({ data }) => setSuppliers(data.results))
      .catch(() => setSuppliers([]));
  }, []);

  const list = usePagedList<Purchase>('/purchases/', {
    search: debounced,
    supplier,
    start_date: start,
    end_date: end,
    ordering: '-purchase_date',
  });

  const columns: Column<Purchase>[] = [
    { key: 'ref', header: 'Reference', render: (p) => <span className="font-semibold text-brand-600">{p.reference_no}</span> },
    { key: 'date', header: 'Date', render: (p) => fmtDate(p.purchase_date) },
    { key: 'supplier', header: 'Supplier', render: (p) => <span className="font-medium text-slate-900">{p.supplier_name}</span> },
    { key: 'items', header: 'Items', align: 'right', render: (p) => p.item_count ?? '—' },
    { key: 'total', header: 'Total', align: 'right', render: (p) => <span className="font-semibold text-slate-900">{money(p.total_amount)}</span> },
    { key: 'by', header: 'Recorded by', render: (p) => p.created_by_username },
  ];

  return (
    <>
      <PageHeader
        title="Purchases"
        subtitle="Stock-in records from your suppliers."
        actions={
          <Link to="/purchases/new" className="btn btn-primary">
            <Plus className="h-4 w-4" /> New purchase
          </Link>
        }
      />
      <Card bodyClassName="p-0">
        <div className="grid gap-3 border-b border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <SearchInput value={search} onChange={setSearch} placeholder="Reference or supplier…" />
          <select className="input" value={supplier} onChange={(e) => setSupplier(e.target.value)}>
            <option value="">All suppliers</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <input type="date" className="input" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} aria-label="From date" />
          <input type="date" className="input" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} aria-label="To date" />
        </div>
        <DataTable
          columns={columns}
          rows={list.data?.results ?? []}
          rowKey={(p) => p.id}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          onRowClick={(p) => setDetailId(p.id)}
          emptyTitle="No purchases found"
          emptyDescription="Record a purchase to add stock to your inventory."
        />
        <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
      </Card>
      <PurchaseDetail id={detailId} onClose={() => setDetailId(null)} />
    </>
  );
}
