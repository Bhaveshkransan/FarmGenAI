import React from 'react';
import { Factory, ArchiveRestore, CheckCircle, Package, TrendingUp, AlertCircle, Loader2, Clock } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import StatCard from '@/components/ui/StatCard';

export default function ProcessorDashboard() {
  const queryClient = useQueryClient();

  const { data: offers, isLoading, isError } = useQuery({
    queryKey: ['salvage-offers'],
    queryFn: async () => {
      const res = await api.get('/negotiations/?status=ESCALATED_PROCESSING');
      return Array.isArray(res.data) ? res.data : (res.data?.data || []);
    }
  });

  const acceptMutation = useMutation({
    mutationFn: async ({ id, price }: { id: string, price: number }) => {
      return api.post(`/negotiations/${id}/accept`, { final_price: price });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['salvage-offers'] });
    }
  });

  const handleAccept = (offer: any) => {
    if (window.confirm(`Accept this salvage offer for ${offer.quantity}kg of ${offer.crop}?`)) {
      acceptMutation.mutate({ id: offer.negotiation_id, price: offer.final_price || offer.market_price || 0 });
    }
  };

  const processedToday = 0; // We can fetch history if needed, for now placeholder
  const avgSalvagePrice = offers?.length > 0 ? (offers.reduce((acc: number, curr: any) => acc + (curr.final_price || curr.market_price || 0), 0) / offers.length).toFixed(2) : '0.00';

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Factory className="text-emerald-600" /> Processing Plant Portal
          </h1>
          <p className="text-slate-500 mt-1">Accept highly perishable crops at salvage market prices.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon={<ArchiveRestore />} title="Pending Offers" value={offers?.length || 0} trend="Requires immediate action" color="amber" />
        <StatCard icon={<Package />} title="Processed Today" value={`${processedToday} Tonnes`} trend="Volume received" color="emerald" />
        <StatCard icon={<TrendingUp />} title="Avg Salvage Rate" value={`₹${avgSalvagePrice}/kg`} trend="Market average" color="blue" />
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100">
          <h2 className="font-bold text-lg text-slate-800 flex items-center gap-2">
            <AlertCircle size={18} className="text-amber-500" /> Pending Salvage Offers (Expiring Soon)
          </h2>
        </div>
        
        {isLoading ? (
          <div className="p-12 text-center text-slate-400">
            <Loader2 className="animate-spin mx-auto text-emerald-500 mb-3" size={32} />
            <p>Loading salvage offers...</p>
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-red-400">
            <p>Failed to load salvage offers. Please try again.</p>
          </div>
        ) : !offers || offers.length === 0 ? (
          <div className="p-12 text-center bg-slate-50 border-t border-slate-100">
            <ArchiveRestore size={32} className="mx-auto text-slate-400 mb-3 opacity-50" />
            <p className="text-slate-500">No expiring crop escalations currently sent from AI Planner.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-100">
                <tr>
                  <th className="px-5 py-3 font-medium">Crop</th>
                  <th className="px-5 py-3 font-medium">Farmer</th>
                  <th className="px-5 py-3 font-medium">Volume</th>
                  <th className="px-5 py-3 font-medium">Salvage Price</th>
                  <th className="px-5 py-3 font-medium">Time to Spoilage</th>
                  <th className="px-5 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {offers.map((offer: any) => (
                  <tr key={offer.negotiation_id} className="hover:bg-amber-50/50 transition">
                    <td className="px-5 py-4 font-bold text-slate-800">{offer.crop}</td>
                    <td className="px-5 py-4 text-slate-600">{offer.farmer_name}</td>
                    <td className="px-5 py-4 font-medium">{offer.quantity} kg</td>
                    <td className="px-5 py-4 font-bold text-emerald-600">₹{offer.final_price || offer.market_price || 0}/kg</td>
                    <td className="px-5 py-4 text-red-600 font-medium flex items-center gap-1">
                      <Clock size={14} /> &lt; 24 Hours
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button 
                        onClick={() => handleAccept(offer)}
                        disabled={acceptMutation.isPending}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-bold transition flex items-center gap-2 ml-auto disabled:opacity-50"
                      >
                        {acceptMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                        Accept Offer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
