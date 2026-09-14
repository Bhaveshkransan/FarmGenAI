import React, { useState } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { X, Sprout, ImagePlus, Loader2, ChevronRight, ChevronLeft, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';
import { TOP_MAHARASHTRA_CROPS } from '../../utils/validation';

const CROP_CATEGORIES = ['Vegetables', 'Fruits', 'Grains', 'Pulses', 'Spices', 'Others'];
const QUALITY_GRADES = ['Premium (A+)', 'Grade A', 'Grade B', 'Grade C (Processing)'];

export default function CreateListingForm({ isOpen, onClose, onSuccess }) {
  const { addNotification } = useNotification();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedImages, setUploadedImages] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  const methods = useForm({
    defaultValues: {
      crop: 'Tomato',
      crop_category: 'Vegetables',
      variety: '',
      grade: 'Grade A',
      quantity: 500,
      unit: 'kg',
      min_sale_quantity: 50,
      expected_price: 20,
      min_price: 18,
      price_unit: 'per_kg',
      isOrganic: false,
      moisture: 0,
      harvest_date: '',
      availability_date: '',
      preferred_selling_date: '',
      shelf_life: 7,
      village: '',
      taluka: '',
      district: '',
      state: 'Maharashtra',
      storage_available: false,
      processing_available: false,
      full_supply_chain: false,
      req_market_intel: true,
      req_buyer_match: true,
      req_ai_neg: true,
      req_transport: false,
      req_warehouse: false,
      req_quality: false,
      description: ''
    }
  });

  const { register, handleSubmit, formState: { errors }, watch, reset, trigger } = methods;

  if (!isOpen) return null;

  const totalSteps = 10;
  
  const handleNext = async () => {
    // Basic validation before proceeding (could be improved with granular Zod schemas per step)
    const isStepValid = await trigger();
    if (isStepValid) setCurrentStep(p => Math.min(p + 1, totalSteps));
  };

  const handlePrev = () => setCurrentStep(p => Math.max(p - 1, 1));

  const handleImageChange = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setIsUploading(true);
    const newImages = [];
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await api.post('/integrations/storage/upload?bucket=listings', formData);
        if (res.data && res.data.url) newImages.push(res.data.url);
      } catch (err) {
        addNotification('error', `Failed to upload ${file.name}`);
      }
    }
    setUploadedImages(prev => [...prev, ...newImages]);
    setIsUploading(false);
  };

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      // Build selected_services dynamic object
      const selected_services = data.full_supply_chain 
        ? { full_supply_chain: true }
        : {
            market_intelligence: data.req_market_intel,
            buyer_matching: data.req_buyer_match,
            negotiation: data.req_ai_neg,
            transport: data.req_transport,
            warehouse: data.req_warehouse,
            quality_inspection: data.req_quality
          };

      const payload = {
        crop: data.crop,
        crop_category: data.crop_category,
        variety: data.variety,
        grade: data.grade,
        quantity: Number(data.quantity),
        unit: data.unit,
        min_sale_quantity: Number(data.min_sale_quantity),
        expected_price: Number(data.expected_price),
        min_price: Number(data.min_price),
        price_unit: data.price_unit,
        quality_info: { isOrganic: data.isOrganic, moisture: data.moisture },
        harvest_date: data.harvest_date,
        availability_date: data.availability_date,
        preferred_selling_date: data.preferred_selling_date,
        shelf_life: Number(data.shelf_life),
        location: `${data.village}, ${data.taluka}, ${data.district}`,
        storage_info: { available: data.storage_available },
        processing_info: { available: data.processing_available },
        selected_services,
        images: uploadedImages,
        description: data.description
      };

      await api.post('/listings/', payload);
      addNotification('success', 'Comprehensive listing submitted successfully.');
      reset();
      setUploadedImages([]);
      setCurrentStep(1);
      onSuccess?.();
      onClose();
    } catch (err) {
      addNotification('error', err.response?.data?.detail || 'Failed to submit listing');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formData = watch();

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50 sticky top-0 z-10">
          <div>
            <h3 className="font-bold text-slate-800 flex items-center gap-2 text-lg">
              <Sprout size={20} className="text-emerald-600" /> Create Market Listing
            </h3>
            <p className="text-xs text-slate-500 mt-1">Step {currentStep} of {totalSteps}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition bg-white p-2 rounded-full shadow-sm border border-slate-100">
            <X size={20} />
          </button>
        </div>
        
        {/* Progress Bar */}
        <div className="h-1.5 w-full bg-slate-100">
          <div 
            className="h-full bg-emerald-500 transition-all duration-300 ease-out"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
        
        {/* Scrollable Form Body */}
        <div className="overflow-y-auto flex-1 p-6 sm:p-8 bg-white">
          <FormProvider {...methods}>
            <form id="listing-wizard-form" onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              
              {currentStep === 1 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Crop Information</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Category *</label>
                      <select {...register('crop_category')} className="w-full form-input bg-slate-50">
                        {CROP_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Crop Name *</label>
                      <input 
                        list="maharashtra-listing-crops"
                        {...register('crop')} 
                        placeholder="e.g. Sugarcane, Soybean, Cotton, Onion..." 
                        className="w-full form-input bg-slate-50" 
                      />
                      <datalist id="maharashtra-listing-crops">
                        {TOP_MAHARASHTRA_CROPS.map(c => <option key={c} value={c} />)}
                        <option value="Tomato" />
                        <option value="Wheat" />
                        <option value="Potato" />
                      </datalist>
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Specific Variety *</label>
                      <input {...register('variety')} placeholder="e.g. Nashik Red, Shriram" className="w-full form-input bg-slate-50" />
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 2 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Quantity Details</h4>
                  <div className="grid grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Total Available *</label>
                      <input type="number" {...register('quantity', { valueAsNumber: true })} className="w-full form-input bg-slate-50" />
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
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 3 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Quality Parameters</h4>
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
              )}

              {currentStep === 4 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Pricing Strategy</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Expected Target Price (₹) *</label>
                      <input type="number" step="0.5" {...register('expected_price', { valueAsNumber: true })} className="w-full form-input bg-slate-50 border-blue-200 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Minimum Acceptable Price (₹) *</label>
                      <input type="number" step="0.5" {...register('min_price', { valueAsNumber: true })} className="w-full form-input bg-slate-50 border-red-200 focus:ring-red-500" />
                      {errors.min_price && <p className="text-red-500 text-xs mt-1">{errors.min_price.message}</p>}
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
              )}

              {currentStep === 5 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Farm Location</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Village / Locality *</label>
                      <input {...register('village')} className="w-full form-input bg-slate-50" />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Taluka *</label>
                      <input {...register('taluka')} className="w-full form-input bg-slate-50" />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">District *</label>
                      <input {...register('district')} className="w-full form-input bg-slate-50" />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">State *</label>
                      <input {...register('state')} className="w-full form-input bg-slate-50" />
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 6 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Harvest & Timeline</h4>
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
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Preferred Selling Date</label>
                      <input type="date" {...register('preferred_selling_date')} className="w-full form-input bg-slate-50" />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1.5">Estimated Shelf Life (Days) *</label>
                      <input type="number" {...register('shelf_life', { valueAsNumber: true })} className="w-full form-input bg-slate-50" />
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 7 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Infrastructure Backup</h4>
                  <p className="text-sm text-slate-600 mb-4">Do you have on-farm backup options if market prices are too low?</p>
                  
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('storage_available')} className="w-5 h-5 text-emerald-600 rounded" />
                      <div>
                        <p className="font-semibold text-slate-800">Storage / Cold Storage Available</p>
                        <p className="text-xs text-slate-500">I can store this crop to wait for better prices.</p>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-100 transition">
                      <input type="checkbox" {...register('processing_available')} className="w-5 h-5 text-emerald-600 rounded" />
                      <div>
                        <p className="font-semibold text-slate-800">Processing Fallback</p>
                        <p className="text-xs text-slate-500">I can process this (e.g. drying, puree) or sell to a local processor.</p>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {currentStep === 8 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Supply Chain Services</h4>
                  
                  <label className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl border border-blue-200 cursor-pointer mb-6">
                    <input type="checkbox" {...register('full_supply_chain')} className="w-5 h-5 text-blue-600 rounded" />
                    <div>
                      <p className="font-bold text-blue-900">Full Supply Chain Automation</p>
                      <p className="text-sm text-blue-700">Let AI handle finding buyers, negotiating, booking transport, and quality checks.</p>
                    </div>
                  </label>

                  {!formData.full_supply_chain && (
                    <div className="space-y-3 border-t border-slate-100 pt-4">
                      <p className="text-sm font-semibold text-slate-600 mb-3">Or select individual services:</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_market_intel')} className="rounded" /> Market Intelligence
                        </label>
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_buyer_match')} className="rounded" /> Buyer Matching
                        </label>
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_ai_neg')} className="rounded" /> AI Negotiation
                        </label>
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_transport')} className="rounded" /> Transport Agent
                        </label>
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_warehouse')} className="rounded" /> Warehouse Matching
                        </label>
                        <label className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border text-sm cursor-pointer">
                          <input type="checkbox" {...register('req_quality')} className="rounded" /> Quality Inspector
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {currentStep === 9 && (
                <div className="space-y-4 animate-in slide-in-from-right-4 fade-in duration-300">
                  <h4 className="text-xl font-bold text-slate-800 mb-6">Review & Confirm</h4>
                  
                  <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 space-y-6">
                    <div className="grid grid-cols-2 gap-y-4 text-sm">
                      <div>
                        <p className="text-slate-500">Product</p>
                        <p className="font-bold text-slate-800">{formData.crop} ({formData.variety})</p>
                        <p className="text-emerald-600 font-medium">{formData.grade} {formData.isOrganic ? '- Organic' : ''}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Volume</p>
                        <p className="font-bold text-slate-800">{formData.quantity} {formData.unit}</p>
                        <p className="text-slate-600">Min Sale: {formData.min_sale_quantity} {formData.unit}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Pricing Strategy</p>
                        <p className="font-bold text-slate-800">Target: ₹{formData.expected_price}/{formData.price_unit}</p>
                        <p className="text-red-500 font-medium">Absolute Min: ₹{formData.min_price}/{formData.price_unit}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Location & Timing</p>
                        <p className="font-bold text-slate-800">{formData.village}, {formData.district}</p>
                        <p className="text-slate-600">Shelf Life: {formData.shelf_life} days</p>
                      </div>
                    </div>
                    
                    <div className="pt-4 border-t border-slate-200">
                      <p className="text-slate-500 text-sm mb-2">Requested Services</p>
                      <div className="flex flex-wrap gap-2">
                        {formData.full_supply_chain ? (
                          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-bold">FULL SUPPLY CHAIN</span>
                        ) : (
                          <>
                            {formData.req_market_intel && <span className="px-2 py-1 bg-slate-200 text-slate-700 rounded-md text-xs">Market Intel</span>}
                            {formData.req_buyer_match && <span className="px-2 py-1 bg-slate-200 text-slate-700 rounded-md text-xs">Buyer Match</span>}
                            {formData.req_ai_neg && <span className="px-2 py-1 bg-emerald-100 text-emerald-800 rounded-md text-xs font-bold">AI Negotiator</span>}
                            {formData.req_transport && <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded-md text-xs">Transport</span>}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 10 && (
                <div className="space-y-6 text-center animate-in slide-in-from-bottom-4 fade-in duration-300 py-10">
                  <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 size={48} className="text-emerald-600" />
                  </div>
                  <h4 className="text-2xl font-bold text-slate-800">Ready to Submit</h4>
                  <p className="text-slate-500 max-w-sm mx-auto">
                    Your listing is complete and ready to be processed by the Market Intelligence & Matching Engine.
                  </p>
                </div>
              )}

            </form>
          </FormProvider>
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-100 flex justify-between bg-slate-50 sticky bottom-0 z-10">
          <button 
            type="button" 
            onClick={handlePrev} 
            disabled={currentStep === 1 || isSubmitting}
            className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold rounded-xl transition disabled:opacity-30 flex items-center gap-2 shadow-sm"
          >
            <ChevronLeft size={18} /> Back
          </button>
          
          {currentStep < totalSteps ? (
            <button 
              type="button" 
              onClick={handleNext}
              className="px-8 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl transition shadow-md flex items-center gap-2"
            >
              Next Step <ChevronRight size={18} />
            </button>
          ) : (
            <button 
              type="submit" 
              form="listing-wizard-form"
              disabled={isSubmitting} 
              className="px-8 py-2.5 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl transition shadow-md"
            >
              {isSubmitting ? <><Loader2 size={18} className="animate-spin" /> Publishing...</> : 'Publish Listing'}
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
