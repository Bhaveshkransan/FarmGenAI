import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Bell, LogOut, Sprout, Menu, X,
  LayoutDashboard, Handshake, BarChart3, User,
  Receipt, Cpu, Settings, Truck, Warehouse, Factory
} from 'lucide-react';

// Role-specific navigation — each role ONLY sees their own section
const NAV_CONFIG: Record<string, { label: string; items: { to: string; label: string; icon: any }[] }> = {
  farmer: {
    label: 'Farmer Agent',
    items: [
      { to: '/dashboard/farmer', label: 'My Dashboard', icon: LayoutDashboard },
      { to: '/farmer/listings', label: 'My Listings', icon: BarChart3 },
      { to: '/farmer/negotiations', label: 'My Negotiations', icon: Handshake },
      { to: '/transactions', label: 'Transactions', icon: Receipt },
      { to: '/analytics', label: 'Market Analytics', icon: BarChart3 },
    ],
  },
  buyer: {
    label: 'Buyer Agent',
    items: [
      { to: '/dashboard/buyer', label: 'My Dashboard', icon: LayoutDashboard },
      { to: '/buyer/matches', label: 'Find Suppliers', icon: BarChart3 },
      { to: '/buyer/negotiations', label: 'My Deals', icon: Handshake },
      { to: '/transactions', label: 'Transactions', icon: Receipt },
      { to: '/analytics', label: 'Market Intel', icon: BarChart3 },
    ],
  },
  transport: {
    label: 'Transport Agent',
    items: [
      { to: '/dashboard/transport', label: 'My Dashboard', icon: LayoutDashboard },
      { to: '/dashboard/transport/negotiation', label: 'My Negotiations', icon: Handshake },
      { to: '/dashboard/transport/transactions', label: 'Transactions', icon: Receipt },
      { to: '/dashboard/transport/analytics', label: 'Market Analytics', icon: BarChart3 },
    ],
  },
  warehouse: {
    label: 'Warehouse Agent',
    items: [
      { to: '/dashboard/warehouse', label: 'My Dashboard', icon: Warehouse },
      { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
  processor: {
    label: 'Processor Agent',
    items: [
      { to: '/dashboard/processor', label: 'My Dashboard', icon: Factory },
      { to: '/transactions', label: 'Transactions', icon: Receipt },
      { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
  admin: {
    label: 'Admin Console',
    items: [
      { to: '/dashboard/admin', label: 'Admin Overview', icon: LayoutDashboard },
      { to: '/dashboard/farmer', label: 'Farmer Agent', icon: Sprout },
      { to: '/dashboard/buyer', label: 'Buyer Agent', icon: Handshake },
      { to: '/dashboard/transport', label: 'Transport Agent', icon: Truck },
      { to: '/dashboard/warehouse', label: 'Warehouse Agent', icon: Warehouse },
      { to: '/dashboard/processor', label: 'Processor Agent', icon: Factory },
      { to: '/dashboard/ai-ops', label: 'AI Operations', icon: Cpu },
      { to: '/dashboard/settings', label: 'Settings', icon: Settings },
      { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
};

// Role badge colors
const ROLE_COLORS: Record<string, string> = {
  farmer: 'bg-emerald-600',
  buyer: 'bg-blue-600',
  transport: 'bg-orange-600',
  warehouse: 'bg-purple-600',
  processor: 'bg-rose-600',
  admin: 'bg-slate-600',
};


export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const role = user?.role?.toLowerCase() || 'farmer';
  const roleConfig = NAV_CONFIG[role] || NAV_CONFIG['farmer'];
  const navItems = roleConfig.items;
  const roleLabel = roleConfig.label;
  const roleBadgeColor = ROLE_COLORS[role] || 'bg-slate-600';

  const isActive = (path: string) =>
    location.pathname === path ||
    (path !== '/dashboard' && location.pathname.startsWith(path));

  const currentPageLabel = navItems.find(n => isActive(n.to))?.label || roleLabel;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row relative">
      
      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden animate-fade-in"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed md:static inset-y-0 left-0 w-64 bg-emerald-900 text-white
        flex flex-col z-30 dark-scroll overflow-y-auto
        transition-transform duration-300 ease-in-out
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        
        {/* Logo */}
        <div className="p-5 flex items-center justify-between md:justify-start gap-3 border-b border-emerald-800/50 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-700/50 p-2 rounded-xl">
              <Sprout size={22} className="text-emerald-300" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">FarmGenAI</h1>
              <p className="text-[10px] text-emerald-400 font-semibold tracking-wider uppercase">Autonomous Agri System</p>
            </div>
          </div>
          <button
            className="md:hidden text-emerald-300 hover:text-white p-1 rounded-lg hover:bg-emerald-800 transition"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Role Badge */}
        <div className="px-4 py-3 border-b border-emerald-800/40">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider text-white ${roleBadgeColor}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-white/70 animate-pulse"></span>
            {roleLabel}
          </span>
        </div>

        {/* Navigation — role-scoped only */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-300/60 px-3 py-1 mb-1">
            Navigation
          </div>
          {navItems.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              onClick={() => setIsMobileMenuOpen(false)}
              className={`nav-link ${isActive(to) ? 'nav-link-active' : ''}`}
            >
              <Icon size={18} className="flex-shrink-0" />
              <span>{label}</span>
            </Link>
          ))}

          {/* Profile Link — always available */}
          <div className="pt-3 mt-3 border-t border-emerald-800/40">
            <Link
              to="/profile"
              onClick={() => setIsMobileMenuOpen(false)}
              className={`nav-link ${isActive('/profile') ? 'nav-link-active' : ''}`}
            >
              <User size={18} className="flex-shrink-0" />
              <span>My Profile</span>
            </Link>
          </div>
        </nav>

        {/* User Footer */}
        <div className="p-3 border-t border-emerald-800/50 flex-shrink-0">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            <div className={`w-9 h-9 rounded-xl ${roleBadgeColor} flex items-center justify-center font-bold text-sm flex-shrink-0`}>
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-emerald-400 truncate capitalize">{user?.role || 'Farmer'}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm
                       text-emerald-200 hover:text-white bg-emerald-800/40 hover:bg-red-500/80
                       rounded-xl transition-all duration-200 active:scale-95"
          >
            <LogOut size={15} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden w-full">
        
        {/* Top Header */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 sticky top-0 z-10 glass">
          <button
            className="md:hidden p-2 -ml-1 rounded-xl hover:bg-slate-100 text-slate-600 transition"
            onClick={() => setIsMobileMenuOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>

          {/* Breadcrumb on desktop */}
          <div className="hidden md:flex items-center text-sm text-slate-400 gap-2">
            <span className="text-slate-800 font-bold">{currentPageLabel}</span>
            <span className="text-slate-300">•</span>
            <span className={`text-xs font-semibold text-white px-2.5 py-0.5 rounded-full ${roleBadgeColor} flex items-center gap-1.5`}>
              <span className="w-1.5 h-1.5 rounded-full bg-white/70 animate-pulse"></span>
              {roleLabel}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Notifications */}
            <button className="p-2 rounded-xl hover:bg-slate-100 relative transition">
              <Bell size={18} className="text-slate-600" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-4 md:p-6">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}

