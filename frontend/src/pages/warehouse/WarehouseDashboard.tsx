import React from 'react';
import { Warehouse, PackageSearch, Activity, MapPin, Loader2, AlertCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import ChartCard from '@/components/ui/ChartCard';

export default function WarehouseDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['warehouses'],
    queryFn: async () => {
      const res = await api.get('/warehouse/list');
      return res.data || {};
    },
  });

  const warehouses = data?.warehouses || [];
  const summary = data?.summary || {};

  const totalMT = (summary.total_capacity_kg || 0) / 1000;
  const usedMT = (summary.used_capacity_kg || 0) / 1000;
  const availMT = (summary.available_capacity_kg || 0) / 1000;
  const occupancyPct = totalMT > 0 ? Math.round((usedMT / totalMT) * 100) : 0;

  const chartData = warehouses.slice(0, 6).map(w => ({
    name: (w.name || '').split(' ')[0],
    value: Math.round(((w.capacity_mt || 0) - (w.available_capacity_mt || 0)) / (w.capacity_mt || 1) * 100)
  }));

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Warehouse className="text-purple-600" /> Cold Storage Management
          </h1>
          <p className="text-slate-500 mt-1">Monitor capacity, manage reservations, and track inventory health.</p>
        </div>
      </div>
      
      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <Loader2 className="animate-spin mx-auto text-purple-500 mb-3" size={32} />
          <p className="text-slate-500">Loading warehouse data...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <AlertCircle className="mx-auto text-red-400 mb-3" size={32} />
          <p className="text-slate-500">Failed to load warehouse data.</p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* KPI Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-purple-100 rounded-xl w-fit mb-3"><PackageSearch className="text-purple-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">{occupancyPct}%</p>
              <p className="text-sm font-medium text-slate-600">Occupancy Rate</p>
              <p className="text-xs text-slate-400 mt-1">{usedMT.toFixed(1)} MT used of {totalMT.toFixed(1)} MT</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-emerald-100 rounded-xl w-fit mb-3"><Activity className="text-emerald-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">{warehouses.length}</p>
              <p className="text-sm font-medium text-slate-600">Total Facilities</p>
              <p className="text-xs text-slate-400 mt-1">Across Maharashtra</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-blue-100 rounded-xl w-fit mb-3"><MapPin className="text-blue-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">{availMT.toFixed(1)} MT</p>
              <p className="text-sm font-medium text-slate-600">Available Space</p>
              <p className="text-xs text-slate-400 mt-1">Ready for booking</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <div className="p-2 bg-amber-100 rounded-xl w-fit mb-3"><Warehouse className="text-amber-600" size={20} /></div>
              <p className="text-2xl font-bold text-slate-800">
                {warehouses.length > 0 ? (warehouses.reduce((acc, w) => acc + (w.rating || 0), 0) / warehouses.length).toFixed(1) : '—'}★
              </p>
              <p className="text-sm font-medium text-slate-600">Avg Rating</p>
              <p className="text-xs text-slate-400 mt-1">Out of 5.0</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {chartData.length > 0 && (
              <div className="lg:col-span-1">
                <ChartCard 
                  title="Occupancy by Facility" 
                  subtitle="% filled per warehouse"
                  data={chartData} 
                  color="#9333ea" 
                  height={260}
                />
              </div>
            )}
            <div className={`${chartData.length > 0 ? 'lg:col-span-2' : 'lg:col-span-3'} bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden`}>
              <div className="p-5 border-b border-slate-100">
                <h2 className="font-bold text-slate-800">All Warehouse Facilities</h2>
              </div>
              {warehouses.length === 0 ? (
                <div className="p-12 text-center text-slate-400">
                  <Warehouse size={32} className="mx-auto mb-3 opacity-30" />
                  <p>No warehouses found in database.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100">
                    <thead className="bg-slate-50">
                      <tr>
                        {['Name', 'District', 'Type', 'Capacity (MT)', 'Available (MT)', 'Rate/MT/day', 'Rating'].map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {warehouses.map((w) => (
                        <tr key={w.warehouse_id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3 text-sm font-medium text-slate-800">{w.name}</td>
                          <td className="px-4 py-3 text-sm text-slate-600">{w.district}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">{w.type}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-600">{w.capacity_mt}</td>
                          <td className="px-4 py-3 text-sm font-bold text-emerald-600">{w.available_capacity_mt}</td>
                          <td className="px-4 py-3 text-sm text-slate-600">₹{w.price_per_mt_per_day}</td>
                          <td className="px-4 py-3 text-sm font-bold text-amber-600">{w.rating}★</td>
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
