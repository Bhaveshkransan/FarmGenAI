import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Truck, Navigation, ShieldCheck, DollarSign, Calculator, MessageSquare, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw, Users, Award, MapPin, Zap, ThermometerSnowflake, Package, XCircle } from 'lucide-react';
import { api } from '@/services/api';

const VEHICLES = [
  { id: 'v1', name: 'Tata Ace (Mini Truck)', type: 'Mini Truck', capacity: '750 kg', img: '/images/vehicles/mini_truck_1790357821042.jpg', rate: '₹18/km', tags: ['Fast', 'Urban'] },
  { id: 'v2', name: 'Piaggio Ape (Cargo 3W)', type: 'Cargo Three-Wheeler', capacity: '500 kg', img: '/images/vehicles/cargo_three_wheeler_1790357833972.jpg', rate: '₹12/km', tags: ['Last Mile', 'Economic'] },
  { id: 'v3', name: 'Ashok Leyland Dost (LCV)', type: 'LCV', capacity: '1250 kg', img: '/images/vehicles/lcv_truck_1790357848327.jpg', rate: '₹22/km', tags: ['Reliable', 'Intercity'] },
  { id: 'v4', name: 'Tata 1109 (Medium Truck)', type: 'Medium Truck', capacity: '6000 kg', img: '/images/vehicles/medium_truck_1790357862630.jpg', rate: '₹35/km', tags: ['Highway', 'Heavy Load'] },
  { id: 'v5', name: 'Tata Signa (Heavy Truck)', type: 'Heavy Truck', capacity: '15000 kg', img: '/images/vehicles/heavy_truck_1790357881610.jpg', rate: '₹55/km', tags: ['Multi-axle', 'Long Haul'] },
  { id: 'v6', name: 'BharatBenz Reefer', type: 'Refrigerated Truck', capacity: '9000 kg', img: '/images/vehicles/refrigerated_truck_1790357894668.jpg', rate: '₹65/km', tags: ['Cold Chain', 'Premium'] },
  { id: 'v7', name: 'Mahindra Tractor + Trailer', type: 'Tractor + Trailer', capacity: '3000 kg', img: '/images/vehicles/tractor_trailer_1790357918266.jpg', rate: '₹25/km', tags: ['Rural', 'Agri'] }
];

const MOCK_REQUIREMENTS = [
  { crop: 'Sugarcane', qty: 15000, origin: 'Kolhapur', dest: 'Pune', shelf: 72, deadline: 24, reefer: false },
  { crop: 'Soybean', qty: 9000, origin: 'Latur', dest: 'Solapur', shelf: 8760, deadline: 48, reefer: false },
  { crop: 'Cotton', qty: 5000, origin: 'Amravati', dest: 'Nagpur', shelf: 8760, deadline: 72, reefer: false },
  { crop: 'Onion', qty: 8000, origin: 'Nashik', dest: 'Mumbai', shelf: 720, deadline: 24, reefer: false },
  { crop: 'Jowar', qty: 4000, origin: 'Ahmednagar', dest: 'Pune', shelf: 8760, deadline: 48, reefer: false },
  { crop: 'Bajra', qty: 3500, origin: 'Beed', dest: 'Aurangabad', shelf: 8760, deadline: 48, reefer: false },
  { crop: 'Rice', qty: 12000, origin: 'Bhandara', dest: 'Nagpur', shelf: 8760, deadline: 72, reefer: false },
];

export default function TransportAgentStudio() {
  const location = useLocation();
  const navigate = useNavigate();
  const prefill = location.state?.prefillData;
  const prefillVeh = location.state?.prefillVehicle;

  const initial = prefill ? {
    crop: prefill.crop,
    qty: prefill.quantity,
    origin: prefill.location?.split(',')[2]?.trim() || prefill.location?.split(',')[0]?.trim() || 'Ahmednagar',
    dest: 'Pune',
    shelf: prefill.shelf_life || 24,
    deadline: 8,
    reefer: prefill.grade === 'A'
  } : prefillVeh ? {
    crop: 'Tomato',
    qty: prefillVeh.capacity_kg || 1000,
    origin: prefillVeh.current_location || 'Pune',
    dest: 'Mumbai',
    shelf: 48,
    deadline: 12,
    reefer: Boolean(prefillVeh.refrigerated)
  } : MOCK_REQUIREMENTS[Math.floor(Math.random() * MOCK_REQUIREMENTS.length)];

  // Input Request Form State
  const [crop, setCrop] = useState(initial.crop);
  const [quantityKg, setQuantityKg] = useState<number>(initial.qty);
  const [pickupLocation, setPickupLocation] = useState(initial.origin);
  const [deliveryLocation, setDeliveryLocation] = useState(initial.dest);
  const [deadlineHours, setDeadlineHours] = useState<number>(initial.deadline);
  const [shelfLifeHours, setShelfLifeHours] = useState<number>(initial.shelf);
  const [refrigeratedRequired, setRefrigeratedRequired] = useState<boolean>(initial.reefer);

  // Execution State
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [planResult, setPlanResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(() => {
    if (prefillVeh) {
      const match = VEHICLES.find(v => v.type === prefillVeh.vehicle_type || v.id === prefillVeh.vehicle_id);
      return match ? match.id : null;
    }
    return null;
  });
  const [userFloorPrice, setUserFloorPrice] = useState<number | null>(null);
  const [viewingVehicle, setViewingVehicle] = useState<any>(null);
  
  const hasAutoEvaluated = useRef(false);

  useEffect(() => {
    if (prefill && pickupLocation && deliveryLocation && !hasAutoEvaluated.current) {
      hasAutoEvaluated.current = true;
      handleEvaluateRoute();
    }
  }, [prefill, pickupLocation, deliveryLocation]);

  const getPayload = () => ({
    crop,
    quantity_kg: Number(quantityKg),
    pickup_location: pickupLocation,
    delivery_location: deliveryLocation,
    delivery_deadline_hours: Number(deadlineHours),
    shelf_life_hours: Number(shelfLifeHours),
    refrigerated_required: refrigeratedRequired,
    buyer_offer: null, // Stakeholder negotiation agent will dynamically propose in the backend
    floor_price: userFloorPrice !== null ? userFloorPrice : (planResult?.full_state?.minimum_acceptable_price || null)
  });

  const handleEvaluateRoute = async () => {
    setEvaluating(true);
    setErrorMsg(null);
    try {
      const res = await api.post('/transport/plan', getPayload());
      const json = res.data;

      if (json.success && json.data) {
        setPlanResult(json);
        if (json.full_state?.minimum_acceptable_price) {
          setUserFloorPrice(json.full_state.minimum_acceptable_price);
        }
        if (json.full_state?.selected_vehicle) {
           const match = VEHICLES.find(v => v.type === json.full_state.selected_vehicle.vehicle_type);
           if (match) setSelectedVehicleId(match.id);
        }
      } else if (json.status === 'INFEASIBLE') {
        setErrorMsg(json.message || 'No suitable vehicle matches requested constraints.');
        setPlanResult(json);
      } else {
        setErrorMsg(json.detail || 'Failed to generate transport plan.');
        setPlanResult(null);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Network error evaluating route.');
    } finally {
      setEvaluating(false);
    }
  };

  const handleOpenNegotiationRoom = () => {
    if (!userFloorPrice && (!state || !state.minimum_acceptable_price)) {
      setErrorMsg("Please evaluate the route and ensure a floor price is set before negotiating.");
      return;
    }
    navigate('/dashboard/transport/negotiation', { state: { payload: getPayload() } });
  };

  const plan = planResult?.data;
  const state = planResult?.full_state;
  
  let waypoints = (state?.route?.route_waypoints && state.route.route_waypoints.length > 0) 
    ? [...state.route.route_waypoints] 
    : [
        {name: pickupLocation, type: "origin"},
        {name: "Highway", type: "waypoint"},
        {name: deliveryLocation, type: "destination"}
      ];

  // Dynamically inject tolls if the route is too simple
  if (waypoints.length <= 3 && state) {
     const origin = waypoints[0];
     const dest = waypoints[waypoints.length - 1];
     waypoints = [
       origin,
       { name: "Highway Toll Plaza", type: "toll", cost: Math.floor(state.distance_km * 0.8) },
       { name: "Mid-way Transit Hub", type: "waypoint" },
       { name: "City Entry Toll", type: "toll", cost: Math.floor(state.distance_km * 0.5) },
       dest
     ];
  }

  return (
    <div className="min-h-screen bg-slate-50 space-y-8 pb-12 animate-in fade-in duration-500">
      
      {/* Hero Header */}
      <div className="relative bg-slate-900 rounded-b-3xl shadow-2xl overflow-hidden -mt-6 pt-12 pb-24 px-8 text-white flex flex-col items-center justify-center text-center">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl mix-blend-overlay"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl mix-blend-overlay"></div>
        
        <div className="relative z-10 max-w-4xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 border border-white/20 text-blue-300 text-xs font-bold rounded-full backdrop-blur-sm mb-2">
            <Truck size={14} /> Transporter Hub
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight">Fleet Management & AI Negotiation</h1>
          <p className="text-slate-300 text-sm max-w-2xl mx-auto">
            Review incoming transport requirements from farmers/buyers, match them against your listed vehicles, calculate strict operational floor costs, and dispatch our AI agent to negotiate the most profitable freight rate.
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 -mt-16 relative z-20 space-y-8">
        
        {/* Vehicle Fleet Listing Showcase */}
        <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-extrabold text-slate-800 flex items-center gap-2">
              <Truck className="text-blue-600" size={24} /> My Vehicle Fleet (Maharashtra)
            </h3>
            <span className="text-sm font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded-full">{VEHICLES.length} Active Vehicles</span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {VEHICLES.map((vehicle) => (
              <div 
                key={vehicle.id} 
                className={`relative rounded-2xl overflow-hidden border-2 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${selectedVehicleId === vehicle.id ? 'border-blue-500 ring-4 ring-blue-500/20' : 'border-slate-100 hover:border-slate-300'}`}
                onClick={() => {
                  setSelectedVehicleId(vehicle.id);
                  setViewingVehicle(vehicle);
                }}
              >
                <div className="aspect-video w-full overflow-hidden bg-slate-100 relative">
                  <img src={vehicle.img} alt={vehicle.name} className="w-full h-full object-cover transition-transform duration-700 hover:scale-105" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                  <div className="absolute bottom-2 left-2 flex gap-1">
                    {vehicle.tags.map(tag => (
                      <span key={tag} className="text-[9px] font-black uppercase tracking-wider bg-white/20 backdrop-blur-md text-white px-2 py-0.5 rounded shadow-sm">{tag}</span>
                    ))}
                  </div>
                </div>
                <div className="p-4 bg-white">
                  <h4 className="font-extrabold text-slate-800 text-sm truncate">{vehicle.name}</h4>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Capacity</span>
                      <span className="text-sm font-black text-slate-700">{vehicle.capacity}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Base Rate</span>
                      <span className="text-sm font-black text-emerald-600">{vehicle.rate}</span>
                    </div>
                  </div>
                </div>
                {selectedVehicleId === vehicle.id && (
                  <div className="absolute top-2 right-2 bg-blue-500 text-white p-1 rounded-full shadow-lg">
                    <CheckCircle2 size={16} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Incoming Request Matcher */}
          <div className="lg:col-span-5 bg-white p-8 rounded-3xl shadow-xl border border-slate-100 space-y-6">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <h3 className="text-lg font-extrabold text-slate-800 flex items-center gap-2">
                <Package className="text-emerald-600" size={20} /> Incoming Requirement
              </h3>
            </div>

            <div className="space-y-4">
              <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 flex flex-col gap-4 relative overflow-hidden">
                {/* Decorative dots for receipt look */}
                <div className="absolute top-0 left-0 w-full flex justify-around -mt-1 opacity-20">
                   {[...Array(15)].map((_, i) => <div key={i} className="w-2 h-2 bg-slate-400 rounded-full"></div>)}
                </div>
                
                <div className="grid grid-cols-2 gap-y-5 mt-2">
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Cargo Type</span>
                    <span className="text-sm font-extrabold text-slate-800">{crop}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Weight</span>
                    <span className="text-sm font-extrabold text-slate-800">{quantityKg.toLocaleString()} kg</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Origin</span>
                    <span className="text-sm font-extrabold text-slate-800">{pickupLocation}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Destination</span>
                    <span className="text-sm font-extrabold text-slate-800">{deliveryLocation}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Shelf Life</span>
                    <span className="text-sm font-extrabold text-slate-800">{shelfLifeHours} Hrs</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Deadline</span>
                    <span className="text-sm font-extrabold text-slate-800">{deadlineHours} Hrs</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-4 border-t border-dashed border-slate-200">
                  <div className={`flex items-center justify-center w-6 h-6 rounded-full ${refrigeratedRequired ? 'bg-blue-100 text-blue-600' : 'bg-slate-200 text-slate-400'}`}>
                    <ThermometerSnowflake size={14} />
                  </div>
                  <span className="text-xs font-bold text-slate-600">{refrigeratedRequired ? 'Cold Chain Required' : 'Standard Transport'}</span>
                </div>
              </div>

              <div className="bg-red-50 p-5 rounded-2xl border border-red-200">
                <span className="block text-[10px] font-bold text-red-600 uppercase tracking-wider mb-2">Transporter Floor Price {state && `(AI Base: ₹${state.minimum_acceptable_price})`}</span>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-red-700 font-bold text-lg">₹</span>
                  </div>
                  <input 
                    type="number" 
                    value={userFloorPrice !== null ? userFloorPrice : (state?.minimum_acceptable_price || '')} 
                    onChange={(e) => setUserFloorPrice(Number(e.target.value))} 
                    placeholder="Evaluate route to get AI suggestion" 
                    className="w-full pl-8 py-3 bg-white border border-red-300 rounded-xl text-lg font-extrabold text-red-700 focus:outline-none focus:ring-2 focus:ring-red-500" 
                  />
                </div>
                <p className="text-[10px] text-red-600/70 mt-2 font-medium leading-relaxed">
                  Enter your absolute minimum freight rate. Our AI agent will strictly defend this floor limit during the automated negotiation.
                </p>
              </div>

              <button 
                onClick={handleEvaluateRoute} 
                disabled={evaluating}
                className="w-full py-4 bg-slate-900 hover:bg-slate-800 text-white font-extrabold rounded-xl transition flex items-center justify-center gap-2 border border-slate-800 disabled:opacity-50 shadow-lg shadow-slate-900/20"
              >
                {evaluating ? <RefreshCw className="animate-spin" size={18}/> : <Zap size={18}/>} 
                {evaluating ? 'Matching Fleet & Routing...' : 'Match Vehicle & Calculate Costs'}
              </button>
            </div>
            
            {errorMsg && (
              <div className="p-4 bg-red-50 text-red-700 border border-red-200 rounded-xl text-sm font-semibold flex items-center gap-2 animate-in fade-in">
                <AlertTriangle size={18} className="flex-shrink-0" /> 
                <span>{errorMsg}</span>
              </div>
            )}
          </div>

          {/* Right Column: Route, Costs & Negotiation */}
          <div className="lg:col-span-7 space-y-6">
            
            {!state && !evaluating && (
              <div className="bg-white border-2 border-dashed border-slate-200 rounded-3xl flex flex-col items-center justify-center p-16 text-center shadow-sm h-full min-h-[400px]">
                <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mb-6">
                  <MapPin size={40} className="text-blue-500" />
                </div>
                <h3 className="text-2xl font-extrabold text-slate-700 mb-3">Awaiting Requirement Match</h3>
                <p className="text-slate-500 max-w-sm mx-auto">Click "Match Vehicle & Calculate Costs" to let the Transport Agent evaluate feasibility, routing, and strict floor limits.</p>
              </div>
            )}

            {state && (
              <div className="bg-white rounded-3xl shadow-xl border border-slate-200 overflow-hidden animate-in slide-in-from-right-4">

                {/* Google Maps-style Route Visualization */}
                <div className="bg-slate-800 px-6 pt-6 pb-10 text-white">
                  <div className="flex justify-between items-start mb-6">
                    <h3 className="text-base font-bold flex items-center gap-2">
                      <Navigation className="text-blue-400" size={18} />
                      OSRM Live Route
                    </h3>
                    <div className="bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-xs font-bold border border-emerald-500/30">
                      Feasible Route Found
                    </div>
                  </div>
                  <div className="overflow-x-auto pb-2">
                    <div className="flex items-center min-w-max gap-0">
                      {waypoints.map((wp: any, idx: number) => (
                        <React.Fragment key={idx}>
                          <div className="flex flex-col items-center">
                            {wp.type === 'toll' ? (
                              <div className="flex flex-col items-center">
                                <div className="bg-amber-400 border-2 border-amber-600 rounded-lg px-2 py-1 flex flex-col items-center shadow-lg">
                                  <span className="text-[9px] font-black text-amber-900 uppercase tracking-wider">TOLL</span>
                                  <span className="text-xs font-black text-amber-900">₹{wp.cost}</span>
                                </div>
                                <span className="text-[10px] font-semibold text-amber-300 mt-1.5 max-w-[72px] text-center leading-tight">{wp.name}</span>
                              </div>
                            ) : (
                              <div className="flex flex-col items-center">
                                <div className={`w-10 h-10 rounded-full border-4 flex items-center justify-center shadow-lg ${idx === 0 ? 'bg-blue-500 border-blue-300' : idx === waypoints.length - 1 ? 'bg-emerald-500 border-emerald-300' : 'bg-slate-600 border-slate-400'}`}>
                                  <MapPin size={16} className="text-white" />
                                </div>
                                <span className={`text-[11px] font-bold mt-1.5 max-w-[64px] text-center leading-tight ${idx === 0 ? 'text-blue-300' : idx === waypoints.length - 1 ? 'text-emerald-300' : 'text-slate-300'}`}>
                                  {wp.name}
                                </span>
                                {idx === 0 && <span className="text-[9px] bg-blue-500/30 text-blue-300 px-1.5 py-0.5 rounded mt-1 font-bold">ORIGIN</span>}
                                {idx === waypoints.length - 1 && <span className="text-[9px] bg-emerald-500/30 text-emerald-300 px-1.5 py-0.5 rounded mt-1 font-bold">DEST</span>}
                              </div>
                            )}
                          </div>
                          {idx < waypoints.length - 1 && (
                            <div className="flex items-center mx-1">
                              <div className={`h-0.5 w-8 ${waypoints[idx + 1]?.type === 'toll' || wp.type === 'toll' ? 'bg-amber-500/60' : 'bg-slate-500'}`}></div>
                              <svg width="8" height="8" viewBox="0 0 8 8" fill={waypoints[idx + 1]?.type === 'toll' || wp.type === 'toll' ? '#f59e0b' : '#64748b'}>
                                <path d="M0 0 L8 4 L0 8 Z"/>
                              </svg>
                            </div>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="p-8">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                      <span className="text-xs font-bold text-slate-400 uppercase block mb-1">Distance</span>
                      <span className="text-2xl font-extrabold text-slate-800">{state.distance_km} <span className="text-sm font-bold text-slate-500">km</span></span>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                      <span className="text-xs font-bold text-slate-400 uppercase block mb-1">Est. Time</span>
                      <span className="text-2xl font-extrabold text-slate-800">{state.estimated_duration_hours} <span className="text-sm font-bold text-slate-500">hrs</span></span>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                      <span className="text-xs font-bold text-slate-400 uppercase block mb-1">Oper. Cost</span>
                      <span className="text-2xl font-extrabold text-slate-800">₹{state.total_operating_cost || 0}</span>
                    </div>
                  </div>

                  <button
                    onClick={handleOpenNegotiationRoom}
                    className="w-full py-5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white text-lg font-extrabold rounded-2xl transition shadow-xl shadow-blue-900/20 flex items-center justify-center gap-3 transform hover:-translate-y-1"
                  >
                    <Users size={24} /> Launch Parallel AI Negotiator
                  </button>
                  <p className="text-center text-xs font-semibold text-slate-400 mt-4">
                    The Transporter Agent will strictly defend the floor price and maximize your profit margin.
                  </p>
                </div>
              </div>
            )}


          </div>
        </div>
      </div>
      {viewingVehicle && (
        <div className="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-3xl shadow-2xl overflow-hidden max-w-lg w-full transform transition-all animate-in zoom-in-95">
            <div className="relative h-48 bg-slate-100">
              <img src={viewingVehicle.img} alt={viewingVehicle.name} className="w-full h-full object-cover" />
              <button 
                onClick={(e) => { e.stopPropagation(); setViewingVehicle(null); }}
                className="absolute top-4 right-4 bg-black/40 hover:bg-black/60 text-white rounded-full p-2 backdrop-blur-md transition"
              >
                <XCircle size={20} />
              </button>
              <div className="absolute bottom-4 left-4 flex gap-2">
                {viewingVehicle.tags.map(tag => (
                  <span key={tag} className="text-[10px] font-black uppercase tracking-wider bg-white/90 text-slate-800 px-2 py-1 rounded shadow-sm">{tag}</span>
                ))}
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <h3 className="text-2xl font-extrabold text-slate-800">{viewingVehicle.name}</h3>
                <p className="text-sm font-bold text-slate-500 mt-1">{viewingVehicle.type} • Capacity: {viewingVehicle.capacity}</p>
              </div>
              
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 text-sm text-slate-600">
                <p><strong>Best Suited For:</strong> {viewingVehicle.tags.includes('Cold Chain') ? 'Perishable goods, temperature-sensitive crops (fruits, vegetables, dairy) requiring strict cold chain integrity.' : viewingVehicle.tags.includes('Last Mile') ? 'Short distance, intra-city deliveries and navigating narrow mandi roads.' : viewingVehicle.tags.includes('Heavy Load') ? 'Interstate bulk transport, grains, and heavy commodities.' : 'Standard agricultural transport across state highways.'}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-emerald-50 border border-emerald-100 p-4 rounded-2xl">
                  <span className="block text-[10px] font-bold uppercase text-emerald-600 mb-1">Base Rate</span>
                  <span className="text-xl font-black text-emerald-700">{viewingVehicle.rate}</span>
                </div>
                <div className="bg-blue-50 border border-blue-100 p-4 rounded-2xl">
                  <span className="block text-[10px] font-bold uppercase text-blue-600 mb-1">Est. Trip Cost</span>
                  <span className="text-xl font-black text-blue-700">
                    {state?.distance_km ? `₹${(state.distance_km * parseInt(viewingVehicle.rate.replace(/\\D/g, ''))).toLocaleString('en-IN')}` : 'Evaluate Route First'}
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <button 
                  onClick={() => setViewingVehicle(null)}
                  className="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl transition"
                >
                  Select & Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
