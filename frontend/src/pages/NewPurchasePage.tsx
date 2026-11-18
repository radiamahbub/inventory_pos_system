import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Card, PageHeader } from '@/components/ui/Card';
import { Field, FormError, inputClass } from '@/components/ui/Form';
import { ProductSearch } from '@/components/ui/ProductSearch';
import type { Paginated, Product, Supplier } from '@/types';
import { parseError } from '@/utils/errors';
import { money, todayISO } from '@/utils/format';

interface Line {
  product: Product;
  quantity: string;
  unit_price: string;
}

export default function NewPurchasePage() {
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplier, setSupplier] = useState('');
  const [date, setDate] = useState(todayISO());
  const [note, setNote] = useState('');
  const [lines, setLines] = useState<Line[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    api
      .get<Paginated<Supplier>>('/suppliers/', { params: { page_size: 100 } })
      .then(({ data }) => setSuppliers(data.results))
      .catch(() => setSuppliers([]));
  }, []);

  const addProduct = (product: Product) => {
    setLines((prev) => {
      if (prev.some((l) => l.product.id === product.id)) {
        toast('Product is already in the list — update its quantity instead.');
        return prev;
      }
      return [...prev, { product, quantity: '1', unit_price: product.purchase_price ?? '' }];
    });
  };

  const updateLine = (id: number, patch: Partial<Pick<Line, 'quantity' | 'unit_price'>>) =>
    setLines((prev) => prev.map((l) => (l.product.id === id ? { ...l, ...patch } : l)));

  const total = useMemo(
    () => lines.reduce((sum, l) => sum + (Number(l.quantity) || 0) * (Number(l.unit_price) || 0), 0),
    [lines],
  );

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});
    if (!supplier) {
      setFieldErrors({ supplier: 'Please select a supplier.' });
      return;
    }
    if (lines.length === 0) {
      setError('Add at least one product to the purchase.');
      return;
    }
    if (lines.some((l) => !(Number(l.quantity) >= 1) || !(Number(l.unit_price) > 0))) {
      setError('Every line needs a quantity of at least 1 and a unit price greater than 0.');
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.post<{ reference_no: string }>('/purchases/', {
        supplier: Number(supplier),
        purchase_date: date,
        note,
        items: lines.map((l) => ({
          product: l.product.id,
          quantity: Math.floor(Number(l.quantity)),
          unit_price: Number(l.unit_price).toFixed(2),
        })),
      });
      toast.success(`Purchase ${data.reference_no} recorded — stock updated`);
      navigate('/purchases');
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      setError(parsed.fields.supplier || parsed.fields.purchase_date ? '' : parsed.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader
        title="New purchase"
        subtitle="Record stock received from a supplier. Stock and average cost update automatically."
        actions={
          <Link to="/purchases" className="btn btn-secondary">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
        }
      />

      <form onSubmit={onSubmit} className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card title="Purchase details">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Supplier" required error={fieldErrors.supplier}>
                <select className={inputClass(fieldErrors.supplier)} value={supplier} onChange={(e) => setSupplier(e.target.value)}>
                  <option value="">Select supplier</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Purchase date" required error={fieldErrors.purchase_date}>
                <input type="date" className={inputClass(fieldErrors.purchase_date)} value={date} max={todayISO()} onChange={(e) => setDate(e.target.value)} required />
              </Field>
              <Field label="Note" className="sm:col-span-2">
                <input className="input" maxLength={255} placeholder="Optional (e.g. Monthly restock)" value={note} onChange={(e) => setNote(e.target.value)} />
              </Field>
            </div>
          </Card>

          <Card title="Items" bodyClassName="p-0">
            <div className="border-b border-slate-100 p-4">
              <ProductSearch onSelect={addProduct} placeholder="Search and add a product…" />
            </div>
            {lines.length === 0 ? (
              <p className="px-5 py-12 text-center text-sm text-slate-500">No products added yet. Search above to add items.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100">
                  <thead className="bg-slate-50/70">
                    <tr>
                      <th className="th">Product</th>
                      <th className="th w-28 text-right">Quantity</th>
                      <th className="th w-36 text-right">Unit price</th>
                      <th className="th w-32 text-right">Line total</th>
                      <th className="th w-12" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lines.map((l) => (
                      <tr key={l.product.id}>
                        <td className="td">
                          <p className="font-medium text-slate-900">{l.product.name}</p>
                          <p className="text-xs text-slate-500">
                            {l.product.sku} · Current stock {l.product.stock_quantity}
                          </p>
                        </td>
                        <td className="td">
                          <input
                            type="number"
                            min={1}
                            className="input text-right"
                            value={l.quantity}
                            onChange={(e) => updateLine(l.product.id, { quantity: e.target.value })}
                          />
                        </td>
                        <td className="td">
                          <input
                            type="number"
                            min="0.01"
                            step="0.01"
                            className="input text-right"
                            value={l.unit_price}
                            onChange={(e) => updateLine(l.product.id, { unit_price: e.target.value })}
                          />
                        </td>
                        <td className="td text-right font-semibold text-slate-900">
                          {money((Number(l.quantity) || 0) * (Number(l.unit_price) || 0))}
                        </td>
                        <td className="td">
                          <button
                            type="button"
                            className="btn-icon hover:!bg-red-50 hover:!text-red-600"
                            onClick={() => setLines((prev) => prev.filter((x) => x.product.id !== l.product.id))}
                            aria-label="Remove line"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Card title="Summary">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between text-slate-600">
                <dt>Products</dt>
                <dd>{lines.length}</dd>
              </div>
              <div className="flex justify-between text-slate-600">
                <dt>Total quantity</dt>
                <dd>{lines.reduce((n, l) => n + (Math.floor(Number(l.quantity)) || 0), 0)}</dd>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-3 text-lg font-bold text-slate-900">
                <dt>Total</dt>
                <dd>{money(total)}</dd>
              </div>
            </dl>
            <div className="mt-4">
              <FormError message={error} />
            </div>
            <button className="btn btn-primary w-full py-2.5" disabled={saving}>
              {saving ? 'Saving…' : 'Record purchase'}
            </button>
            <p className="mt-3 text-xs text-slate-500">Purchases cannot be edited after saving, so please double-check the details.</p>
          </Card>
        </aside>
      </form>
    </>
  );
}
