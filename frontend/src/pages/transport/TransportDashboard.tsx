import React, { useState } from 'react';
import { Truck, Navigation, Route, Droplets, Cpu } from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import ChartCard from '@/components/ui/ChartCard';
import DataTable from '@/components/ui/DataTable';
import TransportAgentStudio from '@/features/transport/TransportAgentStudio';

const routeData = [
  { name: 'Mon', value: 450 },
  { name: 'Tue', value: 520 },
  { name: 'Wed', value: 610 },
  { name: 'Thu', value: 580 },
  { name: 'Fri', value: 890 },
];

const mockDeliveries = [
  { id: '1', route: 'Nashik -> Mumbai', load: '10 MT Onions', eta: '4 hrs', status: 'In Transit' },
  { id: '2', route: 'Pune -> Surat', load: '5 MT Tomatoes', eta: 'Pending Dispatch', status: 'Scheduled' },
];

export default function TransportDashboard() {
  const [activeTab, setActiveTab] = useState<'fleet' | 'agent'>('agent');

  const tableColumns = [
    { header: 'Route', accessor: 'route', className: 'font-medium text-slate-800' },
    { header: 'Payload', accessor: 'load', className: 'text-slate-600' },
    { header: 'ETA', accessor: 'eta', className: 'text-slate-600' },
    { 
      header: 'Status', 
      accessor: 'status',
      render: (row: any) => (
        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
          row.status === 'In Transit' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
        }`}>
          {row.status}
        </span>
      )
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Truck className="text-amber-600" /> Transport Logistics Hub
          </h1>
          <p className="text-slate-500 mt-1">Manage fleet capacity, compute OSRM road routes, and run Transport Agent workflows.</p>
        </div>

        {/* Tab Selector */}
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setActiveTab('agent')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition flex items-center gap-2 ${
              activeTab === 'agent' ? 'bg-amber-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Cpu size={14} /> Transport Agent Studio
          </button>
          <button
            onClick={() => setActiveTab('fleet')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition flex items-center gap-2 ${
              activeTab === 'fleet' ? 'bg-amber-500 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Truck size={14} /> Fleet Overview
          </button>
        </div>
      </div>

      {/* Tab 1: Transport Agent Studio */}
      {activeTab === 'agent' && (
        <TransportAgentStudio />
      )}

      {/* Tab 2: Fleet Overview */}
      {activeTab === 'fleet' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard icon={<Navigation />} title="Active Deliveries" value="14" trend="3 arriving soon" color="blue" />
            <StatCard icon={<Truck />} title="Available Fleet" value="7" trend="Out of 20 total vehicles" color="emerald" />
            <StatCard icon={<Route />} title="Distance Covered" value="2,450 km" trend="This week" color="amber" />
            <StatCard icon={<Droplets />} title="Fuel Efficiency" value="14.2 km/l" trend="+0.4 km/l vs last week" color="purple" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 h-[350px]">
              <DataTable 
                title="Live Delivery Tracking" 
                columns={tableColumns} 
                data={mockDeliveries} 
              />
            </div>
            <div className="lg:col-span-1 h-[350px]">
              <ChartCard 
                title="Fleet Mileage Trend" 
                subtitle="Total km driven across fleet (Daily)"
                data={routeData} 
                color="#f59e0b" 
                height={260}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
