import { useEffect } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import { api } from '@/api/client';
import { ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { useFetch } from '@/hooks/useFetch';
import { useShop } from '@/hooks/useShop';
import type { Sale } from '@/types';
import { fmtDateTime, money } from '@/utils/format';

/** 80mm থার্মাল প্রিন্টারের জন্য রসিদ। প্রিন্ট ডায়ালগে প্রিন্টার বেছে "Margins: None" দিন। */
export default function ReceiptPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const shop = useShop();
  const { data: sale, loading, error, reload } = useFetch<Sale>(async () => {
    const { data } = await api.get<Sale>(`/sales/${id}/`);
    return data;
  }, [id]);

  // শুধু এই পেজ থাকাকালীন কাগজের সাইজ 80mm চওড়া (অন্য পেজের প্রিন্টে প্রভাব ফেলে না)
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = '@page { size: 80mm auto; margin: 0; }';
    document.head.appendChild(style);
    return () => style.remove();
  }, []);

  const autoPrint = params.get('print') === '1';
  useEffect(() => {
    if (!autoPrint || !sale) return;
    const t = window.setTimeout(() => window.print(), 400);
    return () => window.clearTimeout(t);
  }, [autoPrint, sale]);

  if (loading) return <PageLoader label="Loading receipt…" />;
  if (error || !sale) {
    return (
      <div className="space-y-4">
        <Link to="/sales" className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to sales
        </Link>
        <ErrorBanner message={error ?? 'Receipt not found.'} onRetry={reload} />
      </div>
    );
  }

  const items = sale.items ?? [];
  const row = 'flex justify-between gap-2';
  const rule = <div className="my-1.5 border-t border-dashed border-slate-500" />;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between print:hidden">
        <Link to={`/sales/${sale.id}`} className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to invoice
        </Link>
        <button className="btn btn-primary btn-sm" onClick={() => window.print()}>
          <Printer className="h-4 w-4" /> Print receipt
        </button>
      </div>

      <article className="mx-auto w-[72mm] bg-white p-2 font-mono text-[12px] leading-snug text-black shadow print:m-0 print:w-[72mm] print:shadow-none">
        <header className="text-center">
          <p className="text-base font-bold">{shop.name}</p>
          {shop.address && <p>{shop.address}</p>}
          {shop.phone && <p>{shop.phone}</p>}
        </header>
        {rule}
        <p className="font-bold">Invoice: {sale.invoice_number}</p>
        <p>{fmtDateTime(sale.sale_date)}</p>
        <p>Customer: {sale.customer_name ?? 'Walk-in'}</p>
        <p>Cashier: {sale.created_by_username}</p>
        {rule}
        {items.map((it) => (
          <div key={it.id} className="mb-1">
            <p className="font-bold">{it.product_name}</p>
            <div className={row}>
              <span>
                {it.quantity} x {money(it.unit_price)}
                {it.returned_quantity > 0 ? ` (returned ${it.returned_quantity})` : ''}
              </span>
              <span>{money(it.line_total)}</span>
            </div>
          </div>
        ))}
        {rule}
        <div className={row}>
          <span>Subtotal</span>
          <span>{money(sale.subtotal)}</span>
        </div>
        {Number(sale.discount) > 0 && (
          <div className={row}>
            <span>Discount</span>
            <span>- {money(sale.discount)}</span>
          </div>
        )}
        <div className={`${row} text-sm font-bold`}>
          <span>Total</span>
          <span>{money(sale.grand_total)}</span>
        </div>
        {Number(sale.returned_total) > 0 && (
          <>
            <div className={row}>
              <span>Returned</span>
              <span>- {money(sale.returned_total)}</span>
            </div>
            <div className={`${row} font-bold`}>
              <span>Net total</span>
              <span>{money(sale.net_total)}</span>
            </div>
          </>
        )}
        <div className={row}>
          <span>Paid</span>
          <span>{money(Number(sale.total_paid) - Number(sale.refunded_total))}</span>
        </div>
        {Number(sale.due_amount) > 0 && (
          <div className={`${row} text-sm font-bold`}>
            <span>DUE</span>
            <span>{money(sale.due_amount)}</span>
          </div>
        )}
        {rule}
        <p>Payment: {sale.payment_method_display}</p>
        {sale.note && <p>Note: {sale.note}</p>}
        <p className="mt-2 text-center">{shop.footer}</p>
      </article>
    </div>
  );
}
