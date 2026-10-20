import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Sprout, ArrowLeft, Bot, Zap, ShieldCheck, Truck, Warehouse, Factory } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  type DemoRole = 'buyer' | 'farmer' | 'transport' | 'warehouse' | 'processor' | 'admin';

  const handleSuccessfulAuth = (user: any) => {
    const role = user?.role?.toLowerCase();
    if (role === 'buyer') {
      navigate('/dashboard/buyer');
    } else if (role === 'farmer') {
      navigate('/dashboard/farmer');
    } else if (role === 'transport' || role === 'transporter') {
      navigate('/dashboard/transport');
    } else if (role === 'warehouse') {
      navigate('/dashboard/warehouse');
    } else if (role === 'processor') {
      navigate('/dashboard/processor');
    } else if (role === 'admin') {
      navigate('/dashboard/admin');
    } else {
      navigate('/dashboard');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    const res = await login({ email, password });
    if (res.success) {
      handleSuccessfulAuth(res.user);
    } else {
      setError(res.error || 'Invalid email or password');
      setIsLoading(false);
    }
  };

  const handleDemoSignIn = async (role: DemoRole) => {
    setError('');
    setIsLoading(true);
    const demoEmail = `${role}@agrinegotiator.com`;
    const demoPassword = 'password123';
    setEmail(demoEmail);
    setPassword(demoPassword);

    const res = await login({ email: demoEmail, password: demoPassword });
    if (res.success) {
      handleSuccessfulAuth(res.user);
    } else {
      setError(res.error || `Failed to sign in as ${role}`);
      setIsLoading(false);
    }
  };

  // 1-Click direct URL access: /login?demo=farmer, buyer, transport, warehouse, processor, admin
  useEffect(() => {
    const demo = searchParams.get('demo') as DemoRole | null;
    const validRoles: DemoRole[] = ['buyer', 'farmer', 'transport', 'warehouse', 'processor', 'admin'];
    if (demo && validRoles.includes(demo)) {
      handleDemoSignIn(demo);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-10 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center text-emerald-600 mb-3">
          <Sprout size={44} />
        </div>
        <h2 className="text-center text-3xl font-extrabold text-slate-900 tracking-tight">
          Sign in to AgriNegotiator
        </h2>
        <p className="mt-1 text-center text-sm text-slate-500">
          Autonomous Multi-Agent Agricultural Procurement & Logistics
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-5 shadow-sm sm:rounded-2xl sm:px-10 border border-slate-200">
          <div className="mb-5 flex items-center justify-between">
            <Link to="/" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              <ArrowLeft size={16} className="mr-1" /> Back to Home
            </Link>
            <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full font-medium border border-emerald-200/60 flex items-center gap-1">
              <ShieldCheck size={12} /> SSL Secured
            </span>
          </div>

          {/* ── 1-Click Demo Accounts ────────────────────────── */}
          <div className="mb-6 bg-gradient-to-br from-slate-50 to-emerald-50/30 p-4 rounded-xl border border-emerald-100/80">
            <div className="flex items-center gap-2 mb-2.5">
              <Zap size={15} className="text-amber-500" />
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Instant 1-Click Demo Sign-In
              </span>
            </div>
            
            <div className="space-y-2">
              <button
                type="button"
                id="demo-buyer-signin-btn"
                onClick={() => handleDemoSignIn('buyer')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-all shadow-sm active:scale-[0.99] disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <Bot size={16} className="text-blue-200" />
                  <span>Buyer Agent (AgroCorp Procurement)</span>
                </div>
                <span className="text-[11px] bg-white/20 px-2 py-0.5 rounded font-mono">1-Click</span>
              </button>

              <button
                type="button"
                id="demo-farmer-signin-btn"
                onClick={() => handleDemoSignIn('farmer')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 rounded-lg text-sm font-semibold border border-emerald-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <span>🌾</span>
                  <span>Farmer Agent (Ramesh Patil)</span>
                </div>
                <span className="text-[11px] bg-emerald-200/70 text-emerald-900 px-2 py-0.5 rounded font-mono">1-Click</span>
              </button>

              <button
                type="button"
                id="demo-transport-signin-btn"
                onClick={() => handleDemoSignIn('transport')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-2 bg-amber-50 hover:bg-amber-100 text-amber-900 rounded-lg text-sm font-semibold border border-amber-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <Truck size={16} className="text-amber-600" />
                  <span>Transporter (MahaLogistics Fleet)</span>
                </div>
                <span className="text-[11px] bg-amber-200/70 text-amber-950 px-2 py-0.5 rounded font-mono">1-Click</span>
              </button>

              <button
                type="button"
                id="demo-warehouse-signin-btn"
                onClick={() => handleDemoSignIn('warehouse')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-2 bg-purple-50 hover:bg-purple-100 text-purple-900 rounded-lg text-sm font-semibold border border-purple-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <Warehouse size={16} className="text-purple-600" />
                  <span>Warehouse Hub (MahaWarehouse Storage)</span>
                </div>
                <span className="text-[11px] bg-purple-200/70 text-purple-950 px-2 py-0.5 rounded font-mono">1-Click</span>
              </button>

              <button
                type="button"
                id="demo-processor-signin-btn"
                onClick={() => handleDemoSignIn('processor')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-2 bg-teal-50 hover:bg-teal-100 text-teal-900 rounded-lg text-sm font-semibold border border-teal-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <Factory size={16} className="text-teal-600" />
                  <span>Processor (Sahyadri Agro Milling)</span>
                </div>
                <span className="text-[11px] bg-teal-200/70 text-teal-950 px-2 py-0.5 rounded font-mono">1-Click</span>
              </button>

              <button
                type="button"
                id="demo-admin-signin-btn"
                onClick={() => handleDemoSignIn('admin')}
                disabled={isLoading}
                className="w-full flex items-center justify-between px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold border border-slate-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <span>⚙️</span>
                  <span>Platform Operations Admin</span>
                </div>
                <span className="text-[10px] bg-slate-300 text-slate-800 px-1.5 py-0.5 rounded font-mono">1-Click</span>
              </button>
            </div>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-slate-400 font-semibold tracking-wider">
                Or Sign In With Email
              </span>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 text-red-700 p-3 rounded-xl text-sm font-medium border border-red-100">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-700">Email Address</label>
              <div className="mt-1">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm"
                  placeholder="e.g. buyer@agrinegotiator.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Password</label>
              <div className="mt-1">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition-colors"
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center">
            <span className="text-sm text-slate-500">
              Don't have an account?{' '}
              <Link to="/register" className="font-medium text-emerald-600 hover:text-emerald-500">
                Register here
              </Link>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
