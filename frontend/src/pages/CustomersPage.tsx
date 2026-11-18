import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import { ResourcePage } from '@/components/ResourcePage';
import { Badge } from '@/components/ui/Feedback';
import { useAuth } from '@/context/AuthContext';
import type { Customer } from '@/types';
import { fmtDate, money } from '@/utils/format';

const dash = <span className="text-slate-400">—</span>;

export default function CustomersPage() {
  const { isAdmin } = useAuth();
  const [params] = useSearchParams();
  const [onlyDue, setOnlyDue] = useState(params.get('due') === '1');

  return (
    <ResourcePage<Customer>
      title="Customers"
      subtitle="People who buy from you, and what they owe."
      singular="Customer"
      endpoint="/customers/"
      searchPlaceholder="Search by name, phone or email…"
      canCreate
      canEdit
      canDelete={isAdmin}
      filterParams={{ has_due: onlyDue ? 'true' : undefined }}
      filters={
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            checked={onlyDue}
            onChange={(e) => setOnlyDue(e.target.checked)}
          />
          Only customers with due
        </label>
      }
      columns={[
        {
          key: 'name',
          header: 'Customer',
          render: (c) => (
            <Link to={`/customers/${c.id}/ledger`} className="font-medium text-slate-900 hover:text-brand-600 hover:underline">
              {c.name}
            </Link>
          ),
        },
        { key: 'phone', header: 'Phone', render: (c) => c.phone || dash },
        {
          key: 'due',
          header: 'Due',
          align: 'right',
          render: (c) =>
            Number(c.balance) > 0 ? <Badge tone="amber">{money(c.balance)}</Badge> : <span className="text-slate-400">—</span>,
        },
        { key: 'address', header: 'Address', className: 'max-w-xs truncate', render: (c) => c.address || dash },
        { key: 'created', header: 'Added', render: (c) => fmtDate(c.created_at) },
      ]}
      fields={[
        { name: 'name', label: 'Full name', required: true, half: true },
        { name: 'phone', label: 'Phone', half: true, placeholder: '01XXXXXXXXX' },
        { name: 'email', label: 'Email', type: 'email' },
        { name: 'address', label: 'Address', type: 'textarea' },
      ]}
      extraActions={(c) => (
        <Link to={`/customers/${c.id}/ledger`} className="btn-icon" title="Ledger / collect due">
          <BookOpen className="h-4 w-4" />
        </Link>
      )}
    />
  );
}
