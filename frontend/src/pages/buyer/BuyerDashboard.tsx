import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ShoppingCart, Target, Wallet, Activity, Search } from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import ChartCard from '@/components/ui/ChartCard';
import DataTable from '@/components/ui/DataTable';

// Mock Data
const budgetData = [
  { name: 'Mon', value: 120000 },
  { name: 'Tue', value: 250000 },
  { name: 'Wed', value: 450000 },
  { name: 'Thu', value: 300000 },
  { name: 'Fri', value: 850000 },
  { name: 'Sat', value: 950000 },
  { name: 'Sun', value: 1100000 },
];

const mockOffers = [
  { id: '1', farmer: 'Ramesh Patil', crop: 'Onion', qty: '500 kg', price: '₹22/kg', status: 'Pending' },
  { id: '2', farmer: 'Suresh Kumar', crop: 'Soybean', qty: '1000 kg', price: '₹68/kg', status: 'Accepted' },
  { id: '3', farmer: 'Anand Rao', crop: 'Cotton', qty: '5 MT', price: '₹65/kg', status: 'Negotiating' },
];

export default function BuyerDashboard() {
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');

  const tableColumns = [
    { header: 'Farmer', accessor: 'farmer', className: 'font-medium text-slate-800' },
    { header: 'Crop', accessor: 'crop', className: 'text-slate-600' },
    { header: 'Volume', accessor: 'qty', className: 'text-slate-600' },
    { header: 'Price', accessor: 'price', className: 'font-bold text-blue-600' },
    { 
      header: 'Status', 
      accessor: 'status',
      render: (row) => (
        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
          row.status === 'Accepted' ? 'bg-emerald-100 text-emerald-700' : 
          row.status === 'Negotiating' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
        }`}>
          {row.status}
        </span>
      )
    },
    { 
      header: 'Actions', 
      accessor: 'actions',
      render: () => <button className="text-blue-600 font-medium hover:underline text-sm">View Details</button>
    }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-100 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Procurement Command Center</h1>
          <p className="text-slate-500 mt-1">Manage budgets, track active negotiations, and discover suppliers.</p>
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
          <button className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition shadow-sm whitespace-nowrap">
            Post Requirement
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={<Wallet />} title="Budget Utilized" value="₹11.5L" trend="45% of monthly limit" color="blue" />
        <StatCard icon={<ShoppingCart />} title="Active Requirements" value="8" trend="+2 this week" color="emerald" />
        <StatCard icon={<Activity />} title="Live Negotiations" value="3" trend="2 require action" color="amber" />
        <StatCard icon={<Target />} title="Fulfillment Rate" value="92%" trend="+4% vs last month" color="purple" />
      </div>

      {/* Charts & Activity Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Trend Chart (Spans 2 columns) */}
        <div className="lg:col-span-2 flex">
          <div className="w-full">
            <ChartCard 
              title="Procurement Spend Trend" 
              subtitle="Daily expenditure across all agricultural commodities"
              data={budgetData} 
              color="#2563eb" 
              height={350}
            />
          </div>
        </div>

        {/* AI Recommendations Sidebar */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 flex flex-col h-full">
          <h2 className="font-bold text-lg text-slate-800 mb-1">AI Market Insights</h2>
          <p className="text-sm text-slate-500 mb-6">Real-time procurement recommendations</p>
          
          <div className="space-y-4 flex-1">
            <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
              <p className="text-xs font-bold text-blue-600 mb-1">PRICE DROP DETECTED</p>
              <p className="text-sm text-slate-800 font-medium">Onion supply surging in Nashik.</p>
              <p className="text-xs text-slate-600 mt-2">Recommendation: Delay bulk purchases by 48 hrs for 5% savings.</p>
            </div>
            <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
              <p className="text-xs font-bold text-emerald-600 mb-1">NEW SUPPLIER MATCH</p>
              <p className="text-sm text-slate-800 font-medium">3 verified farmers near Pune have listed Tomatoes.</p>
              <button className="mt-3 text-xs font-bold text-emerald-700 bg-emerald-200/50 px-3 py-1.5 rounded-lg w-full hover:bg-emerald-200 transition">
                View Profiles
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* Main Data Table */}
      <div className="h-[400px]">
        <DataTable 
          title="Active Procurement Negotiations" 
          columns={tableColumns} 
          data={mockOffers} 
        />
      </div>

    </div>
  );
}
