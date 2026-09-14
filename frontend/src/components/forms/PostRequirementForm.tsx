import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { requirementSchema, TOP_MAHARASHTRA_CROPS } from '../../utils/validation';
import { X, Target, Loader2, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';

export default function PostRequirementForm({ isOpen, onClose, onSuccess }) {
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
    reset
  } = useForm({
    resolver: zodResolver(requirementSchema),
    defaultValues: {
      quality: 'ANY',
      storageRequired: false,
      transportRequired: true,
    }
  });

  if (!isOpen) return null;

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      const payload = {
        crop: data.crop,
        quantity: Number(data.quantity) || 500,
        target_price: Number(data.maxBudget) || 20,
        max_price: Number(data.maxBudget) || 25,
        budget: (Number(data.quantity) || 500) * (Number(data.maxBudget) || 25),
        location: data.preferredLocation || 'Maharashtra',
        preferredLocation: data.preferredLocation || 'Maharashtra',
        maxBudget: Number(data.maxBudget) || 20,
        quality_grade: data.quality || 'A',
        quality: data.quality || 'A',
        deliveryDate: data.deliveryDate || '',
        transportRequired: Boolean(data.transportRequired),
        storageRequired: Boolean(data.storageRequired),
      };
      const res = await api.post('/requirements', payload);
      const created = res.data?.data || { ...payload, id: res.data?.requirement_id };
      reset();
      onSuccess?.(created);
      onClose();
    } catch (err) {
      addNotification('error', err.response?.data?.detail || 'Failed to post requirement');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 sticky top-0 z-10">
          <h3 className="font-bold text-slate-700 flex items-center gap-2">
            <Target size={18} className="text-blue-600" /> Post Procurement Requirement
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
            <X size={20} />
          </button>
        </div>
        
        {/* Scrollable Form Body */}
        <div className="overflow-y-auto flex-1 p-6">
          <form id="req-form" onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            {/* 1. Basic Details */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">1. Commodity Needs</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Crop Name *</label>
                  <input 
                    list="maharashtra-crops-list"
                    {...register('crop')}
                    placeholder="e.g. Sugarcane, Soybean, Cotton, Jowar..."
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold text-slate-900 placeholder-slate-500"
                  />
                  <datalist id="maharashtra-crops-list">
                    {TOP_MAHARASHTRA_CROPS.map(c => <option key={c} value={c} />)}
                    <option value="Tomato" />
                    <option value="Wheat" />
                    <option value="Potato" />
                  </datalist>
                  {errors.crop && <p className="text-xs text-red-500 mt-1">{errors.crop.message}</p>}
                  
                  {/* Quick Select Chips for Maharashtra Top Crops */}
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Top Crops:</span>
                    {TOP_MAHARASHTRA_CROPS.map(c => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setValue('crop', c, { shouldValidate: true })}
                        className="px-2 py-0.5 text-[11px] font-semibold bg-slate-100 hover:bg-blue-100 hover:text-blue-700 text-slate-600 rounded-md transition cursor-pointer"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Quality Grade</label>
                  <select {...register('quality')} className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="ANY">Any Grade</option>
                    <option value="A">Grade A (Premium Only)</option>
                    <option value="B">Grade B (Standard)</option>
                    <option value="C">Grade C (Processing)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* 2. Constraints */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">2. Budget & Volume</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Required Volume (kg) *</label>
                  <input 
                    type="number"
                    {...register('quantity', { valueAsNumber: true })}
                    placeholder="e.g. 5000"
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold text-slate-900 placeholder-slate-500"
                  />
                  {errors.quantity && <p className="text-xs text-red-500 mt-1">{errors.quantity.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Max Budget (₹/kg) *</label>
                  <input 
                    type="number" step="0.5"
                    {...register('maxBudget', { valueAsNumber: true })}
                    placeholder="e.g. 18.50"
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold text-slate-900 placeholder-slate-500"
                  />
                  {errors.maxBudget && <p className="text-xs text-red-500 mt-1">{errors.maxBudget.message}</p>}
                </div>
              </div>
            </div>

            {/* 3. Logistics */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">3. Logistics</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Preferred Location (Maharashtra Only)</label>
                  <input 
                    list="maharashtra-locations-list"
                    {...register('preferredLocation')}
                    placeholder="e.g. Pune, Nashik, or All Maharashtra"
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold text-slate-900 placeholder-slate-500"
                  />
                  <datalist id="maharashtra-locations-list">
                    <option value="All Maharashtra" />
                    <option value="Nashik Mandi" />
                    <option value="Pune Market Yard" />
                    <option value="Vashi APMC, Navi Mumbai" />
                    <option value="Nagpur Mandi" />
                    <option value="Chhatrapati Sambhajinagar (Aurangabad)" />
                    <option value="Solapur Mandi" />
                    <option value="Kolhapur APMC" />
                    <option value="Ahmednagar Mandi" />
                    <option value="Satara Mandi" />
                    <option value="Sangli Mandi" />
                    <option value="Jalgaon Mandi" />
                    <option value="Amravati Mandi" />
                  </datalist>
                  {errors.preferredLocation ? (
                    <p className="text-xs text-red-500 mt-1">{errors.preferredLocation.message}</p>
                  ) : (
                    <p className="text-[11px] text-slate-400 mt-1">Platform is strictly limited to Maharashtra mandis & districts.</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Delivery Deadline *</label>
                  <input 
                    type="date"
                    min={new Date().toISOString().split('T')[0]}
                    {...register('deliveryDate')}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold text-slate-900"
                  />
                  {errors.deliveryDate ? (
                    <p className="text-xs text-red-500 mt-1">{errors.deliveryDate.message}</p>
                  ) : (
                    <p className="text-[11px] text-slate-400 mt-1">Must be today or a future date.</p>
                  )}
                </div>
              </div>
              
              <div className="flex gap-4 items-center">
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" {...register('transportRequired')} className="rounded text-blue-600 focus:ring-blue-500" />
                  Require Logistics Setup
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" {...register('storageRequired')} className="rounded text-blue-600 focus:ring-blue-500" />
                  Require Cold Storage
                </label>
              </div>
            </div>

          </form>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-100 flex gap-3 bg-white sticky bottom-0 z-10">
          <button type="button" onClick={onClose} className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition">
            Cancel
          </button>
          <button 
            type="submit" 
            form="req-form"
            disabled={isSubmitting} 
            className="flex-1 py-2.5 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:scale-95 disabled:opacity-50 text-white font-bold rounded-xl transition shadow-sm cursor-pointer"
          >
            {isSubmitting ? <><Loader2 size={18} className="animate-spin" /> Matching...</> : 'Save & Find Matches →'}
          </button>
        </div>

      </div>
    </div>
  );
}
