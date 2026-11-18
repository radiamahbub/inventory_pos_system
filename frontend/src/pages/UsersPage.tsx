import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { UserCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { ResourcePage } from '@/components/ResourcePage';
import { Badge } from '@/components/ui/Feedback';
import { useAuth } from '@/context/AuthContext';
import type { User } from '@/types';
import { parseError } from '@/utils/errors';
import { fmtDateTime, fullName } from '@/utils/format';

/** Self-register করা (এখনো কখনো login করেনি) inactive অ্যাকাউন্ট = approval-এর অপেক্ষায় */
const isPending = (u: User) => !u.is_active && !u.last_login;

function ApproveButton({ user, onDone }: { user: User; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const approve = async () => {
    setBusy(true);
    try {
      await api.patch(`/users/${user.id}/`, { is_active: true });
      toast.success(`${user.username} approved — they can sign in now`);
      onDone();
    } catch (err) {
      toast.error(parseError(err).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button className="btn btn-sm bg-emerald-600 text-white hover:bg-emerald-700" onClick={approve} disabled={busy}>
      <UserCheck className="h-3.5 w-3.5" /> {isPending(user) ? 'Approve' : 'Activate'}
    </button>
  );
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const [params] = useSearchParams();
  const [role, setRole] = useState('');
  const [status, setStatus] = useState(params.get('status') ?? '');

  return (
    <ResourcePage<User>
      title="Users"
      subtitle="Manage who can sign in and what they can do. New self-registered accounts appear here for approval."
      singular="User"
      endpoint="/users/"
      searchPlaceholder="Search by username, name or email…"
      canCreate
      canEdit
      canDelete
      // boolean false cleanParams-এ বাদ পড়ে, তাই string পাঠাই
      filterParams={{ role, is_active: status === 'active' ? 'true' : status === 'inactive' ? 'false' : '' }}
      filters={
        <>
          <select className="input sm:w-40" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">All roles</option>
            <option value="admin">Admin</option>
            <option value="cashier">Cashier</option>
          </select>
          <select className="input sm:w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive / pending</option>
          </select>
        </>
      }
      extraActions={(u, reload) => (u.is_active ? null : <ApproveButton user={u} onDone={reload} />)}
      columns={[
        {
          key: 'user',
          header: 'User',
          render: (u) => (
            <div>
              <p className="font-medium text-slate-900">
                {fullName(u)} {u.id === me?.id && <span className="text-xs font-normal text-slate-400">(you)</span>}
              </p>
              <p className="text-xs text-slate-500">@{u.username}</p>
            </div>
          ),
        },
        { key: 'email', header: 'Email', render: (u) => u.email || <span className="text-slate-400">—</span> },
        {
          key: 'role',
          header: 'Role',
          render: (u) => <Badge tone={u.role === 'admin' ? 'indigo' : 'blue'}>{u.role === 'admin' ? 'Admin' : 'Cashier'}</Badge>,
        },
        {
          key: 'status',
          header: 'Status',
          render: (u) =>
            u.is_active ? <Badge tone="green">Active</Badge> : isPending(u) ? <Badge tone="amber">Pending approval</Badge> : <Badge tone="slate">Inactive</Badge>,
        },
        { key: 'login', header: 'Last login', render: (u) => fmtDateTime(u.last_login) },
      ]}
      fields={[
        { name: 'username', label: 'Username', required: true, half: true },
        { name: 'email', label: 'Email', type: 'email', half: true },
        { name: 'first_name', label: 'First name', half: true },
        { name: 'last_name', label: 'Last name', half: true },
        {
          name: 'role',
          label: 'Role',
          type: 'select',
          half: true,
          options: [
            { value: 'cashier', label: 'Cashier' },
            { value: 'admin', label: 'Admin' },
          ],
        },
        { name: 'password', label: 'Password', type: 'password', required: true, half: true },
        { name: 'is_active', label: 'Account is active', type: 'checkbox' },
      ]}
      defaults={{ role: 'cashier', is_active: true }}
      deleteMessage={(u) =>
        `"${u.username}" will be deleted. Users who already have sales or purchase history cannot be deleted — deactivate them instead.`
      }
    />
  );
}
