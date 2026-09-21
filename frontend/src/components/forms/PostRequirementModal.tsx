import React, { useState, useEffect } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { 
  X, 
  Target, 
  Loader2, 
  CheckCircle2, 
  TrendingUp, 
  BrainCircuit, 
  MapPin, 
  Building2, 
  Layers, 
  Truck, 
  Warehouse, 
  ShieldCheck,
  Bot
} from 'lucide-react';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import { useNotification } from '@/contexts/NotificationContext';
import ChartCard from '../ui/ChartCard';

const CROP_CATEGORIES = ['Grains', 'Oilseeds', 'Cash Crops', 'Vegetables', 'Pulses', 'Fruits', 'Spices'];
const QUALITY_GRADES = ['Premium (A+)', 'Grade A', 'Grade B', 'Grade C (Processing)', 'Any Grade (Best Value)'];

const PROCUREMENT_PURPOSES = [
  { id: 'food_processing', label: '🏭 Food Processing & Milling' },
  { id: 'oil_extraction', label: '🛢️ Oil Extraction & Solvent Refining' },
  { id: 'ginning_spinning', label: '🧵 Cotton Ginning & Textile Spinning' },
  { id: 'wholesale_trader', label: '🏢 APMC Mandi Wholesale Distribution' },
  { id: 'retail_supermarket', label: '🛒 Supermarket Retail Chain' },
  { id: 'restaurant', label: '🍽️ Restaurant & Cloud Kitchen Chain' },
  { id: 'institutional', label: '🏫 Institutional & Govt Supply' },
];

const CROP_DEFAULT_CATEGORY: Record<string, string> = {
  'Sugarcane': 'Cash Crops',
  'Soybean': 'Oilseeds',
  'Cotton': 'Cash Crops',
  'Jowar': 'Grains',
  'Onion': 'Vegetables',
  'Bajra': 'Grains',
  'Rice': 'Grains'
};

const MAHARASHTRA_CROPS = [
  { name: 'Sugarcane', image: '/crops/sugarcane.jpg', benchmark: '₹3.40/kg FRP' },
  { name: 'Soybean', image: '/crops/soybean.jpg', benchmark: '₹48.92/kg MSP' },
  { name: 'Cotton', image: '/crops/cotton.jpg', benchmark: '₹71.21/kg MSP' },
  { name: 'Jowar', image: '/crops/jowar.jpg', benchmark: '₹33.71/kg MSP' },
  { name: 'Onion', image: '/crops/onion.jpg', benchmark: '₹25.00/kg Modal' },
  { name: 'Bajra', image: '/crops/bajra.jpg', benchmark: '₹26.25/kg MSP' },
  { name: 'Rice', image: '/crops/rice.jpg', benchmark: '₹23.00/kg MSP' }
];

const MAHARASHTRA_DISTRICTS = [
  'Ahmednagar', 'Akola', 'Amravati', 'Aurangabad', 'Beed', 'Bhandara', 'Buldhana', 
  'Chandrapur', 'Dhule', 'Gadchiroli', 'Gondia', 'Hingoli', 'Jalgaon', 'Jalna', 
  'Kolhapur', 'Latur', 'Mumbai City', 'Mumbai Suburban', 'Nagpur', 'Nanded', 
  'Nandurbar', 'Nashik', 'Osmanabad', 'Palghar', 'Parbhani', 'Pune', 'Raigad', 
  'Ratnagiri', 'Sangli', 'Satara', 'Sindhudurg', 'Solapur', 'Thane', 'Wardha', 
  'Washim', 'Yavatmal'
];

const procurementSchema = z.object({
  crop: z.enum(['Sugarcane', 'Soybean', 'Cotton', 'Jowar', 'Onion', 'Bajra', 'Rice']),
  crop_category: z.string(),
  variety: z.string().min(1, 'Variety is required'),
  purpose: z.string(),
  grade: z.string(),
  quantity: z.number().positive('Quantity must be greater than 0'),
  unit: z.string(),
  min_batch_size: z.number().positive('Minimum batch size must be greater than 0'),
  expected_price: z.number().positive('Expected target price must be greater than 0'),
  max_price: z.number().positive('Maximum acceptable price must be greater than 0'),
  price_unit: z.string(),
  isOrganic: z.boolean(),
  moisture: z.number().min(0).max(100).optional(),
  delivery_deadline: z.string().optional(),
  earliest_delivery: z.string().optional(),
  shelf_life: z.number().positive('Shelf life / urgency must be valid').optional(),
  delivery_hub: z.string().min(1, 'Hub / locality is required'),
  taluka: z.string().min(1, 'Taluka is required'),
  district: z.string().min(1, 'District is required'),
  state: z.string(),
  req_full_logistics: z.boolean(),
  req_farmer_match: z.boolean(),
  req_transport: z.boolean(),
  req_warehouse: z.boolean(),
  req_quality: z.boolean(),
  description: z.string().optional()
}).refine(data => data.min_batch_size <= data.quantity, {
  message: "Minimum batch size cannot exceed total procurement quantity",
  path: ["min_batch_size"]
}).refine(data => data.expected_price <= data.max_price, {
  message: "Target price cannot exceed maximum reservation budget",
  path: ["max_price"]
});

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
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [insight, setInsight] = useState<any>(null);
  const [isInsightLoading, setIsInsightLoading] = useState(false);
  const [isLocating, setIsLocating] = useState(false);

  const methods = useForm({
    resolver: zodResolver(procurementSchema),
    defaultValues: {
      crop: (initialCrop as any) || 'Soybean',
      crop_category: CROP_DEFAULT_CATEGORY[initialCrop] || 'Oilseeds',
      variety: 'Commercial Lot',
      purpose: 'food_processing',
      grade: 'Grade A',
      quantity: 5000,
      unit: 'kg',
      min_batch_size: 500,
      expected_price: 48,
      max_price: 52,
      price_unit: 'per_kg',
      isOrganic: false,
      moisture: 10,
      delivery_deadline: '',
      earliest_delivery: '',
      shelf_life: 30,
      delivery_hub: 'Hadapsar Processing Center',
      taluka: 'Haveli',
      district: 'Pune',
      state: 'Maharashtra',
      req_full_logistics: false,
      req_farmer_match: true,
      req_transport: true,
      req_warehouse: false,
      req_quality: true,
      description: ''
    }
  });

  const { register, handleSubmit, formState: { errors }, watch, reset, setValue } = methods;
  const formData = watch();
  const selectedCrop = watch('crop');
  const selectedDistrict = watch('district');
  const currentQuantity = watch('quantity');

  // Live GPS Geolocation Detection via HTML5 Geolocation + OpenStreetMap Nominatim
  const handleFetchLocation = () => {
    setIsLocating(true);
    if (!navigator.geolocation) {
      addNotification('Geolocation is not supported by your browser', 'error');
      setIsLocating(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10`
          );
          const data = await response.json();
          
          if (data && data.address) {
            const state = data.address.state || 'Maharashtra';
            let district = data.address.state_district || data.address.county || 'Pune';
            district = district.replace(' District', '').trim();
            const taluka = data.address.county || data.address.suburb || data.address.city_district || 'Haveli';
            const village = data.address.village || data.address.town || data.address.suburb || data.address.city || 'Central Procurement Facility';

            if (!MAHARASHTRA_DISTRICTS.includes(district)) {
              district = MAHARASHTRA_DISTRICTS.find(d => district.includes(d)) || 'Pune';
            }

            setValue('state', state, { shouldValidate: true });
            setValue('district', district, { shouldValidate: true });
            setValue('taluka', taluka, { shouldValidate: true });
            setValue('delivery_hub', village, { shouldValidate: true });
            
            addNotification('Live GPS location detected successfully!', 'success');
          }
        } catch (error) {
          console.error("Geocoding failed:", error);
          addNotification('Failed to detect precise address. Please select district manually.', 'error');
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error("Geolocation error:", error);
        addNotification('Location access denied or unavailable. Using default Maharashtra hub.', 'info');
        setIsLocating(false);
      }
    );
  };

  // Automatically request permission and fetch location as soon as modal is opened!
  useEffect(() => {
    if (isOpen) {
      handleFetchLocation();
    }
  }, [isOpen]);

  // Auto-adapt Category whenever selected Crop changes
  useEffect(() => {
    if (selectedCrop && CROP_DEFAULT_CATEGORY[selectedCrop]) {
      setValue('crop_category', CROP_DEFAULT_CATEGORY[selectedCrop], { shouldValidate: true });
    }
  }, [selectedCrop, setValue]);

  // Fetch real AI Market Intelligence insights & 7-day forecast chart
  useEffect(() => {
    if (!selectedCrop || !isOpen) return;
    
    const fetchInsight = async () => {
      setIsInsightLoading(true);
      try {
        const res = await api.get(`/market-intelligence/insights?crop=${selectedCrop}&location=${selectedDistrict || 'Maharashtra'}`);
        if (res.data?.success) {
          setInsight(res.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch market insight", err);
      } finally {
        setIsInsightLoading(false);
      }
    };
    
    const timer = setTimeout(fetchInsight, 600);
    return () => clearTimeout(timer);
  }, [selectedCrop, selectedDistrict, isOpen]);

  // Auto-update price defaults when real market intelligence price loads
  useEffect(() => {
    if (insight && insight.live_price > 0) {
      const live = Number(insight.live_price);
      // For buyer: Target price is 4% under market, Max acceptable ceiling is 8% over market
      setValue('expected_price', Number((live * 0.96).toFixed(1)), { shouldValidate: true });
      setValue('max_price', Number((live * 1.08).toFixed(1)), { shouldValidate: true });
    }
  }, [insight?.crop, insight?.live_price, setValue]);

  const setPresetQuantity = (qty: number) => {
    setValue('quantity', qty, { shouldValidate: true });
    setValue('min_batch_size', Math.min(qty, Math.max(10, Math.floor(qty / 2))), { shouldValidate: true });
  };

  const onSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      const selected_services = {
        market_intelligence: true,
        negotiation: true,
        quality_inspection: data.req_full_logistics || data.req_quality,
        farmer_matching: data.req_full_logistics || data.req_farmer_match,
        transport: data.req_full_logistics || data.req_transport,
        warehouse: data.req_full_logistics || data.req_warehouse
      };

      const payload = {
        crop: data.crop,
        crop_category: data.crop_category,
        variety: data.variety,
        purpose: data.purpose,
        grade: data.grade,
        quality_grade: data.grade,
        quality: data.grade,
        quantity: data.quantity,
        unit: data.unit,
        min_sale_quantity: data.min_batch_size,
        min_batch_size: data.min_batch_size,
        target_price: data.expected_price,
        expected_price: data.expected_price,
        max_price: data.max_price,
        maxBudget: data.max_price,
        budget: data.quantity * data.max_price,
        price_unit: data.price_unit,
        isOrganic: data.isOrganic,
        is_organic: data.isOrganic,
        moisture: data.moisture,
        max_moisture: data.moisture,
        delivery_deadline: data.delivery_deadline,
        deliveryDate: data.delivery_deadline,
        earliest_delivery: data.earliest_delivery,
        shelf_life: data.shelf_life || 30,
        location: `${data.delivery_hub}, ${data.taluka}, ${data.district}, Maharashtra`,
        preferredLocation: `${data.district}, Maharashtra`,
        selected_services,
        transport_required: data.req_full_logistics || data.req_transport,
        transportRequired: data.req_full_logistics || data.req_transport,
        warehouse_required: data.req_full_logistics || data.req_warehouse,
        storageRequired: data.req_full_logistics || data.req_warehouse,
        buyer_mode: true,
        max_rounds: 5,
        description: data.description || '',
        notes: data.description || ''
      };

      const res = await api.post('/requirements', payload);
      const reqData = res.data?.data || res.data;
      const reqId = reqData?.id || reqData?.requirement_id;

      // Automatically launch the Autonomous AI Negotiation session for this requirement
      let negId: string | null = null;
      try {
        const startNegPayload = {
          crop: data.crop,
          quantity: Number(data.quantity) || 1000,
          min_price: Number(data.expected_price) || 20,
          shelf_life: Number(data.shelf_life) || 30,
          location: `${data.delivery_hub || data.district}, Maharashtra`,
          quality: data.grade || 'Grade A',
          buyer_mode: true,
          buyer_name: user?.businessName || user?.name || user?.full_name || 'Buyer Enterprise',
          buyer_budget: Number(data.quantity) * Number(data.max_price || data.expected_price * 1.08),
          buyer_max_quantity: Number(data.quantity) || 1000,
          buyer_target_price: Number(data.expected_price),
          buyer_location: `${data.district}, Maharashtra`,
          buyer_strategy: data.purpose || 'Balanced',
          buyer_persona: data.purpose ? `Commercial ${data.purpose}` : 'Balanced Corporate Buyer',
          max_rounds: 5,
          requirement_id: reqId
        };

        const negRes = await api.post('/negotiations/start-negotiation', startNegPayload);
        negId = negRes.data?.negotiation_id || negRes.data?.id;
      } catch (negErr) {
        console.warn('Auto start negotiation error:', negErr);
      }

      addNotification('Procurement requirement published! Directing to AI Negotiation Room...', 'success');
      reset();
      onSuccess?.({ ...reqData, negId });
      onClose();

      if (negId) {
        navigate(`/negotiations/${negId}`);
      }
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to submit procurement requirement', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50 sticky top-0 z-10">
          <div>
            <h3 className="font-bold text-slate-800 flex items-center gap-2 text-lg">
              <Target size={20} className="text-blue-600" /> New Procurement Requirement
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Publish your commercial demand across Maharashtra APMC mandis & direct farmer networks
            </p>
          </div>
          <button 
            onClick={onClose} 
            className="text-slate-400 hover:text-slate-600 transition bg-white p-2 rounded-full shadow-sm border border-slate-100 cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Scrollable Form Body */}
        <div className="overflow-y-auto flex-1 p-6 sm:p-8 bg-white">
          <FormProvider {...methods}>
            <form id="procurement-form" onSubmit={handleSubmit(onSubmit)} className="space-y-10">
              
              {/* 1. Visual Crop Selection */}
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b pb-2">
                  <h4 className="text-lg font-bold text-slate-800">1. Select Commodity Crop</h4>
                  <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100">
                    7 Maharashtra Canonical Crops
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                  {MAHARASHTRA_CROPS.map(c => {
                    const isSelected = selectedCrop === c.name;
                    return (
                      <div 
                        key={c.name}
                        onClick={() => {
                          setValue('crop', c.name as any, { shouldValidate: true });
                          if (CROP_DEFAULT_CATEGORY[c.name]) {
                            setValue('crop_category', CROP_DEFAULT_CATEGORY[c.name], { shouldValidate: true });
                          }
                        }}
                        className={`cursor-pointer rounded-xl overflow-hidden border-2 transition-all duration-200 ${
                          isSelected 
                            ? 'border-emerald-500 ring-2 ring-emerald-200 shadow-md scale-105' 
                            : 'border-slate-200 hover:border-emerald-400 opacity-100 shadow-sm hover:shadow'
                        }`}
                      >
                        <div className="h-24 w-full bg-slate-100 relative overflow-hidden">
                          <img 
                            src={c.image} 
                            alt={c.name} 
                            className="w-full h-full object-cover transition-transform duration-200 hover:scale-105" 
                          />
                          {isSelected && (
                            <div className="absolute top-1 right-1 bg-emerald-500 text-white rounded-full p-0.5 shadow">
                              <CheckCircle2 size={16} />
                            </div>
                          )}
                        </div>
                        <div className={`p-2 text-center text-xs font-semibold ${isSelected ? 'bg-emerald-50 text-emerald-800 font-bold' : 'bg-white text-slate-700'}`}>
                          <div>{c.name}</div>
                          <span className="text-[10px] text-slate-400 block font-normal">{c.benchmark}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {errors.crop && <p className="text-red-500 text-xs mt-1">{errors.crop.message as string}</p>}
              </div>

              {/* 2. Procurement Specifications */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">2. Procurement Specifications</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Category *</label>
                    <select {...register('crop_category')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      {CROP_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Commercial Variety *</label>
                    <input 
                      {...register('variety')} 
                      placeholder="e.g. Nashik Red, Shriram, Commercial Grade" 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    {errors.variety && <p className="text-red-500 text-xs mt-1">{errors.variety.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Commercial Purpose / Sector *</label>
                    <select {...register('purpose')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      {PROCUREMENT_PURPOSES.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* 3. Quantity Details */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">3. Volume & Lot Batching</h4>
                
                {/* Volume Quick Presets */}
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-slate-500 mr-1">Quick Presets:</span>
                  {[
                    { label: '120 kg (Kitchen/Sample)', val: 120 },
                    { label: '500 kg (Micro Lot)', val: 500 },
                    { label: '1,000 kg (1 Ton)', val: 1000 },
                    { label: '5,000 kg (5 Tons)', val: 5000 },
                    { label: '10,000 kg (10 Tons)', val: 10000 }
                  ].map(p => (
                    <button
                      key={p.val}
                      type="button"
                      onClick={() => setPresetQuantity(p.val)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                        Number(currentQuantity) === p.val 
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm' 
                          : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Total Required Volume *</label>
                    <input 
                      type="number" 
                      {...register('quantity', { valueAsNumber: true })} 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    {errors.quantity && <p className="text-red-500 text-xs mt-1">{errors.quantity.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Measurement Unit *</label>
                    <select {...register('unit')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      <option value="kg">Kilograms (kg)</option>
                      <option value="quintal">Quintals (100 kg)</option>
                      <option value="ton">Metric Tons (MT)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Minimum Batch Acceptance Size *</label>
                    <input 
                      type="number" 
                      {...register('min_batch_size', { valueAsNumber: true })} 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    <p className="text-[11px] text-slate-400 mt-1">Smallest consignment accepted from an individual seller</p>
                    {errors.min_batch_size && <p className="text-red-500 text-xs mt-1">{errors.min_batch_size.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* 4. Quality Parameters */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">4. Quality Parameters</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Acceptable Quality Grade *</label>
                    <select {...register('grade')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      {QUALITY_GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Maximum Moisture Content (%)</label>
                    <input 
                      type="number" 
                      {...register('moisture', { valueAsNumber: true })} 
                      placeholder="e.g. 10" 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                  </div>
                  <div className="md:col-span-2 flex items-center gap-3 p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                    <input 
                      type="checkbox" 
                      id="procure-organic" 
                      {...register('isOrganic')} 
                      className="w-5 h-5 text-emerald-600 rounded cursor-pointer" 
                    />
                    <label htmlFor="procure-organic" className="font-medium text-emerald-900 cursor-pointer text-sm">
                      Require Certified Organic Produce (Verified APMC/PGS-India Certification)
                    </label>
                  </div>
                </div>
              </div>

              {/* 5. Pricing Strategy & AI Market Intelligence */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">5. Pricing Strategy & Market Intelligence</h4>
                
                {/* AI Market Intelligence Box */}
                <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100 rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 text-emerald-800 font-bold mb-2">
                    <BrainCircuit size={18} />
                    <h3>AI Market Intelligence (MandiMitra)</h3>
                    {isInsightLoading && <Loader2 size={14} className="animate-spin ml-2 text-emerald-600" />}
                  </div>
                  {!isInsightLoading && insight ? (
                    <div className="text-sm text-slate-700 space-y-3">
                      {/* Price Row */}
                      <div className="flex items-center flex-wrap gap-2">
                        <span className="bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-md font-semibold text-xs">
                          Live APMC Modal: ₹{insight.live_price}/kg
                        </span>
                        <span className="bg-blue-100 text-blue-800 px-2.5 py-1 rounded-md font-semibold text-xs flex items-center gap-1">
                          <TrendingUp size={12} /> Trend: {insight.trend}
                        </span>
                        {insight.ml_forecast_price && (
                          <span className={`px-2.5 py-1 rounded-md font-semibold text-xs flex items-center gap-1 ${
                            insight.ml_forecast_direction === 'up' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {insight.ml_forecast_direction === 'up' ? '▲' : '▼'} 7-Day Forecast: ₹{insight.ml_forecast_price}/kg
                          </span>
                        )}
                      </div>
                      {/* LLM Recommendation */}
                      <p className="bg-white/70 p-3 rounded-lg border border-emerald-100 font-medium text-xs leading-relaxed">
                        <span className="text-emerald-700 font-bold mr-1">AI Buyer Advice:</span> 
                        {insight.recommendation}
                      </p>
                      
                      {/* Price Trend Chart */}
                      {insight.chart_data && insight.chart_data.length > 0 && (
                        <div className="mt-4 bg-white p-3 rounded-xl border border-emerald-100 shadow-sm">
                          <ChartCard 
                            title={`${selectedCrop} Wholesale Price Forecast (Next 7 Days)`} 
                            subtitle="AI projected modal price in ₹/kg based on historical APMC data and market arrivals."
                            data={insight.chart_data} 
                            xKey="date" 
                            yKey="price" 
                            color={insight.ml_forecast_direction === 'up' ? '#10b981' : '#ef4444'}
                            height={160} 
                          />
                        </div>
                      )}
                    </div>
                  ) : isInsightLoading ? (
                    <p className="text-xs text-slate-500 animate-pulse">
                      Analyzing historical APMC auction records, arrival velocities, and ML price predictions for {selectedCrop}...
                    </p>
                  ) : null}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Expected Target Price (₹) *</label>
                    <input 
                      type="number" 
                      step="any" 
                      {...register('expected_price', { valueAsNumber: true })} 
                      className="w-full form-input bg-slate-50 border border-blue-200 focus:ring-blue-500 rounded-xl px-3 py-2 text-sm" 
                    />
                    <p className="text-[11px] text-slate-400 mt-1">Ideal negotiation target price</p>
                    {errors.expected_price && <p className="text-red-500 text-xs mt-1">{errors.expected_price.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Max Reservation Ceiling (₹) *</label>
                    <input 
                      type="number" 
                      step="any" 
                      {...register('max_price', { valueAsNumber: true })} 
                      className="w-full form-input bg-slate-50 border border-red-200 focus:ring-red-500 rounded-xl px-3 py-2 text-sm" 
                    />
                    <p className="text-[11px] text-slate-400 mt-1">Hard buyer cutoff (deals above this are blocked)</p>
                    {errors.max_price && <p className="text-red-500 text-xs mt-1">{errors.max_price.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Pricing Unit *</label>
                    <select {...register('price_unit')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      <option value="per_kg">Per kg (₹/kg)</option>
                      <option value="per_quintal">Per quintal (₹/quintal)</option>
                      <option value="per_ton">Per ton (₹/MT)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* 6. Delivery & Procurement Hub Location */}
              <div className="space-y-4">
                <div className="flex justify-between items-center border-b pb-2">
                  <h4 className="text-lg font-bold text-slate-800">6. Delivery & Procurement Hub Location</h4>
                  <button 
                    type="button" 
                    onClick={handleFetchLocation}
                    disabled={isLocating}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-xs font-semibold hover:bg-blue-100 transition disabled:opacity-50 cursor-pointer shadow-sm border border-blue-200"
                  >
                    {isLocating ? <Loader2 size={15} className="animate-spin" /> : <MapPin size={15} />}
                    {isLocating ? 'Locating via GPS...' : 'Detect Location (Live GPS)'}
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Delivery Facility / Locality *</label>
                    <input 
                      {...register('delivery_hub')} 
                      placeholder="e.g. Hadapsar Processing Hub, MIDC Yard"
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    {errors.delivery_hub && <p className="text-red-500 text-xs mt-1">{errors.delivery_hub.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Taluka *</label>
                    <input 
                      {...register('taluka')} 
                      placeholder="e.g. Haveli, Baramati"
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    {errors.taluka && <p className="text-red-500 text-xs mt-1">{errors.taluka.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">District *</label>
                    <select {...register('district')} className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm">
                      {MAHARASHTRA_DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">State *</label>
                    <input 
                      {...register('state')} 
                      placeholder="e.g. Maharashtra" 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800" 
                    />
                    {errors.state && <p className="text-red-500 text-xs mt-1">{errors.state.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* 7. Fulfillment Schedule & Timeline */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">7. Fulfillment Schedule & Timeline</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Required Delivery Deadline</label>
                    <input 
                      type="date" 
                      {...register('delivery_deadline')} 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Earliest Acceptable Inflow</label>
                    <input 
                      type="date" 
                      {...register('earliest_delivery')} 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Shelf Life Expectation (Days) *</label>
                    <input 
                      type="number" 
                      {...register('shelf_life', { valueAsNumber: true })} 
                      className="w-full form-input bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm" 
                    />
                    {errors.shelf_life && <p className="text-red-500 text-xs mt-1">{errors.shelf_life.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* 8. Supply Chain & Logistics Assistance */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">8. Optional Logistics & Supply Chain Assistance</h4>
                
                <p className="text-xs text-slate-600 mb-3">
                  AI Multi-Agent Negotiation and Statutory MSP/FRP Verification are enabled by default. Select additional ecosystem services:
                </p>

                <label className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl border border-blue-200 cursor-pointer mb-4">
                  <input 
                    type="checkbox" 
                    {...register('req_full_logistics')} 
                    className="w-5 h-5 text-blue-600 rounded cursor-pointer" 
                  />
                  <div>
                    <p className="font-bold text-blue-900 text-sm">Full Turnkey Logistics Dispatch</p>
                    <p className="text-xs text-blue-700">Autonomous multi-agent dispatch: Inbound freight haulage, APMC assaying, and buffer warehousing.</p>
                  </div>
                </label>
                
                {!formData.req_full_logistics && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <label className="flex items-center gap-2.5 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs cursor-pointer hover:bg-slate-100 transition">
                      <input 
                        type="checkbox" 
                        {...register('req_farmer_match')} 
                        className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" 
                      /> 
                      <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                        <Bot size={14} className="text-emerald-600" /> Farmer Sourcing & Seller Matching
                      </span>
                    </label>
                    <label className="flex items-center gap-2.5 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs cursor-pointer hover:bg-slate-100 transition">
                      <input 
                        type="checkbox" 
                        {...register('req_transport')} 
                        className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" 
                      /> 
                      <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                        <Truck size={14} className="text-blue-600" /> Transport Agent (Highway Haulage)
                      </span>
                    </label>
                    <label className="flex items-center gap-2.5 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs cursor-pointer hover:bg-slate-100 transition">
                      <input 
                        type="checkbox" 
                        {...register('req_warehouse')} 
                        className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" 
                      /> 
                      <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                        <Warehouse size={14} className="text-amber-600" /> Warehouse Allocation & Storage
                      </span>
                    </label>
                    <label className="flex items-center gap-2.5 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs cursor-pointer hover:bg-slate-100 transition">
                      <input 
                        type="checkbox" 
                        {...register('req_quality')} 
                        className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" 
                      /> 
                      <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                        <ShieldCheck size={14} className="text-purple-600" /> APMC Quality Assaying & Inspection
                      </span>
                    </label>
                  </div>
                )}
              </div>

            </form>
          </FormProvider>
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-100 flex justify-between bg-slate-50 sticky bottom-0 z-10">
          <button 
            type="button" 
            onClick={onClose} 
            disabled={isSubmitting}
            className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold rounded-xl transition disabled:opacity-30 flex items-center gap-2 shadow-sm text-sm cursor-pointer"
          >
            Cancel
          </button>
          
          <button 
            type="submit" 
            form="procurement-form"
            disabled={isSubmitting} 
            className="px-8 py-2.5 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl transition shadow-md text-sm cursor-pointer active:scale-95"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="animate-spin" /> Submitting to Matching Engine...
              </>
            ) : (
              'Submit to AI Procurement Engine'
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
