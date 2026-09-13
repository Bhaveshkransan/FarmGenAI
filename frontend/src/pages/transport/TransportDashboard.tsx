import React from 'react';
import { Truck, Navigation, Route, Droplets } from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import ChartCard from '@/components/ui/ChartCard';
import DataTable from '@/components/ui/DataTable';

const routeData = [
  { name: 'Mon', value: 450 },
  { name: 'Tue', value: 520 },
  { name: 'Wed', value: 610 },
  { name: 'Thu', value: 580 },
  { name: 'Fri', value: 890 },
];

const mockDeliveries = [
  { id: '1', route: 'Nashik -> Mumbai', load: '10 MT Onions', eta: '4 hrs', status: 'In Transit' },
  { id: '2', route: 'Latur -> Pune', load: '5 MT Soybean', eta: 'Pending Dispatch', status: 'Scheduled' },
];

export default function TransportDashboard() {
  const tableColumns = [
    { header: 'Route', accessor: 'route', className: 'font-medium text-slate-800' },
    { header: 'Payload', accessor: 'load', className: 'text-slate-600' },
    { header: 'ETA', accessor: 'eta', className: 'text-slate-600' },
    { 
      header: 'Status', 
      accessor: 'status',
      render: (row) => (
        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
          row.status === 'In Transit' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
        }`}>
          {row.status}
        </span>
      )
    },
    { 
      header: 'Action', 
      accessor: 'actions',
      render: () => <button className="text-amber-600 font-medium hover:underline text-sm">Track Live</button>
    }
  ];

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
        <button className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition shadow-sm">
          Dispatch Vehicle
        </button>
      </div>
      
      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={<Navigation />} title="Active Deliveries" value="14" trend="3 arriving soon" color="blue" />
        <StatCard icon={<Truck />} title="Available Fleet" value="6" trend="Out of 20 total vehicles" color="emerald" />
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
  );
}
