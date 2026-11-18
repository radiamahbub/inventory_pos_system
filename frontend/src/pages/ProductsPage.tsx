import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Card, PageHeader } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import type { Column } from '@/components/ui/DataTable';
import { Badge, StockBadge } from '@/components/ui/Feedback';
import { Field, FormError, SearchInput, inputClass } from '@/components/ui/Form';
import { ConfirmDialog, Modal } from '@/components/ui/Modal';
import { Pagination } from '@/components/ui/Pagination';
import { useAuth } from '@/context/AuthContext';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagedList } from '@/hooks/useFetch';
import type { Category, Paginated, Product } from '@/types';
import { parseError } from '@/utils/errors';
import { money } from '@/utils/format';

interface ProductForm {
  name: string;
  sku: string;
  category: string;
  purchase_price: string;
  selling_price: string;
  min_stock_level: string;
  initial_stock: string;
  description: string;
  is_active: boolean;
}

const EMPTY_FORM: ProductForm = {
  name: '',
  sku: '',
  category: '',
  purchase_price: '',
  selling_price: '',
  min_stock_level: '5',
  initial_stock: '0',
  description: '',
  is_active: true,
};

export default function ProductsPage() {
  const { isAdmin } = useAuth();

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [stockFilter, setStockFilter] = useState('');
  const debounced = useDebounce(search);

  const [categories, setCategories] = useState<Category[]>([]);
  useEffect(() => {
    api
      .get<Paginated<Category>>('/categories/', { params: { page_size: 100 } })
      .then(({ data }) => setCategories(data.results))
      .catch(() => setCategories([]));
  }, []);

  const list = usePagedList<Product>('/products/', {
    search: debounced,
    category,
    // boolean false cleanParams-এ বাদ পড়ে, তাই string পাঠাই
    is_active: status === '' ? undefined : status === 'active' ? 'true' : 'false',
    low_stock: stockFilter === 'low' ? true : undefined,
    in_stock: stockFilter === 'out' ? 'false' : undefined,
    ordering: 'name',
  });

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<ProductForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [deleting, setDeleting] = useState<Product | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const set = <K extends keyof ProductForm>(key: K, value: ProductForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, category: categories[0] ? String(categories[0].id) : '' });
    setFormError('');
    setFieldErrors({});
    setFormOpen(true);
  };

  const openEdit = (p: Product) => {
    setEditing(p);
    setForm({
      name: p.name,
      sku: p.sku,
      category: String(p.category),
      purchase_price: p.purchase_price ?? '',
      selling_price: p.selling_price,
      min_stock_level: String(p.min_stock_level),
      initial_stock: '0',
      description: p.description,
      is_active: p.is_active,
    });
    setFormError('');
    setFieldErrors({});
    setFormOpen(true);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    setFieldErrors({});
    const payload: Record<string, unknown> = {
      name: form.name,
      sku: form.sku,
      category: form.category ? Number(form.category) : null,
      purchase_price: form.purchase_price,
      selling_price: form.selling_price,
      min_stock_level: Number(form.min_stock_level || 0),
      description: form.description,
      is_active: form.is_active,
    };
    if (!editing) payload.initial_stock = Number(form.initial_stock || 0);

    try {
      if (editing) {
        await api.patch(`/products/${editing.id}/`, payload);
        toast.success('Product updated');
      } else {
        await api.post('/products/', payload);
        toast.success('Product created');
      }
      setFormOpen(false);
      list.reload();
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      const known = ['name', 'sku', 'category', 'purchase_price', 'selling_price', 'min_stock_level', 'initial_stock', 'description'];
      setFormError(Object.keys(parsed.fields).some((k) => known.includes(k)) ? '' : parsed.message);
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await api.delete(`/products/${deleting.id}/`);
      toast.success('Product deleted');
      setDeleting(null);
      if (list.data && list.data.results.length === 1 && list.page > 1) list.setPage(list.page - 1);
      else list.reload();
    } catch (err) {
      toast.error(parseError(err).message);
      setDeleting(null);
    } finally {
      setDeleteBusy(false);
    }
  };

  const columns: Column<Product>[] = [
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
  ];
  if (isAdmin) {
    columns.push({ key: 'cost', header: 'Cost', align: 'right', render: (p) => money(p.purchase_price) });
  }
  columns.push(
    {
      key: 'price',
      header: 'Price',
      align: 'right',
      render: (p) => <span className="font-semibold text-slate-900">{money(p.selling_price)}</span>,
    },
    {
      key: 'stock',
      header: 'Stock',
      align: 'right',
      render: (p) => (
        <div className="flex flex-col items-end gap-1">
          <span className="font-semibold text-slate-900">{p.stock_quantity}</span>
          <StockBadge qty={p.stock_quantity} min={p.min_stock_level} />
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p) => <Badge tone={p.is_active ? 'green' : 'slate'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
  );
  if (isAdmin) {
    columns.push({
      key: 'actions',
      header: '',
      align: 'right',
      render: (p) => (
        <div className="flex justify-end gap-1">
          <button className="btn-icon" title="Edit" onClick={() => openEdit(p)}>
            <Pencil className="h-4 w-4" />
          </button>
          <button className="btn-icon hover:!bg-red-50 hover:!text-red-600" title="Delete" onClick={() => setDeleting(p)}>
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    });
  }

  return (
    <>
      <PageHeader
        title="Products"
        subtitle="Manage your catalog, prices and stock levels."
        actions={
          isAdmin && (
            <button className="btn btn-primary" onClick={openCreate}>
              <Plus className="h-4 w-4" /> Add product
            </button>
          )
        }
      />

      <Card bodyClassName="p-0">
        <div className="grid gap-3 border-b border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <SearchInput value={search} onChange={setSearch} placeholder="Search name, SKU, category…" />
          <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <select className="input" value={stockFilter} onChange={(e) => setStockFilter(e.target.value)}>
            <option value="">All stock levels</option>
            <option value="low">Low stock</option>
            <option value="out">Out of stock</option>
          </select>
        </div>
        <DataTable
          columns={columns}
          rows={list.data?.results ?? []}
          rowKey={(p) => p.id}
          loading={list.loading}
          error={list.error}
          onRetry={list.reload}
          emptyTitle="No products found"
          emptyDescription="Try changing your filters or add a new product."
        />
        <Pagination page={list.page} count={list.data?.count ?? 0} onChange={list.setPage} />
      </Card>

      <Modal
        open={formOpen}
        onClose={() => !saving && setFormOpen(false)}
        title={editing ? 'Edit product' : 'Add product'}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setFormOpen(false)} disabled={saving}>
              Cancel
            </button>
            <button type="submit" form="product-form" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Create product'}
            </button>
          </>
        }
      >
        <form id="product-form" onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2 [&:empty]:hidden">
            <FormError message={formError} />
          </div>
          <Field label="Product name" required error={fieldErrors.name} className="sm:col-span-2">
            <input className={inputClass(fieldErrors.name)} value={form.name} onChange={(e) => set('name', e.target.value)} required />
          </Field>
          <Field label="SKU" required error={fieldErrors.sku} hint="Unique code. Saved in upper-case.">
            <input className={inputClass(fieldErrors.sku)} value={form.sku} onChange={(e) => set('sku', e.target.value)} required />
          </Field>
          <Field label="Category" required error={fieldErrors.category}>
            <select className={inputClass(fieldErrors.category)} value={form.category} onChange={(e) => set('category', e.target.value)} required>
              <option value="" disabled>
                Select category
              </option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Purchase price (cost)" required error={fieldErrors.purchase_price}>
            <input
              type="number"
              min="0"
              step="0.01"
              className={inputClass(fieldErrors.purchase_price)}
              value={form.purchase_price}
              onChange={(e) => set('purchase_price', e.target.value)}
              required
            />
          </Field>
          <Field label="Selling price" required error={fieldErrors.selling_price}>
            <input
              type="number"
              min="0.01"
              step="0.01"
              className={inputClass(fieldErrors.selling_price)}
              value={form.selling_price}
              onChange={(e) => set('selling_price', e.target.value)}
              required
            />
          </Field>
          <Field label="Minimum stock level" error={fieldErrors.min_stock_level} hint="Low-stock alert triggers at or below this number.">
            <input
              type="number"
              min="0"
              className={inputClass(fieldErrors.min_stock_level)}
              value={form.min_stock_level}
              onChange={(e) => set('min_stock_level', e.target.value)}
            />
          </Field>
          {editing ? (
            <Field label="Current stock" hint="Change stock via Purchases or Inventory adjustment.">
              <input className="input" value={editing.stock_quantity} disabled />
            </Field>
          ) : (
            <Field label="Opening stock" error={fieldErrors.initial_stock} hint="Optional starting quantity.">
              <input
                type="number"
                min="0"
                className={inputClass(fieldErrors.initial_stock)}
                value={form.initial_stock}
                onChange={(e) => set('initial_stock', e.target.value)}
              />
            </Field>
          )}
          <Field label="Description" error={fieldErrors.description} className="sm:col-span-2">
            <textarea className={inputClass(fieldErrors.description)} rows={3} value={form.description} onChange={(e) => set('description', e.target.value)} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={form.is_active}
              onChange={(e) => set('is_active', e.target.checked)}
            />
            Product is active (available for sale)
          </label>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete product?"
        message={
          deleting
            ? `"${deleting.name}" will be deleted. If it already has sales or purchase history it cannot be deleted — deactivate it instead.`
            : ''
        }
        loading={deleteBusy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </>
  );
}
