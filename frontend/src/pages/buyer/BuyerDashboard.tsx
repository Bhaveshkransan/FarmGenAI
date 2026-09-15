import React, { useState, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { 
  ShoppingCart, 
  Target, 
  Wallet, 
  Activity, 
  Search, 
  Plus, 
  X, 
  Zap, 
  RefreshCw, 
  Bot, 
  MapPin, 
  Clock, 
  Sparkles,
  ArrowRight,
  TrendingDown,
  Building2,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import ChartCard from '@/components/ui/ChartCard';
import PostRequirementForm from '@/components/forms/PostRequirementForm';
import { matchCrops, TOP_MAHARASHTRA_CROPS } from '@/utils/validation';

// Baseline market trends
const budgetData = [
  { name: 'Mon', value: 120000 },
  { name: 'Tue', value: 250000 },
  { name: 'Wed', value: 450000 },
  { name: 'Thu', value: 300000 },
  { name: 'Fri', value: 850000 },
  { name: 'Sat', value: 950000 },
  { name: 'Sun', value: 1100000 },
];

// Fallback produce items ensuring immediate rich interactive data
const FALLBACK_LISTINGS = [
  { id: 'prod_1', farmer_name: 'Rajesh Kumar', crop: 'Tomato', quantity: 500, min_price: 20, shelf_life: 5, quality: 'A', location: 'Nashik, Maharashtra', status: 'ACTIVE' },
  { id: 'prod_2', farmer_name: 'Sita Devi', crop: 'Onion', quantity: 800, min_price: 18, shelf_life: 30, quality: 'B', location: 'Pune, Maharashtra', status: 'ACTIVE' },
  { id: 'prod_3', farmer_name: 'Anand Rao', crop: 'Potato', quantity: 1000, min_price: 22, shelf_life: 45, quality: 'A', location: 'Bangalore, Karnataka', status: 'ACTIVE' },
  { id: 'prod_4', farmer_name: 'Gurpreet Singh', crop: 'Wheat', quantity: 3000, min_price: 25, shelf_life: 120, quality: 'A', location: 'Ludhiana, Punjab', status: 'ACTIVE' },
  { id: 'prod_5', farmer_name: 'Vijay Patel', crop: 'Cotton', quantity: 1500, min_price: 52, shelf_life: 365, quality: 'B', location: 'Ahmedabad, Gujarat', status: 'ACTIVE' },
  { id: 'prod_6', farmer_name: 'Lakshmi Bai', crop: 'Spinach', quantity: 200, min_price: 24, shelf_life: 3, quality: 'A', location: 'Mysore, Karnataka', status: 'ACTIVE' },
];

export default function BuyerDashboard() {
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'listings' | 'requirements'>('listings');
  const [isPostModalOpen, setIsPostModalOpen] = useState(false);
  const [matchedRequirement, setMatchedRequirement] = useState<any | null>(null);

  // Negotiation Launch Dialog State
  const [selectedListing, setSelectedListing] = useState<any>(null);
  const [targetOfferPrice, setTargetOfferPrice] = useState<number>(20);
  const [maxCeilingPrice, setMaxCeilingPrice] = useState<number>(25);
  const [isStartingNeg, setIsStartingNeg] = useState(false);

  // Directly derive active persona from registration / profile inputs
  const storedUser = useMemo(() => {
    try {
      const s = localStorage.getItem('agri_user');
      return s ? JSON.parse(s) : null;
    } catch {
      return null;
    }
  }, []);

  const activeBuyerPersona = storedUser?.buyerPersona || user?.buyerPersona || 'food_processing';
  const personaDisplayName = useMemo(() => {
    switch (activeBuyerPersona) {
      case 'restaurant': return '🍽️ Restaurant & Cloud Kitchen Chain';
      case 'wholesale_trader': return '🏢 Wholesale APMC Mandi Trader';
      case 'retail_supermarket': return '🛒 Retail Supermarket Chain';
      case 'institutional': return '🏫 Institutional Canteen';
      default: return '🏭 Food Processing Unit';
    }
  }, [activeBuyerPersona]);

  // 1. Fetch Market Produce Listings from API
  const { data: listingsData, isLoading: isLoadingListings, refetch: refetchListings } = useQuery({
    queryKey: ['market_listings'],
    queryFn: async () => {
      try {
        const res = await api.get('/listings');
        const items = res.data?.data || res.data;
        if (Array.isArray(items) && items.length > 0) {
          return items;
        }
      } catch (err) {
        console.warn('Using fallback produce listings:', err);
      }
      return FALLBACK_LISTINGS;
    }
  });

  // 2. Fetch Buyer Requirements from API (with local persistence)
  const { data: requirementsData, isLoading: isLoadingReqs, refetch: refetchRequirements } = useQuery({
    queryKey: ['buyer_requirements'],
    queryFn: async () => {
      try {
        const res = await api.get('/requirements');
        const items = res.data?.data || [];
        if (Array.isArray(items) && items.length > 0) {
          try {
            localStorage.setItem('agri_buyer_requirements', JSON.stringify(items));
          } catch (_) {}
          return items;
        }
      } catch (err) {
        console.warn('Using cached requirements fallback:', err);
      }
      try {
        const cached = localStorage.getItem('agri_buyer_requirements');
        if (cached) return JSON.parse(cached);
      } catch (_) {}
      return [];
    }
  });

  const allListings = useMemo(() => {
    const raw = (listingsData && listingsData.length > 0) ? listingsData : FALLBACK_LISTINGS;
    return raw.filter((item: any) => item && item.crop && String(item.crop).trim().length > 0);
  }, [listingsData]);

  // Filter listings based on search term and matched requirement
  const filteredListings = useMemo(() => {
    let list = allListings;

    // Filter by matched requirement if one is active
    if (matchedRequirement && matchedRequirement.crop) {
      list = list.filter((item: any) => {
        if (!item || !item.crop) return false;
        return matchCrops(item.crop, matchedRequirement.crop);
      });
    }

    const term = (searchTerm || '').toString().toLowerCase().trim();
    if (!term) return list;

    return list.filter(item => 
      matchCrops(item.crop, term) ||
      (item.crop && String(item.crop).toLowerCase().includes(term)) ||
      (item.farmer_name && String(item.farmer_name).toLowerCase().includes(term)) ||
      (item.location && String(item.location).toLowerCase().includes(term)) ||
      (item.quality && String(item.quality).toLowerCase().includes(term))
    );
  }, [allListings, searchTerm, matchedRequirement]);

  // Filter requirements based on search term (strictly ignoring blank/null personas, newest first)
  const filteredRequirements = useMemo(() => {
    const reqs = (requirementsData || []).filter(
      (r: any) => r && r.crop && String(r.crop).trim().length > 0
    );
    const sorted = [...reqs].reverse();
    const term = (searchTerm || '').toString().toLowerCase().trim();
    if (!term) return sorted;
    return sorted.filter(r => 
      matchCrops(r.crop, term) ||
      (r.crop && String(r.crop).toLowerCase().includes(term)) ||
      (r.location && String(r.location).toLowerCase().includes(term)) ||
      (r.status && String(r.status).toLowerCase().includes(term))
    );
  }, [requirementsData, searchTerm]);

  // Delete a requirement
  const handleDeleteRequirement = async (reqId: string) => {
    if (!reqId) return;
    try {
      await api.delete(`/requirements/${reqId}`);
      addNotification('success', 'Requirement removed.');
      refetchRequirements();
    } catch (err: any) {
      addNotification('error', err.response?.data?.detail || 'Failed to delete requirement');
    }
  };

  // Quick crop filters
  const handleFilterChip = (cropName: string) => {
    if (!cropName) return;
    setMatchedRequirement(null);
    setSearchTerm(String(cropName));
    setActiveTab('listings');
  };

  // Find suppliers matching a specific requirement
  const handleFindSuppliers = (req: any) => {
    if (!req || !req.crop) return;
    setMatchedRequirement(req);
    setSearchTerm('');
    setActiveTab('listings');
  };

  // Clear active requirement filter
  const handleClearRequirementFilter = () => {
    setMatchedRequirement(null);
    setSearchTerm('');
  };

  // Open Negotiation Dialog
  const handleOpenNegotiate = (item: any) => {
    setSelectedListing(item);
    const askPrice = item.min_price || item.price || 20;
    if (matchedRequirement && matchedRequirement.target_price) {
      setTargetOfferPrice(Number(matchedRequirement.target_price));
      setMaxCeilingPrice(Number(matchedRequirement.max_price || askPrice));
    } else {
      setTargetOfferPrice(Math.round(askPrice * 0.9 * 10) / 10);
      setMaxCeilingPrice(Math.round(askPrice * 1.1 * 10) / 10);
    }
  };

  // Submit and Launch AI Negotiation
  const handleLaunchNegotiation = async () => {
    if (!selectedListing) return;
    setIsStartingNeg(true);

    try {
      const payload = {
        crop: selectedListing.crop || 'Tomato',
        quantity: Number(selectedListing.quantity) || 500,
        min_price: Number(selectedListing.min_price) || 20,
        shelf_life: Number(selectedListing.shelf_life) || 5,
        location: selectedListing.location || 'Maharashtra',
        farmer_name: selectedListing.farmer_name || 'Farmer',
        buyer_mode: true,
        buyer_name: storedUser?.businessName || user?.name || user?.full_name || 'Buyer Enterprise',
        buyer_budget: (Number(selectedListing.quantity) || 500) * maxCeilingPrice,
        buyer_max_quantity: Number(selectedListing.quantity) || 500,
        buyer_target_price: targetOfferPrice,
        buyer_strategy: activeBuyerPersona,
        buyer_persona: activeBuyerPersona,
        max_rounds: 3
      };

      const res = await api.post('/negotiations/start-negotiation', payload);
      const negId = res.data?.negotiation_id || res.data?.id;

      addNotification(`Autonomous Buyer Agent dispatched! Room: ${negId || 'Active'}`, 'success');
      setSelectedListing(null);

      if (negId) {
        navigate(`/negotiations/${negId}`);
      } else {
        refetchListings();
      }
    } catch (err: any) {
      console.error('Failed to start negotiation:', err);
      addNotification(err.response?.data?.detail || err.message || 'Failed to dispatch AI agent', 'error');
    } finally {
      setIsStartingNeg(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500 pb-12">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-slate-100 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-800">Procurement Command Center</h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 rounded-full border border-blue-200 flex items-center gap-1">
              <Bot size={12} /> Autonomous Buyer Agent Active
            </span>
          </div>
          <p className="text-slate-500 mt-1">Search real-time farmer produce, post procurement requirements, and run multi-round AI negotiations.</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Search Box */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="text" 
              placeholder="Search crops, farmers, cities..." 
              className="pl-10 pr-9 py-2.5 bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm w-64 md:w-72 transition-all text-slate-900 placeholder-slate-500 font-semibold"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button 
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {/* Post Requirement Button */}
          <button 
            onClick={() => setIsPostModalOpen(true)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl transition shadow-sm flex items-center gap-2 whitespace-nowrap cursor-pointer"
          >
            <Plus size={18} /> Post Requirement
          </button>
        </div>
      </div>

      {/* Quick Search Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 font-semibold uppercase tracking-wider text-[11px] mr-1 shrink-0">MH Top Crops:</span>
        <button 
          onClick={() => setSearchTerm('')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer shrink-0 ${
            !searchTerm ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          All Commodities
        </button>
        <button 
          onClick={() => handleFilterChip('sugarcane')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('sugarcane') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🎋</span> Sugarcane
        </button>
        <button 
          onClick={() => handleFilterChip('soybean')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('soybean') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🌱</span> Soybean
        </button>
        <button 
          onClick={() => handleFilterChip('cotton')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('cotton') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>☁️</span> Cotton
        </button>
        <button 
          onClick={() => handleFilterChip('jowar')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('jowar') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🌾</span> Jowar (Sorghum)
        </button>
        <button 
          onClick={() => handleFilterChip('onion')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('onion') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🧅</span> Onion
        </button>
        <button 
          onClick={() => handleFilterChip('bajra')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('bajra') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🌾</span> Bajra (Pearl Millet)
        </button>
        <button 
          onClick={() => handleFilterChip('rice')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('rice') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🍚</span> Rice
        </button>
        <button 
          onClick={() => handleFilterChip('tomato')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('tomato') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🍅</span> Tomato
        </button>
        <button 
          onClick={() => handleFilterChip('wheat')}
          className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 shrink-0 ${
            (searchTerm || '').toLowerCase().includes('wheat') ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <span>🌾</span> Wheat
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={<Wallet />} title="Procurement Budget" value="₹15.0L" trend="Monthly limit" color="blue" />
        <StatCard icon={<ShoppingCart />} title="Active Requirements" value={requirementsData?.length || 3} trend="+2 this week" color="emerald" />
        <StatCard icon={<Activity />} title="Market Produce Listed" value={allListings.length} trend="Fresh supplies" color="amber" />
        <StatCard icon={<Target />} title="Autonomous Agent BATNA" value="Active" trend="Ollama qwen2.5:1.5b" color="purple" />
      </div>

      {/* Charts & AI Insights Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Trend Chart */}
        <div className="lg:col-span-2 flex">
          <div className="w-full">
            <ChartCard 
              title="Procurement Spend Trend" 
              subtitle="Daily expenditure across all agricultural commodities"
              data={budgetData} 
              color="#2563eb" 
              height={320}
            />
          </div>
        </div>

        {/* AI Market Insights */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <Sparkles size={18} className="text-amber-500" /> AI Market Insights
              </h2>
              <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">LIVE</span>
            </div>
            <p className="text-sm text-slate-500 mb-4">Real-time APMC Mandi price signals</p>
            
            <div className="space-y-3">
              {/* Insight 1: Onions */}
              <div className="p-4 bg-blue-50/70 border border-blue-100 rounded-xl hover:border-blue-300 transition">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-blue-600 flex items-center gap-1">
                    <TrendingDown size={14} /> PRICE DROP DETECTED
                  </p>
                </div>
                <p className="text-sm text-slate-800 font-semibold mt-1">Onion supply surging in Nashik Mandi.</p>
                <p className="text-xs text-slate-600 mt-1">Recommendation: Target price ₹17-18/kg. Bulk buying window open.</p>
                <button 
                  onClick={() => handleFilterChip('onion')}
                  className="mt-3 text-xs font-bold text-blue-700 bg-blue-100/80 hover:bg-blue-200 px-3 py-1.5 rounded-lg w-full transition flex items-center justify-center gap-1 cursor-pointer"
                >
                  Explore Onions ({allListings.filter(l => l.crop?.toLowerCase().includes('onion')).length} available) <ArrowRight size={13} />
                </button>
              </div>

              {/* Insight 2: Tomatoes */}
              <div className="p-4 bg-emerald-50/70 border border-emerald-100 rounded-xl hover:border-emerald-300 transition">
                <p className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 size={14} /> NEW VERIFIED SUPPLIERS
                </p>
                <p className="text-sm text-slate-800 font-semibold mt-1">High quality Tomatoes listed in Pune & Nashik.</p>
                <p className="text-xs text-slate-600 mt-1">Average asking: ₹20-22/kg. Shelf life: 5 days.</p>
                <button 
                  onClick={() => handleFilterChip('tomato')}
                  className="mt-3 text-xs font-bold text-emerald-700 bg-emerald-100/80 hover:bg-emerald-200 px-3 py-1.5 rounded-lg w-full transition flex items-center justify-center gap-1 cursor-pointer"
                >
                  View Tomato Listings <ArrowRight size={13} />
                </button>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400 flex items-center justify-between">
            <span>Powered by Ollama qwen2.5:1.5b</span>
            <button onClick={() => { refetchListings(); refetchRequirements(); }} className="text-blue-600 hover:underline flex items-center gap-1 cursor-pointer">
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
        </div>

      </div>

      {/* Main Interactive Marketplace Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        
        {/* Table Tabs Header */}
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('listings')}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition flex items-center gap-2 cursor-pointer ${
                activeTab === 'listings' 
                  ? 'bg-blue-600 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span>🌾</span> Market Produce Listings
              <span className={`px-2 py-0.5 rounded-full text-xs ${activeTab === 'listings' ? 'bg-blue-700 text-white' : 'bg-slate-200 text-slate-700'}`}>
                {filteredListings.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('requirements')}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition flex items-center gap-2 cursor-pointer ${
                activeTab === 'requirements' 
                  ? 'bg-blue-600 text-white shadow-sm' 
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <Target size={16} /> My Requirements
              <span className={`px-2 py-0.5 rounded-full text-xs ${activeTab === 'requirements' ? 'bg-blue-700 text-white' : 'bg-slate-200 text-slate-700'}`}>
                {filteredRequirements.length}
              </span>
            </button>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-500">
            {searchTerm && (
              <span className="bg-amber-50 text-amber-800 px-3 py-1 rounded-lg border border-amber-200 font-medium">
                Filtering by: "{searchTerm}"
              </span>
            )}
            <button 
              onClick={() => { refetchListings(); refetchRequirements(); }} 
              className="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition cursor-pointer"
              title="Refresh listings"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* Tab 1: Market Produce (Suppliers) */}
        {activeTab === 'listings' && (
          <div>
            {/* Active Matched Requirement Banner */}
            {matchedRequirement && (
              <div className="mx-5 my-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm animate-in fade-in duration-200">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-md">
                    <Target size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-slate-800 text-sm">
                        Suppliers Matching Requirement: <span className="text-blue-600 capitalize font-extrabold">{matchedRequirement.crop}</span>
                      </h3>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
                        {filteredListings.length} Supplier{filteredListings.length === 1 ? '' : 's'} Found
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1">
                      Volume needed: <span className="font-semibold text-slate-800">{Number(matchedRequirement.quantity || 0).toLocaleString()} kg</span> • 
                      Target Price: <span className="font-bold text-emerald-600">₹{matchedRequirement.target_price || matchedRequirement.min_price || '—'}/kg</span> • 
                      Max Ceiling: <span className="font-bold text-slate-700">₹{matchedRequirement.max_price || '—'}/kg</span>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClearRequirementFilter}
                    className="px-3.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold rounded-xl transition shadow-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    <X size={14} /> Clear Requirement Filter
                  </button>
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-100">
                  <tr>
                    <th className="px-5 py-3 font-medium">Farmer / Origin</th>
                    <th className="px-5 py-3 font-medium">Crop</th>
                    <th className="px-5 py-3 font-medium">Available Volume</th>
                    <th className="px-5 py-3 font-medium">Asking Price</th>
                    <th className="px-5 py-3 font-medium">Shelf Life</th>
                    <th className="px-5 py-3 font-medium">Quality</th>
                    <th className="px-5 py-3 font-medium text-right">Autonomous Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isLoadingListings ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center text-slate-400">
                        <div className="animate-pulse flex flex-col items-center gap-2">
                          <div className="h-4 w-32 bg-slate-200 rounded"></div>
                          <div className="h-3 w-48 bg-slate-100 rounded"></div>
                        </div>
                      </td>
                    </tr>
                  ) : filteredListings.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center">
                        <p className="text-slate-600 font-bold text-base mb-1">
                          {matchedRequirement 
                            ? `No suppliers currently matching ${matchedRequirement.crop}` 
                            : `No crops match "${searchTerm}"`}
                        </p>
                        <p className="text-slate-400 text-sm mb-4">
                          {matchedRequirement
                            ? `We couldn't find active listings for ${matchedRequirement.crop}. Try posting a wider target price or explore all produce.`
                            : 'Try clearing the search or post a new procurement requirement.'}
                        </p>
                        <button 
                          onClick={handleClearRequirementFilter} 
                          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-xs transition cursor-pointer"
                        >
                          View All Commodities
                        </button>
                      </td>
                    </tr>
                  ) : (
                    filteredListings.map((item: any, idx: number) => {
                      const askP = Number(item.min_price || item.price || 0);
                      const targetP = Number(matchedRequirement?.target_price || 0);
                      const maxP = Number(matchedRequirement?.max_price || 999999);
                      const isMatch = Boolean(matchedRequirement && matchedRequirement.crop);

                      return (
                        <tr key={item.id || idx} className="hover:bg-blue-50/30 transition">
                          <td className="px-5 py-4">
                            <p className="font-bold text-slate-800">{item.farmer_name || 'Farmer Producer'}</p>
                            <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                              <MapPin size={11} /> {item.location || 'Maharashtra'}
                            </p>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 text-base capitalize">
                                {item.crop}
                              </span>
                              {isMatch && (
                                askP <= targetP ? (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                    🎯 Target Price Match
                                  </span>
                                ) : askP <= maxP ? (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-200">
                                    ✅ In Budget
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-100 text-amber-800 border border-amber-200">
                                    ⚡ AI Negotiable
                                  </span>
                                )
                              )}
                            </div>
                          </td>
                          <td className="px-5 py-4 font-semibold text-slate-700">
                            {Number(item.quantity).toLocaleString()} kg
                          </td>
                          <td className="px-5 py-4">
                            <span className="font-bold text-emerald-600 text-base">
                              ₹{item.min_price || item.price}
                            </span>
                            <span className="text-xs text-slate-400"> / kg</span>
                          </td>
                          <td className="px-5 py-4">
                            <span className={`px-2.5 py-1 text-xs rounded-full font-bold flex items-center gap-1 w-fit ${
                              (item.shelf_life || 5) <= 3 ? 'bg-red-100 text-red-700' :
                              (item.shelf_life || 5) <= 7 ? 'bg-amber-100 text-amber-700' :
                              'bg-emerald-100 text-emerald-700'
                            }`}>
                              <Clock size={11} /> {item.shelf_life || 5} days
                            </span>
                          </td>
                          <td className="px-5 py-4">
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-700 text-xs font-bold rounded">
                              Grade {item.quality || 'A'}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-right">
                            <button
                              onClick={() => handleOpenNegotiate(item)}
                              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl text-xs transition shadow-sm inline-flex items-center gap-1.5 cursor-pointer"
                            >
                              <Zap size={14} className="fill-white" /> Negotiate with AI
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: My Requirements */}
        {activeTab === 'requirements' && (
          <div>
            {/* Requirements Explainer Card */}
            <div className="p-5 bg-gradient-to-r from-blue-50/80 to-slate-50 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-xs">
                  <Target size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-sm">Procurement Requirements & Auto-Matching</h3>
                  <p className="text-xs text-slate-500 mt-0.5 max-w-2xl leading-relaxed">
                    Post your demand specifications (crop, volume, price targets). AgriNegotiator stores your requirements and continuously scans all farmer produce listings. Click <strong>"Find Suppliers"</strong> on any requirement to immediately view and negotiate with matching farmers.
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setIsPostModalOpen(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl text-xs transition shadow-xs flex items-center gap-1.5 whitespace-nowrap self-start md:self-auto cursor-pointer"
              >
                <Plus size={15} /> Post New Requirement
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 text-slate-500 border-b border-slate-100">
                  <tr>
                    <th className="px-5 py-3 font-medium">Crop</th>
                    <th className="px-5 py-3 font-medium">Volume Required</th>
                    <th className="px-5 py-3 font-medium">Target Price</th>
                    <th className="px-5 py-3 font-medium">Max Price Ceiling</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isLoadingReqs ? (
                    <tr>
                      <td colSpan={6} className="p-12 text-center text-slate-400">Loading requirements...</td>
                    </tr>
                  ) : filteredRequirements.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-12 text-center">
                        <p className="text-slate-600 font-bold text-base mb-1">No requirements found</p>
                        <p className="text-slate-400 text-sm mb-4">Post a requirement so AI agents can match you with farmers.</p>
                        <button 
                          onClick={() => setIsPostModalOpen(true)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs transition cursor-pointer"
                        >
                          + Post Your First Requirement
                        </button>
                      </td>
                    </tr>
                  ) : (
                    filteredRequirements.map((req: any, idx: number) => {
                      const reqCrop = String(req.crop || '').toLowerCase().trim();
                      const matchingSuppliers = allListings.filter((l: any) => {
                        if (!l || !l.crop) return false;
                        const lCrop = String(l.crop).toLowerCase().trim();
                        return lCrop.includes(reqCrop) || reqCrop.includes(lCrop);
                      });
                      const matchCount = matchingSuppliers.length;

                      return (
                        <tr key={req.requirement_id || req.id || idx} className="hover:bg-slate-50/50 transition">
                          <td className="px-5 py-4 font-bold text-slate-800 text-base">
                            <div className="flex items-center gap-2">
                              <span className="capitalize">{req.crop}</span>
                              {matchCount > 0 && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                  {matchCount} Supplier{matchCount === 1 ? '' : 's'}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-5 py-4 text-slate-700 font-semibold">{Number(req.quantity || 0).toLocaleString()} kg</td>
                          <td className="px-5 py-4 font-bold text-blue-600">₹{req.target_price || req.min_price || '—'}/kg</td>
                          <td className="px-5 py-4 text-slate-500 font-medium">₹{req.max_price || req.budget || '—'}/kg</td>
                          <td className="px-5 py-4">
                            <span className="px-2.5 py-1 text-xs rounded-full font-bold bg-emerald-100 text-emerald-700">
                              {req.status || 'ACTIVE'}
                            </span>
                          </td>
                          <td className="px-5 py-4 text-right">
                            <div className="inline-flex items-center gap-2">
                              <button
                                onClick={() => handleFindSuppliers(req)}
                                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl text-xs transition shadow-xs inline-flex items-center gap-1.5 cursor-pointer"
                                title={`Find suppliers matching ${req.crop}`}
                              >
                                <span>Find Suppliers</span>
                                <span className="px-1.5 py-0.5 bg-blue-500/90 rounded text-[10px] font-extrabold">
                                  {matchCount}
                                </span>
                                <ArrowRight size={12} />
                              </button>
                              <button
                                onClick={() => handleDeleteRequirement(req.requirement_id || req.id)}
                                className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition cursor-pointer"
                                title="Delete requirement"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

      {/* Post Requirement Form Modal */}
      <PostRequirementForm 
        isOpen={isPostModalOpen} 
        onClose={() => setIsPostModalOpen(false)} 
        onSuccess={(created: any) => {
          refetchRequirements();
          refetchListings();
          if (created && created.crop) {
            setMatchedRequirement(created);
            setSearchTerm(String(created.crop));
            setActiveTab('listings');
            addNotification('success', `Found matching suppliers for ${created.crop}!`);
          } else {
            setActiveTab('listings');
          }
        }}
      />

      {/* Autonomous Negotiation Setup Modal */}
      {selectedListing && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-blue-100 text-blue-700 rounded-lg">
                  <Bot size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">Configure Buyer Agent</h3>
                  <p className="text-xs text-slate-500">Autonomous multi-round negotiation powered by Ollama</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedListing(null)} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5">
              
              {/* Target Produce Details */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex justify-between items-center">
                <div>
                  <p className="text-xs text-slate-500 font-medium">Selected Crop Listing</p>
                  <p className="text-lg font-bold text-slate-800">{selectedListing.crop} ({selectedListing.quantity} kg)</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <MapPin size={12} /> {selectedListing.farmer_name} • {selectedListing.location}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">Asking Floor</p>
                  <p className="text-lg font-bold text-emerald-600">₹{selectedListing.min_price}/kg</p>
                </div>
              </div>

              {/* Price Limits */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Target Counter Offer (₹/kg)</label>
                  <input 
                    type="number"
                    step="0.5"
                    value={targetOfferPrice}
                    onChange={(e) => setTargetOfferPrice(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-base font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Starting counter price</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Max Ceiling Price (₹/kg)</label>
                  <input 
                    type="number"
                    step="0.5"
                    value={maxCeilingPrice}
                    onChange={(e) => setMaxCeilingPrice(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-base font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">Hard walkaway BATNA</p>
                </div>
              </div>

              {/* Sourced directly from Registration */}
              <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">
                    Buyer Business Persona
                  </p>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">
                    {personaDisplayName}
                  </p>
                </div>
                <span className="text-[10px] bg-emerald-200 text-emerald-900 font-bold px-2 py-0.5 rounded-full border border-emerald-300">
                  Auto-loaded from Registration
                </span>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-5 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setSelectedListing(null)}
                className="px-4 py-2 border border-slate-200 text-slate-600 font-bold rounded-xl text-sm hover:bg-white transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isStartingNeg}
                onClick={handleLaunchNegotiation}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold rounded-xl text-sm transition shadow-sm flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isStartingNeg ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" /> Dispatching AI Agent...
                  </>
                ) : (
                  <>
                    <Zap size={16} className="fill-white" /> Launch Autonomous AI Agent
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
