import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { User, MapPin, Building, Phone, Mail, Save, ShieldCheck } from 'lucide-react';

export default function UserProfile() {
  const { user } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  
  // Mock initial state based on user role
  // Initial state based on user role and saved credentials
  const [formData, setFormData] = useState({
    fullName: user?.name || user?.full_name || '',
    email: user?.email || (user?.name ? `${user.name.toLowerCase().replace(/\s+/g, '.')}@example.com` : ''),
    phone: user?.phone || '+91 98765 43210',
    companyName: user?.businessName || (user?.role === 'buyer' ? `${user?.name || 'Buyer'} Agro Procure Ltd.` : 'Green Farms Organic'),
    location: user?.location || 'Pune, Maharashtra',
    gstin: user?.gstin || '27AABCU9603R1ZM',
    buyerPersona: user?.buyerPersona || 'food_processing',
    fssaiLicense: user?.fssaiLicense || '11522020000123',
    mandiLicense: user?.mandiLicense || 'MH-APMC-PUN-4091',
    processingCapacity: user?.processingCapacity || '100 MT / month',
    procurementWindow: user?.procurementWindow || 'Early Morning 4 AM - 7 AM'
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const stored = localStorage.getItem('agri_user');
      const currentUser = stored ? JSON.parse(stored) : (user || {});
      const updatedUser = {
        ...currentUser,
        name: formData.fullName,
        full_name: formData.fullName,
        businessName: formData.companyName,
        companyName: formData.companyName,
        location: formData.location,
        buyerPersona: formData.buyerPersona,
        fssaiLicense: formData.fssaiLicense,
        gstin: formData.gstin,
        mandiLicense: formData.mandiLicense,
        processingCapacity: formData.processingCapacity,
        procurementWindow: formData.procurementWindow,
        verificationStatus: (formData.fssaiLicense || formData.gstin) ? 'VERIFIED' : 'PENDING'
      };
      localStorage.setItem('agri_user', JSON.stringify(updatedUser));
    } catch (err) {}

    setTimeout(() => {
      setIsSaving(false);
      setSuccessMsg('Profile & Enterprise credentials updated successfully!');
      setTimeout(() => setSuccessMsg(''), 3000);
    }, 600);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-slide-up">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center space-x-6">
        <div className="bg-emerald-100 w-24 h-24 rounded-full flex items-center justify-center border-4 border-white shadow-md">
          <User className="h-12 w-12 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{formData.fullName}</h1>
          <p className="text-slate-500 flex items-center mt-1">
            <ShieldCheck className="w-4 h-4 mr-1 text-emerald-600" /> 
            Verified {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'Buyer'}
            {user?.role === 'buyer' && (
              <span className="ml-2 text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-0.5 rounded-full border border-emerald-300">
                {formData.buyerPersona === 'restaurant' ? '🍽️ Restaurant / Food Service' :
                 formData.buyerPersona === 'wholesale_trader' ? '🏢 APMC Mandi Trader' :
                 formData.buyerPersona === 'retail_supermarket' ? '🛒 Retail Grocery Chain' :
                 formData.buyerPersona === 'institutional' ? '🏫 Institutional Canteen' :
                 '🏭 Food Processing Unit'}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <h2 className="text-lg font-bold text-slate-900">Personal & Business Credentials</h2>
          {successMsg && (
            <span className="text-sm font-medium text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              {successMsg}
            </span>
          )}
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div className="space-y-2">
              <label className="flex items-center text-sm font-medium text-slate-700">
                <User className="w-4 h-4 mr-2 text-slate-400" /> Full Name
              </label>
              <input 
                type="text" 
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center text-sm font-medium text-slate-700">
                <Mail className="w-4 h-4 mr-2 text-slate-400" /> Email Address
              </label>
              <input 
                type="email" 
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center text-sm font-medium text-slate-700">
                <Phone className="w-4 h-4 mr-2 text-slate-400" /> Phone Number
              </label>
              <input 
                type="text" 
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center text-sm font-medium text-slate-700">
                <MapPin className="w-4 h-4 mr-2 text-slate-400" /> Location / APMC Mandi (Maharashtra)
              </label>
              <input 
                type="text" 
                name="location"
                value={formData.location}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
              />
            </div>

            {/* BUYER PERSONA & BUSINESS SECTION */}
            {user?.role === 'buyer' && (
              <>
                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <Building className="w-4 h-4 mr-2 text-slate-400" /> Buyer Persona / Category
                  </label>
                  <select
                    name="buyerPersona"
                    value={formData.buyerPersona}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 bg-white font-semibold text-slate-800"
                  >
                    <option value="food_processing">🏭 Food Processing Unit (Pulp, Flour, Sauces)</option>
                    <option value="restaurant">🍽️ Restaurant / Cloud Kitchen / Hospitality Chain</option>
                    <option value="wholesale_trader">🏢 Wholesale APMC Trader / Commission Agent</option>
                    <option value="retail_supermarket">🛒 Supermarket / Retail Grocery Chain</option>
                    <option value="institutional">🏫 Institutional Canteen / Bulk Catering</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <Building className="w-4 h-4 mr-2 text-slate-400" /> Registered Business / Unit Name
                  </label>
                  <input 
                    type="text" 
                    name="companyName"
                    value={formData.companyName}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
                  />
                </div>

                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <ShieldCheck className="w-4 h-4 mr-2 text-slate-400" /> FSSAI License Number (14 Digits)
                  </label>
                  <input 
                    type="text" 
                    maxLength={14}
                    name="fssaiLicense"
                    value={formData.fssaiLicense}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 font-mono" 
                  />
                </div>

                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <ShieldCheck className="w-4 h-4 mr-2 text-slate-400" /> GSTIN Tax ID (15 Characters)
                  </label>
                  <input 
                    type="text" 
                    maxLength={15}
                    name="gstin"
                    value={formData.gstin}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 font-mono uppercase" 
                  />
                </div>

                {formData.buyerPersona === 'food_processing' && (
                  <div className="space-y-2">
                    <label className="flex items-center text-sm font-medium text-slate-700">
                      Processing Capacity
                    </label>
                    <input 
                      type="text" 
                      name="processingCapacity"
                      value={formData.processingCapacity}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
                    />
                  </div>
                )}

                {formData.buyerPersona === 'restaurant' && (
                  <div className="space-y-2">
                    <label className="flex items-center text-sm font-medium text-slate-700">
                      Delivery Procurement Window
                    </label>
                    <input 
                      type="text" 
                      name="procurementWindow"
                      value={formData.procurementWindow}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
                    />
                  </div>
                )}

                {formData.buyerPersona === 'wholesale_trader' && (
                  <div className="space-y-2">
                    <label className="flex items-center text-sm font-medium text-slate-700">
                      APMC Trader License Code
                    </label>
                    <input 
                      type="text" 
                      name="mandiLicense"
                      value={formData.mandiLicense}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 font-mono" 
                    />
                  </div>
                )}
              </>
            )}

            {user?.role !== 'buyer' && (
              <>
                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <Building className="w-4 h-4 mr-2 text-slate-400" /> Farm / Enterprise Name
                  </label>
                  <input 
                    type="text" 
                    name="companyName"
                    value={formData.companyName}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500" 
                  />
                </div>

                <div className="space-y-2">
                  <label className="flex items-center text-sm font-medium text-slate-700">
                    <ShieldCheck className="w-4 h-4 mr-2 text-slate-400" /> GSTIN / Mandi ID
                  </label>
                  <input 
                    type="text" 
                    name="gstin"
                    value={formData.gstin}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-emerald-500 focus:border-emerald-500 font-mono" 
                  />
                </div>
              </>
            )}

          </div>

          <div className="pt-6 border-t border-slate-200 flex justify-end">
            <button 
              type="submit"
              disabled={isSaving}
              className="bg-emerald-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-emerald-700 transition-colors flex items-center disabled:opacity-70"
            >
              {isSaving ? (
                'Saving...'
              ) : (
                <><Save className="w-4 h-4 mr-2" /> Save Changes</>
              )}
            </button>
          </div>
        </form>
      </div>

    </div>
  );
}
