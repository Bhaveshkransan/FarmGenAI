import React, { useState, useEffect } from 'react';
import { Truck, Navigation, Route, Droplets, Cpu, Fuel, RefreshCw, CheckCircle, ShieldAlert, Sprout, Handshake, ExternalLink } from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import TransportAgentStudio from '@/features/transport/TransportAgentStudio';
import { api } from '@/services/api';
import { useNavigate } from 'react-router-dom';

export default function TransportDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'agent' | 'fleet' | 'farmer_consignments'>('agent');
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [trips, setTrips] = useState<any[]>([]);
  const [farmerDeals, setFarmerDeals] = useState<any[]>([]);
  const [fuelInfo, setFuelInfo] = useState<any>(null);
  const [loadingFleet, setLoadingFleet] = useState<boolean>(false);
  const [fleetError, setFleetError] = useState<string | null>(null);

  useEffect(() => {
    fetchFleetData();
  }, []);

  const fetchFleetData = async () => {
    setLoadingFleet(true);
    setFleetError(null);
    try {
      const [vehRes, paramRes, tripsRes, negRes] = await Promise.all([
        api.get('/transport/vehicles?status='),
        api.get('/transport/parameters'),
        api.get('/transport/trips?limit=15'),
        api.get('/negotiations/?limit=30')
      ]);

      if (vehRes.data && Array.isArray(vehRes.data.data)) {
        setVehicles(vehRes.data.data);
      }
      if (paramRes.data && paramRes.data.fuel_benchmark) {
        setFuelInfo(paramRes.data.fuel_benchmark);
      }
      if (tripsRes.data && Array.isArray(tripsRes.data.data)) {
        setTrips(tripsRes.data.data);
      }
      if (negRes.data && Array.isArray(negRes.data.data)) {
        setFarmerDeals(negRes.data.data);
      }
    } catch (err: any) {
      console.error('Failed to load fleet data:', err);
      setFleetError('Unable to load live fleet records from transport service.');
    } finally {
      setLoadingFleet(false);
    }
  };

  const totalCapacityKg = vehicles.reduce((acc, v) => acc + (v.capacity_kg || 0), 0);
  const availableCount = vehicles.filter(v => v.status === 'AVAILABLE').length;
  const avgEfficiency = vehicles.length > 0
    ? (vehicles.reduce((acc, v) => acc + (v.fuel_efficiency_kmpl || 0), 0) / vehicles.length).toFixed(1)
    : '14.5';

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header — Aligned with FarmerDashboard */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Truck className="text-emerald-600" /> Transport Logistics Hub
          </h1>
          <p className="text-slate-500 mt-1">
            Real registered vehicle fleet, OSRM road routing, deterministic financial engine, and autonomous freight agent.
          </p>
        </div>

        <div className="flex items-center gap-4 text-sm flex-wrap">
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-xl border border-slate-200">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-semibold text-slate-700">Autonomous Fleet Active</span>
          </div>
          <div className="text-right">
            <p className="text-slate-400 text-xs font-medium">Carrier Readiness</p>
            <p className="font-bold text-emerald-600 text-lg leading-tight">4.9 <span className="text-xs text-slate-400">/ 5.0</span></p>
          </div>

          {/* Tab Selector */}
          <div className="flex bg-slate-100 p-1.5 rounded-xl border border-slate-200">
            <button
              onClick={() => setActiveTab('agent')}
              className={`px-3.5 py-2 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'agent' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Cpu size={14} /> Studio
            </button>
            <button
              onClick={() => setActiveTab('fleet')}
              className={`px-3.5 py-2 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'fleet' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Truck size={14} /> Live Fleet ({vehicles.length})
            </button>
            <button
              onClick={() => setActiveTab('farmer_consignments')}
              className={`px-3.5 py-2 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'farmer_consignments' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sprout size={14} /> Farmer Consignments ({farmerDeals.filter(d => d.transport_plan || d.status === 'DEAL').length})
            </button>
          </div>
        </div>
      </div>

      {/* Tab 1: Transport Agent Studio */}
      {activeTab === 'agent' && (
        <TransportAgentStudio />
      )}

      {/* Tab 2: Fleet Overview */}
      {activeTab === 'fleet' && (
        <div className="space-y-6">
          {/* Dynamic Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard 
              icon={<Truck className="text-emerald-600" />} 
              title="Registered Fleet" 
              value={`${vehicles.length} Vehicles`} 
              trend={`${availableCount} Available Now`} 
              color="emerald" 
            />
            <StatCard 
              icon={<Navigation className="text-blue-600" />} 
              title="Total Fleet Capacity" 
              value={`${(totalCapacityKg / 1000).toFixed(1)} MT`} 
              trend="Across SCV, LCV & Refrigerator" 
              color="blue" 
            />
            <StatCard 
              icon={<Droplets className="text-purple-600" />} 
              title="Average Fuel Economy" 
              value={`${avgEfficiency} km/L`} 
              trend="Deterministic Engine Benchmarks" 
              color="purple" 
            />
            <StatCard 
              icon={<Fuel className="text-amber-600" />} 
              title="State Fuel Benchmark" 
              value={`₹${fuelInfo?.price_per_litre || 92.5}/L`} 
              trend={`${fuelInfo?.state || 'Maharashtra'} (${fuelInfo?.fuel_type || 'Diesel'})`} 
              color="amber" 
            />
          </div>

          {/* Real Vehicles Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center flex-wrap gap-4">
              <div>
                <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                  <Route size={18} className="text-emerald-600" /> Live Registered Vehicles & Telematics
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Direct database records loaded from PostgreSQL <code className="text-xs font-mono bg-slate-100 px-1 py-0.5 rounded">vehicles</code> table.
                </p>
              </div>
              <button
                onClick={fetchFleetData}
                disabled={loadingFleet}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <RefreshCw size={13} className={loadingFleet ? "animate-spin" : ""} /> Refresh Fleet
              </button>
            </div>

            {fleetError && (
              <div className="p-4 bg-red-50 text-red-700 border-b border-red-100 text-xs flex items-center gap-2">
                <ShieldAlert size={16} /> {fleetError}
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider border-b border-slate-100 text-[11px]">
                  <tr>
                    <th className="px-5 py-3">Vehicle Details</th>
                    <th className="px-5 py-3">Type</th>
                    <th className="px-5 py-3">Capacity</th>
                    <th className="px-5 py-3">Fuel & Efficiency</th>
                    <th className="px-5 py-3">Base Rate</th>
                    <th className="px-5 py-3">Home Hub</th>
                    <th className="px-5 py-3">Refrigeration</th>
                    <th className="px-5 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loadingFleet && vehicles.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                        <RefreshCw className="animate-spin inline mr-2" size={16} /> Loading vehicle fleet...
                      </td>
                    </tr>
                  ) : vehicles.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                        No vehicles currently registered in the transport fleet.
                      </td>
                    </tr>
                  ) : (
                    vehicles.map((v) => (
                      <tr key={v.vehicle_id} className="hover:bg-slate-50/60 transition">
                        <td className="px-5 py-3.5">
                          <div className="font-bold text-slate-800">{v.vehicle_name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">{v.vehicle_id} • {v.carrier_name || 'AgriLogistics'}</div>
                        </td>
                        <td className="px-5 py-3.5 font-medium text-slate-700">{v.vehicle_type}</td>
                        <td className="px-5 py-3.5 font-semibold text-slate-800">
                          {v.capacity_kg >= 1000 ? `${(v.capacity_kg / 1000).toFixed(1)} MT` : `${v.capacity_kg} kg`}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="font-medium text-slate-700">{v.fuel_type}</span>
                          <span className="text-slate-400 text-[10px] block">{v.fuel_efficiency_kmpl} km/L</span>
                        </td>
                        <td className="px-5 py-3.5 font-bold text-slate-800">₹{v.base_rate_per_km}/km</td>
                        <td className="px-5 py-3.5 text-slate-600">{v.current_location || 'Maharashtra Hub'}</td>
                        <td className="px-5 py-3.5">
                          {v.refrigerated ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                              <Droplets size={10} /> Reefer
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[10px]">Standard</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            v.status === 'AVAILABLE'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            <CheckCircle size={10} /> {v.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Autonomous Trips & Dispatches */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                <Navigation size={18} className="text-blue-600" /> Recent Autonomous Trips & Dispatches
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Logged trips and rate agreements executed by the Transport Agent LangGraph workflow.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider border-b border-slate-100 text-[11px]">
                  <tr>
                    <th className="px-5 py-3">Trip / Request</th>
                    <th className="px-5 py-3">Crop & Quantity</th>
                    <th className="px-5 py-3">Route (OSRM)</th>
                    <th className="px-5 py-3">Vehicle</th>
                    <th className="px-5 py-3">Operating Cost</th>
                    <th className="px-5 py-3">Agreed Freight</th>
                    <th className="px-5 py-3">Net Profit</th>
                    <th className="px-5 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {trips.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                        No transport trips recorded yet. Run a workflow in the Studio tab to generate one.
                      </td>
                    </tr>
                  ) : (
                    trips.map((t) => (
                      <tr key={t.trip_id} className="hover:bg-slate-50/60 transition">
                        <td className="px-5 py-3.5">
                          <div className="font-mono font-bold text-slate-800">{t.trip_id}</div>
                          <div className="text-[10px] text-slate-400 font-mono">{t.request_id}</div>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="font-semibold text-slate-800">{t.crop}</span>
                          <span className="text-slate-400 text-[10px] block">{t.quantity_kg?.toLocaleString()} kg</span>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="font-medium text-slate-700">{t.pickup_location} → {t.delivery_location}</span>
                          <span className="text-slate-400 text-[10px] block">{t.distance_km} km • {t.estimated_duration_hours} hrs</span>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="font-semibold text-slate-800">{t.vehicle_id}</span>
                          <span className="text-slate-400 text-[10px] block">{t.vehicle_type}</span>
                        </td>
                        <td className="px-5 py-3.5 font-medium text-slate-700">₹{t.total_operating_cost?.toLocaleString()}</td>
                        <td className="px-5 py-3.5 font-bold text-emerald-700">₹{t.agreed_price?.toLocaleString()}</td>
                        <td className="px-5 py-3.5 font-semibold text-emerald-600">
                          {t.expected_profit ? `+₹${t.expected_profit.toLocaleString()}` : '—'}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle size={10} /> {t.status || 'CONFIRMED'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* Tab 3: Farmer Produce Logistics & Consignments */}
      {activeTab === 'farmer_consignments' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCard 
              icon={<Sprout className="text-emerald-600" />} 
              title="Farmer Consignments" 
              value={`${farmerDeals.length} Total`} 
              trend="From Live AI Negotiations" 
              color="emerald" 
            />
            <StatCard 
              icon={<Truck className="text-blue-600" />} 
              title="Dispatched / Confirmed" 
              value={`${farmerDeals.filter(d => d.transport_plan || d.status === 'DEAL').length} Loads`} 
              trend="Autonomous Carrier Match" 
              color="blue" 
            />
            <StatCard 
              icon={<Fuel className="text-purple-600" />} 
              title="Freight Volume Moved" 
              value={`${(farmerDeals.reduce((acc, d) => acc + (d.quantity || 0), 0) / 1000).toFixed(1)} MT`} 
              trend="Across Maharashtra Mandis" 
              color="purple" 
            />
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-800 text-base flex items-center gap-2">
                  <Handshake size={18} className="text-emerald-600" /> Farmer Consignment & Dispatch Ledger
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Direct agricultural produce shipments originating from farmer negotiations and assigned to transport fleet.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider border-b border-slate-100 text-[11px]">
                  <tr>
                    <th className="px-5 py-3">Consignment ID</th>
                    <th className="px-5 py-3">Farmer & Crop</th>
                    <th className="px-5 py-3">Volume</th>
                    <th className="px-5 py-3">Buyer & Route</th>
                    <th className="px-5 py-3">Assigned Logistics</th>
                    <th className="px-5 py-3">Agreed Freight</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {farmerDeals.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                        No farmer consignments recorded yet. Start a negotiation in the Farmer Dashboard to trigger logistics coordination.
                      </td>
                    </tr>
                  ) : (
                    farmerDeals.map((deal) => {
                      const tp = typeof deal.transport_plan === 'string' && deal.transport_plan.startsWith('{')
                        ? JSON.parse(deal.transport_plan)
                        : deal.transport_plan;
                      const buyerName = (deal.deal && deal.deal.buyer_name) || (deal.selected_buyer && deal.selected_buyer.name) || 'APMC Buyer';
                      const isClosed = deal.status === 'DEAL';

                      return (
                        <tr key={deal.negotiation_id} className="hover:bg-slate-50/60 transition">
                          <td className="px-5 py-3.5">
                            <span className="font-mono font-bold text-slate-800">{deal.negotiation_id}</span>
                            <span className="text-[10px] text-slate-400 block">{deal.farmer_name || 'Farmer'}</span>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="font-bold text-slate-800">{deal.crop}</span>
                          </td>
                          <td className="px-5 py-3.5 font-medium text-slate-700">
                            {deal.quantity?.toLocaleString()} kg
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="font-semibold text-slate-800">{buyerName}</span>
                            <span className="text-[10px] text-slate-400 block">{deal.selected_buyer?.location || 'Maharashtra Hub'}</span>
                          </td>
                          <td className="px-5 py-3.5">
                            {tp ? (
                              <div>
                                <span className="font-semibold text-slate-800 flex items-center gap-1">
                                  <Truck size={12} className="text-emerald-600" />
                                  {tp.vehicle_name || tp.agent || 'Assigned Carrier'}
                                </span>
                                <span className="text-[10px] text-slate-400 block">
                                  {tp.distance ? `${tp.distance} km` : 'Local route'} • {tp.vehicle_type || 'Transport'}
                                </span>
                              </div>
                            ) : (
                              <span className="text-slate-400 italic text-[11px]">Pending Route Match</span>
                            )}
                          </td>
                          <td className="px-5 py-3.5 font-bold text-emerald-700">
                            {tp?.cost ? `₹${Number(tp.cost).toLocaleString()}` : tp?.agreed_price ? `₹${Number(tp.agreed_price).toLocaleString()}` : '—'}
                          </td>
                          <td className="px-5 py-3.5">
                            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                              isClosed
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-blue-50 text-blue-700 border border-blue-200'
                            }`}>
                              <CheckCircle size={10} /> {deal.status}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-right">
                            <button
                              onClick={() => navigate(`/negotiations/${deal.negotiation_id}`)}
                              className="inline-flex items-center gap-1 text-emerald-600 hover:text-emerald-700 font-bold hover:underline"
                            >
                              Room <ExternalLink size={12} />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
