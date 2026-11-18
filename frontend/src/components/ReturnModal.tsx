import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Field, FormError, inputClass } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import type { PaymentMethod, Sale, SaleReturn } from '@/types';
import { parseError } from '@/utils/errors';
import { PAYMENT_LABEL, money } from '@/utils/format';

/** ইনভয়েসের ডিসকাউন্ট আইটেমগুলোর মধ্যে ভাগ করে ফেরতের দাম হিসাব (backend-এর নিয়মের সাথে মেলে) */
function unitRefund(sale: Sale, unitPrice: string): number {
  const subtotal = Number(sale.subtotal);
  if (subtotal <= 0) return 0;
  return (Number(unitPrice) * Number(sale.grand_total)) / subtotal;
}

export function ReturnModal({
  sale,
  open,
  onClose,
  onDone,
}: {
  sale: Sale;
  open: boolean;
  onClose: () => void;
  onDone: (ret: SaleReturn) => void;
}) {
  const items = useMemo(() => (sale.items ?? []).filter((i) => i.returnable_quantity > 0), [sale]);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [reason, setReason] = useState('');
  const [method, setMethod] = useState<PaymentMethod>(sale.payment_method);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setQty({});
      setReason('');
      setMethod(sale.payment_method);
      setError('');
    }
  }, [open, sale]);

  const setItemQty = (id: number, max: number, value: number) =>
    setQty((prev) => ({ ...prev, [id]: Math.max(0, Math.min(max, Math.floor(value) || 0)) }));

  const chosen = items.filter((i) => (qty[i.id] ?? 0) > 0);
  const refund = chosen.reduce((sum, i) => sum + unitRefund(sale, i.unit_price) * (qty[i.id] ?? 0), 0);
  const available = Number(sale.grand_total) - Number(sale.returned_total);
  const estimate = Math.min(refund, available);

  const submit = async () => {
    setError('');
    if (chosen.length === 0) {
      setError('Enter the quantity to return for at least one item.');
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<SaleReturn>(`/sales/${sale.id}/returns/`, {
        items: chosen.map((i) => ({ sale_item: i.id, quantity: qty[i.id] })),
        reason,
        refund_method: method,
      });
      toast.success(`Return ${data.return_number} saved`);
      onDone(data);
    } catch (err) {
      setError(parseError(err).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => !busy && onClose()}
      title={`Return items · ${sale.invoice_number}`}
      size="lg"
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={submit} disabled={busy || chosen.length === 0}>
            {busy ? 'Saving…' : `Confirm return · ${money(estimate)}`}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <FormError message={error} />
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Item</th>
                <th className="px-3 py-2 text-right">Sold</th>
                <th className="px-3 py-2 text-right">Already returned</th>
                <th className="px-3 py-2 text-right">Return qty</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((i) => (
                <tr key={i.id}>
                  <td className="px-3 py-2">
                    <p className="font-medium text-slate-900">{i.product_name}</p>
                    <p className="text-xs text-slate-500">
                      {i.product_sku} · {money(unitRefund(sale, i.unit_price))} each
                    </p>
                  </td>
                  <td className="px-3 py-2 text-right">{i.quantity}</td>
                  <td className="px-3 py-2 text-right">{i.returned_quantity}</td>
                  <td className="px-3 py-2 text-right">
                    <div className="inline-flex items-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={i.returnable_quantity}
                        className="input w-20 text-right"
                        value={qty[i.id] ?? 0}
                        onChange={(e) => setItemQty(i.id, i.returnable_quantity, Number(e.target.value))}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => setItemQty(i.id, i.returnable_quantity, i.returnable_quantity)}
                      >
                        All ({i.returnable_quantity})
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Refund paid by" hint="Used only if money is refunded">
            <select className={inputClass()} value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
              {(['cash', 'card', 'mobile_banking'] as PaymentMethod[]).map((m) => (
                <option key={m} value={m}>
                  {PAYMENT_LABEL[m]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Reason" hint="Optional, e.g. damaged / wrong item">
            <input className={inputClass()} maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        </div>

        <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          Returned items go back into stock. The goods are valued after sharing the invoice discount across the items. If the
          customer already paid more than the goods they keep, the difference is refunded; any unpaid (due) amount is reduced
          instead. The server works out the exact split.
        </p>
      </div>
    </Modal>
  );
}
