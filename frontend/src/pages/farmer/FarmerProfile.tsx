import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import { Save, User, MapPin, Tractor, Edit2, Check, X } from 'lucide-react';
import { useNotification } from '@/contexts/NotificationContext';

export default function FarmerProfile() {
  const { user, updateProfile } = useAuth();
  const { addNotification } = useNotification();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    name: user?.name || '',
    phone: user?.phone || '',
    village: user?.village || '',
    taluka: user?.taluka || '',
    district: user?.district || '',
    state: user?.state || 'Maharashtra',
    farm_size: user?.farm_size || '',
    farming_type: user?.farming_type || 'Conventional'
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // 1. Update basic user profile (name, phone)
      await api.patch('/profiles/me', {
        name: formData.name,
        phone: formData.phone
      });
      
      // 2. Update extended farmer profile
      const response = await api.post('/profiles/farmer', {
        user_id: user?.id || 'unknown',
        location: formData.district || 'Maharashtra',
        village: formData.village,
        taluka: formData.taluka,
        district: formData.district,
        state: formData.state,
        farm_size_acres: formData.farm_size ? parseFloat(formData.farm_size) : null,
        farming_type: formData.farming_type
      });
      
      if (updateProfile) {
        updateProfile({ ...user, name: formData.name, phone: formData.phone, ...response.data.data });
      }
      addNotification('success', 'Profile updated successfully.');
      setIsEditing(false);
    } catch (error) {
      console.error("Profile save error", error);
      addNotification('error', 'Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Farmer Profile</h1>
          <p className="text-slate-500 mt-1">Manage your personal information and farm details.</p>
        </div>
        <div>
          {!isEditing ? (
            <button 
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-2 bg-emerald-50 text-emerald-700 px-4 py-2 rounded-xl font-medium hover:bg-emerald-100 transition"
            >
              <Edit2 size={16} /> Edit Profile
            </button>
          ) : (
            <div className="flex gap-2">
              <button 
                onClick={() => setIsEditing(false)}
                className="flex items-center gap-2 bg-slate-100 text-slate-600 px-4 py-2 rounded-xl font-medium hover:bg-slate-200 transition"
              >
                <X size={16} /> Cancel
              </button>
              <button 
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-xl font-medium hover:bg-emerald-700 transition"
              >
                <Check size={16} /> {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Personal Details */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-5">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b pb-3 border-slate-100">
            <User size={18} className="text-emerald-500" /> Personal Details
          </h2>
          
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">Full Name</label>
            <input 
              name="name"
              value={formData.name}
              onChange={handleChange}
              disabled={!isEditing}
              className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">Mobile Number</label>
            <input 
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              disabled={!isEditing}
              className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
            />
          </div>
        </div>

        {/* Location */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-5">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b pb-3 border-slate-100">
            <MapPin size={18} className="text-emerald-500" /> Farm Location
          </h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Village</label>
              <input 
                name="village"
                value={formData.village}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="Village name"
                className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Taluka</label>
              <input 
                name="taluka"
                value={formData.taluka}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="Taluka"
                className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">District</label>
              <input 
                name="district"
                value={formData.district}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="District"
                className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">State</label>
              <input 
                name="state"
                value={formData.state}
                disabled={true}
                className="w-full form-input bg-transparent border-transparent px-0 font-medium text-slate-900" 
              />
            </div>
          </div>
        </div>

        {/* Farm Details */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-5 md:col-span-2">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 border-b pb-3 border-slate-100">
            <Tractor size={18} className="text-emerald-500" /> Farm Capacity
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Total Farm Size (Acres)</label>
              <input 
                name="farm_size"
                type="number"
                value={formData.farm_size}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="e.g. 5"
                className="w-full form-input bg-slate-50 disabled:bg-transparent disabled:border-transparent disabled:px-0 disabled:font-medium disabled:text-slate-900" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Primary Farming Type</label>
              {isEditing ? (
                <select 
                  name="farming_type"
                  value={formData.farming_type}
                  onChange={handleChange}
                  className="w-full form-input bg-slate-50"
                >
                  <option>Conventional</option>
                  <option>Organic Certified</option>
                  <option>Mixed (Both)</option>
                  <option>Greenhouse/Polyhouse</option>
                </select>
              ) : (
                <div className="font-medium text-slate-900 mt-2">{formData.farming_type}</div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
