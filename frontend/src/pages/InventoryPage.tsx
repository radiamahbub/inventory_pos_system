import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Card, PageHeader } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge, StockBadge } from '@/components/ui/Feedback';
import { Field, FormError, SearchInput, inputClass } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { Pagination } from '@/components/ui/Pagination';
import { ProductSearch } from '@/components/ui/ProductSearch';
import { useAuth } from '@/context/AuthContext';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagedList } from '@/hooks/useFetch';
import type { Category, MovementType, Paginated, Product, StockItem, StockMovement } from '@/types';
import { parseError } from '@/utils/errors';
import { fmtDateTime } from '@/utils/format';

const MOVEMENT_TONE: Record<MovementType, 'blue' | 'green' | 'amber' | 'indigo'> = {
  opening: 'blue',
  purchase: 'green',
  sale: 'indigo',
  return: 'green',
  adjustment: 'amber',
};

function StockTab({ reloadKey }: { reloadKey: number }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [lowOnly, setLowOnly] = useState(false);
  const debounced = useDebounce(search);
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    api
      .get<Paginated<Category>>('/categories/', { params: { page_size: 100 } })
      .then(({ data }) => setCategories(data.results))
      .catch(() => setCategories([]));
  }, []);

  const list = usePagedList<StockItem>('/inventory/stock/', {
    search: debounced,
    category,
    low_stock: lowOnly,
    reload: reloadKey, // adjustment-এর পর তালিকা রিফ্রেশ
  });

  const columns: Column<StockItem>[] = [
    {
      key: 'product',
      header: 'Product',
      render: (s) => (
        <div>
          <p className="font-medium text-slate-900">{s.name}</p>
          <p className="text-xs text-slate-500">SKU: {s.sku}</p>
        </div>
      ),
    },
    { key: 'category', header: 'Category', render: (s) => <Badge tone="slate">{s.category_name}</Badge> },
    { key: 'qty', header: 'In stock', align: 'right', render: (s) => <span className="text-base font-semibold text-slate-900">{s.stock_quantity}</span> },
    { key: 'min', header: 'Min. level', align: 'right', render: (s) => s.min_stock_level },
    { key: 'status', header: 'Status', render: (s) => <StockBadge qty={s.stock_quantity} min={s.min_stock_level} /> },
    {
      key: 'active',
      header: 'Product',
      render: (s) => <Badge tone={s.is_active ? 'green' : 'slate'}>{s.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
  ];

  return (
    <Card bodyClassName="p-0">
      <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-center">
        <SearchInput value={search} onChange={setSearch} placeholder="Search name or SKU…" className="lg:w-80" />
        <select className="input lg:w-52" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            checked={lowOnly}
            onChange={(e) => setLowOnly(e.target.checked)}
          />
          Low stock only
        </label>
      </div>
      <DataTable
        columns={columns}
        rows={list.data?.results ?? []}
        rowKey={(s) => s.id}
        loading={list.loading}
        error={list.error}
        onRetry={list.reload}
        emptyTitle="No stock records found"
      />
      <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
    </Card>
  );
}

function MovementsTab({ reloadKey }: { reloadKey: number }) {
  const [search, setSearch] = useState('');
  const [type, setType] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const debounced = useDebounce(search);

  const list = usePagedList<StockMovement>('/inventory/movements/', {
    search: debounced,
    movement_type: type,
    start_date: start,
    end_date: end,
    ordering: '-created_at',
    reload: reloadKey,
  });

  const columns: Column<StockMovement>[] = [
    { key: 'date', header: 'Date', render: (m) => <span className="whitespace-nowrap">{fmtDateTime(m.created_at)}</span> },
    {
      key: 'product',
      header: 'Product',
      render: (m) => (
        <div>
          <p className="font-medium text-slate-900">{m.product_name}</p>
          <p className="text-xs text-slate-500">{m.product_sku}</p>
        </div>
      ),
    },
    { key: 'type', header: 'Type', render: (m) => <Badge tone={MOVEMENT_TONE[m.movement_type]}>{m.movement_type_display}</Badge> },
    {
      key: 'change',
      header: 'Change',
      align: 'right',
      render: (m) => (
        <span className={`font-semibold ${m.quantity_change > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
          {m.quantity_change > 0 ? '+' : ''}
          {m.quantity_change}
        </span>
      ),
    },
    { key: 'balance', header: 'Before → After', align: 'right', render: (m) => `${m.quantity_before} → ${m.quantity_after}` },
    { key: 'ref', header: 'Reference', render: (m) => m.reference || <span className="text-slate-400">—</span> },
    { key: 'note', header: 'Note', className: 'max-w-[220px] truncate', render: (m) => m.note || <span className="text-slate-400">—</span> },
    { key: 'by', header: 'By', render: (m) => m.created_by_username ?? '—' },
  ];

  return (
    <Card bodyClassName="p-0">
      <div className="grid gap-3 border-b border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Product, SKU, reference…" />
        <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All movement types</option>
          <option value="opening">Opening stock</option>
          <option value="purchase">Purchase (stock in)</option>
          <option value="sale">Sale (stock out)</option>
          <option value="return">Sales return (stock in)</option>
          <option value="adjustment">Admin adjustment</option>
        </select>
        <input type="date" className="input" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} aria-label="From date" />
        <input type="date" className="input" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} aria-label="To date" />
      </div>
      <DataTable
        columns={columns}
        rows={list.data?.results ?? []}
        rowKey={(m) => m.id}
        loading={list.loading}
        error={list.error}
        onRetry={list.reload}
        emptyTitle="No stock movements found"
      />
      <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
    </Card>
  );
}

function AdjustModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [product, setProduct] = useState<Product | null>(null);
  const [change, setChange] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setProduct(null);
      setChange('');
      setReason('');
      setFormError('');
      setFieldErrors({});
    }
  }, [open]);

  const delta = Number(change);
  const after = product && Number.isFinite(delta) ? product.stock_quantity + delta : null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!product) {
      setFormError('Please select a product.');
      return;
    }
    setSaving(true);
    setFormError('');
    setFieldErrors({});
    try {
      await api.post('/inventory/adjust/', { product: product.id, quantity_change: delta, reason });
      toast.success('Stock adjusted');
      onDone();
      onClose();
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      setFormError(Object.keys(parsed.fields).some((k) => ['quantity_change', 'reason'].includes(k)) ? '' : parsed.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => !saving && onClose()}
      title="Adjust stock"
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" form="adjust-form" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Apply adjustment'}
          </button>
        </>
      }
    >
      <form id="adjust-form" onSubmit={onSubmit} className="space-y-4">
        <FormError message={formError} />
        <Field label="Product" required>
          {product ? (
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <div>
                <p className="text-sm font-medium text-slate-900">{product.name}</p>
                <p className="text-xs text-slate-500">
                  {product.sku} · Current stock {product.stock_quantity}
                </p>
              </div>
              <button type="button" className="btn-icon" onClick={() => setProduct(null)} aria-label="Change product">
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <ProductSearch onSelect={setProduct} autoFocus />
          )}
        </Field>
        <Field label="Quantity change" required error={fieldErrors.quantity_change} hint="Use a positive number to add stock, a negative number to remove it.">
          <input
            type="number"
            step="1"
            className={inputClass(fieldErrors.quantity_change)}
            placeholder="e.g. 10 or -3"
            value={change}
            onChange={(e) => setChange(e.target.value)}
            required
          />
        </Field>
        {product && after !== null && change !== '' && (
          <p className={`rounded-lg px-3 py-2 text-sm ${after < 0 ? 'bg-red-50 text-red-700' : 'bg-brand-50 text-brand-700'}`}>
            Stock will change from <strong>{product.stock_quantity}</strong> to <strong>{after}</strong>
            {after < 0 && ' — stock cannot go below zero.'}
          </p>
        )}
        <Field label="Reason" required error={fieldErrors.reason}>
          <input
            className={inputClass(fieldErrors.reason)}
            placeholder="e.g. Damaged goods, stock count correction"
            value={reason}
            maxLength={255}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        </Field>
      </form>
    </Modal>
  );
}

export default function InventoryPage() {
  const { isAdmin } = useAuth();
  const [tab, setTab] = useState<'stock' | 'movements'>('stock');
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const tabs: { id: 'stock' | 'movements'; label: string }[] = [{ id: 'stock', label: 'Current stock' }];
  if (isAdmin) tabs.push({ id: 'movements', label: 'Movement history' });

  return (
    <>
      <PageHeader
        title="Inventory"
        subtitle="Monitor stock levels and every stock movement."
        actions={
          isAdmin && (
            <button className="btn btn-primary" onClick={() => setAdjustOpen(true)}>
              <SlidersHorizontal className="h-4 w-4" /> Adjust stock
            </button>
          )
        }
      />

      <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
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

      {tab === 'stock' ? <StockTab reloadKey={reloadKey} /> : <MovementsTab reloadKey={reloadKey} />}

      {isAdmin && (
        <AdjustModal open={adjustOpen} onClose={() => setAdjustOpen(false)} onDone={() => setReloadKey((k) => k + 1)} />
      )}
    </>
  );
}
