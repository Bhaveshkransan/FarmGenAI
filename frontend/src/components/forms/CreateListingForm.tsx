import React, { useState, useEffect } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { X, Sprout, Loader2, CheckCircle2, TrendingUp, BrainCircuit, MapPin } from 'lucide-react';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { api } from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';
import ChartCard from '../ui/ChartCard';

const CROP_CATEGORIES = ['Grains', 'Oilseeds', 'Cash Crops', 'Vegetables', 'Pulses', 'Fruits', 'Spices'];
const QUALITY_GRADES = ['Premium (A+)', 'Grade A', 'Grade B', 'Grade C (Processing)'];

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
  { name: 'Sugarcane', image: '/crops/sugarcane.jpg' },
  { name: 'Soybean', image: '/crops/soybean.jpg' },
  { name: 'Cotton', image: '/crops/cotton.jpg' },
  { name: 'Jowar', image: '/crops/jowar.jpg' },
  { name: 'Onion', image: '/crops/onion.jpg' },
  { name: 'Bajra', image: '/crops/bajra.jpg' },
  { name: 'Rice', image: '/crops/rice.jpg' }
];

const MAHARASHTRA_DISTRICTS = [
  'Ahmednagar', 'Akola', 'Amravati', 'Aurangabad', 'Beed', 'Bhandara', 'Buldhana', 
  'Chandrapur', 'Dhule', 'Gadchiroli', 'Gondia', 'Hingoli', 'Jalgaon', 'Jalna', 
  'Kolhapur', 'Latur', 'Mumbai City', 'Mumbai Suburban', 'Nagpur', 'Nanded', 
  'Nandurbar', 'Nashik', 'Osmanabad', 'Palghar', 'Parbhani', 'Pune', 'Raigad', 
  'Ratnagiri', 'Sangli', 'Satara', 'Sindhudurg', 'Solapur', 'Thane', 'Wardha', 
  'Washim', 'Yavatmal'
];

const listingSchema = z.object({
  crop: z.enum(['Sugarcane', 'Soybean', 'Cotton', 'Jowar', 'Onion', 'Bajra', 'Rice']),
  crop_category: z.string(),
  variety: z.string().min(1, 'Variety is required'),
  grade: z.string(),
  quantity: z.number().positive('Quantity must be greater than 0'),
  unit: z.string(),
  min_sale_quantity: z.number().positive('Minimum sale quantity must be greater than 0'),
  expected_price: z.number().positive('Expected price must be greater than 0'),
  min_price: z.number().positive('Minimum acceptable price must be greater than 0'),
  price_unit: z.string(),
  isOrganic: z.boolean(),
  moisture: z.number().min(0).max(100).optional(),
  harvest_date: z.string().optional(),
  availability_date: z.string().optional(),
  preferred_selling_date: z.string().optional(),
  shelf_life: z.number().positive('Shelf life must be valid'),
  village: z.string().min(1, 'Village is required'),
  taluka: z.string().min(1, 'Taluka is required'),
  district: z.string().min(1, 'District is required'),
  state: z.string(),
  req_full_logistics: z.boolean(),
  req_buyer_match: z.boolean(),
  req_transport: z.boolean(),
  req_warehouse: z.boolean(),
  req_processor: z.boolean(),
  description: z.string().optional()
}).refine(data => data.min_sale_quantity <= data.quantity, {
  message: "Minimum sale qty cannot be > total quantity",
  path: ["min_sale_quantity"]
}).refine(data => data.min_price <= data.expected_price, {
  message: "Minimum price cannot be > expected price",
  path: ["min_price"]
});

export default function CreateListingForm({ isOpen, onClose, onSuccess }) {
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [insight, setInsight] = useState(null);
  const [isInsightLoading, setIsInsightLoading] = useState(false);

  const methods = useForm({
    resolver: zodResolver(listingSchema),
    defaultValues: {
      crop: 'Soybean',
      crop_category: 'Oilseeds',
      variety: '',
      grade: 'Grade A',
      quantity: 500,
      unit: 'kg',
      min_sale_quantity: 50,
      expected_price: 70,
      min_price: 65,
      price_unit: 'per_kg',
      isOrganic: false,
      moisture: 0,
      harvest_date: '',
      availability_date: '',
      preferred_selling_date: '',
      shelf_life: 7,
      village: '',
      taluka: '',
      district: 'Nashik',
      state: 'Maharashtra',
      req_full_logistics: false,
      req_buyer_match: false,
      req_transport: false,
      req_warehouse: false,
      req_processor: false,
      description: ''
    }
  });

  const { register, handleSubmit, formState: { errors }, watch, reset, setValue } = methods;

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      const selected_services = {
        market_intelligence: true,
        negotiation: true,
        quality_inspection: true,
        buyer_matching: data.req_full_logistics || data.req_buyer_match,
        transport: data.req_full_logistics || data.req_transport,
        warehouse: data.req_full_logistics || data.req_warehouse,
        processor: data.req_full_logistics || data.req_processor
      };

      const payload = {
        crop: data.crop,
        crop_category: data.crop_category,
        variety: data.variety,
        grade: data.grade,
        quantity: data.quantity,
        unit: data.unit,
        min_sale_quantity: data.min_sale_quantity,
        expected_price: data.expected_price,
        min_price: data.min_price,
        price_unit: data.price_unit,
        quality_info: { isOrganic: data.isOrganic, moisture: data.moisture },
        harvest_date: data.harvest_date,
        availability_date: data.availability_date,
        preferred_selling_date: data.preferred_selling_date,
        shelf_life: data.shelf_life,
        location: `${data.village}, ${data.taluka}, ${data.district}`,
        storage_info: { available: false },
        processing_info: { available: false },
        selected_services,
        images: [], // Images handled internally via catalog ID implicitly
        description: data.description
      };

      await api.post('/listings/', payload);
      addNotification('success', 'Comprehensive listing submitted successfully.');
      reset();
      onSuccess?.();
      onClose();
    } catch (err) {
      addNotification('error', err.response?.data?.detail || 'Failed to submit listing');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formData = watch();
  const selectedCrop = watch('crop');
  const selectedDistrict = watch('district');

  const [isLocating, setIsLocating] = useState(false);

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
          // Using nominatim reverse geocoding API
          const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10`);
          const data = await response.json();
          
          if (data && data.address) {
            const state = data.address.state || 'Maharashtra';
            let district = data.address.state_district || data.address.county || 'Pune';
            district = district.replace(' District', '');
            const taluka = data.address.county || data.address.suburb || data.address.city_district || 'Haveli';
            const village = data.address.village || data.address.town || data.address.suburb || data.address.city || 'Local Farm';

            // Check if district is in our allowed list, otherwise default to Pune
            if (!MAHARASHTRA_DISTRICTS.includes(district)) {
              district = MAHARASHTRA_DISTRICTS.find(d => district.includes(d)) || 'Pune';
            }

            methods.setValue('state', state, { shouldValidate: true });
            methods.setValue('district', district, { shouldValidate: true });
            methods.setValue('taluka', taluka, { shouldValidate: true });
            methods.setValue('village', village, { shouldValidate: true });
            
            addNotification('Location detected successfully!', 'success');
          }
        } catch (error) {
          console.error("Geocoding failed:", error);
          addNotification('Failed to detect precise address. Please enter manually.', 'error');
        } finally {
          setIsLocating(false);
        }
      },
      (error) => {
        console.error("Geolocation error:", error);
        addNotification('Location access denied or unavailable.', 'error');
        setIsLocating(false);
      }
    );
  };

  // Automatically request permission and fetch location as soon as listing modal is opened
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

  useEffect(() => {
    if (!selectedCrop) return;
    
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
    
    const timer = setTimeout(fetchInsight, 800);
    return () => clearTimeout(timer);
  }, [selectedCrop, selectedDistrict]);

  // Auto-update pricing when real market intelligence price loads
  useEffect(() => {
    if (insight && insight.live_price > 0) {
      const live = Number(insight.live_price);
      setValue('expected_price', Number((live * 1.05).toFixed(1)), { shouldValidate: true });
      setValue('min_price', Number((live * 0.95).toFixed(1)), { shouldValidate: true });
    }
  }, [insight?.crop, insight?.live_price, setValue]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50 sticky top-0 z-10">
          <div>
            <h3 className="font-bold text-slate-800 flex items-center gap-2 text-lg">
              <Sprout size={20} className="text-emerald-600" /> New Crop Listing
            </h3>
            <p className="text-xs text-slate-500 mt-1">Fill out the details below to list your crop</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition bg-white p-2 rounded-full shadow-sm border border-slate-100">
            <X size={20} />
          </button>
        </div>
        
        {/* Scrollable Form Body */}
        <div className="overflow-y-auto flex-1 p-6 sm:p-8 bg-white">
          <FormProvider {...methods}>
            <form id="listing-form" onSubmit={handleSubmit(onSubmit)} className="space-y-10">
              
              {/* Visual Crop Selection */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">1. Select Crop</h4>
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
                        <div className={`p-2 text-center text-sm font-semibold ${isSelected ? 'bg-emerald-50 text-emerald-800 font-bold' : 'bg-white text-slate-700'}`}>
                          {c.name}
                        </div>
                      </div>
                    )
                  })}
                </div>
                {errors.crop && <p className="text-red-500 text-xs mt-1">{errors.crop.message as string}</p>}
              </div>

              {/* Crop Information */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">2. Crop Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Category *</label>
                    <select {...register('crop_category')} className="w-full form-input bg-slate-50">
                      {CROP_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="md:col-span-1">
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Specific Variety *</label>
                    <input {...register('variety')} placeholder="e.g. Nashik Red, Shriram" className="w-full form-input bg-slate-50" />
                    {errors.variety && <p className="text-red-500 text-xs mt-1">{errors.variety.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* Quantity Details */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">3. Quantity Details</h4>
                <div className="grid grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Total Available *</label>
                    <input type="number" {...register('quantity', { valueAsNumber: true })} className="w-full form-input bg-slate-50" />
                    {errors.quantity && <p className="text-red-500 text-xs mt-1">{errors.quantity.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Unit *</label>
                    <select {...register('unit')} className="w-full form-input bg-slate-50">
                      <option value="kg">Kilograms (kg)</option>
                      <option value="quintal">Quintals</option>
                      <option value="ton">Metric Tons (MT)</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Minimum Sale Quantity *</label>
                    <p className="text-xs text-slate-500 mb-2">The smallest amount you are willing to sell to a single buyer.</p>
                    <input type="number" {...register('min_sale_quantity', { valueAsNumber: true })} className="w-full form-input bg-slate-50" />
                    {errors.min_sale_quantity && <p className="text-red-500 text-xs mt-1">{errors.min_sale_quantity.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* Quality Parameters */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">4. Quality Parameters</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Quality Grade *</label>
                    <select {...register('grade')} className="w-full form-input bg-slate-50">
                      {QUALITY_GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Moisture Content (%)</label>
                    <input type="number" {...register('moisture', { valueAsNumber: true })} placeholder="Optional" className="w-full form-input bg-slate-50" />
                  </div>
                  <div className="md:col-span-2 flex items-center gap-3 p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                    <input type="checkbox" id="organic" {...register('isOrganic')} className="w-5 h-5 text-emerald-600 rounded" />
                    <label htmlFor="organic" className="font-medium text-emerald-900 cursor-pointer">Certified Organic Produce</label>
                  </div>
                </div>
              </div>

              {/* Pricing Strategy */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">5. Pricing Strategy</h4>
                
                {/* AI Market Intelligence Box */}
                <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100 rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 text-emerald-800 font-bold mb-2">
                    <BrainCircuit size={18} />
                    <h3>AI Market Intelligence</h3>
                    {isInsightLoading && <Loader2 size={14} className="animate-spin ml-2 text-emerald-600" />}
                  </div>
                  {!isInsightLoading && insight ? (
                    <div className="text-sm text-slate-700 space-y-3">
                      {/* Price Row */}
                      <div className="flex items-center flex-wrap gap-2">
                        <span className="bg-emerald-100 text-emerald-800 px-2 py-1 rounded-md font-semibold text-xs">
                          Live Price: ₹{insight.live_price}/kg
                        </span>
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md font-semibold text-xs flex items-center gap-1">
                          <TrendingUp size={12} /> Trend: {insight.trend}
                        </span>
                        {insight.ml_forecast_price && (
                          <span className={`px-2 py-1 rounded-md font-semibold text-xs flex items-center gap-1 ${insight.ml_forecast_direction === 'up' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {insight.ml_forecast_direction === 'up' ? '▲' : '▼'} 7-Day Forecast: ₹{insight.ml_forecast_price}/kg
                          </span>
                        )}
                      </div>
                      {/* LLM Recommendation */}
                      <p className="bg-white/60 p-3 rounded-lg border border-emerald-100 font-medium">
                        <span className="text-emerald-700 font-bold mr-1">AI Advice:</span> 
                        {insight.recommendation}
                      </p>
                      
                      {/* Price Trend Chart */}
                      {insight.chart_data && insight.chart_data.length > 0 && (
                        <div className="mt-4 bg-white p-3 rounded-xl border border-emerald-100 shadow-sm">
                          <ChartCard 
                            title={`${selectedCrop} Price Forecast (Next 7 Days)`} 
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
                    <p className="text-xs text-slate-500 animate-pulse">Analyzing regional datasets and historical patterns for {selectedCrop}...</p>
                  ) : null}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Expected Target Price (₹) *</label>
                    <input type="number" step="any" {...register('expected_price', { valueAsNumber: true })} className="w-full form-input bg-slate-50 border-blue-200 focus:ring-blue-500" />
                    {errors.expected_price && <p className="text-red-500 text-xs mt-1">{errors.expected_price.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Minimum Acceptable Price (₹) *</label>
                    <input type="number" step="any" {...register('min_price', { valueAsNumber: true })} className="w-full form-input bg-slate-50 border-red-200 focus:ring-red-500" />
                    {errors.min_price && <p className="text-red-500 text-xs mt-1">{errors.min_price.message as string}</p>}
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Pricing Unit *</label>
                    <select {...register('price_unit')} className="w-full form-input bg-slate-50">
                      <option value="per_kg">Per kg</option>
                      <option value="per_quintal">Per quintal</option>
                      <option value="per_ton">Per ton (MT)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Farm Location */}
              <div className="space-y-4">
                <div className="flex justify-between items-center border-b pb-2">
                  <h4 className="text-lg font-bold text-slate-800">6. Farm Location</h4>
                  <button 
                    type="button" 
                    onClick={handleFetchLocation}
                    disabled={isLocating}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-semibold hover:bg-blue-100 transition disabled:opacity-50"
                  >
                    {isLocating ? <Loader2 size={16} className="animate-spin" /> : <MapPin size={16} />}
                    {isLocating ? 'Locating...' : 'Detect Location'}
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Village / Locality *</label>
                    <input {...register('village')} className="w-full form-input bg-slate-50" />
                    {errors.village && <p className="text-red-500 text-xs mt-1">{errors.village.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Taluka *</label>
                    <input {...register('taluka')} className="w-full form-input bg-slate-50" />
                    {errors.taluka && <p className="text-red-500 text-xs mt-1">{errors.taluka.message as string}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">District *</label>
                    <select {...register('district')} className="w-full form-input bg-slate-50">
                      {MAHARASHTRA_DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">State *</label>
                    <input {...register('state')} placeholder="e.g. Maharashtra" className="w-full form-input bg-slate-50 text-slate-800" />
                    {errors.state && <p className="text-red-500 text-xs mt-1">{errors.state.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* Harvest & Timeline */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">7. Harvest & Timeline</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Date of Harvest</label>
                    <input type="date" {...register('harvest_date')} className="w-full form-input bg-slate-50" />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Date Available for Pickup</label>
                    <input type="date" {...register('availability_date')} className="w-full form-input bg-slate-50" />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Estimated Shelf Life (Days) *</label>
                    <input type="number" {...register('shelf_life', { valueAsNumber: true })} className="w-full form-input bg-slate-50" />
                    {errors.shelf_life && <p className="text-red-500 text-xs mt-1">{errors.shelf_life.message as string}</p>}
                  </div>
                </div>
              </div>

              {/* Supply Chain Services */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-slate-800 border-b pb-2">8. Optional Logistics Assistance</h4>
                
                <p className="text-sm text-slate-600 mb-3">
                  Matching, Quality Checks, and AI Negotiation are included by default. Do you need help with finding buyers or physical logistics?
                </p>

                <label className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl border border-blue-200 cursor-pointer mb-4">
                  <input type="checkbox" {...register('req_full_logistics')} className="w-5 h-5 text-blue-600 rounded" />
                  <div>
                    <p className="font-bold text-blue-900">Full Logistics Assistance</p>
                    <p className="text-sm text-blue-700">Let AI handle finding buyers, booking transport, matching warehouses, and processors.</p>
                  </div>
                </label>
                
                {!formData.req_full_logistics && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('req_buyer_match')} className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" /> 
                      <span className="font-medium text-slate-700">Buyer Agent</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('req_transport')} className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" /> 
                      <span className="font-medium text-slate-700">Transport Agent</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('req_warehouse')} className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" /> 
                      <span className="font-medium text-slate-700">Warehouse Matching</span>
                    </label>
                    <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('req_processor')} className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500" /> 
                      <span className="font-medium text-slate-700">Processor Matching</span>
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
            className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold rounded-xl transition disabled:opacity-30 flex items-center gap-2 shadow-sm"
          >
            Cancel
          </button>
          
          <button 
            type="submit" 
            form="listing-form"
            disabled={isSubmitting} 
            className="px-8 py-2.5 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl transition shadow-md"
          >
            {isSubmitting ? <><Loader2 size={18} className="animate-spin" /> Submitting...</> : 'Submit to AI Validator'}
          </button>
        </div>

      </div>
    </div>
  );
}
