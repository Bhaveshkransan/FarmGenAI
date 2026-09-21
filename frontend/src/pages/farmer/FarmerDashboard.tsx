import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/services/api';
import { Leaf, TrendingUp, AlertCircle, Clock, Plus, Search, Bot, ArrowRight, X, ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import StatCard from '@/components/ui/StatCard';
import CreateListingForm from '@/components/forms/CreateListingForm';

export default function FarmerDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Real-time WebSocket connection
  const token = localStorage.getItem('agri_token');
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/${token}`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedListing, setSelectedListing] = useState<any>(null);
  const [isMatchingOpen, setIsMatchingOpen] = useState(false);

  // Fetch active listings using React Query from the FastAPI backend
  const { data: listingsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['farmer_listings'],
    queryFn: async () => {
      try {
        const res = await api.get('/listings/me');
        const data = res.data;
        if (Array.isArray(data)) return data;
        if (Array.isArray(data?.data)) return data.data;
        if (Array.isArray(data?.listings)) return data.listings;
        if (Array.isArray(data?.items)) return data.items;
        return [];
      } catch (err) {
        console.error("Failed to fetch farmer listings:", err);
        return [];
      }
    }
  });

  const listings = Array.isArray(listingsData) ? listingsData : [];

  // Read deal history from localStorage
  const savedDeals = JSON.parse(localStorage.getItem('agri_deals') || '[]');
  const deals = savedDeals.length > 0 ? savedDeals : [
    {
      id: 'CN-8492',
      crop: 'Tomato',
      buyer: 'Metro Wholesale',
      quantity: 500,
      price: 20.5,
      total: 10250,
      status: 'ACCEPTED',
      date: 'Just Now'
    },
    {
      id: 'REJ-9102',
      crop: 'Onion',
      buyer: 'BigStore India',
      quantity: 300,
      price: 17.0,
      total: 5100,
      status: 'REJECTED',
      date: 'Yesterday'
    }
  ];

  const handleOpenMatches = (listing: any) => {
    setSelectedListing(listing);
    setIsMatchingOpen(true);
  };

  const handleStartNegotiation = (buyerName?: string, targetPrice?: number) => {
    setIsMatchingOpen(false);
    navigate('/negotiation/sim_direct');
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header Section */}
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Welcome back, {user?.name || 'Farmer'}!</h1>
          <p className="text-slate-500 mt-1">Here is your agricultural market overview & AI buyer matching center.</p>
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
        <StatCard icon={<TrendingUp />} title="Market Trend" value="Bullish" trend="Tomatoes +15%" color="blue" />
        <StatCard icon={<Clock />} title="Avg. Deal Time" value="2.4 hrs" trend="-15 mins" color="purple" />
      </div>

      {/* Main Grid: Listings & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Listings Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex justify-between items-center">
            <h2 className="font-bold text-lg text-slate-800">Your Active Listings</h2>
            <button 
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
                ) : listings.length === 0 ? (
                  <tr><td colSpan={5} className="p-8 text-center text-slate-400">No active listings found. Click "+ New Listing" to create one.</td></tr>
                ) : (
                  listings.map((listing: any) => (
                    <tr key={listing.id || listing.listing_id || Math.random()} className="hover:bg-slate-50/50 transition">
                      <td className="px-5 py-4 font-medium text-slate-800">{listing.crop}</td>
                      <td className="px-5 py-4 text-slate-600">{listing.quantity ?? listing.qty ?? 0} kg</td>
                      <td className="px-5 py-4 font-medium text-emerald-600">₹{listing.min_price ?? listing.price ?? 0}/kg</td>
                      <td className="px-5 py-4">
                        <span className="px-2.5 py-1 text-xs rounded-full font-medium bg-emerald-100 text-emerald-700">
                          {listing.status || 'ACTIVE'}
                        </span>
                      </td>
                      <td className="px-5 py-4 flex items-center gap-2">
                        <button 
                          onClick={() => handleOpenMatches(listing)}
                          className="text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg flex items-center gap-1 transition"
                        >
                          <Search size={13} /> Find Buyers
                        </button>
                        <button 
                          onClick={() => handleStartNegotiation()}
                          className="text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-lg flex items-center gap-1 transition"
                        >
                          <Bot size={13} /> AI Room
                        </button>
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
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl animate-fade-in">
                <p className="text-xs font-semibold text-blue-600 mb-1">Just Now</p>
                <p className="text-sm text-slate-700">{JSON.stringify(lastMessage)}</p>
              </div>
            )}
            
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 mb-1">10 mins ago</p>
              <p className="text-sm text-slate-700">Nashik Mandi: Tomato prices spiked to ₹23/kg due to local shortage.</p>
            </div>
            
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 mb-1">1 hr ago</p>
              <p className="text-sm text-slate-700">Your produce listing was indexed by the Workflow Planner.</p>
            </div>
          </div>
        </div>

      </div>

      {/* Negotiations & Deal Outcomes History Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h2 className="font-bold text-lg text-slate-800 flex items-center gap-2">
              <CheckCircle2 size={20} className="text-emerald-600" />
              AI Deal Outcomes & Negotiation History
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Real-time record of accepted, rejected, and active buyer negotiations</p>
          </div>
          <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-3 py-1 rounded-full">
            {deals.length} Total Deals
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Deal ID</th>
                <th className="px-5 py-3 font-medium">Crop</th>
                <th className="px-5 py-3 font-medium">Matched Buyer</th>
                <th className="px-5 py-3 font-medium">Agreed Price</th>
                <th className="px-5 py-3 font-medium">Total Payout</th>
                <th className="px-5 py-3 font-medium">Outcome Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {deals.map((deal: any, index: number) => (
                <tr key={index} className="hover:bg-slate-50/50 transition">
                  <td className="px-5 py-4 font-mono text-xs font-semibold text-slate-500">{deal.id}</td>
                  <td className="px-5 py-4 font-medium text-slate-800">{deal.crop} ({deal.quantity} kg)</td>
                  <td className="px-5 py-4 text-slate-700 font-medium">{deal.buyer}</td>
                  <td className="px-5 py-4 font-bold text-emerald-600">₹{deal.price}/kg</td>
                  <td className="px-5 py-4 font-bold text-slate-800">₹{deal.total?.toLocaleString() || (deal.price * deal.quantity).toLocaleString()}</td>
                  <td className="px-5 py-4">
                    {deal.status === 'ACCEPTED' ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-full font-bold bg-emerald-100 text-emerald-800">
                        <CheckCircle2 size={13} /> ACCEPTED
                      </span>
                    ) : deal.status === 'REJECTED' ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-full font-bold bg-red-100 text-red-700">
                        <XCircle size={13} /> REJECTED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-full font-bold bg-blue-100 text-blue-700">
                        NEGOTIATING
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Listing Modal */}
      <CreateListingForm 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        onSuccess={() => refetch()} 
      />

      {/* Matching Buyers Modal */}
      {isMatchingOpen && selectedListing && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            <div className="p-5 bg-slate-900 text-white flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg flex items-center gap-2">
                  <Bot className="text-emerald-400" size={20} /> AI Buyer Matching Engine
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">
                  Matching Buyers for <span className="font-bold text-emerald-400">{selectedListing.crop}</span> ({selectedListing.quantity || selectedListing.qty || 500} kg @ Min ₹{selectedListing.min_price || selectedListing.price || 18}/kg)
                </p>
              </div>
              <button onClick={() => setIsMatchingOpen(false)} className="text-slate-400 hover:text-white transition">
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto bg-slate-50">
              {/* Buyer Card 1 */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-emerald-500 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="inline-block px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full mb-1">Grade A Match (96%)</span>
                    <h4 className="font-bold text-slate-800 text-base">Metro Cash & Carry Wholesale</h4>
                    <p className="text-xs text-slate-500">Location: Nashik Central Mandi | Demand: 500 kg</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Offered Target Price</p>
                    <p className="font-extrabold text-emerald-600 text-lg">₹22.00 / kg</p>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <ShieldCheck size={14} className="text-emerald-500" /> Verified Buyer • Instant Escrow Payment
                  </span>
                  <button 
                    onClick={() => handleStartNegotiation('Metro Cash & Carry', 22.0)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg flex items-center gap-1 transition shadow-sm"
                  >
                    Start AI Negotiation <ArrowRight size={14} />
                  </button>
                </div>
              </div>

              {/* Buyer Card 2 */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-emerald-500 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full mb-1">Grade A Match (92%)</span>
                    <h4 className="font-bold text-slate-800 text-base">Reliance Fresh Retail Chain</h4>
                    <p className="text-xs text-slate-500">Location: Pune Hub | Demand: 1,000 kg</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Offered Target Price</p>
                    <p className="font-extrabold text-emerald-600 text-lg">₹20.50 / kg</p>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <ShieldCheck size={14} className="text-emerald-500" /> Verified Buyer • Transport Provided
                  </span>
                  <button 
                    onClick={() => handleStartNegotiation('Reliance Fresh', 20.5)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg flex items-center gap-1 transition shadow-sm"
                  >
                    Start AI Negotiation <ArrowRight size={14} />
                  </button>
                </div>
              </div>

              {/* Buyer Card 3 */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-emerald-500 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="inline-block px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-bold rounded-full mb-1">Grade B Match (88%)</span>
                    <h4 className="font-bold text-slate-800 text-base">GreenLeaf Restaurant Network</h4>
                    <p className="text-xs text-slate-500">Location: Nashik West | Demand: 200 kg</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Offered Target Price</p>
                    <p className="font-extrabold text-emerald-600 text-lg">₹24.00 / kg</p>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center">
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <ShieldCheck size={14} className="text-emerald-500" /> Premium Grade Procurement
                  </span>
                  <button 
                    onClick={() => handleStartNegotiation('GreenLeaf Restaurant', 24.0)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg flex items-center gap-1 transition shadow-sm"
                  >
                    Start AI Negotiation <ArrowRight size={14} />
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
