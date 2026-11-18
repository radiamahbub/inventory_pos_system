import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { AtSign, Loader2, Mail, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { AuthShell } from '@/components/auth/AuthShell';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { PageLoader } from '@/components/ui/Feedback';
import { useAuth } from '@/context/AuthContext';
import { parseError } from '@/utils/errors';

interface Status {
  enabled: boolean;
  requires_approval: boolean;
}

interface RegisterResponse {
  detail: string;
  requires_approval: boolean;
}

function passwordStrength(pw: string): { label: string; width: string; color: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (!pw) return { label: '', width: '0%', color: 'bg-slate-200' };
  if (score <= 2) return { label: 'Weak', width: '33%', color: 'bg-red-500' };
  if (score <= 3) return { label: 'Fair', width: '66%', color: 'bg-amber-500' };
  return { label: 'Strong', width: '100%', color: 'bg-emerald-500' };
}

export default function RegisterPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  const [status, setStatus] = useState<Status | null>(null);
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    username: '',
    email: '',
    password: '',
    confirm_password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    api
      .get<Status>('/auth/registration-status/')
      .then(({ data }) => setStatus(data))
      .catch(() => setStatus({ enabled: false, requires_approval: true }));
  }, []);

  if (!loading && user) return <Navigate to="/" replace />;

  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));
  const strength = passwordStrength(form.password);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const errors: Record<string, string> = {};
    if (!form.first_name.trim()) errors.first_name = 'First name is required.';
    if (!form.username.trim()) errors.username = 'Username is required.';
    if (!form.password) errors.password = 'Password is required.';
    if (form.password && form.password !== form.confirm_password) errors.confirm_password = 'Passwords do not match.';
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const { data } = await api.post<RegisterResponse>('/auth/register/', {
        ...form,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
      });
      if (data.requires_approval) {
        navigate('/login', { replace: true, state: { registered: true, requiresApproval: true } });
      } else {
        // Auto-approve চালু থাকলে সাথে সাথে login করিয়ে দিই
        await login(form.username.trim(), form.password);
        toast.success('Account created — welcome!');
        navigate('/', { replace: true });
      }
    } catch (err) {
      const parsed = parseError(err);
      setFieldErrors(parsed.fields);
      const known = ['first_name', 'last_name', 'username', 'email', 'password', 'confirm_password'];
      setError(Object.keys(parsed.fields).some((k) => known.includes(k)) ? '' : parsed.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!status) {
    return (
      <AuthShell>
        <PageLoader />
      </AuthShell>
    );
  }

  if (!status.enabled) {
    return (
      <AuthShell>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Registration is closed</h2>
        <p className="mt-2 text-sm text-slate-500">
          New accounts can only be created by an administrator. Please contact your manager.
        </p>
        <Link to="/login" className="btn btn-primary mt-6">
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  const err = (k: string) => fieldErrors[k];
  const cls = (k: string) => `input ${err(k) ? 'input-error' : ''}`;

  return (
    <AuthShell>
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">Create your account</h2>
      <p className="mt-2 text-sm text-slate-500">
        {status.requires_approval
          ? 'Your account will be reviewed and activated by an administrator.'
          : 'Fill in your details to get started.'}
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4" noValidate>
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="first_name" className="label">
              First name <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input id="first_name" className={`${cls('first_name')} pl-9`} autoFocus value={form.first_name} onChange={(e) => set('first_name')(e.target.value)} />
            </div>
            {err('first_name') && <p className="mt-1 text-xs text-red-600">{err('first_name')}</p>}
          </div>
          <div>
            <label htmlFor="last_name" className="label">
              Last name
            </label>
            <input id="last_name" className={cls('last_name')} value={form.last_name} onChange={(e) => set('last_name')(e.target.value)} />
            {err('last_name') && <p className="mt-1 text-xs text-red-600">{err('last_name')}</p>}
          </div>
        </div>

        <div>
          <label htmlFor="username" className="label">
            Username <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input id="username" className={`${cls('username')} pl-9`} autoComplete="username" value={form.username} onChange={(e) => set('username')(e.target.value)} />
          </div>
          {err('username') && <p className="mt-1 text-xs text-red-600">{err('username')}</p>}
        </div>

        <div>
          <label htmlFor="email" className="label">
            Email <span className="text-xs font-normal text-slate-400">(optional)</span>
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input id="email" type="email" className={`${cls('email')} pl-9`} autoComplete="email" value={form.email} onChange={(e) => set('email')(e.target.value)} />
          </div>
          {err('email') && <p className="mt-1 text-xs text-red-600">{err('email')}</p>}
        </div>

        <div>
          <label htmlFor="password" className="label">
            Password <span className="text-red-500">*</span>
          </label>
          <PasswordInput id="password" value={form.password} onChange={set('password')} autoComplete="new-password" hasError={Boolean(err('password'))} />
          {form.password && (
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200">
                <div className={`h-full rounded-full transition-all ${strength.color}`} style={{ width: strength.width }} />
              </div>
              <span className="text-xs text-slate-500">{strength.label}</span>
            </div>
          )}
          {err('password') ? (
            <p className="mt-1 text-xs text-red-600">{err('password')}</p>
          ) : (
            <p className="mt-1 text-xs text-slate-500">At least 8 characters. Avoid common or all-numeric passwords.</p>
          )}
        </div>

        <div>
          <label htmlFor="confirm_password" className="label">
            Confirm password <span className="text-red-500">*</span>
          </label>
          <PasswordInput id="confirm_password" value={form.confirm_password} onChange={set('confirm_password')} autoComplete="new-password" hasError={Boolean(err('confirm_password'))} />
          {err('confirm_password') && <p className="mt-1 text-xs text-red-600">{err('confirm_password')}</p>}
        </div>

        <button type="submit" className="btn btn-primary w-full py-2.5" disabled={submitting}>
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Creating account…
            </>
          ) : (
            'Create account'
          )}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand-600 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
