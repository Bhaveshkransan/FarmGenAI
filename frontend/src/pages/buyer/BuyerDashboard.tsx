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
  TrendingUp,
  TrendingDown,
  Building2,
  CheckCircle2,
  Trash2,
  Truck,
  Compass,
  Layers,
  ChevronRight,
  Info,
  ShieldCheck,
  AlertCircle,
  FileText
} from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import PostRequirementModal from '@/components/forms/PostRequirementModal';
import { matchCrops } from '@/utils/validation';

export const CANONICAL_7_CROPS = [
  { id: 'Soybean', name: 'Soybean', emoji: '🫘', type: 'MSP', benchmark: '₹48.92/kg', desc: 'Commercial Oilseed' },
  { id: 'Cotton', name: 'Cotton', emoji: '☁️', type: 'MSP', benchmark: '₹71.21/kg', desc: 'Fibre / Cash Crop' },
  { id: 'Jowar', name: 'Jowar (Sorghum)', emoji: '🌾', type: 'MSP', benchmark: '₹33.71/kg', desc: 'Nutri-Cereal' },
  { id: 'Onion', name: 'Onion', emoji: '🧅', type: 'Mandi Modal', benchmark: 'Market Modal', desc: 'APMC Benchmarked' },
  { id: 'Bajra', name: 'Bajra (Millet)', emoji: '🌾', type: 'MSP', benchmark: '₹26.25/kg', desc: 'Nutri-Cereal' },
  { id: 'Rice', name: 'Rice (Paddy)', emoji: '🌾', type: 'MSP', benchmark: '₹23.00/kg', desc: 'Staple Cereal' },
  { id: 'Sugarcane', name: 'Sugarcane', emoji: '🎋', type: 'FRP', benchmark: '₹3.40/kg', desc: 'Industrial Cash Crop' },
];

export const MAHARASHTRA_BUYER_HUBS = [
  'Pune',
  'Nashik',
  'Mumbai',
  'Latur',
  'Chhatrapati Sambhajinagar',
  'Ahmednagar',
  'Kolhapur',
  'Nagpur',
  'Solapur'
];

export default function BuyerDashboard() {
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const navigate = useNavigate();

  // State Management
  const [selectedCrop, setSelectedCrop] = useState<string>('Soybean');
  const [buyerLocation, setBuyerLocation] = useState<string>('Pune');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [hoveredPoint, setHoveredPoint] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'lots' | 'requirements'>('lots');
  const [isPostReqModalOpen, setIsPostReqModalOpen] = useState<boolean>(false);

  // Negotiation Modal State
  const [selectedListing, setSelectedListing] = useState<any | null>(null);
  const [targetOfferPrice, setTargetOfferPrice] = useState<number>(45);
  const [maxCeilingPrice, setMaxCeilingPrice] = useState<number>(52);
  const [isStartingNeg, setIsStartingNeg] = useState<boolean>(false);

  // Derive Buyer Persona
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
      case 'restaurant': return '🍽️ Restaurant Chain';
      case 'wholesale_trader': return '🏢 Wholesale Mandi Trader';
      case 'retail_supermarket': return '🛒 Retail Supermarket';
      case 'institutional': return '🏫 Institutional Canteen';
      default: return '🏭 Food Processing Enterprise';
    }
  }, [activeBuyerPersona]);

  // 1. Fetch Mandi Comparison Radar Data (MandiMitra for Buyers)
  const { data: mandiData, isLoading: isLoadingMandi } = useQuery({
    queryKey: ['mandi_comparison', selectedCrop, buyerLocation],
    queryFn: async () => {
      try {
        const res = await api.get(`/buyers/mandi-comparison?crop=${encodeURIComponent(selectedCrop)}&buyer_location=${encodeURIComponent(buyerLocation)}`);
        return res.data;
      } catch (err) {
        return null;
      }
    }
  });

  // 2. Fetch 7-Day ML Price Forecast Data
  const { data: forecastData } = useQuery({
    queryKey: ['price_forecast', selectedCrop, buyerLocation],
    queryFn: async () => {
      try {
        const res = await api.get(`/buyers/price-forecast?crop=${encodeURIComponent(selectedCrop)}&location=${encodeURIComponent(buyerLocation)}`);
        return res.data;
      } catch (err) {
        return null;
      }
    }
  });

  // 3. Fetch Authentic Produce Listings from Database
  const { data: listingsData, isLoading: isLoadingListings, refetch: refetchListings } = useQuery({
    queryKey: ['market_listings'],
    queryFn: async () => {
      try {
        const res = await api.get('/listings');
        const items = res.data?.data || res.data;
        if (Array.isArray(items) && items.length > 0) return items;
      } catch (err) {}
      return [];
    }
  });

  // 4. Fetch Buyer Requirements
  const { data: requirementsData, refetch: refetchRequirements } = useQuery({
    queryKey: ['buyer_requirements'],
    queryFn: async () => {
      try {
        const res = await api.get('/requirements');
        return res.data?.data || [];
      } catch (err) {
        return [];
      }
    }
  });

  // 5. Fetch Active Negotiations
  const { data: negotiationsData, refetch: refetchNegotiations } = useQuery({
    queryKey: ['active_negotiations'],
    queryFn: async () => {
      try {
        const res = await api.get('/negotiations');
        return res.data?.data || res.data || [];
      } catch (err) {
        return [];
      }
    },
    refetchInterval: 5000
  });

  // Filter listings
  const allListings = useMemo(() => {
    return (listingsData || []).filter((item: any) => item && item.crop);
  }, [listingsData]);

  const filteredListings = useMemo(() => {
    let list = allListings;
    if (selectedCrop) {
      list = list.filter((item: any) => matchCrops(item.crop, selectedCrop));
    }
    const term = (searchTerm || '').toLowerCase().trim();
    if (!term) return list;
    return list.filter((item: any) =>
      matchCrops(item.crop, term) ||
      (item.crop && String(item.crop).toLowerCase().includes(term)) ||
      (item.farmer_name && String(item.farmer_name).toLowerCase().includes(term)) ||
      (item.location && String(item.location).toLowerCase().includes(term)) ||
      (item.variety && String(item.variety).toLowerCase().includes(term))
    );
  }, [allListings, selectedCrop, searchTerm]);

  // Crop count dictionary for cards
  const cropListingCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of CANONICAL_7_CROPS) counts[c.id] = 0;
    for (const item of allListings) {
      for (const c of CANONICAL_7_CROPS) {
        if (matchCrops(item.crop, c.id)) {
          counts[c.id] = (counts[c.id] || 0) + 1;
        }
      }
    }
    return counts;
  }, [allListings]);

  // Open AI Negotiation Dialog from produce lot
  const handleOpenNegotiate = (item: any) => {
    setSelectedListing(item);
    const askPrice = Number(item.min_price) || Number(item.price) || 40;
    const mlPredicted = forecastData?.predicted_modal_price || askPrice;
    
    const sensibleTarget = Math.min(Math.round(mlPredicted * 0.96 * 10) / 10, askPrice);
    const sensibleCeiling = Math.round(askPrice * 1.05 * 10) / 10;

    setTargetOfferPrice(sensibleTarget);
    setMaxCeilingPrice(sensibleCeiling);
  };

  // Launch Autonomous Negotiation
  const handleLaunchNegotiation = async () => {
    if (!selectedListing) return;
    setIsStartingNeg(true);

    try {
      const payload = {
        crop: selectedListing.crop,
        quantity: Number(selectedListing.quantity) || 1000,
        min_price: Number(selectedListing.min_price) || 40,
        shelf_life: Number(selectedListing.shelf_life) || 30,
        location: selectedListing.location || 'Maharashtra',
        farmer_name: selectedListing.farmer_name || 'Maharashtra Farmer',
        buyer_mode: true,
        buyer_name: storedUser?.businessName || user?.name || user?.full_name || 'Buyer Enterprise',
        buyer_budget: (Number(selectedListing.quantity) || 1000) * maxCeilingPrice,
        buyer_max_quantity: Number(selectedListing.quantity) || 1000,
        buyer_target_price: targetOfferPrice,
        buyer_strategy: activeBuyerPersona,
        buyer_persona: activeBuyerPersona,
        max_rounds: 5
      };

      const res = await api.post('/negotiations/start-negotiation', payload);
      const negId = res.data?.negotiation_id || res.data?.id;

      addNotification(`Autonomous Buyer Agent dispatched! Room: ${negId || 'Active'}`, 'success');
      setSelectedListing(null);

      if (negId) {
        navigate(`/negotiations/${negId}`);
      }
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to dispatch Buyer Agent', 'error');
    } finally {
      setIsStartingNeg(false);
    }
  };

  // Launch or Re-enter Autonomous Negotiation for a Requirement
  const handleLaunchNegotiationForRequirement = async (req: any) => {
    const reqId = req.id || req._id;
    const existingNeg = (negotiationsData || []).find((n: any) => 
      (n.requirement_id && reqId && n.requirement_id === reqId) ||
      (matchCrops(n.crop, req.crop) && (n.status === 'ACTIVE' || n.status === 'IN_PROGRESS'))
    );

    if (existingNeg) {
      const existingId = existingNeg.id || existingNeg.negotiation_id;
      addNotification(`Opening active AI negotiation room for ${req.crop}...`, 'info');
      navigate(`/negotiations/${existingId}`);
      return;
    }

    setIsStartingNeg(true);
    try {
      const payload = {
        crop: req.crop,
        quantity: Number(req.quantity) || 1000,
        min_price: Number(req.target_price || req.expected_price || 40),
        shelf_life: Number(req.shelf_life) || 30,
        location: req.location || req.preferredLocation || 'Maharashtra',
        quality: req.quality_grade || req.quality || 'Grade A',
        buyer_mode: true,
        buyer_name: storedUser?.businessName || user?.name || user?.full_name || 'Buyer Enterprise',
        buyer_budget: Number(req.quantity) * Number(req.max_price || req.maxBudget || 60),
        buyer_max_quantity: Number(req.quantity) || 1000,
        buyer_target_price: Number(req.target_price || req.expected_price || 45),
        buyer_location: req.location || req.preferredLocation || 'Maharashtra',
        buyer_strategy: activeBuyerPersona,
        buyer_persona: activeBuyerPersona,
        max_rounds: 5,
        requirement_id: reqId
      };

      const res = await api.post('/negotiations/start-negotiation', payload);
      const negId = res.data?.negotiation_id || res.data?.id;

      addNotification(`Autonomous Buyer Agent dispatched! Room: ${negId || 'Active'}`, 'success');
      refetchNegotiations?.();
      if (negId) {
        navigate(`/negotiations/${negId}`);
      }
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to dispatch Buyer Agent', 'error');
    } finally {
      setIsStartingNeg(false);
    }
  };

  // Build SVG Chart Geometry for 7-Day Forecast
  const chartPoints = forecastData?.chart_points || [];
  const chartGeometry = useMemo(() => {
    if (!chartPoints || chartPoints.length === 0) return null;
    const prices = chartPoints.map((p: any) => p.price);
    const minPrice = Math.min(...prices) * 0.98;
    const maxPrice = Math.max(...prices) * 1.02;
    const range = maxPrice - minPrice || 1;

    const width = 650;
    const height = 180;
    const padding = 35;

    const coords = chartPoints.map((p: any, idx: number) => {
      const x = padding + (idx / (chartPoints.length - 1)) * (width - padding * 2);
      const y = height - padding - ((p.price - minPrice) / range) * (height - padding * 2);
      return { x, y, ...p };
    });

    const pathD = coords.reduce((acc: string, pt: any, idx: number) => {
      return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
    }, '');

    const areaD = `${pathD} L ${coords[coords.length - 1].x} ${height - padding} L ${coords[0].x} ${height - padding} Z`;

    return { coords, pathD, areaD, width, height, minPrice, maxPrice };
  }, [chartPoints]);

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      
      {/* ── 1. Top Enterprise Welcome Bar ── */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              Procurement Intelligence Hub
            </h1>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-200">
              {personaDisplayName}
            </span>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            Real-time APMC Mandi discovery, landed logistics analytics, and autonomous multi-agent negotiations.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          <button
            onClick={() => setIsPostReqModalOpen(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center gap-1.5 cursor-pointer active:scale-95"
          >
            <Plus size={16} /> Post Procurement Requirement
          </button>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>APMC Live</span>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-slate-400 font-medium">Trust Score</p>
              <p className="text-sm font-bold text-emerald-600">4.9/5</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Stat Overview Grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard 
          icon={<ShoppingCart className="text-emerald-600" />} 
          title="Verified Produce Lots" 
          value={allListings.length} 
          trend="35 active across Maharashtra" 
          color="emerald" 
        />
        <StatCard 
          icon={<Compass className="text-blue-600" />} 
          title="Monitored Mandis" 
          value="10 APMCs" 
          trend="Pune, Nashik, Latur, Solapur..." 
          color="blue" 
        />
        <StatCard 
          icon={<Truck className="text-indigo-600" />} 
          title="Avg. Inbound Freight" 
          value="₹1.85/kg" 
          trend="Optimized logistics routing" 
          color="purple" 
        />
        <StatCard 
          icon={<Activity className="text-amber-600" />} 
          title="Active Negotiations" 
          value={negotiationsData?.length || 0} 
          trend="LangGraph Autonomous Agents" 
          color="amber" 
        />
      </div>

      {/* ── 3. 7-Crop Quick-Filter Selector Cards ── */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers size={18} className="text-emerald-600" /> Canonical Maharashtra Crops
          </h2>
          <span className="text-xs text-slate-500">Strict 7-Crop Statutory Allowlist</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {CANONICAL_7_CROPS.map((crop) => {
            const isSelected = selectedCrop === crop.id;
            const count = cropListingCounts[crop.id] || 0;
            return (
              <button
                key={crop.id}
                onClick={() => {
                  setSelectedCrop(crop.id);
                  setSearchTerm('');
                }}
                className={`p-3.5 rounded-xl border text-left transition-all relative flex flex-col justify-between cursor-pointer ${
                  isSelected 
                    ? 'bg-emerald-800 text-white border-emerald-900 shadow-md ring-2 ring-emerald-500/20' 
                    : 'bg-white text-slate-800 border-slate-200/90 hover:border-emerald-300 hover:shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-2xl">{crop.emoji}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    isSelected ? 'bg-emerald-700 text-emerald-100' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {crop.type}
                  </span>
                </div>
                <div className="mt-2">
                  <p className="font-bold text-sm truncate">{crop.name}</p>
                  <p className={`text-[11px] mt-0.5 ${isSelected ? 'text-emerald-200' : 'text-slate-500'}`}>
                    {count} lots available
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 4. Main Intelligence Section: MandiMitra Radar & ML Price Forecast ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* ── Left Column: Mandi Procurement Radar (MandiMitra for Buyers) (7 Cols) ── */}
        <div className="lg:col-span-7 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Compass className="text-emerald-600" size={20} /> MandiMitra Procurement Radar
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Compares APMC terminal markets across Maharashtra for lowest landed procurement cost.
                </p>
              </div>

              {/* Location Selector */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-medium">Buyer Facility:</span>
                <select
                  value={buyerLocation}
                  onChange={(e) => setBuyerLocation(e.target.value)}
                  className="form-select text-xs py-1.5 px-2.5 rounded-lg border-slate-200 bg-slate-50 font-semibold text-slate-800 focus:ring-emerald-500"
                >
                  {MAHARASHTRA_BUYER_HUBS.map((hub) => (
                    <option key={hub} value={hub}>{hub}, MH</option>
                  ))}
                </select>
              </div>
            </div>

            {/* AI Recommendation Banner */}
            {mandiData?.recommendation && (
              <div className="mt-4 p-4 bg-emerald-50/90 border border-emerald-200/80 rounded-xl flex items-start gap-3 animate-in fade-in duration-300">
                <div className="p-2 bg-emerald-600 text-white rounded-lg mt-0.5">
                  <Sparkles size={16} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-emerald-800 uppercase tracking-wider bg-emerald-200/60 px-2 py-0.5 rounded">
                      {mandiData.recommendation.action}
                    </span>
                    <span className="text-xs font-bold text-emerald-950">
                      Best Procurement Option: {mandiData.recommendation.best_mandi}
                    </span>
                  </div>
                  <p className="text-xs text-emerald-900 mt-1.5 leading-relaxed font-medium">
                    {mandiData.recommendation.reason}
                  </p>
                </div>
              </div>
            )}

            {/* Mandi Comparison Table */}
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                    <th className="py-2.5 px-3">Mandi Terminal</th>
                    <th className="py-2.5 px-3">Distance</th>
                    <th className="py-2.5 px-3">APMC Modal</th>
                    <th className="py-2.5 px-3">Inbound Freight</th>
                    <th className="py-2.5 px-3 text-emerald-800 font-bold">Landed Cost</th>
                    <th className="py-2.5 px-3">Trend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isLoadingMandi ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        Querying real APMC mandi feeds & logistics models...
                      </td>
                    </tr>
                  ) : !mandiData?.mandis || mandiData.mandis.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400">
                        No active APMC mandis reporting for {selectedCrop}.
                      </td>
                    </tr>
                  ) : (
                    mandiData.mandis.map((m: any, idx: number) => (
                      <tr 
                        key={idx} 
                        className={`hover:bg-slate-50/80 transition-colors ${
                          m.is_best ? 'bg-emerald-50/40 font-semibold' : ''
                        }`}
                      >
                        <td className="py-3 px-3 flex items-center gap-1.5 text-slate-900 font-medium">
                          {m.mandi}
                          {m.is_best && (
                            <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] rounded font-bold">
                              Lowest
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-slate-600">{m.distance_km} km</td>
                        <td className="py-3 px-3 font-semibold text-slate-800">₹{m.modal_price}/kg</td>
                        <td className="py-3 px-3 text-slate-500">+₹{m.transport_cost}/kg</td>
                        <td className="py-3 px-3 font-bold text-emerald-700 text-sm">
                          ₹{m.landed_cost}/kg
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            m.trend === 'Bullish' ? 'bg-amber-100 text-amber-700' :
                            m.trend === 'Bearish' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {m.trend}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 mt-4 text-right">
            Landed Cost = APMC Modal Price + Freight (₹0.50/kg base + ₹0.0065/km)
          </p>
        </div>

        {/* ── Right Column: AI Market Intelligence & 7-Day Forecast Chart (5 Cols) ── */}
        <div className="lg:col-span-5 bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Bot className="text-emerald-600" size={20} /> AI Market Intelligence
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  XGBoost ML model trained on 13,179 APMC records.
                </p>
              </div>
            </div>

            {/* Price Badges Row */}
            <div className="grid grid-cols-3 gap-2 mt-4">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                <p className="text-[11px] text-slate-500 font-medium">Live Price</p>
                <p className="text-base font-bold text-slate-900 mt-0.5">
                  ₹{forecastData?.current_price || '--'}/kg
                </p>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                <p className="text-[11px] text-slate-500 font-medium">Market Trend</p>
                <div className="flex items-center justify-center gap-1 mt-0.5">
                  {forecastData?.trend === 'Bullish' ? (
                    <TrendingUp size={14} className="text-emerald-600" />
                  ) : forecastData?.trend === 'Bearish' ? (
                    <TrendingDown size={14} className="text-blue-600" />
                  ) : null}
                  <span className={`text-xs font-bold ${
                    forecastData?.trend === 'Bullish' ? 'text-emerald-700' :
                    forecastData?.trend === 'Bearish' ? 'text-blue-700' : 'text-slate-700'
                  }`}>
                    {forecastData?.trend || 'Stable'}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-center">
                <p className="text-[11px] text-emerald-800 font-medium">7-Day Forecast</p>
                <p className="text-base font-bold text-emerald-700 mt-0.5">
                  ₹{forecastData?.forecast_7day || '--'}/kg
                </p>
              </div>
            </div>

            {/* AI Strategic Advice Box */}
            <div className="mt-4 p-3.5 bg-blue-50/70 border border-blue-200/80 rounded-xl text-xs text-blue-900 leading-relaxed font-medium">
              <span className="font-bold text-blue-950 flex items-center gap-1.5 mb-1">
                <ShieldCheck size={14} className="text-blue-700" /> AI Strategic Procurement Advice:
              </span>
              {forecastData?.ai_advice || `Loading procurement intelligence for ${selectedCrop}...`}
            </div>

            {/* Interactive 7-Day Forecast Chart */}
            <div className="mt-5">
              <div className="flex justify-between items-center mb-1">
                <p className="text-xs font-bold text-slate-800">
                  {selectedCrop} Price Forecast (Next 7 Days)
                </p>
                <span className="text-[10px] text-slate-400">Hover points for price</span>
              </div>
              <p className="text-[11px] text-slate-500 mb-2">
                AI projected modal price in ₹/kg based on historical APMC data and market arrivals.
              </p>

              {chartGeometry ? (
                <div className="relative bg-slate-50/60 rounded-xl border border-slate-200/60 p-2 overflow-hidden">
                  <svg 
                    viewBox={`0 0 ${chartGeometry.width} ${chartGeometry.height}`} 
                    className="w-full h-44 overflow-visible"
                  >
                    <defs>
                      <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#059669" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#059669" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    <path d={chartGeometry.areaD} fill="url(#chartFill)" />

                    <path 
                      d={chartGeometry.pathD} 
                      fill="none" 
                      stroke="#059669" 
                      strokeWidth="2.5" 
                      strokeLinecap="round" 
                    />

                    {chartGeometry.coords.map((pt: any, idx: number) => {
                      if (pt.date === 'Today') {
                        return (
                          <line
                            key="today-line"
                            x1={pt.x}
                            y1={10}
                            x2={pt.x}
                            y2={chartGeometry.height - 25}
                            stroke="#047857"
                            strokeDasharray="3 3"
                            strokeWidth="1.5"
                          />
                        );
                      }
                      return null;
                    })}

                    {chartGeometry.coords.map((pt: any, idx: number) => (
                      <g 
                        key={idx} 
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredPoint(pt)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      >
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r={hoveredPoint?.date === pt.date ? 6 : pt.date === 'Today' ? 4.5 : 3.5}
                          fill={pt.date === 'Today' ? '#047857' : pt.is_projected ? '#10b981' : '#64748b'}
                          stroke="#ffffff"
                          strokeWidth="2"
                        />
                        {(idx % 2 === 0 || pt.date === 'Today') && (
                          <text
                            x={pt.x}
                            y={chartGeometry.height - 8}
                            textAnchor="middle"
                            fontSize="10"
                            fill={pt.date === 'Today' ? '#047857' : '#94a3b8'}
                            fontWeight={pt.date === 'Today' ? '700' : '500'}
                          >
                            {pt.date}
                          </text>
                        )}
                      </g>
                    ))}
                  </svg>

                  {hoveredPoint && (
                    <div 
                      className="absolute bg-slate-900 text-white px-2.5 py-1.5 rounded-lg text-xs shadow-lg pointer-events-none transform -translate-x-1/2 -translate-y-full"
                      style={{ 
                        left: `${(hoveredPoint.x / chartGeometry.width) * 100}%`, 
                        top: `${(hoveredPoint.y / chartGeometry.height) * 100}%` 
                      }}
                    >
                      <p className="font-semibold text-[10px] text-slate-300">{hoveredPoint.display_date || hoveredPoint.date}</p>
                      <p className="font-bold text-emerald-400">price: ₹{hoveredPoint.price}/kg</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-44 flex items-center justify-center bg-slate-50 rounded-xl text-slate-400 text-xs">
                  Loading ML forecast projection...
                </div>
              )}
            </div>
          </div>
        </div>

      </div>

      {/* ── 5. Marketplace Produce Lots & Buyer Requirements Section ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* ── Left Column: Tables with Tabs (8 Cols) ── */}
        <div className="lg:col-span-8 bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden flex flex-col justify-between">
          <div>
            {/* Tab Header */}
            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/60">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab('lots')}
                  className={`px-3.5 py-2 text-xs font-bold rounded-xl transition cursor-pointer flex items-center gap-2 ${
                    activeTab === 'lots' 
                      ? 'bg-emerald-600 text-white shadow-sm' 
                      : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                  }`}
                >
                  <ShoppingCart size={15} /> Produce Lots ({filteredListings.length})
                </button>
                <button
                  onClick={() => setActiveTab('requirements')}
                  className={`px-3.5 py-2 text-xs font-bold rounded-xl transition cursor-pointer flex items-center gap-2 ${
                    activeTab === 'requirements' 
                      ? 'bg-emerald-600 text-white shadow-sm' 
                      : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                  }`}
                >
                  <Target size={15} /> Your Requirements ({requirementsData?.length || 0})
                </button>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-56">
                  <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search farmer, district..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:ring-emerald-500"
                  />
                  {searchTerm && (
                    <button onClick={() => setSearchTerm('')} className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600">
                      <X size={12} />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* TAB 1: Produce Lots Table */}
            {activeTab === 'lots' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                      <th className="py-3 px-4">Crop & Variety</th>
                      <th className="py-3 px-4">Farmer / Location</th>
                      <th className="py-3 px-4">Volume</th>
                      <th className="py-3 px-4">Grade</th>
                      <th className="py-3 px-4">Asking Price</th>
                      <th className="py-3 px-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {isLoadingListings ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-400">
                          Querying Maharashtra produce lots...
                        </td>
                      </tr>
                    ) : filteredListings.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-400">
                          No active lots found for {selectedCrop} matching your filters.
                        </td>
                      </tr>
                    ) : (
                      filteredListings.map((item: any) => (
                        <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-3.5 px-4">
                            <p className="font-bold text-slate-900 text-sm">{item.crop}</p>
                            <p className="text-[11px] text-slate-500">{item.variety || 'Certified Lot'}</p>
                          </td>
                          <td className="py-3.5 px-4">
                            <p className="font-medium text-slate-800">{item.farmer_name || 'Maharashtra Farmer'}</p>
                            <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                              <MapPin size={10} /> {item.location}
                            </p>
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-slate-700">
                            {Number(item.quantity).toLocaleString()} kg
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              item.grade?.includes('A') ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
                            }`}>
                              {item.grade || 'Grade A'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-bold text-slate-900 text-sm">
                              ₹{item.min_price || item.expected_price}/kg
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <button
                              onClick={() => handleOpenNegotiate(item)}
                              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3.5 py-1.5 rounded-lg text-xs shadow-sm transition-all flex items-center gap-1.5 mx-auto cursor-pointer"
                            >
                              <Zap size={13} className="text-amber-300" />
                              Negotiate with AI
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB 2: Your Active Requirements */}
            {activeTab === 'requirements' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                      <th className="py-3 px-4">Required Commodity</th>
                      <th className="py-3 px-4">Target Quantity</th>
                      <th className="py-3 px-4">Target / Max Price</th>
                      <th className="py-3 px-4">Delivery Facility</th>
                      <th className="py-3 px-4">Logistics</th>
                      <th className="py-3 px-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {!requirementsData || requirementsData.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-400">
                          No active procurement requirements posted yet.<br />
                          Click "+ Post Procurement Requirement" above to define your volume & quality needs.
                        </td>
                      </tr>
                    ) : (
                      requirementsData.map((req: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-3.5 px-4">
                            <p className="font-bold text-slate-900 text-sm">{req.crop}</p>
                            <p className="text-[11px] text-slate-500">{req.quality_grade || 'Grade A'}</p>
                          </td>
                          <td className="py-3.5 px-4 font-bold text-slate-800">
                            {Number(req.quantity).toLocaleString()} {req.unit || 'kg'}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-bold text-emerald-700">₹{req.target_price || req.maxBudget}/kg</span>
                            <span className="text-slate-400 text-[10px]"> (Max ₹{req.max_price || req.maxBudget}/kg)</span>
                          </td>
                          <td className="py-3.5 px-4 text-slate-600">
                            {req.location || req.preferredLocation || 'Maharashtra'}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              req.transportRequired || req.transport_required ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-600'
                            }`}>
                              {req.transportRequired || req.transport_required ? 'Freight Required' : 'Self-Arranged'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <button
                                onClick={() => handleLaunchNegotiationForRequirement(req)}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow-sm transition flex items-center gap-1.5 cursor-pointer"
                                title="Launch or Enter AI Negotiation Room"
                              >
                                <Zap size={13} className="fill-amber-300 text-amber-300" />
                                <span>Negotiate with AI</span>
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedCrop(req.crop);
                                  setActiveTab('lots');
                                }}
                                className="px-2.5 py-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg font-semibold text-xs transition cursor-pointer"
                              >
                                Lots →
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

          </div>
          
          <div className="p-4 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 flex justify-between items-center">
            <span>Showing {activeTab === 'lots' ? filteredListings.length : (requirementsData?.length || 0)} items in Maharashtra</span>
            <span className="font-medium text-emerald-700">Autonomous multi-agent matching ready</span>
          </div>
        </div>

        {/* ── Right Column: Active Negotiations & Live Updates (4 Cols) ── */}
        <div className="lg:col-span-4 space-y-6">

          {/* Active Negotiations */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5">
            <h2 className="font-bold text-base text-slate-900 mb-3 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Activity size={18} className="text-emerald-600" /> Your Active Negotiations
              </span>
              <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                {negotiationsData?.length || 0} Live
              </span>
            </h2>

            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {!negotiationsData || negotiationsData.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No active negotiations found.<br />Click "Negotiate with AI" on any lot above to launch.
                </div>
              ) : (
                negotiationsData.slice(0, 5).map((neg: any, idx: number) => {
                  const negId = neg.id || neg.negotiation_id;
                  return (
                    <div 
                      key={negId || idx} 
                      className="p-3 bg-slate-50 hover:bg-slate-100/90 rounded-xl border border-slate-200/70 transition cursor-pointer flex justify-between items-center group"
                      onClick={() => navigate(`/negotiations/${negId}`)}
                    >
                      <div>
                        <p className="font-bold text-xs text-slate-900 group-hover:text-emerald-700 transition">{neg.crop || 'Produce Lot'}</p>
                        <p className="text-[11px] text-slate-500">
                          {neg.quantity ? `${Number(neg.quantity).toLocaleString()} kg` : '1,000 kg'} • {neg.location || 'Maharashtra'}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          neg.status === 'DEAL' || neg.status === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-800' :
                          neg.status === 'ACTIVE' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {neg.status || 'ACTIVE'}
                        </span>
                        <p className="text-[11px] text-emerald-600 font-semibold mt-1 flex items-center gap-0.5 justify-end group-hover:underline">
                          Enter Room <ChevronRight size={12} />
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Live Market Updates Sidebar */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5">
            <h2 className="font-bold text-base text-slate-900 mb-3 flex items-center gap-2">
              <AlertCircle size={18} className="text-blue-600" /> Live Market Feeds
            </h2>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-emerald-50/70 border border-emerald-100 rounded-xl">
                <p className="font-bold text-emerald-900">MandiMitra Alert</p>
                <p className="text-slate-600 mt-1">
                  Pune APMC: Soybean modal rate settled at ₹33.29/kg with 180 MT inbound arrivals.
                </p>
              </div>
              <div className="p-3 bg-blue-50/70 border border-blue-100 rounded-xl">
                <p className="font-bold text-blue-900">Buyer Agent Matching</p>
                <p className="text-slate-600 mt-1">
                  Matching against 6 criteria: Crop, Quantity, Quality Grade, Location, Price & Freight.
                </p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200/70 rounded-xl">
                <p className="font-bold text-slate-800">Processing Industry Insight</p>
                <p className="text-slate-600 mt-1">
                  Crushing units in Solapur & Latur are paying premium for Grade A low-moisture oilseeds.
                </p>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* ── 6. Autonomous Buyer Agent Negotiation Launch Modal (from Lot) ── */}
      {selectedListing && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-emerald-600 text-white rounded-lg">
                  <Bot size={18} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">
                    Dispatch Autonomous Buyer Agent
                  </h3>
                  <p className="text-xs text-slate-500">
                    Negotiating on {selectedListing.crop} ({selectedListing.farmer_name})
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedListing(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 text-xs">
              
              {/* Listing Overview Card */}
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 grid grid-cols-2 gap-2 text-slate-700">
                <div>
                  <span className="text-slate-400 text-[11px]">Commodity:</span>
                  <p className="font-bold text-slate-900">{selectedListing.crop} ({selectedListing.variety || 'Lot'})</p>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Farmer Location:</span>
                  <p className="font-bold text-slate-900">{selectedListing.location}</p>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Quantity Available:</span>
                  <p className="font-bold text-slate-900">{selectedListing.quantity} kg</p>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Farmer Asking Price:</span>
                  <p className="font-bold text-emerald-700">₹{selectedListing.min_price || selectedListing.expected_price}/kg</p>
                </div>
              </div>

              {/* Economic Target Input */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Buyer Target Price (₹/kg) *
                  </label>
                  <p className="text-[10px] text-slate-500 mb-1.5">Ideal purchase settlement price</p>
                  <input
                    type="number"
                    step="0.5"
                    value={targetOfferPrice}
                    onChange={(e) => setTargetOfferPrice(Number(e.target.value))}
                    className="w-full form-input text-xs rounded-lg border-emerald-300 focus:ring-emerald-500 bg-emerald-50/30 font-bold text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Maximum Ceiling Price (₹/kg) *
                  </label>
                  <p className="text-[10px] text-slate-500 mb-1.5">Strict walk-away limit</p>
                  <input
                    type="number"
                    step="0.5"
                    value={maxCeilingPrice}
                    onChange={(e) => setMaxCeilingPrice(Number(e.target.value))}
                    className="w-full form-input text-xs rounded-lg border-slate-300 focus:ring-slate-500 bg-slate-50 font-bold text-slate-900"
                  />
                </div>
              </div>

              {/* Guardrails Info */}
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-950 text-[11px] leading-relaxed">
                <p className="font-bold mb-0.5">Autonomous RL Policy & Safety Guardrails Active:</p>
                BuyerAgent will defend your ceiling price of <strong>₹{maxCeilingPrice}/kg</strong> and negotiate down toward 
                your target price of <strong>₹{targetOfferPrice}/kg</strong>, benchmarking offers against real APMC modal rates.
              </div>

              {/* Total Budget Preview */}
              <div className="flex justify-between items-center py-2 px-3 bg-slate-100/70 rounded-lg text-slate-600">
                <span>Maximum Total Budget Allocation:</span>
                <span className="font-bold text-slate-900 text-sm">
                  ₹{((selectedListing.quantity || 1000) * maxCeilingPrice).toLocaleString()}
                </span>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-5 border-t border-slate-100 flex justify-end gap-3 bg-slate-50">
              <button
                onClick={() => setSelectedListing(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleLaunchNegotiation}
                disabled={isStartingNeg}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-2 rounded-xl text-xs shadow-md transition flex items-center gap-2 disabled:opacity-50"
              >
                {isStartingNeg ? (
                  <>Launching Agent...</>
                ) : (
                  <>
                    <Zap size={14} className="text-amber-300" />
                    Dispatch Autonomous Buyer Agent
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
      )}

      {/* ── 7. Multi-Step Post Procurement Requirement Modal ── */}
      <PostRequirementModal
        isOpen={isPostReqModalOpen}
        onClose={() => setIsPostReqModalOpen(false)}
        initialCrop={selectedCrop}
        onSuccess={(data) => {
          refetchRequirements();
          refetchNegotiations();
          if (data?.negId) {
            navigate(`/negotiations/${data.negId}`);
          }
        }}
      />

    </div>
  );
}
