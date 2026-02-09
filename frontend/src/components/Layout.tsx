import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FolderOpen, PlusCircle, Coins, Settings, LogOut } from 'lucide-react';
import type { ReactNode } from 'react';
import type { UserProfile } from '../api/client';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/projects', label: 'Projects', icon: FolderOpen },
  { to: '/projects/new', label: 'New Project', icon: PlusCircle },
  { to: '/credits', label: 'Credits', icon: Coins },
  { to: '/settings', label: 'Settings', icon: Settings },
];

interface Props {
  children: ReactNode;
  onLogout: () => void;
  user: UserProfile | null;
}

export default function Layout({ children, onLogout, user }: Props) {
  const { pathname } = useLocation();

  const initial = user?.email?.charAt(0).toUpperCase() ?? '?';

  return (
    <div className="min-h-screen bg-slate-950 flex">
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-xl font-bold text-white">IndexAI</h1>
          <p className="text-xs text-slate-500 mt-1">SEO Indexation Service</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-cyan-500/10 text-cyan-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-slate-800">
          {user && (
            <div className="flex items-center gap-3 px-3 py-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-sm font-bold shrink-0">
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-300 truncate">{user.email}</p>
                <p className="text-xs text-slate-500">{user.credit_balance} credits</p>
              </div>
            </div>
          )}
          <button
            onClick={onLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors w-full"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
