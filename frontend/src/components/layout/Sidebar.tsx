import { NavLink } from 'react-router-dom';
import { LogOut, Store, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useLogout } from '@/hooks/useLogout';
import { fullName } from '@/utils/format';
import { NAV_GROUPS } from './nav';

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const handleLogout = useLogout();

  return (
    <>
      {/* মোবাইলে overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-[2px] lg:hidden print:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-brand-950 text-slate-300 transition-transform duration-200 lg:translate-x-0 print:hidden ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-lg shadow-brand-900/40">
              <Store className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-bold text-white">Inventory POS</p>
              <p className="text-[11px] text-brand-300">Management System</p>
            </div>
          </div>
          <button className="text-slate-400 hover:text-white lg:hidden" onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
          {NAV_GROUPS.map((group) => {
            const items = group.items.filter((i) => !i.roles || (user && i.roles.includes(user.role)));
            if (items.length === 0) return null;
            return (
              <div key={group.title}>
                <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-brand-400/80">
                  {group.title}
                </p>
                <ul className="space-y-1">
                  {items.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        onClick={onClose}
                        className={({ isActive }) =>
                          `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                            isActive
                              ? 'bg-brand-600 text-white shadow-md shadow-brand-900/30'
                              : 'text-slate-300 hover:bg-white/5 hover:text-white'
                          }`
                        }
                      >
                        <item.icon className="h-[18px] w-[18px] shrink-0" />
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>

        {user && (
          <div className="border-t border-white/10 p-3">
            <div className="flex items-center gap-3 rounded-lg px-2 py-2">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                {fullName(user).slice(0, 1).toUpperCase()}
              </span>
              <div className="min-w-0 leading-tight">
                <p className="truncate text-sm font-semibold text-white">{fullName(user)}</p>
                <p className="text-xs capitalize text-brand-300">{user.role}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-red-500/15 hover:text-red-300"
            >
              <LogOut className="h-[18px] w-[18px]" />
              Sign out
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
