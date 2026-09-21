import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { listingSchema } from '../../utils/validation';
import { X, Sprout, ImagePlus, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { useNotification } from '../../contexts/NotificationContext';

export default function CreateListingForm({ isOpen, onClose, onSuccess }) {
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedImages, setUploadedImages] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleBoxClick = () => {
    document.getElementById('crop-image-upload').click();
  };

  const handleImageChange = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setIsUploading(true);
    const newImages = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await api.post('/integrations/storage/upload?bucket=listings', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        if (res.data && res.data.url) {
          newImages.push(res.data.url);
        }
      } catch (err) {
        addNotification('error', `Failed to upload ${file.name}`);
      }
    }

    setUploadedImages(prev => [...prev, ...newImages]);
    setIsUploading(false);
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm({
    resolver: zodResolver(listingSchema),
    defaultValues: {
      grade: 'A',
      isOrganic: false,
      transportRequired: false,
      warehouseRequired: false,
    }
  });

  if (!isOpen) return null;

  const onSubmit = async (data) => {
    setIsSubmitting(true);
    try {
      const spoilageMapping = {
        Tomato: 5,
        Onion: 30,
        Potato: 45,
        Cabbage: 7,
        Wheat: 180,
        Soybean: 180,
      };

      const payload = {
        crop: data.crop,
        quantity: Number(data.quantity),
        min_price: Number(data.price),
        location: data.location,
        spoilage_days: spoilageMapping[data.crop] || 7,
        description: `Variety: ${data.variety}, Grade: ${data.grade}, Organic: ${data.isOrganic ? 'Yes' : 'No'}, Moisture: ${data.moisture || 0}%, Harvest Date: ${data.harvestDate}. Images: ${uploadedImages.join(', ')}`
      };

      // Post crop listing to backend API
      await api.post('/listings/', payload);
      addNotification('success', 'Listing published successfully! AI Market Agents are now matching valid buyers.');

      reset();
      setUploadedImages([]);
      onSuccess?.();
      onClose();
    } catch (err) {
      addNotification('error', err.response?.data?.detail || 'Failed to submit listing');
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
            <Sprout size={18} className="text-emerald-600" /> New Crop Listing
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
            <X size={20} />
          </button>
        </div>
        
        {/* Scrollable Form Body */}
        <div className="overflow-y-auto flex-1 p-6">
          <form id="listing-form" onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            {/* 1. Basic Details */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">1. Basic Details</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Crop Name *</label>
                  <select 
                    {...register('crop')}
                    className="mt-1 form-input text-sm"
                  >
                    <option value="Tomato">Tomato</option>
                    <option value="Onion">Onion</option>
                    <option value="Potato">Potato</option>
                    <option value="Cabbage">Cabbage</option>
                    <option value="Wheat">Wheat</option>
                    <option value="Soybean">Soybean</option>
                  </select>
                  {errors.crop && <p className="text-xs text-red-500 mt-1">{errors.crop.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Variety *</label>
                  <input 
                    {...register('variety')}
                    placeholder="e.g. Nashik Red"
                    className="mt-1 form-input text-sm"
                  />
                  {errors.variety && <p className="text-xs text-red-500 mt-1">{errors.variety.message}</p>}
                </div>
              </div>
            </div>

            {/* 2. Volume & Pricing */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">2. Volume & Pricing</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Total Volume (kg) *</label>
                  <input 
                    type="number"
                    {...register('quantity', { valueAsNumber: true })}
                    placeholder="e.g. 500"
                    className="mt-1 form-input text-sm"
                  />
                  {errors.quantity && <p className="text-xs text-red-500 mt-1">{errors.quantity.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Target Price (₹/kg) *</label>
                  <input 
                    type="number" step="0.5"
                    {...register('price', { valueAsNumber: true })}
                    placeholder="e.g. 22.50"
                    className="mt-1 form-input text-sm"
                  />
                  {errors.price && <p className="text-xs text-red-500 mt-1">{errors.price.message}</p>}
                </div>
              </div>
            </div>

            {/* 3. Quality & Origin */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">3. Quality Metrics</h4>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Quality Grade *</label>
                  <select {...register('grade')} className="mt-1 form-input text-sm">
                    <option value="A">Grade A (Premium)</option>
                    <option value="B">Grade B (Standard)</option>
                    <option value="C">Grade C (Processing)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Moisture (%)</label>
                  <input 
                    type="number"
                    {...register('moisture', { valueAsNumber: true })}
                    placeholder="e.g. 12"
                    className="mt-1 form-input text-sm"
                  />
                  {errors.moisture && <p className="text-xs text-red-500 mt-1">{errors.moisture.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Harvest Date *</label>
                  <input 
                    type="date"
                    {...register('harvestDate')}
                    className="mt-1 form-input text-sm"
                  />
                  {errors.harvestDate && <p className="text-xs text-red-500 mt-1">{errors.harvestDate.message}</p>}
                </div>
              </div>
              
              <div className="flex gap-4 items-center">
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" {...register('isOrganic')} className="rounded text-emerald-600 focus:ring-emerald-500" />
                  Certified Organic
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" {...register('transportRequired')} className="rounded text-emerald-600 focus:ring-emerald-500" />
                  Requires Transport
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input type="checkbox" {...register('warehouseRequired')} className="rounded text-emerald-600 focus:ring-emerald-500" />
                  Requires Warehouse
                </label>
              </div>
            </div>

            {/* 4. Location */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">4. Location</h4>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Village / Taluka *</label>
                <input 
                  {...register('location')}
                  placeholder="e.g. Niphad, Nashik"
                  className="mt-1 form-input text-sm"
                />
                {errors.location && <p className="text-xs text-red-500 mt-1">{errors.location.message}</p>}
              </div>
            </div>

            {/* 5. Images Upload */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-800 border-b pb-2">5. Crop Images</h4>
              <input 
                type="file" 
                multiple 
                accept="image/*" 
                className="hidden" 
                id="crop-image-upload"
                onChange={handleImageChange}
              />
              <div 
                onClick={handleBoxClick}
                className="border-2 border-dashed border-slate-300 rounded-xl p-8 flex flex-col items-center justify-center text-slate-500 hover:bg-slate-50 transition cursor-pointer"
              >
                {isUploading ? (
                  <>
                    <Loader2 size={32} className="mb-2 text-slate-400 animate-spin" />
                    <p className="text-sm font-medium">Uploading images...</p>
                  </>
                ) : (
                  <>
                    <ImagePlus size={32} className="mb-2 text-slate-400" />
                    <p className="text-sm font-medium">Click to select crop images</p>
                    <p className="text-xs mt-1">Supports JPG, PNG (Max 5MB)</p>
                  </>
                )}
              </div>

              {/* Previews */}
              {uploadedImages.length > 0 && (
                <div className="grid grid-cols-4 gap-4 mt-4">
                  {uploadedImages.map((url, idx) => (
                    <div key={idx} className="relative aspect-square rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-50 group">
                      <img 
                        src={`http://localhost:8000${url}`} 
                        alt="Crop Preview" 
                        className="w-full h-full object-cover" 
                      />
                      <button 
                        type="button"
                        onClick={() => setUploadedImages(prev => prev.filter((_, i) => i !== idx))}
                        className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 shadow hover:bg-red-600 transition"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
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
            form="listing-form"
            disabled={isSubmitting} 
            className="flex-1 py-2.5 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl transition shadow-sm"
          >
            {isSubmitting ? <><Loader2 size={18} className="animate-spin" /> Submitting...</> : 'Submit to AI Validator'}
          </button>
        </div>

      </div>
    </div>
  );
}
