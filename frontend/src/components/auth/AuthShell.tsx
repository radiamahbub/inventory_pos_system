import type { ReactNode } from 'react';
import { BarChart3, Boxes, ShieldCheck, ShoppingCart, Store } from 'lucide-react';

const FEATURES = [
  { icon: ShoppingCart, title: 'Fast POS billing', text: 'Multi-item sales with instant invoices and automatic stock deduction.' },
  { icon: Boxes, title: 'Live inventory', text: 'Track stock movements and get low-stock alerts before you run out.' },
  { icon: BarChart3, title: 'Business reports', text: 'Daily, monthly and yearly sales with estimated profit.' },
  { icon: ShieldCheck, title: 'Role based access', text: 'Separate Admin and Cashier permissions keep your data safe.' },
];

/** Login ও Register পেজের সাধারণ লেআউট (বাঁদিকে brand panel, ডানদিকে form) */
export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-950 via-brand-900 to-brand-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-sky-400/10 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/20">
            <Store className="h-6 w-6" />
          </div>
          <div className="leading-tight">
            <p className="text-lg font-bold">Inventory POS</p>
            <p className="text-xs text-brand-200">Management System</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-4xl font-bold leading-tight tracking-tight">Run your shop with clarity and control.</h1>
          <p className="mt-4 text-brand-100">Sales, purchases, stock and reports — everything in one clean workspace.</p>
          <ul className="mt-10 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <f.icon className="h-5 w-5" />
                </span>
                <span>
                  <span className="block text-sm font-semibold">{f.title}</span>
                  <span className="block text-sm text-brand-200">{f.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-brand-300">© {new Date().getFullYear()} Inventory POS · BASIS Final Project</p>
      </div>

      <div className="flex items-center justify-center bg-slate-50 px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
              <Store className="h-5 w-5" />
            </div>
            <p className="text-lg font-bold text-slate-900">Inventory POS</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
