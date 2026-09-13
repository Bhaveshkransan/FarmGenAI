import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ShoppingCart, Target, Wallet, Activity, Search, Loader2, TrendingUp, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useNavigate } from 'react-router-dom';
import ChartCard from '@/components/ui/ChartCard';

export default function BuyerDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch all produce listings
  const { data: listingsData, isLoading: listingsLoading } = useQuery({
    queryKey: ['produce-listings'],
    queryFn: async () => {
      const res = await api.get('/listings/');
      return res.data?.data || res.data || [];
    },
  });

  // Fetch active negotiations (history)
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['buyer-history', user?.id],
    queryFn: async () => {
      if (!user?.id) return [];
      const res = await api.get(`/history/history/${user.id}`);
      return res.data?.history || [];
    },
    enabled: !!user?.id,
  });

  const listings = (listingsData || []).filter(l =>
    !searchTerm ||
    (l.crop || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (l.farmer_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const history = historyData || [];
  const activeNegs = history.filter(h => !['DEAL', 'NO_DEAL'].includes(h.status || ''));
  const completedDeals = history.filter(h => h.status === 'DEAL');
  const totalSpend = completedDeals.reduce((acc, h) => acc + (h.final_price || 0) * (h.quantity || 0), 0);

  // Build chart from recent history
  const spendChartData = history.slice(-7).map((h, i) => ({
    name: `Deal ${i + 1}`,
    value: (h.final_price || 0) * (h.quantity || 0)
  }));

  const getStatusBadge = (status) => {
    const s = (status || '').toUpperCase();
    if (s === 'DEAL') return <span className="px-2.5 py-1 text-xs rounded-full font-medium bg-emerald-100 text-emerald-700">Closed</span>;
    if (s === 'NO_DEAL') return <span className="px-2.5 py-1 text-xs rounded-full font-medium bg-red-100 text-red-700">No Deal</span>;
    return <span className="px-2.5 py-1 text-xs rounded-full font-medium bg-amber-100 text-amber-700">Active</span>;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-100 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Procurement Command Center</h1>
          <p className="text-slate-500 mt-1">Welcome back, {user?.name || 'Buyer'}. Here's your live procurement overview.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="text" 
              placeholder="Search crops or farmers..." 
              className="pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-64 transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="p-2 bg-blue-100 rounded-xl"><Wallet className="text-blue-600" size={20} /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">₹{(totalSpend / 100000).toFixed(1)}L</p>
          <p className="text-sm font-medium text-slate-600">Total Spend</p>
          <p className="text-xs text-slate-400 mt-1">{completedDeals.length} closed deals</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="p-2 bg-emerald-100 rounded-xl"><ShoppingCart className="text-emerald-600" size={20} /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{listings.length}</p>
          <p className="text-sm font-medium text-slate-600">Available Listings</p>
          <p className="text-xs text-slate-400 mt-1">Live from APMC farmers</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="p-2 bg-amber-100 rounded-xl"><Activity className="text-amber-600" size={20} /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{activeNegs.length}</p>
          <p className="text-sm font-medium text-slate-600">Active Negotiations</p>
          <p className="text-xs text-slate-400 mt-1">In progress</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="p-2 bg-purple-100 rounded-xl"><Target className="text-purple-600" size={20} /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">
            {history.length > 0 ? `${Math.round((completedDeals.length / history.length) * 100)}%` : '—'}
          </p>
          <p className="text-sm font-medium text-slate-600">Deal Success Rate</p>
          <p className="text-xs text-slate-400 mt-1">{history.length} total negotiations</p>
        </div>
      </div>

      {/* Charts & Activity Grid */}
      {spendChartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ChartCard 
              title="Procurement Spend Trend" 
              subtitle="Deal value across recent negotiations"
              data={spendChartData} 
              color="#2563eb" 
              height={280}
            />
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <h2 className="font-bold text-lg text-slate-800 mb-1">AI Market Insights</h2>
            <p className="text-sm text-slate-500 mb-4">Based on your procurement history</p>
            <div className="space-y-3">
              {completedDeals.slice(0, 3).map((deal, i) => (
                <div key={i} className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
                  <p className="text-xs font-bold text-emerald-600 mb-1">CLOSED DEAL #{i+1}</p>
                  <p className="text-sm text-slate-800 font-medium">{deal.crop} — ₹{deal.final_price}/kg</p>
                  <p className="text-xs text-slate-500">{deal.quantity} kg</p>
                </div>
              ))}
              {completedDeals.length === 0 && (
                <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                  <p className="text-xs font-bold text-blue-600 mb-1">GETTING STARTED</p>
                  <p className="text-sm text-slate-800">Browse listings below and click "Negotiate" to start your first AI deal.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Available Produce Listings Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 text-lg flex items-center gap-2">
            <TrendingUp size={18} className="text-emerald-500" /> Available Farmer Listings
          </h2>
          {listingsLoading && <Loader2 size={18} className="text-slate-400 animate-spin" />}
        </div>
        {listingsLoading ? (
          <div className="p-12 text-center text-slate-400">
            <Loader2 size={32} className="animate-spin mx-auto mb-3" />
            Loading live listings...
          </div>
        ) : listings.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <ShoppingCart size={32} className="mx-auto mb-3 opacity-30" />
            <p>No listings match your search.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  {['Farmer', 'Crop', 'Quantity', 'Expected Price', 'Location', 'Status', 'Action'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {listings.map((listing) => (
                  <tr key={listing.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-4 text-sm font-medium text-slate-800">{listing.farmer_name || '—'}</td>
                    <td className="px-5 py-4 text-sm text-slate-600">{listing.crop}</td>
                    <td className="px-5 py-4 text-sm text-slate-600">{listing.quantity} kg</td>
                    <td className="px-5 py-4 text-sm font-bold text-blue-600">₹{listing.expected_price || listing.min_price}/kg</td>
                    <td className="px-5 py-4 text-sm text-slate-500">{listing.location || '—'}</td>
                    <td className="px-5 py-4">
                      <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
                        listing.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                      }`}>{listing.status}</span>
                    </td>
                    <td className="px-5 py-4">
                      <button
                        onClick={async () => {
                          try {
                            const res = await api.post('/negotiations/', {
                              user_id: user?.id,
                              buyer_name: user?.name || 'Buyer',
                              crop: listing.crop,
                              quantity: listing.quantity || 100,
                              min_price: listing.min_price || listing.expected_price || 10,
                              location: listing.location || 'Maharashtra',
                              quality: listing.grade || 'A',
                              language: 'English',
                              buyer_mode: true,
                              buyer_target_price: listing.expected_price || listing.min_price || 10,
                            });
                            if (res.data?.negotiation_id) navigate(`/negotiations/${res.data.negotiation_id}`);
                            else alert('Could not start negotiation. Please try again.');
                          } catch (e) {
                            alert('Failed to start negotiation.');
                          }
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition shadow-sm"
                      >
                        Negotiate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Negotiations History */}
      {history.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h2 className="font-bold text-slate-800 text-lg">Your Negotiation History</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  {['Crop', 'Quantity', 'Final Price', 'Total', 'Status', 'Action'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {history.slice(0, 10).map((h, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-5 py-4 text-sm font-medium text-slate-800">{h.crop || '—'}</td>
                    <td className="px-5 py-4 text-sm text-slate-600">{h.quantity ? `${h.quantity} kg` : '—'}</td>
                    <td className="px-5 py-4 text-sm font-bold text-blue-600">{h.final_price ? `₹${h.final_price}/kg` : '—'}</td>
                    <td className="px-5 py-4 text-sm font-bold text-emerald-600">
                      {h.final_price && h.quantity ? `₹${(h.final_price * h.quantity).toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="px-5 py-4">{getStatusBadge(h.status)}</td>
                    <td className="px-5 py-4">
                      {h.negotiation_id && (
                        <button onClick={() => navigate(`/negotiations/${h.negotiation_id}`)}
                          className="text-blue-600 font-medium hover:underline text-sm">View</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
