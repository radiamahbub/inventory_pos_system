import { ResourcePage } from '@/components/ResourcePage';
import { useAuth } from '@/context/AuthContext';
import type { Supplier } from '@/types';

const dash = <span className="text-slate-400">—</span>;

export default function SuppliersPage() {
  const { isAdmin } = useAuth();
  return (
    <ResourcePage<Supplier>
      title="Suppliers"
      subtitle="Vendors you purchase stock from."
      singular="Supplier"
      endpoint="/suppliers/"
      searchPlaceholder="Search suppliers…"
      canCreate={isAdmin}
      canEdit={isAdmin}
      canDelete={isAdmin}
      columns={[
        { key: 'name', header: 'Supplier', render: (s) => <span className="font-medium text-slate-900">{s.name}</span> },
        { key: 'contact', header: 'Contact person', render: (s) => s.contact_person || dash },
        { key: 'phone', header: 'Phone', render: (s) => s.phone || dash },
        { key: 'email', header: 'Email', render: (s) => s.email || dash },
        { key: 'address', header: 'Address', className: 'max-w-xs truncate', render: (s) => s.address || dash },
      ]}
      fields={[
        { name: 'name', label: 'Supplier name', required: true, half: true },
        { name: 'contact_person', label: 'Contact person', half: true },
        { name: 'phone', label: 'Phone', half: true, placeholder: '01XXXXXXXXX' },
        { name: 'email', label: 'Email', type: 'email', half: true },
        { name: 'address', label: 'Address', type: 'textarea' },
      ]}
    />
  );
}
