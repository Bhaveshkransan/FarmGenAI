import React, { useState, useEffect } from 'react';
import { 
  X, 
  Target, 
  ChevronRight, 
  ChevronLeft, 
  Sparkles, 
  Truck, 
  Warehouse, 
  Building2, 
  TrendingUp, 
  Bot, 
  CheckCircle2,
  ShieldCheck,
  Layers,
  MapPin
} from 'lucide-react';
import { api } from '@/services/api';
import { useNotification } from '@/contexts/NotificationContext';
import { CANONICAL_7_CROPS, MAHARASHTRA_BUYER_HUBS } from '@/pages/buyer/BuyerDashboard';

const PROCUREMENT_PURPOSES = [
  { id: 'food_processing', label: '🏭 Food Processing & Milling' },
  { id: 'oil_extraction', label: '🛢️ Oil Extraction & Solvent Refining' },
  { id: 'ginning_spinning', label: '🧵 Cotton Ginning & Textile Spinning' },
  { id: 'wholesale_trader', label: '🏢 APMC Mandi Wholesale Distribution' },
  { id: 'retail_supermarket', label: '🛒 Supermarket Retail Chain' },
  { id: 'restaurant', label: '🍽️ Restaurant & Cloud Kitchen Chain' },
  { id: 'institutional', label: '🏫 Institutional & Govt Supply' },
];

const QUALITY_GRADES = [
  { id: 'Grade A', label: 'Grade A (Premium / Export Quality)' },
  { id: 'Grade B', label: 'Grade B (Standard Commercial)' },
  { id: 'Grade C', label: 'Grade C (Industrial Processing Grade)' },
  { id: 'ANY', label: 'Any Quality Grade (Best Value)' },
];

interface PostRequirementModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (createdData: any) => void;
  initialCrop?: string;
}

export default function PostRequirementModal({
  isOpen,
  onClose,
  onSuccess,
  initialCrop = 'Soybean'
}: PostRequirementModalProps) {
  const { addNotification } = useNotification();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [crop, setCrop] = useState(initialCrop);
  const [variety, setVariety] = useState('');
  const [purpose, setPurpose] = useState('food_processing');
  const [quantity, setQuantity] = useState<number | string>(5000);
  const [unit, setUnit] = useState('kg');
  const [minBatchSize, setMinBatchSize] = useState<number | string>(500);
  const [qualityGrade, setQualityGrade] = useState('Grade A');
  const [maxMoisture, setMaxMoisture] = useState(10);
  const [isOrganic, setIsOrganic] = useState(false);
  const [deliveryLocation, setDeliveryLocation] = useState('Pune');
  const [villageTaluka, setVillageTaluka] = useState('Hadapsar MIDC');
  const [transportRequired, setTransportRequired] = useState(true);
  const [warehouseRequired, setWarehouseRequired] = useState(false);
  const [targetPrice, setTargetPrice] = useState(45);
  const [maxCeilingPrice, setMaxCeilingPrice] = useState(52);
  const [aiIntel, setAiIntel] = useState<any>(null);
  const [isLoadingIntel, setIsLoadingIntel] = useState(false);

  // Reset step & sync crop whenever modal opens
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(1);
      if (initialCrop) setCrop(initialCrop);
    }
  }, [isOpen, initialCrop]);

  // Handle quantity input with auto-batch adjustment
  const handleQuantityChange = (val: string) => {
    setQuantity(val);
    const num = Number(val);
    if (!isNaN(num) && num > 0) {
      const curBatch = Number(minBatchSize) || 0;
      if (curBatch > num || curBatch === 0) {
        setMinBatchSize(Math.min(num, Math.max(10, Math.floor(num / 2))));
      }
    }
  };

  const handleUnitChange = (newUnit: string) => {
    const oldUnit = unit;
    setUnit(newUnit);
    const num = Number(quantity);
    if (!num || num <= 0) return;

    if (oldUnit === 'kg' && newUnit === 'quintal') {
      const q = Math.max(1, Math.round(num / 100));
      setQuantity(q);
      setMinBatchSize(Math.max(1, Math.floor(q / 2)));
    } else if (oldUnit === 'kg' && newUnit === 'ton') {
      const t = Math.max(1, Math.round(num / 1000));
      setQuantity(t);
      setMinBatchSize(Math.max(1, Math.floor(t / 2)));
    } else if (oldUnit === 'quintal' && newUnit === 'kg') {
      setQuantity(num * 100);
      setMinBatchSize(Math.max(50, Math.floor((num * 100) / 2)));
    } else if (oldUnit === 'quintal' && newUnit === 'ton') {
      const t = Math.max(1, Math.round(num / 10));
      setQuantity(t);
      setMinBatchSize(Math.max(1, Math.floor(t / 2)));
    } else if (oldUnit === 'ton' && newUnit === 'kg') {
      setQuantity(num * 1000);
      setMinBatchSize(Math.max(100, Math.floor((num * 1000) / 2)));
    } else if (oldUnit === 'ton' && newUnit === 'quintal') {
      setQuantity(num * 10);
      setMinBatchSize(Math.max(1, Math.floor((num * 10) / 2)));
    }
  };

  const setPresetQuantity = (qty: number) => {
    setQuantity(qty);
    setMinBatchSize(Math.min(qty, Math.max(10, Math.floor(qty / 2))));
  };

  // Fetch ML Market Intel when crop changes
  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    setIsLoadingIntel(true);
    api.get(`/buyers/price-forecast?crop=${encodeURIComponent(crop)}&location=${encodeURIComponent(deliveryLocation)}`)
      .then(res => {
        if (isMounted && res.data) {
          setAiIntel(res.data);
          const livePrice = res.data.current_price || 40;
          const predPrice = res.data.predicted_modal_price || livePrice;
          setTargetPrice(Math.round(predPrice * 0.95 * 10) / 10);
          setMaxCeilingPrice(Math.round(predPrice * 1.06 * 10) / 10);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (isMounted) setIsLoadingIntel(false);
      });
    return () => { isMounted = false; };
  }, [crop, deliveryLocation, isOpen]);

  if (!isOpen) return null;

  const totalSteps = 5;

  const handleNext = () => {
    if (currentStep === 1 && !crop) {
      addNotification('Please select a commodity crop', 'error');
      return;
    }
    if (currentStep === 2) {
      const numQty = Number(quantity);
      if (!numQty || numQty <= 0) {
        addNotification('Please enter a valid procurement quantity greater than 0', 'error');
        return;
      }
      let numBatch = Number(minBatchSize);
      if (!numBatch || numBatch <= 0 || numBatch > numQty) {
        numBatch = Math.min(numQty, Math.max(10, Math.floor(numQty / 2)));
        setMinBatchSize(numBatch);
      }
    }
    setCurrentStep(p => Math.min(p + 1, totalSteps));
  };

  const handlePrev = () => setCurrentStep(p => Math.max(p - 1, 1));

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        crop,
        variety: variety || 'Commercial Lot',
        purpose,
        quantity: Number(quantity),
        unit,
        min_batch_size: Number(minBatchSize),
        quality_grade: qualityGrade,
        quality: qualityGrade,
        max_moisture: Number(maxMoisture),
        is_organic: isOrganic,
        location: `${villageTaluka}, ${deliveryLocation}, Maharashtra`,
        preferredLocation: `${deliveryLocation}, Maharashtra`,
        transport_required: transportRequired,
        transportRequired: transportRequired,
        warehouse_required: warehouseRequired,
        storageRequired: warehouseRequired,
        target_price: Number(targetPrice),
        buyer_target_price: Number(targetPrice),
        max_price: Number(maxCeilingPrice),
        maxBudget: Number(maxCeilingPrice),
        budget: Number(quantity) * Number(maxCeilingPrice),
        buyer_mode: true,
        max_rounds: 5,
        timestamp: new Date().toISOString()
      };

      // 1. Save to requirements database
      const reqRes = await api.post('/requirements', payload);
      const reqId = reqRes.data?.data?.id || reqRes.data?.requirement_id || `req_${Date.now()}`;

      // 2. Start Autonomous Matching & Multi-Agent Negotiation
      const startPayload = {
        ...payload,
        requirement_id: reqId,
        min_price: targetPrice,
        shelf_life: 60,
        farmer_name: 'Maharashtra Farmer Network',
        buyer_name: 'Procurement Buyer',
        buyer_budget: payload.budget,
        buyer_max_quantity: payload.quantity,
        buyer_strategy: purpose,
        buyer_persona: purpose
      };

      const negRes = await api.post('/negotiations/start-negotiation', startPayload);
      const negId = negRes.data?.negotiation_id || negRes.data?.id;

      addNotification(`Requirement posted & AI Matching initiated! ID: ${negId || reqId}`, 'success');
      onSuccess?.({ reqId, negId, ...payload });
      onClose();
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to submit procurement requirement', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50 sticky top-0 z-10">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-sm">
              <Target size={20} />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">
                Post Procurement Requirement
              </h3>
              <p className="text-xs text-slate-500">
                Step {currentStep} of {totalSteps} • AI matching & autonomous price discovery
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Stepper Indicator Bar */}
        <div className="bg-slate-100/80 px-6 py-2.5 flex justify-between items-center border-b border-slate-200/60 text-xs">
          {[
            { num: 1, label: 'Commodity' },
            { num: 2, label: 'Quantity' },
            { num: 3, label: 'Quality' },
            { num: 4, label: 'Logistics' },
            { num: 5, label: 'ML Strategy' },
          ].map((s) => (
            <div key={s.num} className="flex items-center gap-1.5">
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                currentStep === s.num 
                  ? 'bg-emerald-600 text-white ring-2 ring-emerald-400/30' 
                  : currentStep > s.num 
                  ? 'bg-emerald-100 text-emerald-800' 
                  : 'bg-slate-200 text-slate-600'
              }`}>
                {currentStep > s.num ? '✓' : s.num}
              </span>
              <span className={`hidden sm:inline font-medium ${currentStep === s.num ? 'text-slate-900 font-bold' : 'text-slate-500'}`}>
                {s.label}
              </span>
            </div>
          ))}
        </div>

        {/* Modal Scrollable Body */}
        <div className="overflow-y-auto flex-1 p-6 text-xs">
          
          {/* ── STEP 1: Commodity Needs & Industry Purpose ── */}
          {currentStep === 1 && (
            <div className="space-y-5 animate-in slide-in-from-right-3 duration-200">
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">1. Select Commodity Crop & Industry Purpose</h4>
                <p className="text-slate-500">Strictly grounded in the 7 statutory Maharashtra crops.</p>
              </div>

              {/* Crop Grid */}
              <div>
                <label className="block font-semibold text-slate-700 mb-2">Select Crop *</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {CANONICAL_7_CROPS.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setCrop(c.id)}
                      className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition ${
                        crop === c.id 
                          ? 'border-emerald-600 bg-emerald-50/80 text-emerald-950 font-bold ring-2 ring-emerald-500/20' 
                          : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                      }`}
                    >
                      <span className="text-2xl">{c.emoji}</span>
                      <div>
                        <p className="text-xs font-bold">{c.name}</p>
                        <p className="text-[10px] text-slate-400">{c.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Specific Variety */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Preferred Variety (Optional)</label>
                <input
                  type="text"
                  value={variety}
                  onChange={(e) => setVariety(e.target.value)}
                  placeholder="e.g. Indrayani, JS-335, Maldandi M-35-1, Lasalgaon Red..."
                  className="w-full form-input text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500"
                />
              </div>

              {/* Procurement Purpose */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Procurement Purpose / Industry Sector *</label>
                <select
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  className="w-full form-select text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500 font-medium text-slate-800"
                >
                  {PROCUREMENT_PURPOSES.map((p) => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* ── STEP 2: Quantity Details ── */}
          {currentStep === 2 && (
            <div className="space-y-5 animate-in slide-in-from-right-3 duration-200">
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">2. Quantity & Batch Details</h4>
                <p className="text-slate-500">Specify procurement volume and fulfillment batch sizing.</p>
              </div>

              {/* Quick Presets */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                  Quick Volume Presets
                </label>
                <div className="flex flex-wrap gap-2">
                  {unit === 'kg' && [
                    { label: '120 kg (Kitchen/Sample)', val: 120 },
                    { label: '500 kg', val: 500 },
                    { label: '1,000 kg (1 MT)', val: 1000 },
                    { label: '5,000 kg (Commercial)', val: 5000 },
                    { label: '10,000 kg (Bulk)', val: 10000 },
                  ].map((p) => (
                    <button
                      key={p.val}
                      type="button"
                      onClick={() => setPresetQuantity(p.val)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                        Number(quantity) === p.val
                          ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                  {unit === 'quintal' && [
                    { label: '5 Quintals', val: 5 },
                    { label: '10 Quintals', val: 10 },
                    { label: '50 Quintals', val: 50 },
                    { label: '100 Quintals', val: 100 },
                  ].map((p) => (
                    <button
                      key={p.val}
                      type="button"
                      onClick={() => setPresetQuantity(p.val)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                        Number(quantity) === p.val
                          ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                  {unit === 'ton' && [
                    { label: '1 Ton', val: 1 },
                    { label: '5 Tons', val: 5 },
                    { label: '10 Tons', val: 10 },
                    { label: '25 Tons', val: 25 },
                  ].map((p) => (
                    <button
                      key={p.val}
                      type="button"
                      onClick={() => setPresetQuantity(p.val)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                        Number(quantity) === p.val
                          ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Total Quantity Required *</label>
                  <input
                    type="number"
                    min="1"
                    step={unit === 'ton' ? '0.5' : unit === 'quintal' ? '1' : '10'}
                    value={quantity}
                    onChange={(e) => handleQuantityChange(e.target.value)}
                    placeholder="Enter total quantity"
                    className="w-full form-input text-xs rounded-xl bg-slate-50 border-slate-200 font-bold text-slate-900 focus:ring-emerald-500"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    Procurement demand in {unit === 'kg' ? 'kilograms' : unit === 'quintal' ? 'quintals (100 kg)' : 'metric tons'}.
                  </p>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Measurement Unit *</label>
                  <select
                    value={unit}
                    onChange={(e) => handleUnitChange(e.target.value)}
                    className="w-full form-select text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500 font-semibold text-slate-800"
                  >
                    <option value="kg">Kilograms (kg)</option>
                    <option value="quintal">Quintals (100 kg)</option>
                    <option value="ton">Metric Tons (MT)</option>
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <div className="flex justify-between items-center mb-1">
                    <label className="block font-semibold text-slate-700">Minimum Batch Acceptance Size *</label>
                    <span className="text-[10px] text-slate-400 font-mono">Max allowable: {quantity} {unit}</span>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max={Number(quantity) || 999999}
                    step={unit === 'ton' ? '0.1' : unit === 'quintal' ? '1' : '10'}
                    value={minBatchSize}
                    onChange={(e) => setMinBatchSize(e.target.value)}
                    className="w-full form-input text-xs rounded-xl bg-slate-50 border-slate-200 font-medium text-slate-800 focus:ring-emerald-500"
                  />
                  {Number(minBatchSize) > Number(quantity) ? (
                    <p className="text-[11px] text-amber-600 font-semibold mt-1 flex items-center gap-1">
                      ⚠️ Batch size ({minBatchSize} {unit}) cannot exceed total quantity ({quantity} {unit}). It will be auto-clamped.
                    </p>
                  ) : (
                    <p className="text-[10px] text-slate-400 mt-1">
                      Smallest lot size you will accept from an individual farmer/FPO dispatch.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 3: Quality Parameters ── */}
          {currentStep === 3 && (
            <div className="space-y-5 animate-in slide-in-from-right-3 duration-200">
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">3. Quality Parameters & Inspection Standards</h4>
                <p className="text-slate-500">Define the physical quality and moisture constraints required for processing.</p>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Required Quality Grade *</label>
                <select
                  value={qualityGrade}
                  onChange={(e) => setQualityGrade(e.target.value)}
                  className="w-full form-select text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500 font-semibold text-slate-800"
                >
                  {QUALITY_GRADES.map((g) => (
                    <option key={g.id} value={g.id}>{g.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Maximum Moisture Content (%)</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="5"
                    max="25"
                    step="1"
                    value={maxMoisture}
                    onChange={(e) => setMaxMoisture(Number(e.target.value))}
                    className="flex-1 accent-emerald-600"
                  />
                  <span className="font-bold text-slate-800 w-12 text-center bg-slate-100 py-1 rounded-lg">
                    {maxMoisture}%
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Grain & oilseed lots exceeding this moisture will require artificial drying deduction.
                </p>
              </div>

              <div className="p-3.5 bg-emerald-50/60 border border-emerald-200/80 rounded-xl flex items-center gap-3">
                <input
                  type="checkbox"
                  id="organic_check"
                  checked={isOrganic}
                  onChange={(e) => setIsOrganic(e.target.checked)}
                  className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
                />
                <label htmlFor="organic_check" className="font-semibold text-emerald-950 cursor-pointer">
                  Certified Organic Produce Required
                  <p className="text-[10px] text-emerald-800 font-normal mt-0.5">
                    Requires NPOP / APEDA organic traceability certificate from supplier.
                  </p>
                </label>
              </div>
            </div>
          )}

          {/* ── STEP 4: Facility Location & Logistics ── */}
          {currentStep === 4 && (
            <div className="space-y-5 animate-in slide-in-from-right-3 duration-200">
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">4. Delivery Facility & Logistics Requirements</h4>
                <p className="text-slate-500">Set destination processing center and transport logistics assistance.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Buyer Hub District (Maharashtra) *</label>
                  <select
                    value={deliveryLocation}
                    onChange={(e) => setDeliveryLocation(e.target.value)}
                    className="w-full form-select text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500 font-semibold text-slate-800"
                  >
                    {MAHARASHTRA_BUYER_HUBS.map((hub) => (
                      <option key={hub} value={hub}>{hub}, Maharashtra</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Facility Locality / MIDC Area *</label>
                  <input
                    type="text"
                    value={villageTaluka}
                    onChange={(e) => setVillageTaluka(e.target.value)}
                    placeholder="e.g. Hadapsar Industrial Area, Chakan MIDC..."
                    className="w-full form-input text-xs rounded-xl bg-slate-50 border-slate-200 focus:ring-emerald-500"
                  />
                </div>
              </div>

              {/* Logistics Checkboxes */}
              <div className="space-y-2.5">
                <div className="p-3.5 bg-blue-50/60 border border-blue-200/70 rounded-xl flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="transport_req"
                    checked={transportRequired}
                    onChange={(e) => setTransportRequired(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 mt-0.5"
                  />
                  <label htmlFor="transport_req" className="font-semibold text-blue-950 cursor-pointer">
                    <span className="flex items-center gap-1.5"><Truck size={14} className="text-blue-600" /> Inbound Logistics Dispatch Required</span>
                    <p className="text-[10px] text-blue-800 font-normal mt-0.5">
                      Platform TransporterAgent will coordinate multi-modal freight from farm gate to your facility.
                    </p>
                  </label>
                </div>

                <div className="p-3.5 bg-purple-50/60 border border-purple-200/70 rounded-xl flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="warehouse_req"
                    checked={warehouseRequired}
                    onChange={(e) => setWarehouseRequired(e.target.checked)}
                    className="w-4 h-4 text-purple-600 rounded border-slate-300 focus:ring-purple-500 mt-0.5"
                  />
                  <label htmlFor="warehouse_req" className="font-semibold text-purple-950 cursor-pointer">
                    <span className="flex items-center gap-1.5"><Warehouse size={14} className="text-purple-600" /> Cold Storage / Buffer Warehousing Required</span>
                    <p className="text-[10px] text-purple-800 font-normal mt-0.5">
                      Temporary WDRA-accredited warehousing space for staged processing delivery.
                    </p>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 5: Pricing Strategy & AI Market Intelligence ── */}
          {currentStep === 5 && (
            <div className="space-y-5 animate-in slide-in-from-right-3 duration-200">
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">5. Pricing Strategy & AI Market Intelligence</h4>
                <p className="text-slate-500">Autonomous ML valuation and economic guardrails for your Buyer Agent.</p>
              </div>

              {/* AI Market Intel Banner */}
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-950 flex items-center gap-1.5">
                    <Bot size={16} className="text-emerald-700" /> AI Market Intelligence ({crop})
                  </span>
                  <span className="px-2 py-0.5 bg-emerald-200/80 text-emerald-900 rounded font-bold text-[10px]">
                    {aiIntel?.trend || 'Stable'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-100">
                    <span className="text-slate-400 text-[10px]">Live APMC Modal Price:</span>
                    <p className="text-sm font-bold text-slate-900">₹{aiIntel?.current_price || '--'}/kg</p>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-emerald-100">
                    <span className="text-slate-400 text-[10px]">7-Day ML Forecast:</span>
                    <p className="text-sm font-bold text-emerald-700">₹{aiIntel?.forecast_7day || '--'}/kg</p>
                  </div>
                </div>

                <p className="text-[11px] text-emerald-900 mt-2.5 leading-relaxed font-medium">
                  {aiIntel?.ai_advice || 'Loading XGBoost pricing forecast...'}
                </p>
              </div>

              {/* Target & Ceiling Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Buyer Target Purchase Price (₹/kg) *
                  </label>
                  <p className="text-[10px] text-slate-400 mb-1.5">Target opening settlement benchmark</p>
                  <input
                    type="number"
                    step="0.5"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(Number(e.target.value))}
                    className="w-full form-input text-xs rounded-xl bg-emerald-50/40 border-emerald-300 font-bold text-slate-900 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Maximum Ceiling Price (₹/kg) *
                  </label>
                  <p className="text-[10px] text-slate-400 mb-1.5">Strict walk-away ceiling safeguard</p>
                  <input
                    type="number"
                    step="0.5"
                    value={maxCeilingPrice}
                    onChange={(e) => setMaxCeilingPrice(Number(e.target.value))}
                    className="w-full form-input text-xs rounded-xl bg-slate-50 border-slate-300 font-bold text-slate-900 focus:ring-slate-500"
                  />
                </div>
              </div>

              {/* Total Budget Preview */}
              <div className="p-3 bg-slate-100 rounded-xl flex justify-between items-center text-slate-700">
                <span>Maximum Total Budget Commitment:</span>
                <span className="font-bold text-slate-900 text-sm">
                  ₹{(quantity * maxCeilingPrice).toLocaleString()}
                </span>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center">
          {currentStep > 1 ? (
            <button
              onClick={handlePrev}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 flex items-center gap-1"
            >
              <ChevronLeft size={16} /> Back
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
          )}

          {currentStep < totalSteps ? (
            <button
              onClick={handleNext}
              className="px-5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-sm flex items-center gap-1 transition"
            >
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-6 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md flex items-center gap-2 transition disabled:opacity-50"
            >
              {isSubmitting ? (
                <>Submitting...</>
              ) : (
                <>
                  <Sparkles size={14} className="text-amber-300" />
                  Submit to AI Matcher & Validator
                </>
              )}
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
