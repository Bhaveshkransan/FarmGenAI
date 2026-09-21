import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  Bell, LogOut, Sprout, Menu, X,
  LayoutDashboard, Handshake, BarChart3, User,
  Receipt, Cpu, Settings, Truck, Warehouse, Factory, Bot
} from 'lucide-react';

const agentDashboards = [
  { to: '/dashboard/farmer', label: 'Farmer Agent', icon: Sprout, role: 'farmer' },
  { to: '/dashboard/transport', label: 'Transport Logistics Hub', icon: Truck, role: 'transport' },
  { to: '/dashboard/buyer', label: 'Buyer Agent', icon: Handshake, role: 'buyer' },
  { to: '/dashboard/warehouse', label: 'Warehouse Agent', icon: Warehouse, role: 'warehouse' },
  { to: '/dashboard/processor', label: 'Processor Agent', icon: Factory, role: 'processor' },
  { to: '/dashboard/ai-ops', label: 'AI Operations Center', icon: Cpu, role: 'admin' },
];

const navItemsByRole = {
  farmer: [
    { to: '/dashboard/farmer', label: 'Farmer Overview', icon: LayoutDashboard },
    { to: '/farmer/negotiations', label: 'My Negotiations', icon: Handshake },
    { to: '/farmer/listings', label: 'My Listings', icon: BarChart3 },
    { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
    { to: '/transactions', label: 'Transactions', icon: Receipt },
    { to: '/analytics', label: 'Market Analytics', icon: BarChart3 },
  ],
  buyer: [
    { to: '/dashboard/buyer', label: 'Buyer Overview', icon: LayoutDashboard },
    { to: '/buyer/negotiations', label: 'My Deals', icon: Handshake },
    { to: '/buyer/matches', label: 'Find Suppliers', icon: BarChart3 },
    { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
    { to: '/transactions', label: 'Transactions', icon: Receipt },
    { to: '/analytics', label: 'Market Intel', icon: BarChart3 },
  ],
  admin: [
    { to: '/dashboard/farmer', label: 'Farmer Agent', icon: Sprout },
    { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
    { to: '/dashboard/admin', label: 'Admin Console', icon: Cpu },
    { to: '/dashboard/ai-ops', label: 'AI Operations', icon: Cpu },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/dashboard/settings', label: 'Settings', icon: Settings },
  ],
  warehouse: [
    { to: '/dashboard/warehouse', label: 'Warehouse Overview', icon: LayoutDashboard },
    { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  ],
  transport: [
    { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
    { to: '/dashboard/farmer', label: 'Farmer Consignments', icon: Sprout },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  ],
};

const defaultNav = [
  { to: '/dashboard/farmer', label: 'Farmer Dashboard', icon: Sprout },
  { to: '/dashboard/transport', label: 'Transport Logistics', icon: Truck },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/transactions', label: 'Transactions', icon: Receipt },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = navItemsByRole[user?.role] || defaultNav;

  const isActive = (path: string) => location.pathname === path ||
    (path !== '/dashboard' && location.pathname.startsWith(path));

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

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-300/60 px-3 py-1 mb-1">
            Agent Dashboards
          </div>
          {agentDashboards.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              onClick={() => setIsMobileMenuOpen(false)}
              className={`nav-link ${location.pathname === to ? 'nav-link-active' : ''}`}
            >
              <Icon size={18} className="flex-shrink-0" />
              <span>{label}</span>
            </Link>
          ))}

          {/* Core Menu */}
          <div className="pt-4 mt-3 border-t border-emerald-800/40">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-300/60 px-3 py-1 mb-1">
              Workspaces & Analytics
            </div>
            {navItems.filter(n => !agentDashboards.some(a => a.to === n.to)).map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`nav-link ${isActive(to) ? 'nav-link-active' : ''}`}
              >
                <Icon size={17} className="flex-shrink-0" />
                <span>{label}</span>
              </Link>
            ))}
          </div>
          
          {/* Profile Link */}
          <Link
            to="/profile"
            onClick={() => setIsMobileMenuOpen(false)}
            className={`nav-link mt-2 ${isActive('/profile') ? 'nav-link-active' : ''}`}
          >
            <User size={18} className="flex-shrink-0" />
            <span>My Profile</span>
          </Link>
        </nav>

        {/* User Footer */}
        <div className="p-3 border-t border-emerald-800/50 flex-shrink-0">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            <div className="w-9 h-9 rounded-xl bg-emerald-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
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
            <span className="text-slate-800 font-bold">
              {agentDashboards.find(a => location.pathname === a.to)?.label || navItems.find(n => isActive(n.to))?.label || 'Dashboard'}
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Autonomous Multi-Agent System
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Demo mode badge */}
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
              Demo Mode
            </span>
            
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
