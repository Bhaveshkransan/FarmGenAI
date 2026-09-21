import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sprout, ArrowLeft } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { isMaharashtraLocation } from '@/utils/validation';

export default function Register() {
  const [formData, setFormData] = useState({ name: '', email: '', location: '', password: '', role: 'farmer' });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Maharashtra check
    if (!isMaharashtraLocation(formData.location)) {
      setError('Operational zone is strictly limited to Maharashtra (e.g. Pune, Nashik, Mumbai, Nagpur).');
      return;
    }

    if (formData.role === 'buyer') {
      const persona = formData.buyerPersona || 'food_processing';
      if (!formData.businessName || formData.businessName.trim().length < 2) {
        setError('Please enter a valid entity / business trade name.');
        return;
      }
      if (formData.fssaiLicense && !/^\d{14}$/.test(formData.fssaiLicense.trim())) {
        setError('FSSAI License must be a valid 14-digit numeric code (e.g. 11522020000123).');
        return;
      }
      if (formData.gstin && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/i.test(formData.gstin.trim())) {
        setError('GSTIN must be a valid 15-character Indian tax identification number (e.g. 27AABCS1429B1Z8).');
        return;
      }
    }

    setIsLoading(true);
    const res = await register(formData);
    if (res.success) {
      navigate('/dashboard');
    } else {
      setError(res.error || 'Registration failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center text-emerald-600 mb-4">
          <Sprout size={48} />
        </div>
        <h2 className="mt-2 text-center text-3xl font-extrabold text-slate-900">
          Create an account
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm sm:rounded-xl sm:px-10 border border-slate-200">
          <div className="mb-6">
            <Link to="/" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-emerald-600 transition-colors">
              <ArrowLeft size={16} className="mr-1" /> Back to Home
            </Link>
          </div>
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm font-medium border border-red-100">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-700">Full Name</label>
              <input
                type="text" required
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="mt-1 form-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Email Address</label>
              <input
                type="email" required
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 form-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Location</label>
              <input
                type="text" required
                value={formData.location}
                onChange={(e) => setFormData({...formData, location: e.target.value})}
                className="mt-1 form-input"
                placeholder="e.g. Pune, Maharashtra"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Password</label>
              <input
                type="password" required
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 form-input"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700">Role</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({...formData, role: e.target.value})}
                className="mt-1 form-input"
              >
                <option value="farmer">Farmer</option>
                <option value="buyer">Buyer / Procurement Enterprise</option>
                <option value="warehouse">Warehouse Provider</option>
                <option value="transport">Transport Provider</option>
                <option value="processor">Processor</option>
              </select>
            </div>

            {/* DYNAMIC BUYER PERSONA & BUSINESS VERIFICATION SECTION */}
            {formData.role === 'buyer' && (
              <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-4 animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-emerald-200 pb-2">
                  <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">
                    Buyer Business Persona & Verification
                  </span>
                  <span className="text-[10px] bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full font-semibold">
                    APMC Mandi Verified
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Select Buyer Persona *
                  </label>
                  <select
                    value={formData.buyerPersona || 'food_processing'}
                    onChange={(e) => setFormData({ ...formData, buyerPersona: e.target.value })}
                    className="w-full form-input text-sm font-semibold bg-white"
                  >
                    <option value="food_processing">🏭 Food Processing Unit (Pulp, Flour, Canning, Sauces)</option>
                    <option value="restaurant">🍽️ Restaurant / Cloud Kitchen / Hospitality Chain</option>
                    <option value="wholesale_trader">🏢 Wholesale APMC Trader / Commission Agent</option>
                    <option value="retail_supermarket">🛒 Supermarket / Retail Grocery Chain</option>
                    <option value="institutional">🏫 Institutional Canteen / Bulk Catering</option>
                  </select>
                </div>

                {/* Common Business Name */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {(formData.buyerPersona === 'food_processing' && 'Processing Plant / Unit Name *') ||
                     (formData.buyerPersona === 'restaurant' && 'Restaurant / Outlet Trade Name *') ||
                     (formData.buyerPersona === 'wholesale_trader' && 'APMC Mandi Commission Firm Name *') ||
                     (formData.buyerPersona === 'retail_supermarket' && 'Retail Brand / Chain Name *') ||
                     'Institution / Organization Name *'}
                  </label>
                  <input
                    type="text"
                    required
                    placeholder={
                      formData.buyerPersona === 'food_processing' ? 'e.g. Sahyadri Agro Processing Plant' :
                      formData.buyerPersona === 'restaurant' ? 'e.g. Green Gourmet Cloud Kitchens' :
                      formData.buyerPersona === 'wholesale_trader' ? 'e.g. Nashik APMC Trading Co.' :
                      formData.buyerPersona === 'retail_supermarket' ? 'e.g. FreshHarvest Hypermarket' :
                      'e.g. Symbiosis Campus Central Canteen'
                    }
                    value={formData.businessName || ''}
                    onChange={(e) => setFormData({ ...formData, businessName: e.target.value })}
                    className="w-full form-input text-sm bg-white"
                  />
                </div>

                {/* Persona-Specific: Food Processing */}
                {(!formData.buyerPersona || formData.buyerPersona === 'food_processing') && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          FSSAI Manufacturing License (14 Digits) *
                        </label>
                        <input
                          type="text"
                          maxLength={14}
                          placeholder="e.g. 11522020000123"
                          value={formData.fssaiLicense || ''}
                          onChange={(e) => setFormData({ ...formData, fssaiLicense: e.target.value })}
                          className="w-full form-input text-sm bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          GSTIN Tax Identification *
                        </label>
                        <input
                          type="text"
                          maxLength={15}
                          placeholder="e.g. 27AABCS1429B1Z8"
                          value={formData.gstin || ''}
                          onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                          className="w-full form-input text-sm bg-white font-mono uppercase"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Monthly Processing Capacity
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 100 MT / month (Pulping & Packaging)"
                        value={formData.processingCapacity || ''}
                        onChange={(e) => setFormData({ ...formData, processingCapacity: e.target.value })}
                        className="w-full form-input text-sm bg-white"
                      />
                    </div>
                  </>
                )}

                {/* Persona-Specific: Restaurant */}
                {formData.buyerPersona === 'restaurant' && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          FSSAI Food Safety License *
                        </label>
                        <input
                          type="text"
                          maxLength={14}
                          placeholder="e.g. 21524010000456"
                          value={formData.fssaiLicense || ''}
                          onChange={(e) => setFormData({ ...formData, fssaiLicense: e.target.value })}
                          className="w-full form-input text-sm bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          Daily Procurement Window *
                        </label>
                        <select
                          value={formData.procurementWindow || 'Early Morning 4 AM - 7 AM'}
                          onChange={(e) => setFormData({ ...formData, procurementWindow: e.target.value })}
                          className="w-full form-input text-sm bg-white"
                        >
                          <option value="Early Morning 4 AM - 7 AM">Early Morning (4 AM - 7 AM)</option>
                          <option value="Mid-Day 11 AM - 2 PM">Mid-Day (11 AM - 2 PM)</option>
                          <option value="Evening 6 PM - 9 PM">Evening Batch (6 PM - 9 PM)</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Primary Delivery Hub / Kitchen Mandi
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Pune Market Yard Hub, Kothrud Kitchen"
                        value={formData.kitchenLocation || ''}
                        onChange={(e) => setFormData({ ...formData, kitchenLocation: e.target.value })}
                        className="w-full form-input text-sm bg-white"
                      />
                    </div>
                  </>
                )}

                {/* Persona-Specific: Wholesale APMC Trader */}
                {formData.buyerPersona === 'wholesale_trader' && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          APMC Mandi Trader License / Code *
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. MH-APMC-PUN-4091"
                          value={formData.mandiLicense || ''}
                          onChange={(e) => setFormData({ ...formData, mandiLicense: e.target.value.toUpperCase() })}
                          className="w-full form-input text-sm bg-white font-mono uppercase"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">
                          GSTIN Tax ID *
                        </label>
                        <input
                          type="text"
                          maxLength={15}
                          placeholder="e.g. 27AABCT9981K1Z2"
                          value={formData.gstin || ''}
                          onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                          className="w-full form-input text-sm bg-white font-mono uppercase"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Registered APMC Market Yard
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Pune Market Yard / Nashik APMC"
                        value={formData.primaryMandi || ''}
                        onChange={(e) => setFormData({ ...formData, primaryMandi: e.target.value })}
                        className="w-full form-input text-sm bg-white"
                      />
                    </div>
                  </>
                )}

                {/* Persona-Specific: Retail Supermarket */}
                {formData.buyerPersona === 'retail_supermarket' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Corporate GSTIN *
                      </label>
                      <input
                        type="text"
                        maxLength={15}
                        placeholder="e.g. 27AABCR5512L1Z9"
                        value={formData.gstin || ''}
                        onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                        className="w-full form-input text-sm bg-white font-mono uppercase"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Central DC Location *
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Bhiwandi DC / Chakan Logistics Park"
                        value={formData.centralHub || ''}
                        onChange={(e) => setFormData({ ...formData, centralHub: e.target.value })}
                        className="w-full form-input text-sm bg-white"
                      />
                    </div>
                  </div>
                )}

                {/* Persona-Specific: Institutional */}
                {formData.buyerPersona === 'institutional' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        FSSAI License / Canteen Reg No.
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 11523030000789"
                        value={formData.fssaiLicense || ''}
                        onChange={(e) => setFormData({ ...formData, fssaiLicense: e.target.value })}
                        className="w-full form-input text-sm bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Daily Meal Volume / Beneficiaries
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 2,500 meals / day"
                        value={formData.dailyMealVolume || ''}
                        onChange={(e) => setFormData({ ...formData, dailyMealVolume: e.target.value })}
                        className="w-full form-input text-sm bg-white"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 mt-6"
              >
                {isLoading ? 'Creating account...' : 'Register'}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center">
            <span className="text-sm text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-emerald-600 hover:text-emerald-500">
                Sign in
              </Link>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
