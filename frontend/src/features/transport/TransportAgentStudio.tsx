import React, { useState } from 'react';
import { Truck, Navigation, ShieldCheck, DollarSign, Calculator, MessageSquare, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';
import { api } from '@/services/api';

export default function TransportAgentStudio() {
  // Input Request Form State
  const [crop, setCrop] = useState('Tomato');
  const [quantityKg, setQuantityKg] = useState<number>(2000);
  const [pickupLocation, setPickupLocation] = useState('Ahmednagar');
  const [deliveryLocation, setDeliveryLocation] = useState('Pune');
  const [deadlineHours, setDeadlineHours] = useState<number>(8);
  const [shelfLifeHours, setShelfLifeHours] = useState<number>(24);
  const [refrigeratedRequired, setRefrigeratedRequired] = useState<boolean>(false);
  const [buyerOffer, setBuyerOffer] = useState<string>('4400');

  // Execution State
  const [loading, setLoading] = useState<boolean>(false);
  const [planResult, setPlanResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Interactive Negotiation State
  const [negotiating, setNegotiating] = useState<boolean>(false);
  const [negHistory, setNegHistory] = useState<any[]>([]);

  const handleRunWorkflow = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        crop,
        quantity_kg: Number(quantityKg),
        pickup_location: pickupLocation,
        delivery_location: deliveryLocation,
        delivery_deadline_hours: Number(deadlineHours),
        shelf_life_hours: Number(shelfLifeHours),
        refrigerated_required: refrigeratedRequired,
        buyer_offer: buyerOffer ? Number(buyerOffer) : null,
      };

      const res = await api.post('/transport/plan', payload);
      const json = res.data;

      if (json.success && json.data) {
        setPlanResult(json);
        setErrorMsg(null);
        if (json.full_state?.negotiation_history) {
          setNegHistory(json.full_state.negotiation_history);
        }
      } else if (json.status === 'INFEASIBLE') {
        setErrorMsg(json.message || 'No suitable vehicle matches requested quantity and constraints.');
        setPlanResult(json);
      } else {
        setErrorMsg(json.detail || json.message || 'Failed to generate transport plan.');
        setPlanResult(null);
      }
    } catch (err: any) {
      console.error('Transport Agent error:', err);
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'Network error connecting to Transport Agent API backend.';
      setErrorMsg(typeof msg === 'object' ? JSON.stringify(msg) : String(msg));
      setPlanResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSendOffer = async () => {
    if (!planResult?.full_state || !buyerOffer) return;
    setNegotiating(true);
    try {
      const res = await api.post('/transport/negotiate', {
        state: planResult.full_state,
        buyer_offer: Number(buyerOffer),
      });

      const json = res.data;
      if (json.success) {
        setPlanResult((prev: any) => ({
          ...prev,
          data: json.plan || prev.data,
          full_state: json.state,
        }));
        if (json.state?.negotiation_history) {
          setNegHistory(json.state.negotiation_history);
        }
      }
    } catch (err: any) {
      console.error('Negotiation error:', err);
      const msg = err.response?.data?.detail || err.message || 'Error processing negotiation.';
      setErrorMsg(typeof msg === 'object' ? JSON.stringify(msg) : String(msg));
    } finally {
      setNegotiating(false);
    }
  };

  const plan = planResult?.data;
  const state = planResult?.full_state;
  const breakdown = plan?.cost_breakdown || state?.cost_breakdown;

  // Reusable crisp input style to prevent invisible/light text
  const inputStyle = "w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 bg-white placeholder-slate-400 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none shadow-sm transition";

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Header — Aligned with MandiMitra & Farmer Dashboard */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center flex-wrap gap-4"
        style={{ background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)' }}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-600 flex items-center justify-center shadow-md text-white">
            <Truck size={24} />
          </div>
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-[11px] font-bold rounded-full mb-1">
              <ShieldCheck size={12} className="text-emerald-700" /> Gayatri's 11-Node Autonomous LangGraph Engine
            </div>
            <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              Transport Agent Studio
            </h2>
            <p className="text-slate-600 text-xs mt-0.5">
              Real vehicle fleet matching, OSRM road distance, deterministic fuel & toll engine, and multi-round autonomous freight negotiation.
            </p>
          </div>
        </div>
      </div>

      {/* Grid Layout: Input Form vs Vehicle & Route Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Request Form */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-4">
          
          {/* Quick Presets from Farmer Agent */}
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              ⚡ Quick Presets from Farmer Agent
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Nashik → Pune (Onion 1.5 MT)', crop: 'Onion', qty: 1500, from: 'Nashik', to: 'Pune', deadline: 12, reefer: false, offer: '8000' },
                { label: 'Ahmednagar → Pune (Tomato 2 MT)', crop: 'Tomato', qty: 2000, from: 'Ahmednagar', to: 'Pune', deadline: 8, reefer: true, offer: '7200' },
                { label: 'Akola → Amravati (Cotton 3 MT)', crop: 'Cotton', qty: 3000, from: 'Akola', to: 'Amravati', deadline: 24, reefer: false, offer: '14000' },
                { label: 'Latur → Latur (Soybean 2 MT)', crop: 'Soybean', qty: 2000, from: 'Latur', to: 'Latur', deadline: 48, reefer: false, offer: '6000' },
              ].map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setCrop(p.crop);
                    setQuantityKg(p.qty);
                    setPickupLocation(p.from);
                    setDeliveryLocation(p.to);
                    setDeadlineHours(p.deadline);
                    setRefrigeratedRequired(p.reefer);
                    setBuyerOffer(p.offer);
                  }}
                  className="p-2 text-left bg-slate-50 hover:bg-emerald-50 hover:border-emerald-300 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 transition"
                >
                  <p className="font-bold text-slate-800 truncate">{p.label}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">{p.reefer ? '❄️ Reefer' : '📦 Dry'} • ₹{p.offer} target</p>
                </button>
              ))}
            </div>
          </div>

          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 pt-2 border-t border-slate-100">
            <Calculator className="text-amber-600" size={16} /> Transport Requirement Parameters
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Crop Type</label>
              <input
                type="text"
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className={inputStyle}
                placeholder="e.g. Tomato"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Quantity (kg)</label>
              <input
                type="number"
                value={quantityKg}
                onChange={(e) => setQuantityKg(Number(e.target.value))}
                className={inputStyle}
                placeholder="2000"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Pickup Location</label>
              <input
                type="text"
                value={pickupLocation}
                onChange={(e) => setPickupLocation(e.target.value)}
                className={inputStyle}
                placeholder="e.g. Ahmednagar"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Delivery Location</label>
              <input
                type="text"
                value={deliveryLocation}
                onChange={(e) => setDeliveryLocation(e.target.value)}
                className={inputStyle}
                placeholder="e.g. Pune"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Deadline (Hours)</label>
              <input
                type="number"
                value={deadlineHours}
                onChange={(e) => setDeadlineHours(Number(e.target.value))}
                className={inputStyle}
                placeholder="8"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Shelf Life (Hours)</label>
              <input
                type="number"
                value={shelfLifeHours}
                onChange={(e) => setShelfLifeHours(Number(e.target.value))}
                className={inputStyle}
                placeholder="24"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="reefer"
              checked={refrigeratedRequired}
              onChange={(e) => setRefrigeratedRequired(e.target.checked)}
              className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300"
            />
            <label htmlFor="reefer" className="text-xs font-semibold text-slate-700 cursor-pointer">
              Refrigeration / Temperature Control Required
            </label>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Initial Buyer Offer Freight (₹)</label>
            <input
              type="number"
              value={buyerOffer}
              onChange={(e) => setBuyerOffer(e.target.value)}
              placeholder="e.g. 4200"
              className={inputStyle}
            />
          </div>

          <button
            onClick={handleRunWorkflow}
            disabled={loading}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white font-bold rounded-xl transition shadow-md shadow-emerald-900/10 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="animate-spin" size={18} /> Calculating OSRM Route & Costs...
              </>
            ) : (
              <>
                Run Transport Agent Workflow <ArrowRight size={18} />
              </>
            )}
          </button>

          {errorMsg && (
            <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-xl text-xs flex items-center gap-2 animate-in fade-in">
              <AlertTriangle size={16} className="flex-shrink-0" /> 
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Right Column: Dynamic Analysis & Results */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Infeasible / Rejected Vehicles Card */}
          {planResult?.status === 'INFEASIBLE' && planResult?.rejected_vehicles && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-red-100 space-y-4 animate-in fade-in">
              <div className="flex items-center gap-2 text-red-600 font-bold text-lg">
                <AlertTriangle size={22} />
                <span>Hard Constraints Analysis: Request Infeasible</span>
              </div>
              <p className="text-xs text-slate-600">
                The Transport Agent evaluated all registered vehicles against your shipment parameters (Quantity: <strong>{quantityKg} kg</strong>). No vehicle meets the strict physical capacity or feasibility constraints:
              </p>
              <div className="space-y-2 max-h-[260px] overflow-y-auto">
                {planResult.rejected_vehicles.map((rej: any, idx: number) => (
                  <div key={idx} className="p-3 bg-red-50/60 border border-red-100 rounded-xl text-xs flex justify-between items-center">
                    <span className="font-bold text-slate-800">Vehicle ID: {rej.vehicle_id}</span>
                    <span className="text-red-700 font-medium">{rej.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* OSRM Route & Vehicle Summary */}
          {state && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-4">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Navigation className="text-emerald-600" size={20} /> OSRM Road Route & Vehicle Selection
              </h3>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl text-center">
                <div>
                  <span className="text-xs text-slate-500 block">Selected Vehicle</span>
                  <span className="text-sm font-bold text-slate-800">{state.selected_vehicle?.vehicle_name || 'N/A'}</span>
                  <span className="text-[10px] text-slate-500 block">{state.selected_vehicle?.vehicle_type}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Road Distance</span>
                  <span className="text-sm font-bold text-amber-600">{state.distance_km} km</span>
                  <span className="text-[10px] text-slate-500 block">Deadhead: {state.deadhead_km} km</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Est. Travel Duration</span>
                  <span className="text-sm font-bold text-slate-800">{state.estimated_duration_hours} hrs</span>
                  <span className="text-[10px] text-slate-500 block">OSRM Engine</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Vehicle Capacity</span>
                  <span className="text-sm font-bold text-slate-800">{state.selected_vehicle?.capacity_kg} kg</span>
                  <span className="text-[10px] font-semibold text-emerald-600 block">AVAILABLE</span>
                </div>
              </div>
            </div>
          )}

          {/* Deterministic Financial Breakdown */}
          {state && breakdown && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-4">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <DollarSign className="text-emerald-600" size={20} /> Deterministic Cost & Floor Price Breakdown
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-500 block">Fuel Cost</span>
                  <span className="font-bold text-slate-800 text-sm">₹{breakdown.fuel_cost}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-500 block">Toll Cost ({breakdown.toll_type || 'NHAI'})</span>
                  <span className="font-bold text-slate-800 text-sm">₹{breakdown.toll_cost}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-500 block">Driver Cost</span>
                  <span className="font-bold text-slate-800 text-sm">₹{breakdown.driver_cost}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-500 block">Maintenance Cost</span>
                  <span className="font-bold text-slate-800 text-sm">₹{breakdown.maintenance_cost}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-500 block">Risk Buffer</span>
                  <span className="font-bold text-slate-800 text-sm">₹{breakdown.risk_buffer}</span>
                </div>
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                  <span className="text-emerald-700 font-semibold block">Minimum Floor Price</span>
                  <span className="font-extrabold text-emerald-700 text-sm">₹{state.minimum_acceptable_price}</span>
                </div>
              </div>

              <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 flex justify-between items-center text-xs">
                <div>
                  <span className="text-amber-800 font-semibold block">Operating Cost: ₹{state.total_operating_cost}</span>
                  <span className="text-amber-700">Target Freight Quote: ₹{state.target_price} | Initial Quote: ₹{state.initial_quote}</span>
                </div>
                {plan?.expected_profit && (
                  <div className="text-right">
                    <span className="text-emerald-700 font-bold block text-sm">+₹{plan.expected_profit}</span>
                    <span className="text-emerald-600 text-[10px]">Expected Profit</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Interactive Multi-round Negotiation Room */}
          {state && (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-4">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <MessageSquare className="text-blue-600" size={20} /> Multi-Round AI Freight Negotiation
              </h3>

              <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
                {negHistory.map((item, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1">
                    <div className="flex justify-between font-bold text-slate-700">
                      <span>Round {item.round} — {item.agent_action}</span>
                      <span className={item.status === 'ACCEPTED' ? 'text-emerald-600' : 'text-amber-600'}>
                        {item.agent_counter ? `Counter: ₹${item.agent_counter}` : `Offer: ₹${item.buyer_offer}`}
                      </span>
                    </div>
                    <p className="text-slate-600 italic">"{item.message}"</p>
                  </div>
                ))}
              </div>

              {state.negotiation_status !== 'ACCEPTED' && (
                <div className="flex gap-2 pt-2">
                  <input
                    type="number"
                    value={buyerOffer}
                    onChange={(e) => setBuyerOffer(e.target.value)}
                    placeholder="Enter counter offer (₹)..."
                    className={inputStyle}
                  />
                  <button
                    onClick={handleSendOffer}
                    disabled={negotiating}
                    className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl transition text-xs flex items-center gap-1 disabled:opacity-50 whitespace-nowrap"
                  >
                    {negotiating ? 'Evaluating...' : 'Submit Counter Offer'}
                  </button>
                </div>
              )}

              {state.negotiation_status === 'ACCEPTED' && (
                <div className="p-4 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-emerald-600" />
                  Freight agreement finalized at ₹{state.agreed_price}! Transport Plan generated.
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
