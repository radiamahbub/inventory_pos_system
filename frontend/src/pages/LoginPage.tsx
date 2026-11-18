import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { CheckCircle2, Loader2, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/api/client';
import { AuthShell } from '@/components/auth/AuthShell';
import { PasswordInput } from '@/components/auth/PasswordInput';
import { useAuth } from '@/context/AuthContext';
import { parseError } from '@/utils/errors';

interface LocationState {
  from?: string;
  registered?: boolean;
  requiresApproval?: boolean;
}

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState | null) ?? {};
  const from = state.from ?? '/';

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [registrationEnabled, setRegistrationEnabled] = useState(false);

  // Admin registration বন্ধ রাখলে "Create account" লিংক দেখাব না
  useEffect(() => {
    api
      .get<{ enabled: boolean }>('/auth/registration-status/')
      .then(({ data }) => setRegistrationEnabled(data.enabled))
      .catch(() => setRegistrationEnabled(false));
  }, []);

  if (!loading && user) return <Navigate to={from} replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) {
      setError('Please enter your username and password.');
      return;
    }
    setSubmitting(true);
    try {
      const u = await login(username.trim(), password);
      toast.success(`Welcome back, ${u.first_name || u.username}!`);
      navigate(from, { replace: true });
    } catch (err) {
      const parsed = parseError(err);
      // Backend inactive (approval বাকি) ও ভুল পাসওয়ার্ড — দুটোতেই একই 401 message দেয়
      const isCredentials = /no active account|unable to log in/i.test(parsed.message);
      setError(
        isCredentials
          ? 'Incorrect username or password — or your account is still waiting for administrator approval.'
          : parsed.message,
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">Sign in to your account</h2>
      <p className="mt-2 text-sm text-slate-500">Enter your credentials to access the dashboard.</p>

      {state.registered && (
        <div className="mt-6 flex gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            {state.requiresApproval
              ? 'Account created! An administrator needs to approve it before you can sign in.'
              : 'Account created! You can sign in now.'}
          </p>
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-8 space-y-5" noValidate>
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="username" className="label">
            Username
          </label>
          <div className="relative">
            <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              id="username"
              className="input pl-9"
              autoComplete="username"
              autoFocus
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label htmlFor="password" className="label">
            Password
          </label>
          <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="current-password" placeholder="Enter your password" />
        </div>

        <button type="submit" className="btn btn-primary w-full py-2.5" disabled={submitting}>
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Signing in…
            </>
          ) : (
            'Sign in'
          )}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-slate-500">
        {registrationEnabled ? (
          <>
            New here?{' '}
            <Link to="/register" className="font-semibold text-brand-600 hover:underline">
              Create an account
            </Link>
          </>
        ) : (
          'Need an account? Ask your administrator to create one for you.'
        )}
      </p>
    </AuthShell>
  );
}
