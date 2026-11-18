import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, HandCoins, Printer, Receipt, Wallet } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { Card, PageHeader, StatCard } from '@/components/ui/Card';
import { Badge, ErrorBanner, PageLoader } from '@/components/ui/Feedback';
import { Field, FormError, inputClass } from '@/components/ui/Form';
import { Modal } from '@/components/ui/Modal';
import { useFetch } from '@/hooks/useFetch';
import type { CustomerLedger, LedgerEntry, PaymentMethod } from '@/types';
import { parseError } from '@/utils/errors';
import { PAYMENT_LABEL, fmtDateTime, money } from '@/utils/format';

const TYPE_LABEL: Record<LedgerEntry['type'], { label: string; tone: 'blue' | 'green' | 'amber' | 'indigo' }> = {
  sale: { label: 'Sale', tone: 'blue' },
  payment_at_sale: { label: 'Paid at sale', tone: 'green' },
  return: { label: 'Return', tone: 'amber' },
  collection: { label: 'Collection', tone: 'indigo' },
};

export default function CustomerLedgerPage() {
  const { id } = useParams();
  const { data, loading, error, reload } = useFetch<CustomerLedger>(async () => {
    const { data } = await api.get<CustomerLedger>(`/customers/${id}/ledger/`);
    return data;
  }, [id]);

  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState<PaymentMethod>('cash');
  const [note, setNote] = useState('');
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  if (loading && !data) return <PageLoader label="Loading ledger…" />;
  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link to="/customers" className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to customers
        </Link>
        <ErrorBanner message={error ?? 'Customer not found.'} onRetry={reload} />
      </div>
    );
  }

  const { customer, entries } = data;
  const due = Number(data.balance);

  const openCollect = () => {
    setAmount(due > 0 ? due.toFixed(2) : '');
    setMethod('cash');
    setNote('');
    setFormError('');
    setOpen(true);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setFormError('');
    try {
      await api.post(`/customers/${customer.id}/payments/`, { amount, payment_method: method, note });
      toast.success('Payment recorded');
      setOpen(false);
      reload();
    } catch (err) {
      setFormError(parseError(err).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="mb-4 flex items-center justify-between print:hidden">
        <Link to="/customers" className="btn btn-secondary btn-sm">
          <ArrowLeft className="h-4 w-4" /> Back to customers
        </Link>
        <div className="flex gap-2">
          <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
            <Printer className="h-4 w-4" /> Print statement
          </button>
          <button className="btn btn-primary btn-sm" onClick={openCollect} disabled={due <= 0}>
            <HandCoins className="h-4 w-4" /> Collect payment
          </button>
        </div>
      </div>

      <PageHeader
        title={customer.name}
        subtitle={[customer.phone, customer.address].filter(Boolean).join(' · ') || 'Customer ledger'}
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Total purchases" value={money(data.total_sales)} hint="After returns" icon={Receipt} tone="sky" />
        <StatCard label="Received" value={money(data.total_received)} icon={Wallet} tone="emerald" />
        <StatCard label="Due (balance)" value={money(data.balance)} hint={due > 0 ? 'Customer owes you' : 'Nothing due'} icon={HandCoins} tone={due > 0 ? 'amber' : 'emerald'} />
      </div>

      <Card title="Statement" bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 print:bg-transparent">
                <th className="px-4 py-2 text-left">Date</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Reference</th>
                <th className="px-4 py-2 text-left">Details</th>
                <th className="px-4 py-2 text-right">Charged</th>
                <th className="px-4 py-2 text-right">Credit</th>
                <th className="px-4 py-2 text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-400">
                    No transactions yet.
                  </td>
                </tr>
              )}
              {entries.map((e, i) => (
                <tr key={`${e.type}-${e.reference}-${i}`}>
                  <td className="whitespace-nowrap px-4 py-2 text-slate-600">{fmtDateTime(e.date)}</td>
                  <td className="px-4 py-2">
                    <Badge tone={TYPE_LABEL[e.type].tone}>{TYPE_LABEL[e.type].label}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    {e.sale_id && e.type !== 'collection' ? (
                      <Link to={`/sales/${e.sale_id}`} className="font-medium text-brand-600 hover:underline">
                        {e.reference}
                      </Link>
                    ) : (
                      e.reference
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{e.description}</td>
                  <td className="px-4 py-2 text-right">{Number(e.debit) > 0 ? money(e.debit) : ''}</td>
                  <td className="px-4 py-2 text-right text-emerald-700">{Number(e.credit) > 0 ? money(e.credit) : ''}</td>
                  <td className={`px-4 py-2 text-right font-semibold ${Number(e.balance) > 0 ? 'text-amber-700' : 'text-slate-900'}`}>
                    {money(e.balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal
        open={open}
        onClose={() => !busy && setOpen(false)}
        title={`Collect payment · ${customer.name}`}
        size="sm"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </button>
            <button type="submit" form="collect-form" className="btn btn-primary" disabled={busy}>
              {busy ? 'Saving…' : 'Record payment'}
            </button>
          </>
        }
      >
        <form id="collect-form" onSubmit={submit} className="space-y-4">
          <FormError message={formError} />
          <p className="text-sm text-slate-600">
            Current due: <strong>{money(data.balance)}</strong>. Payments are applied to the oldest unpaid invoices first.
          </p>
          <Field label="Amount (৳)" required>
            <input
              type="number"
              min="0.01"
              max={due > 0 ? due : undefined}
              step="0.01"
              className={inputClass()}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>
          <Field label="Paid by">
            <select className={inputClass()} value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
              {(['cash', 'card', 'mobile_banking'] as PaymentMethod[]).map((m) => (
                <option key={m} value={m}>
                  {PAYMENT_LABEL[m]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Note" hint="Optional">
            <input className={inputClass()} maxLength={255} value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
        </form>
      </Modal>
    </>
  );
}
