import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileDown, Printer, ReceiptText, Store, Undo2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { openPdf } from '@/api/files';
import { api } from '@/api/client';
import { ReturnModal } from '@/components/ReturnModal';
import { Badge, ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { useFetch } from '@/hooks/useFetch';
import { useShop } from '@/hooks/useShop';
import type { Sale } from '@/types';
import { parseError } from '@/utils/errors';
import { fmtDateTime, money } from '@/utils/format';

export default function InvoicePage() {
  const { id } = useParams();
  const [returning, setReturning] = useState(false);
  const shop = useShop();
  const showPdf = (kind: 'invoice' | 'receipt') => {
    openPdf(`/sales/${id}/${kind}-pdf/`).catch((err) => toast.error(parseError(err).message));
  };
  const { data: sale, loading, error, reload } = useFetch<Sale>(async () => {
    const { data } = await api.get<Sale>(`/sales/${id}/`);
    return data;
  }, [id]);

  if (loading) return <PageLoader label="Loading invoice…" />;
  if (error || !sale) {
    return (
      <div className="space-y-4">
        <Link to="/sales" className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to sales
        </Link>
        <ErrorBanner message={error ?? 'Invoice not found.'} onRetry={reload} />
      </div>
    );
  }

  const items = sale.items ?? [];
  const discount = Number(sale.discount);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between print:hidden">
        <Link to="/sales" className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to sales
        </Link>
        <div className="flex flex-wrap justify-end gap-2">
          <button className="btn btn-secondary btn-sm" onClick={() => showPdf('invoice')}>
            <FileDown className="h-4 w-4" /> A4 PDF
          </button>
          <Link to={`/sales/${sale.id}/receipt`} className="btn btn-secondary btn-sm">
            <ReceiptText className="h-4 w-4" /> 80mm receipt
          </Link>
          {sale.return_status !== 'full' && (
            <button className="btn btn-secondary btn-sm" onClick={() => setReturning(true)}>
              <Undo2 className="h-4 w-4" /> Return items
            </button>
          )}
          <button className="btn btn-primary btn-sm" onClick={() => window.print()}>
            <Printer className="h-4 w-4" /> Print invoice
          </button>
        </div>
      </div>

      <article className="card p-8 print:border-0 print:p-0 print:shadow-none">
        <header className="flex items-start justify-between border-b border-slate-200 pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white print:bg-slate-900">
              <Store className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-bold text-slate-900">{shop.name}</p>
              <p className="text-xs text-slate-500">{[shop.address, shop.phone].filter(Boolean).join(' · ') || 'Sales invoice'}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slate-500">Invoice</p>
            <p className="text-lg font-bold text-slate-900">{sale.invoice_number}</p>
            {Number(sale.due_amount) > 0 && (
              <div className="mt-1">
                <Badge tone="amber">{sale.payment_status === 'partial' ? 'Partly paid' : 'Unpaid'}</Badge>
              </div>
            )}
            {sale.return_status !== 'none' && (
              <div className="mt-1">
                <Badge tone={sale.return_status === 'full' ? 'red' : 'amber'}>
                  {sale.return_status === 'full' ? 'Fully returned' : 'Partially returned'}
                </Badge>
              </div>
            )}
          </div>
        </header>

        <section className="grid gap-6 py-6 text-sm sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Billed to</p>
            <p className="mt-1 font-medium text-slate-900">{sale.customer_name ?? 'Walk-in customer'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Date</p>
            <p className="mt-1 font-medium text-slate-900">{fmtDateTime(sale.sale_date)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Payment · Cashier</p>
            <p className="mt-1 font-medium text-slate-900">
              {sale.payment_method_display} · {sale.created_by_username}
            </p>
          </div>
        </section>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-y border-slate-200 bg-slate-50 print:bg-transparent">
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-500">#</th>
                <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-500">Item</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-slate-500">Qty</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-slate-500">Returned</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-slate-500">Unit price</th>
                <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-slate-500">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((it, i) => (
                <tr key={it.id}>
                  <td className="px-3 py-3 text-slate-500">{i + 1}</td>
                  <td className="px-3 py-3">
                    <p className="font-medium text-slate-900">{it.product_name}</p>
                    <p className="text-xs text-slate-500">{it.product_sku}</p>
                  </td>
                  <td className="px-3 py-3 text-right">{it.quantity}</td>
                  <td className="px-3 py-3 text-right text-slate-500">{it.returned_quantity > 0 ? it.returned_quantity : '—'}</td>
                  <td className="px-3 py-3 text-right">{money(it.unit_price)}</td>
                  <td className="px-3 py-3 text-right font-medium text-slate-900">{money(it.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex justify-end">
          <dl className="w-full max-w-xs space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Subtotal</dt>
              <dd className="text-slate-800">{money(sale.subtotal)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Discount</dt>
              <dd className="text-slate-800">{discount > 0 ? `− ${money(sale.discount)}` : money(0)}</dd>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-3 text-base font-bold text-slate-900">
              <dt>Grand total</dt>
              <dd>{money(sale.grand_total)}</dd>
            </div>
            {Number(sale.returned_total) > 0 && (
              <>
                <div className="flex justify-between text-red-600">
                  <dt>Returned / refunded</dt>
                  <dd>− {money(sale.returned_total)}</dd>
                </div>
                <div className="flex justify-between border-t border-slate-200 pt-2 font-bold text-slate-900">
                  <dt>Net total</dt>
                  <dd>{money(sale.net_total)}</dd>
                </div>
              </>
            )}
            <div className="flex justify-between border-t border-slate-100 pt-2">
              <dt className="text-slate-500">Paid</dt>
              <dd className="text-slate-800">{money(Number(sale.total_paid) - Number(sale.refunded_total))}</dd>
            </div>
            {Number(sale.due_amount) > 0 && (
              <div className="flex justify-between font-bold text-amber-700">
                <dt>Due</dt>
                <dd>{money(sale.due_amount)}</dd>
              </div>
            )}
          </dl>
        </div>

        {sale.note && (
          <p className="mt-6 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 print:bg-transparent print:px-0">
            <span className="font-medium text-slate-700">Note:</span> {sale.note}
          </p>
        )}
        <p className="mt-8 border-t border-slate-100 pt-4 text-center text-xs text-slate-400">
          {shop.footer}
        </p>
      </article>

      {(sale.returns ?? []).length > 0 && (
        <section className="card mt-6 p-5 print:hidden">
          <h2 className="text-sm font-semibold text-slate-900">Returns on this invoice</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {(sale.returns ?? []).map((r) => (
              <li key={r.id} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-slate-900">
                    {r.return_number} <span className="font-normal text-slate-500">· {fmtDateTime(r.return_date)} · {r.created_by_username}</span>
                  </p>
                  <p className="text-right font-semibold text-red-600">
                    {money(r.total_amount)}
                    <span className="block text-xs font-normal text-slate-500">
                      {Number(r.refund_amount) > 0 ? `${money(r.refund_amount)} refunded (${r.refund_method_display})` : ''}
                      {Number(r.refund_amount) > 0 && Number(r.due_adjusted) > 0 ? ' · ' : ''}
                      {Number(r.due_adjusted) > 0 ? `${money(r.due_adjusted)} deducted from due` : ''}
                    </span>
                  </p>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {(r.items ?? []).map((it) => `${it.quantity} × ${it.product_name}`).join(', ')}
                  {r.reason ? ` — ${r.reason}` : ''}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ReturnModal
        sale={sale}
        open={returning}
        onClose={() => setReturning(false)}
        onDone={() => {
          setReturning(false);
          reload();
        }}
      />
    </div>
  );
}
