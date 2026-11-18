import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Banknote, CheckCircle2, CreditCard, Minus, Package, Plus, Printer, ShoppingCart, Smartphone, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Spinner, StockBadge } from '@/components/ui/Feedback';
import { FormError, SearchInput } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { useDebounce } from '@/hooks/useDebounce';
import type { Category, Customer, Paginated, PaymentMethod, Product, Sale } from '@/types';
import { parseError } from '@/utils/errors';
import { money } from '@/utils/format';

interface CartLine {
  product: Product;
  quantity: number;
}

const PAYMENTS: { value: PaymentMethod; label: string; icon: typeof Banknote }[] = [
  { value: 'cash', label: 'Cash', icon: Banknote },
  { value: 'card', label: 'Card', icon: CreditCard },
  { value: 'mobile_banking', label: 'Mobile', icon: Smartphone },
];

export default function PosPage() {
  const navigate = useNavigate();

  /* ---------- product catalog ---------- */
  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const debounced = useDebounce(search, 300);
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [productError, setProductError] = useState('');
  const [catalogTick, setCatalogTick] = useState(0);

  const [categories, setCategories] = useState<Category[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);

  useEffect(() => {
    api.get<Paginated<Category>>('/categories/', { params: { page_size: 100 } }).then(({ data }) => setCategories(data.results)).catch(() => undefined);
    api.get<Paginated<Customer>>('/customers/', { params: { page_size: 100 } }).then(({ data }) => setCustomers(data.results)).catch(() => undefined);
  }, []);

  useEffect(() => {
    let active = true;
    setLoadingProducts(true);
    setProductError('');
    api
      .get<Paginated<Product>>('/products/', {
        params: { search: debounced || undefined, category: categoryId || undefined, is_active: true, page_size: 60, ordering: 'name' },
      })
      .then(({ data }) => {
        if (active) setProducts(data.results);
      })
      .catch((err) => {
        if (active) setProductError(parseError(err).message);
      })
      .finally(() => {
        if (active) setLoadingProducts(false);
      });
    return () => {
      active = false;
    };
  }, [debounced, categoryId, catalogTick]);

  /* ---------- cart ---------- */
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customer, setCustomer] = useState('');
  const [payment, setPayment] = useState<PaymentMethod>('cash');
  const [discount, setDiscount] = useState('');
  const [received, setReceived] = useState(''); // খালি = পুরো টাকা পেয়েছি
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState<Sale | null>(null);

  const addToCart = (product: Product) => {
    if (product.stock_quantity <= 0) {
      toast.error(`"${product.name}" is out of stock`);
      return;
    }
    setCart((prev) => {
      const existing = prev.find((l) => l.product.id === product.id);
      if (!existing) return [...prev, { product, quantity: 1 }];
      if (existing.quantity >= product.stock_quantity) {
        toast.error(`Only ${product.stock_quantity} in stock`);
        return prev;
      }
      return prev.map((l) => (l.product.id === product.id ? { ...l, quantity: l.quantity + 1 } : l));
    });
  };

  const setQuantity = (productId: number, value: number) => {
    setCart((prev) =>
      prev.map((l) => {
        if (l.product.id !== productId) return l;
        const max = l.product.stock_quantity;
        const q = Math.max(1, Math.min(max, Math.floor(value) || 1));
        return { ...l, quantity: q };
      }),
    );
  };

  const removeLine = (productId: number) => setCart((prev) => prev.filter((l) => l.product.id !== productId));

  const subtotal = useMemo(
    () => cart.reduce((sum, l) => sum + Number(l.product.selling_price) * l.quantity, 0),
    [cart],
  );
  const discountValue = Math.max(0, Number(discount) || 0);
  const grandTotal = subtotal - discountValue;
  const discountTooHigh = discountValue > subtotal;
  const itemCount = cart.reduce((n, l) => n + l.quantity, 0);
  const totalToPay = Math.max(0, grandTotal);
  const receivedValue = received === '' ? totalToPay : Math.max(0, Number(received) || 0);
  const receivedTooHigh = receivedValue > totalToPay + 0.0001;
  const dueValue = Math.max(0, totalToPay - receivedValue);
  const dueNeedsCustomer = dueValue > 0.0001 && !customer;

  const resetSale = () => {
    setCart([]);
    setCustomer('');
    setPayment('cash');
    setDiscount('');
    setReceived('');
    setNote('');
    setError('');
  };

  const checkout = async () => {
    setError('');
    if (cart.length === 0) {
      setError('Add at least one product to the cart.');
      return;
    }
    if (discountTooHigh) {
      setError('Discount cannot be greater than the subtotal.');
      return;
    }
    if (receivedTooHigh) {
      setError('Amount received cannot be more than the total.');
      return;
    }
    if (dueNeedsCustomer) {
      setError('Select a customer to sell on credit (due).');
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post<Sale>('/sales/', {
        customer: customer ? Number(customer) : null,
        payment_method: payment,
        discount: discountValue.toFixed(2),
        paid_amount: dueValue > 0.0001 ? receivedValue.toFixed(2) : undefined,
        note,
        items: cart.map((l) => ({ product: l.product.id, quantity: l.quantity })),
      });
      setCompleted(data);
      resetSale();
      setCatalogTick((t) => t + 1); // স্টক আপডেট দেখাতে
    } catch (err) {
      setError(parseError(err).message);
      setCatalogTick((t) => t + 1);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
      {/* Catalog */}
      <section className="min-w-0">
        <div className="mb-4">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Point of Sale</h1>
          <p className="mt-1 text-sm text-slate-500">Tap a product to add it to the cart.</p>
        </div>

        <SearchInput value={search} onChange={setSearch} placeholder="Search products by name or SKU…" />

        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setCategoryId('')}
            className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
              categoryId === '' ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
            }`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategoryId(String(c.id))}
              className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
                categoryId === String(c.id) ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
              }`}
            >
              {c.name}
            </button>
          ))}
        </div>

        <div className="mt-4">
          {productError && <FormError message={productError} />}
          {loadingProducts && products.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-500">
              <Spinner /> Loading products…
            </div>
          ) : products.length === 0 ? (
            <div className="card py-16 text-center text-sm text-slate-500">No products found.</div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 2xl:grid-cols-4">
              {products.map((p) => {
                const out = p.stock_quantity <= 0;
                const inCart = cart.find((l) => l.product.id === p.id)?.quantity ?? 0;
                return (
                  <button
                    key={p.id}
                    onClick={() => addToCart(p)}
                    disabled={out}
                    className={`card relative flex flex-col p-3 text-left transition ${
                      out ? 'cursor-not-allowed opacity-60' : 'hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md'
                    } ${inCart > 0 ? 'ring-2 ring-brand-500' : ''}`}
                  >
                    {inCart > 0 && (
                      <span className="absolute -right-2 -top-2 flex h-6 min-w-6 items-center justify-center rounded-full bg-brand-600 px-1.5 text-xs font-bold text-white shadow">
                        {inCart}
                      </span>
                    )}
                    <span className="mb-3 flex h-16 items-center justify-center rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 text-slate-400">
                      <Package className="h-7 w-7" />
                    </span>
                    <span className="line-clamp-2 min-h-[2.5rem] text-sm font-semibold text-slate-900">{p.name}</span>
                    <span className="mt-0.5 text-xs text-slate-500">{p.sku}</span>
                    <span className="mt-2 flex items-center justify-between gap-2">
                      <span className="text-sm font-bold text-brand-700">{money(p.selling_price)}</span>
                      <span className="text-xs text-slate-500">{p.stock_quantity} left</span>
                    </span>
                    <span className="mt-2">
                      <StockBadge qty={p.stock_quantity} min={p.min_stock_level} />
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Cart */}
      <aside className="xl:sticky xl:top-24 xl:self-start">
        <div className="card flex flex-col">
          <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <ShoppingCart className="h-4 w-4 text-brand-600" /> Current sale
              {itemCount > 0 && <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">{itemCount} items</span>}
            </h2>
            {cart.length > 0 && (
              <button className="text-xs font-medium text-red-600 hover:underline" onClick={() => setCart([])}>
                Clear
              </button>
            )}
          </header>

          <div className="max-h-[320px] min-h-[120px] overflow-y-auto">
            {cart.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-6 py-10 text-center text-sm text-slate-400">
                <ShoppingCart className="mb-2 h-8 w-8" />
                Cart is empty
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {cart.map((l) => (
                  <li key={l.product.id} className="px-5 py-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-900">{l.product.name}</p>
                        <p className="text-xs text-slate-500">{money(l.product.selling_price)} each</p>
                      </div>
                      <button className="btn-icon h-7 w-7 hover:!bg-red-50 hover:!text-red-600" onClick={() => removeLine(l.product.id)} aria-label="Remove">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <div className="inline-flex items-center rounded-lg border border-slate-200">
                        <button className="px-2 py-1.5 text-slate-600 hover:bg-slate-100" onClick={() => setQuantity(l.product.id, l.quantity - 1)} aria-label="Decrease">
                          <Minus className="h-3.5 w-3.5" />
                        </button>
                        <input
                          type="number"
                          min={1}
                          max={l.product.stock_quantity}
                          value={l.quantity}
                          onChange={(e) => setQuantity(l.product.id, Number(e.target.value))}
                          className="w-12 border-x border-slate-200 py-1 text-center text-sm focus:outline-none"
                        />
                        <button className="px-2 py-1.5 text-slate-600 hover:bg-slate-100" onClick={() => setQuantity(l.product.id, l.quantity + 1)} aria-label="Increase">
                          <Plus className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <p className="text-sm font-semibold text-slate-900">{money(Number(l.product.selling_price) * l.quantity)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="space-y-4 border-t border-slate-100 px-5 py-4">
            <div>
              <label className="label">Customer</label>
              <select className="input" value={customer} onChange={(e) => setCustomer(e.target.value)}>
                <option value="">Walk-in customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                    {c.phone ? ` · ${c.phone}` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Payment method</label>
              <div className="grid grid-cols-3 gap-2">
                {PAYMENTS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setPayment(p.value)}
                    className={`flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition ${
                      payment === p.value
                        ? 'border-brand-600 bg-brand-50 text-brand-700'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <p.icon className="h-4 w-4" />
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Discount (৳)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className={`input ${discountTooHigh ? 'input-error' : ''}`}
                  placeholder="0.00"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                />
              </div>
              <div>
                <label className="label">Note</label>
                <input className="input" placeholder="Optional" maxLength={255} value={note} onChange={(e) => setNote(e.target.value)} />
              </div>
            </div>
            {discountTooHigh && <p className="text-xs text-red-600">Discount cannot be greater than the subtotal.</p>}

            <div>
              <div className="flex items-center justify-between">
                <label className="label">Amount received (৳)</label>
                {received !== '' && (
                  <button type="button" className="text-xs font-medium text-brand-600 hover:underline" onClick={() => setReceived('')}>
                    Paid in full
                  </button>
                )}
              </div>
              <input
                type="number"
                min="0"
                step="0.01"
                className={`input ${receivedTooHigh || dueNeedsCustomer ? 'input-error' : ''}`}
                placeholder={totalToPay.toFixed(2)}
                value={received}
                onChange={(e) => setReceived(e.target.value)}
              />
              {receivedTooHigh && <p className="mt-1 text-xs text-red-600">Cannot be more than the total.</p>}
              {dueValue > 0.0001 && !receivedTooHigh && (
                <p className={`mt-1 text-xs ${dueNeedsCustomer ? 'text-red-600' : 'text-amber-700'}`}>
                  {dueNeedsCustomer ? 'Select a customer — ' : ''}Due {money(dueValue)} will be added to the customer&apos;s account.
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2 border-t border-slate-100 bg-slate-50/60 px-5 py-4 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal</span>
              <span>{money(subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Discount</span>
              <span>− {money(discountValue)}</span>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-2 text-lg font-bold text-slate-900">
              <span>Total</span>
              <span>{money(Math.max(0, grandTotal))}</span>
            </div>
            {dueValue > 0.0001 && !receivedTooHigh && (
              <div className="flex justify-between text-amber-700">
                <span>Due (credit)</span>
                <span>{money(dueValue)}</span>
              </div>
            )}

            {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}

            <button className="btn btn-primary mt-2 w-full py-3 text-base" onClick={checkout} disabled={submitting || cart.length === 0}>
              {submitting ? 'Processing…' : `Complete sale · ${money(Math.max(0, grandTotal))}`}
            </button>
          </div>
        </div>
      </aside>

      <Modal
        open={completed !== null}
        onClose={() => setCompleted(null)}
        title="Sale completed"
        size="sm"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCompleted(null)}>
              New sale
            </button>
            <button className="btn btn-secondary" onClick={() => completed && navigate(`/sales/${completed.id}`)}>
              Invoice
            </button>
            <button className="btn btn-primary" onClick={() => completed && navigate(`/sales/${completed.id}/receipt?print=1`)}>
              <Printer className="h-4 w-4" /> Print receipt
            </button>
          </>
        }
      >
        {completed && (
          <div className="py-2 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <p className="text-sm text-slate-500">Invoice</p>
            <p className="text-lg font-bold text-slate-900">{completed.invoice_number}</p>
            <p className="mt-3 text-3xl font-bold text-brand-700">{money(completed.grand_total)}</p>
            <p className="mt-1 text-xs text-slate-500">
              Paid via {completed.payment_method_display}
              {Number(completed.due_amount) > 0 && <span className="font-medium text-amber-700"> · Due {money(completed.due_amount)}</span>}
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
