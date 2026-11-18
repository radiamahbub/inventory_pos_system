import { useState } from 'react';
import type { FormEvent } from 'react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { PageHeader, Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Feedback';
import { Field, FormError, inputClass } from '@/components/ui/Form';
import { useAuth } from '@/context/AuthContext';
import { fmtDateTime, fullName } from '@/utils/format';
import { parseError } from '@/utils/errors';

export default function ProfilePage() {
  const { user } = useAuth();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  if (!user) return null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFieldErrors({});
    if (newPassword !== confirm) {
      setFieldErrors({ confirm: 'Passwords do not match.' });
      return;
    }
    setSaving(true);
    try {
      await api.post('/auth/change-password/', { old_password: oldPassword, new_password: newPassword });
      toast.success('Password changed successfully');
      setOldPassword('');
      setNewPassword('');
      setConfirm('');
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      setFormError(Object.keys(parsed.fields).length ? '' : parsed.message);
    } finally {
      setSaving(false);
    }
  };

  const rows: [string, string][] = [
    ['Username', user.username],
    ['Full name', fullName(user)],
    ['Email', user.email || '—'],
    ['Last login', fmtDateTime(user.last_login)],
    ['Member since', fmtDateTime(user.date_joined)],
  ];

  return (
    <>
      <PageHeader title="My Profile" subtitle="Your account details and password." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Account information">
          <div className="mb-5 flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-xl font-bold text-white">
              {fullName(user).slice(0, 1).toUpperCase()}
            </span>
            <div>
              <p className="font-semibold text-slate-900">{fullName(user)}</p>
              <Badge tone={user.role === 'admin' ? 'indigo' : 'blue'}>
                {user.role === 'admin' ? 'Admin' : 'Cashier'}
              </Badge>
            </div>
          </div>
          <dl className="divide-y divide-slate-100 text-sm">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between py-2.5">
                <dt className="text-slate-500">{k}</dt>
                <dd className="font-medium text-slate-800">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card title="Change password">
          <form onSubmit={onSubmit} className="space-y-4">
            <FormError message={formError} />
            <Field label="Current password" required error={fieldErrors.old_password}>
              <input
                type="password"
                autoComplete="current-password"
                className={inputClass(fieldErrors.old_password)}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
              />
            </Field>
            <Field label="New password" required error={fieldErrors.new_password} hint="At least 8 characters, not too common or all numeric.">
              <input
                type="password"
                autoComplete="new-password"
                className={inputClass(fieldErrors.new_password)}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </Field>
            <Field label="Confirm new password" required error={fieldErrors.confirm}>
              <input
                type="password"
                autoComplete="new-password"
                className={inputClass(fieldErrors.confirm)}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </Field>
            <button className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Update password'}
            </button>
          </form>
        </Card>
      </div>
    </>
  );
}
