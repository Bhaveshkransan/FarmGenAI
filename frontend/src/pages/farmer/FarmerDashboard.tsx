import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/services/api';
import { Leaf, TrendingUp, AlertCircle, Clock, Plus, MapPin, Navigation, TrendingDown, Minus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import StatCard from '@/components/ui/StatCard';
import CreateListingForm from '@/components/forms/CreateListingForm';

interface MandiResult {
  mandi_name: string;
  distance_km: number;
  modal_price: number;
  transport_cost: number;
  net_realization: number;
  trend: 'Bullish' | 'Stable' | 'Bearish';
  lat: number;
  lon: number;
}

interface MarketData {
  mandis: MandiResult[];
  best_option: MandiResult;
  recommendation: string;
}

export default function FarmerDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const [isFormOpen, setIsFormOpen] = useState(false);

  // MandiMitra state
  const [mandiData, setMandiData] = useState<MarketData | null>(null);
  const [mandiLoading, setMandiLoading] = useState(false);
  const [mandiError, setMandiError] = useState<string | null>(null);
  const [selectedCrop, setSelectedCrop] = useState('Soybean');
  const [locationStatus, setLocationStatus] = useState<'idle' | 'locating' | 'found' | 'error'>('idle');

  const { data: listings, isLoading, isError, refetch } = useQuery({
    queryKey: ['farmer_listings'],
    queryFn: async () => {
      const res = await api.get('/listings/me');
      return res.data?.data || [];
    }
  });

  const fetchMandiComparison = (lat: number, lon: number, crop: string) => {
    setMandiLoading(true);
    setMandiError(null);
    api.get(`/market-intelligence/compare?crop=${crop}&lat=${lat}&lon=${lon}`)
      .then(res => {
        if (res.data?.success) setMandiData(res.data.data);
      })
      .catch(() => setMandiError('Failed to fetch Mandi data. Please try again.'))
      .finally(() => setMandiLoading(false));
  };

  const handleFindMandis = () => {
    setLocationStatus('locating');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocationStatus('found');
        fetchMandiComparison(pos.coords.latitude, pos.coords.longitude, selectedCrop);
      },
      () => {
        // Fallback to Nashik coords for demo
        setLocationStatus('found');
        fetchMandiComparison(19.99, 73.78, selectedCrop);
      }
    );
  };

  const TrendIcon = ({ trend }: { trend: string }) => {
    if (trend === 'Bullish') return <TrendingUp size={14} className="text-emerald-500" />;
    if (trend === 'Bearish') return <TrendingDown size={14} className="text-red-500" />;
    return <Minus size={14} className="text-slate-400" />;
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header Section */}
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Welcome back, {user?.name || 'Farmer'}!</h1>
          <p className="text-slate-500 mt-1">Here is your agricultural market overview.</p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-lg border">
            <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
            <span className="font-medium text-slate-600">{isConnected ? 'Live Market' : 'Offline'}</span>
          </div>
          <div className="text-right">
            <p className="text-slate-500">Trust Score</p>
            <p className="font-bold text-emerald-600 text-lg">4.8 <span className="text-sm text-slate-400">/ 5.0</span></p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon={<Leaf />} title="Active Listings" value={listings?.length || 0} trend="+1 this week" color="emerald" />
        <StatCard 
          icon={<TrendingUp />} 
          title="Market Trend" 
          value={mandiData ? mandiData.best_option?.trend || "Stable" : "Analyzing..."} 
          trend={mandiData ? `${selectedCrop} ${mandiData.best_option?.trend === 'Bullish' ? '+15%' : '-5%'}` : "Fetch Mandis"} 
          color="blue" 
        />
        <StatCard icon={<Clock />} title="Avg. Deal Time" value="2.4 hrs" trend="-15 mins" color="purple" />
      </div>

      {/* ── MandiMitra Section ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-wrap gap-3 justify-between items-center"
          style={{ background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)' }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow">
              <MapPin size={20} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-slate-800">MandiMitra — Mandi Comparison</h2>
              <p className="text-sm text-slate-500">Government mandis within 500km · Live prices · Net realization after transport</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedCrop}
              onChange={e => setSelectedCrop(e.target.value)}
              className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-emerald-400 outline-none"
            >
              {['Sugarcane', 'Soybean', 'Cotton', 'Jowar', 'Onion', 'Bajra', 'Rice'].map(c => (
                <option key={c}>{c}</option>
              ))}
            </select>
            <button
              id="find-mandis-btn"
              onClick={handleFindMandis}
              disabled={mandiLoading}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-4 py-2 rounded-xl text-sm font-semibold transition shadow-sm"
            >
              <Navigation size={15} className={mandiLoading ? 'animate-spin' : ''} />
              {mandiLoading ? 'Fetching...' : locationStatus === 'idle' ? 'Find My Mandis' : 'Refresh'}
            </button>
          </div>
        </div>

        {mandiError && (
          <div className="p-4 bg-red-50 border-b border-red-100 text-sm text-red-600 flex items-center gap-2">
            <AlertCircle size={16} /> {mandiError}
          </div>
        )}

        {mandiData && (
          <>
            {/* AI Recommendation Banner */}
            <div className={`px-6 py-4 border-b flex items-start gap-3 ${
              mandiData.recommendation.startsWith('SELL')
                ? 'bg-emerald-50 border-emerald-100'
                : 'bg-amber-50 border-amber-100'
            }`}>
              <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                mandiData.recommendation.startsWith('SELL') ? 'bg-emerald-500' : 'bg-amber-500'
              }`}>
                {mandiData.recommendation.startsWith('SELL')
                  ? <TrendingUp size={14} className="text-white" />
                  : <Clock size={14} className="text-white" />}
              </div>
              <div>
                <p className={`font-bold text-sm ${mandiData.recommendation.startsWith('SELL') ? 'text-emerald-800' : 'text-amber-800'}`}>
                  AI Recommendation
                </p>
                <p className={`text-sm mt-0.5 ${mandiData.recommendation.startsWith('SELL') ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {mandiData.recommendation}
                </p>
              </div>
            </div>

            {/* Mandi Comparison Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-100">
                  <tr>
                    <th className="px-5 py-3 font-medium">Mandi</th>
                    <th className="px-5 py-3 font-medium">Distance</th>
                    <th className="px-5 py-3 font-medium">Modal Price</th>
                    <th className="px-5 py-3 font-medium">Transport Cost</th>
                    <th className="px-5 py-3 font-medium">Net Realization</th>
                    <th className="px-5 py-3 font-medium">Trend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {mandiData.mandis.map((m, i) => {
                    const isBest = m.mandi_name === mandiData.best_option?.mandi_name;
                    return (
                      <tr key={i} className={`transition ${isBest ? 'bg-emerald-50/60' : 'hover:bg-slate-50/50'}`}>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2">
                            {isBest && <span className="text-xs bg-emerald-100 text-emerald-700 font-bold px-2 py-0.5 rounded-full">BEST</span>}
                            <span className="font-medium text-slate-800">{m.mandi_name}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-slate-600">{m.distance_km} km</td>
                        <td className="px-5 py-4 font-medium text-slate-800">₹{m.modal_price}/kg</td>
                        <td className="px-5 py-4 text-red-500">- ₹{m.transport_cost}/kg</td>
                        <td className={`px-5 py-4 font-bold ${m.net_realization > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                          ₹{m.net_realization}/kg
                        </td>
                        <td className="px-5 py-4">
                          <span className={`flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full w-fit ${
                            m.trend === 'Bullish' ? 'bg-emerald-100 text-emerald-700' :
                            m.trend === 'Bearish' ? 'bg-red-100 text-red-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            <TrendIcon trend={m.trend} />
                            {m.trend}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!mandiData && !mandiLoading && (
          <div className="p-10 text-center text-slate-400">
            <Navigation size={32} className="mx-auto mb-3 opacity-30" />
            <p className="font-medium">Click "Find My Mandis" to compare government mandis near you.</p>
            <p className="text-sm mt-1">We'll calculate exact transport costs and show you where to sell for maximum profit.</p>
          </div>
        )}
      </div>

      {/* Main Grid: Listings & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Listings Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex justify-between items-center">
            <h2 className="font-bold text-lg text-slate-800">Your Active Listings</h2>
            <button
              id="new-listing-btn"
              onClick={() => setIsFormOpen(true)}
              className="text-sm font-medium text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg flex items-center gap-2"
            >
              <Plus size={16} /> New Listing
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Crop</th>
                  <th className="px-5 py-3 font-medium">Volume</th>
                  <th className="px-5 py-3 font-medium">Base Price</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr><td colSpan={5} className="p-8 text-center text-slate-400">Loading listings from database...</td></tr>
                ) : isError ? (
                  <tr><td colSpan={5} className="p-8 text-center text-red-400">Failed to fetch listings. Backend may be offline.</td></tr>
                ) : !listings || listings.length === 0 ? (
                  <tr><td colSpan={5} className="p-8 text-center text-slate-400">No active listings found.</td></tr>
                ) : (
                  listings.map((listing: any) => (
                    <tr key={listing.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-5 py-4 font-medium text-slate-800">{listing.crop}</td>
                      <td className="px-5 py-4 text-slate-600">{listing.quantity || listing.qty} kg</td>
                      <td className="px-5 py-4 font-medium text-emerald-600">₹{listing.min_price || listing.price}/kg</td>
                      <td className="px-5 py-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
                          listing.status === 'NEGOTIATING' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {listing.status}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        {listing.status === 'NEGOTIATING' ? (
                          <button onClick={() => navigate(`/negotiations/${listing.id}`)} className="text-emerald-600 font-medium hover:underline">View Room</button>
                        ) : (
                          <button
                            onClick={async () => {
                              try {
                                const payload = {
                                  user_id: user?.id,
                                  farmer_name: user?.name || "Unknown Farmer",
                                  crop: listing.crop,
                                  quantity: listing.quantity || listing.qty || 100,
                                  min_price: listing.min_price || listing.price || 10,
                                  shelf_life: listing.shelf_life || 7,
                                  location: listing.location || 'Nashik',
                                  quality: listing.grade || 'A',
                                  language: 'English'
                                };
                                const res = await api.post('/negotiations/', payload);
                                if (res.data?.negotiation_id) {
                                  navigate(`/negotiations/${res.data.negotiation_id}`);
                                } else {
                                  alert('AI negotiation started but could not get a room ID. Please check your dashboard and try again.');
                                }
                              } catch (e) {
                                console.error(e);
                                alert('Failed to start AI negotiation');
                              }
                            }}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition shadow-sm"
                          >
                            AI Match & Negotiate
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Feed Sidebar */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5 flex flex-col h-[400px]">
          <h2 className="font-bold text-lg text-slate-800 mb-4 flex items-center gap-2">
            <AlertCircle size={18} className="text-emerald-500" />
            Live Market Updates
          </h2>
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {lastMessage && (
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                <p className="text-xs font-semibold text-blue-600 mb-1">Live Update</p>
                <p className="text-sm text-slate-700">{lastMessage.message || JSON.stringify(lastMessage)}</p>
              </div>
            )}
            {mandiData && mandiData.best_option && (
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                <p className="text-xs font-semibold text-emerald-600 mb-1">MandiMitra Feed</p>
                <p className="text-sm text-slate-700">
                  {mandiData.best_option.mandi_name}: {selectedCrop} Modal Price is ₹{mandiData.best_option.modal_price}/kg. 
                  Net realization estimated at ₹{mandiData.best_option.net_realization}/kg.
                </p>
              </div>
            )}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 mb-1">Recent Activity</p>
              <p className="text-sm text-slate-700">Your latest listing was indexed and matched against 12 active buyers in your region.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 mb-1">Market Insight</p>
              <p className="text-sm text-slate-700">Local processors are paying premium for Grade A {selectedCrop} this week.</p>
            </div>
          </div>
        </div>

      </div>

      <CreateListingForm
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onSuccess={() => refetch()}
      />
    </div>
  );
}
