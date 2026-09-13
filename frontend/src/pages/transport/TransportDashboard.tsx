import React from 'react';
import { Truck, Navigation, Route, Droplets, Loader2, AlertCircle, Package } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import ChartCard from '@/components/ui/ChartCard';

export default function TransportDashboard() {
  // Fetch fleet from backend
  const { data: fleetData, isLoading, isError } = useQuery({
    queryKey: ['transport-fleet'],
    queryFn: async () => {
      const res = await api.get('/transport/fleet');
      return res.data?.fleet || res.data?.data || [];
    },
  });

  const fleet = fleetData || [];
  const available = fleet.filter(v => v.current_location);
  const totalVehicles = fleet.length;
  
  // Chart: rate per km distribution
  const chartData = fleet.slice(0, 7).map(v => ({
    name: (v.vehicle_type || 'Truck').substring(0, 8),
    value: v.rate_per_km || 0
  }));

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Truck className="text-amber-600" /> Logistics Fleet Manager
          </h1>
          <p className="text-slate-500 mt-1">Track active deliveries, manage fleet capacity, and optimize routes.</p>
        </div>
      </div>
      
      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <Loader2 className="animate-spin mx-auto text-amber-500 mb-3" size={32} />
          <p className="text-slate-500">Loading fleet data...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <AlertCircle className="mx-auto text-red-400 mb-3" size={32} />
          <p className="text-slate-500">Failed to load fleet data.</p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* KPI Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-amber-100 rounded-xl w-fit mb-3"><Truck className="text-amber-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">{totalVehicles}</p>
              <p className="text-sm font-medium text-slate-600">Total Fleet</p>
              <p className="text-xs text-slate-400 mt-1">All vehicle types</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-emerald-100 rounded-xl w-fit mb-3"><Navigation className="text-emerald-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">{available.length}</p>
              <p className="text-sm font-medium text-slate-600">Available Now</p>
              <p className="text-xs text-slate-400 mt-1">Ready to dispatch</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-blue-100 rounded-xl w-fit mb-3"><Package className="text-blue-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">
                {fleet.length > 0 ? `${fleet.reduce((a, v) => a + (v.capacity_mt || 0), 0).toFixed(0)} MT` : '—'}
              </p>
              <p className="text-sm font-medium text-slate-600">Total Capacity</p>
              <p className="text-xs text-slate-400 mt-1">Combined fleet capacity</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-purple-100 rounded-xl w-fit mb-3"><Route className="text-purple-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">
                {fleet.length > 0 ? `₹${(fleet.reduce((a, v) => a + (v.rate_per_km || 0), 0) / fleet.length).toFixed(1)}/km` : '—'}
              </p>
              <p className="text-sm font-medium text-slate-600">Avg Rate/km</p>
              <p className="text-xs text-slate-400 mt-1">Fleet average</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {chartData.length > 0 && (
              <div className="lg:col-span-1">
                <ChartCard 
                  title="Rate per km by Vehicle Type" 
                  subtitle="₹ per kilometre"
                  data={chartData} 
                  color="#f59e0b" 
                  height={260}
                />
              </div>
            )}
            <div className={`${chartData.length > 0 ? 'lg:col-span-2' : 'lg:col-span-3'} bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden`}>
              <div className="p-5 border-b border-slate-100">
                <h2 className="font-bold text-slate-800">Fleet Inventory</h2>
              </div>
              {fleet.length === 0 ? (
                <div className="p-12 text-center text-slate-400">
                  <Truck size={32} className="mx-auto mb-3 opacity-30" />
                  <p>No vehicles found in database.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100">
                    <thead className="bg-slate-50">
                      <tr>
                        {['Provider', 'Vehicle Type', 'Capacity (MT)', 'Rate/km', 'Base Fare', 'Location', 'Rating'].map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {fleet.map((v, i) => (
                        <tr key={v.transporter_id || i} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3 text-sm font-medium text-slate-800">{v.provider_name || '—'}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs rounded-full font-medium">{v.vehicle_type}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{v.capacity_mt}</td>
                          <td className="px-4 py-3 text-sm font-bold text-amber-600">₹{v.rate_per_km}/km</td>
                          <td className="px-4 py-3 text-sm text-slate-600">₹{v.base_fare}</td>
                          <td className="px-4 py-3 text-sm text-slate-500">{v.current_location || '—'}</td>
                          <td className="px-4 py-3 text-sm font-bold text-blue-600">{v.rating}★</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
