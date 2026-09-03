import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/services/api';
import { Leaf, TrendingUp, AlertCircle, Clock, Plus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import StatCard from '@/components/ui/StatCard';
import CreateListingForm from '@/components/forms/CreateListingForm';

export default function FarmerDashboard() {
  const { user } = useAuth();
  
  // Real-time WebSocket connection
  const token = localStorage.getItem('agri_token');
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const [isFormOpen, setIsFormOpen] = useState(false);

  // Fetch active listings using React Query from the FastAPI backend
  const { data: listings, isLoading, isError, refetch } = useQuery({
    queryKey: ['farmer_listings'],
    queryFn: async () => {
      const res = await api.get('/listings/me');
      return res.data?.data || [];
    }
  });

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
                  <tr><td colSpan="5" className="p-8 text-center text-slate-400">Loading listings from database...</td></tr>
                ) : isError ? (
                  <tr><td colSpan="5" className="p-8 text-center text-red-400">Failed to fetch listings. Backend may be offline.</td></tr>
                ) : !listings || listings.length === 0 ? (
                  <tr><td colSpan="5" className="p-8 text-center text-slate-400">No active listings found.</td></tr>
                ) : (
                  listings.map(listing => (
                    <tr key={listing.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-5 py-4 font-medium text-slate-800">{listing.crop}</td>
                      <td className="px-5 py-4 text-slate-600">{listing.qty} kg</td>
                      <td className="px-5 py-4 font-medium text-emerald-600">₹{listing.price}/kg</td>
                      <td className="px-5 py-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
                          listing.status === 'NEGOTIATING' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {listing.status}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        {listing.status === 'NEGOTIATING' ? (
                          <button className="text-emerald-600 font-medium hover:underline">View Room</button>
                        ) : (
                          <span className="text-slate-400">Waiting</span>
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
            {/* Live Message Display */}
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
              <p className="text-sm text-slate-700">Your Onion listing (200kg) was indexed by the Workflow Planner.</p>
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
