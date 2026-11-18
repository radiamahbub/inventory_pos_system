import { ResourcePage } from '@/components/ResourcePage';
import { Badge } from '@/components/ui/Feedback';
import { useAuth } from '@/context/AuthContext';
import type { Category } from '@/types';
import { fmtDate } from '@/utils/format';

export default function CategoriesPage() {
  const { isAdmin } = useAuth();
  return (
    <ResourcePage<Category>
      title="Categories"
      subtitle="Organise your products into categories."
      singular="Category"
      endpoint="/categories/"
      searchPlaceholder="Search categories…"
      canCreate={isAdmin}
      canEdit={isAdmin}
      canDelete={isAdmin}
      columns={[
        { key: 'name', header: 'Name', render: (c) => <span className="font-medium text-slate-900">{c.name}</span> },
        { key: 'description', header: 'Description', render: (c) => c.description || <span className="text-slate-400">—</span> },
        { key: 'count', header: 'Products', render: (c) => <Badge tone="indigo">{c.product_count}</Badge> },
        { key: 'created', header: 'Created', render: (c) => fmtDate(c.created_at) },
      ]}
      fields={[
        { name: 'name', label: 'Category name', required: true, placeholder: 'e.g. Beverages' },
        { name: 'description', label: 'Description', type: 'textarea', placeholder: 'Optional' },
      ]}
      deleteMessage={(c) =>
        c.product_count > 0
          ? `"${c.name}" has ${c.product_count} product(s). It cannot be deleted until those products are moved or removed.`
          : `"${c.name}" will be permanently deleted.`
      }
    />
  );
}
