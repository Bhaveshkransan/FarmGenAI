import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { TrendingUp, Users, PackageCheck, AlertTriangle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';

const successRateData = [
  { name: 'Completed', value: 94 },
  { name: 'Failed', value: 6 }
];

const demandSupplyData = [
  { name: 'Soybean', supply: 12000, demand: 15000 },
  { name: 'Cotton', supply: 8000, demand: 8200 },
  { name: 'Onion', supply: 3000, demand: 3200 },
  { name: 'Sugarcane', supply: 25000, demand: 24000 },
];

const COLORS = ['#10b981', '#f43f5e'];

export default function GlobalAnalytics() {
  const [priceTrendData, setPriceTrendData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRealAnalytics = async () => {
      setIsLoading(true);
      try {
        // Fetch insights for our top 3 crops in parallel
        const [soybeanRes, cottonRes, onionRes] = await Promise.all([
          api.get('/market-intelligence/insights?crop=Soybean&location=Maharashtra'),
          api.get('/market-intelligence/insights?crop=Cotton&location=Maharashtra'),
          api.get('/market-intelligence/insights?crop=Onion&location=Maharashtra')
        ]);

        const soybeanData = soybeanRes.data?.data?.chart_data || [];
        const cottonData = cottonRes.data?.data?.chart_data || [];
        const onionData = onionRes.data?.data?.chart_data || [];

        // Zip them together by date for the Recharts graph
        const mergedData = [];
        if (soybeanData.length > 0) {
          for (let i = 0; i < soybeanData.length; i++) {
            mergedData.push({
              date: soybeanData[i].date,
              soybean: soybeanData[i].price,
              cotton: cottonData[i]?.price || 0,
              onion: onionData[i]?.price || 0,
              type: soybeanData[i].type // Historical, Live, or Forecast
            });
          }
        }
        setPriceTrendData(mergedData);
      } catch (err) {
        console.error("Failed to fetch real market analytics", err);
        setError("Unable to load real-time ML market data from backend.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchRealAnalytics();
  }, []);

  return (
    <div className="space-y-6 animate-slide-up">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Live Market Analytics</h1>
          <p className="text-slate-500">Real-time XGBoost forecasts and APMC Mandi data</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between card-hover">
          <div>
            <p className="text-sm font-medium text-slate-500">Model Accuracy</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">92.4%</p>
          </div>
          <div className="bg-emerald-50 p-3 rounded-lg text-emerald-600">
            <TrendingUp size={24} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">APMC Mandis Tracked</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">1,024</p>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg text-blue-600">
            <Users size={24} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Historical Records</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">20,440</p>
          </div>
          <div className="bg-indigo-50 p-3 rounded-lg text-indigo-600">
            <PackageCheck size={24} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Model Refresh Rate</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">Live</p>
          </div>
          <div className="bg-amber-50 p-3 rounded-lg text-amber-600">
            <AlertTriangle size={24} />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="h-64 flex flex-col items-center justify-center border rounded-xl bg-slate-50">
           <Loader2 className="animate-spin text-emerald-500 mb-2" size={32} />
           <p className="text-slate-500 font-medium">Running distributed ML inference across crops...</p>
        </div>
      ) : error ? (
        <div className="h-64 flex items-center justify-center border border-red-200 rounded-xl bg-red-50 text-red-600 font-medium">
          {error}
        </div>
      ) : (
        /* Charts Grid */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Price Trends */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-2">
            <h3 className="text-lg font-bold text-slate-900 mb-1">14-Day Price Trends & Forecast (₹/kg)</h3>
            <p className="text-xs text-slate-500 mb-6">Historical data merges into ML forecast after "Today"</p>
            <div className="h-96 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={priceTrendData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend />
                  <Line type="monotone" name="Soybean" dataKey="soybean" stroke="#10b981" strokeWidth={3} dot={false} activeDot={{ r: 8 }} />
                  <Line type="monotone" name="Cotton" dataKey="cotton" stroke="#3b82f6" strokeWidth={3} dot={false} />
                  <Line type="monotone" name="Onion" dataKey="onion" stroke="#f43f5e" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Supply vs Demand */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-lg font-bold text-slate-900 mb-6">Supply vs Demand Gap (Tons)</h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={demandSupplyData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    cursor={{ fill: '#f8fafc' }}
                  />
                  <Legend />
                  <Bar dataKey="supply" name="Supply (Arrivals)" fill="#10b981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="demand" name="Demand (Processor Req)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Success Rate */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center">
            <h3 className="text-lg font-bold text-slate-900 mb-6 self-start">AI Negotiation Success</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={successRateData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {successRateData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
