import React, { useState, useMemo, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { API_CONFIG } from '@/config/api';
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
  Minus,
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
  FileText,
  Navigation,
  Edit2
} from 'lucide-react';
import StatCard from '@/components/ui/StatCard';
import PostRequirementModal from '@/components/forms/PostRequirementModal';
import TransactionValidationModal from '@/components/negotiation/TransactionValidationModal';
import { matchCrops } from '@/utils/validation';
import { CANONICAL_CROPS, MAHARASHTRA_DISTRICT_COORDINATES } from '@/constants/crops';

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
  const [isPostReqModalOpen, setIsPostReqModalOpen] = useState<boolean>(false);

  // Active Listings Table Filter States (Parity with Farmer Dashboard)
  const [listingsSearch, setListingsSearch] = useState<string>('');
  const [listingsFilterCrop, setListingsFilterCrop] = useState<string>('');

  // MandiMitra Fetching States (Parity with Farmer Dashboard)
  const [mandiLoading, setMandiLoading] = useState<boolean>(false);
  const [locationStatus, setLocationStatus] = useState<'idle' | 'locating' | 'found' | 'error'>('idle');

  // Real-time WebSocket connection matching Farmer Dashboard
  const wsUrl = `${API_CONFIG.WS_URL}/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);

  // Fallback crop for Mandi Radar & Forecast when "All Crops" is viewed in table
  const radarCrop = selectedCrop || 'Soybean';

  // Negotiation Modal State (Produce Lot)
  const [selectedListing, setSelectedListing] = useState<any | null>(null);
  const [targetOfferPrice, setTargetOfferPrice] = useState<number>(45);
  const [maxCeilingPrice, setMaxCeilingPrice] = useState<number>(52);
  const [isStartingNeg, setIsStartingNeg] = useState<boolean>(false);

  // Contract Modal State matching Farmer Dashboard
  const [isContractModalOpen, setIsContractModalOpen] = useState(false);
  const [contractModalDeal, setContractModalDeal] = useState<any>(null);

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
  const { data: mandiData, isLoading: isLoadingMandi, refetch: refetchMandi } = useQuery({
    queryKey: ['mandi_comparison', radarCrop, buyerLocation],
    queryFn: async () => {
      try {
        const res = await api.get(`/buyers/mandi-comparison?crop=${encodeURIComponent(radarCrop)}&buyer_location=${encodeURIComponent(buyerLocation)}`);
        return res.data;
      } catch (err) {
        return null;
      }
    }
  });

  // 2. Fetch 7-Day ML Price Forecast Data
  const { data: forecastData, refetch: refetchForecast } = useQuery({
    queryKey: ['price_forecast', radarCrop, buyerLocation],
    queryFn: async () => {
      try {
        const res = await api.get(`/buyers/price-forecast?crop=${encodeURIComponent(radarCrop)}&location=${encodeURIComponent(buyerLocation)}`);
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

  // 4. Fetch Buyer Requirements (Active Listings)
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

  // Real-Time Event Listener matching Farmer Dashboard
  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.event === 'NEGOTIATION_FINISHED' || lastMessage.event === 'DEAL_ACCEPTED') {
        refetchNegotiations();
        refetchListings();
        refetchRequirements();
      } else if (lastMessage.event === 'OFFER_MADE' || lastMessage.event === 'COUNTER_OFFER' || lastMessage.event === 'SYNC_STATE') {
        refetchNegotiations();
      }
    }
  }, [lastMessage, refetchNegotiations, refetchListings, refetchRequirements]);

  // Filter listings (Produce lots from farmers)
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

  // Filter Active Procurement Requirements (Buyer's Own Active Listings)
  const filteredRequirements = useMemo(() => {
    let list = requirementsData || [];
    if (listingsFilterCrop) {
      list = list.filter((r: any) => matchCrops(r.crop, listingsFilterCrop));
    }
    if (listingsSearch) {
      const term = listingsSearch.toLowerCase().trim();
      list = list.filter((r: any) =>
        (r.crop && String(r.crop).toLowerCase().includes(term)) ||
        (r.location && String(r.location).toLowerCase().includes(term)) ||
        (r.buyer_name && String(r.buyer_name).toLowerCase().includes(term)) ||
        (r.strategy && String(r.strategy).toLowerCase().includes(term))
      );
    }
    return list;
  }, [requirementsData, listingsFilterCrop, listingsSearch]);

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

  // MandiMitra Live Fetch Handler matching Farmer Dashboard
  const handleFindMandis = async () => {
    setMandiLoading(true);
    setLocationStatus('locating');
    try {
      await Promise.all([
        refetchMandi(),
        refetchForecast(),
        new Promise(resolve => setTimeout(resolve, 600))
      ]);
      setLocationStatus('found');
      addNotification(`Live Mandi feeds & landed costs updated for ${radarCrop} in ${buyerLocation}!`, 'success');
    } catch (err) {
      setLocationStatus('error');
      addNotification('Failed to fetch live Mandi feeds. Please try again.', 'error');
    } finally {
      setMandiLoading(false);
    }
  };

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

  // Launch Autonomous Negotiation from Produce Lot
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
        navigate(`/negotiations/${negId}`, { state: { autoStart: true } });
      }
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to dispatch Buyer Agent', 'error');
    } finally {
      setIsStartingNeg(false);
    }
  };

  // Launch or Re-enter Autonomous Negotiation for an Active Requirement Listing
  const handleLaunchNegotiationForRequirement = async (req: any) => {
    const reqId = req.id || req.requirement_id || req._id;
    const existingNeg = (negotiationsData || []).find((n: any) => 
      (n.requirement_id && reqId && (n.requirement_id === reqId || n.requirement_id === req.id || n.requirement_id === req.requirement_id)) ||
      (matchCrops(n.crop, req.crop) && (n.status === 'ACTIVE' || n.status === 'IN_PROGRESS' || n.status === 'ROUND_1' || n.status === 'ROUND_2' || n.status === 'ROUND_3' || n.status === 'NEGOTIATING'))
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
        min_price: Number(req.target_price || req.min_price || req.expected_price || 40),
        shelf_life: Number(req.shelf_life) || 30,
        location: req.location || req.preferredLocation || 'Maharashtra',
        quality: req.quality_grade || req.quality || 'Grade A',
        buyer_mode: true,
        buyer_name: storedUser?.businessName || user?.name || user?.full_name || 'Buyer Enterprise',
        buyer_budget: Number(req.quantity || 1000) * Number(req.max_price || req.maxBudget || 60),
        buyer_max_quantity: Number(req.quantity) || 1000,
        buyer_target_price: Number(req.target_price || req.min_price || req.expected_price || 45),
        buyer_location: req.location || req.preferredLocation || buyerLocation || 'Maharashtra',
        buyer_strategy: activeBuyerPersona,
        buyer_persona: activeBuyerPersona,
        max_rounds: 5,
        requirement_id: reqId
      };

      const res = await api.post('/negotiations/start-negotiation', payload);
      const negId = res.data?.negotiation_id || res.data?.id;

      addNotification(`Autonomous Buyer Agent dispatched! Room: ${negId || 'Active'}`, 'success');
      refetchNegotiations?.();
      refetchRequirements?.();
      if (negId) {
        navigate(`/negotiations/${negId}`, { state: { autoStart: true } });
      }
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to dispatch Buyer Agent', 'error');
    } finally {
      setIsStartingNeg(false);
    }
  };

  // Delete / Archive Requirement matching Farmer Listing expiration
  const handleDeleteRequirement = async (reqId: string, cropName: string) => {
    if (!window.confirm(`Are you sure you want to remove the procurement requirement for ${cropName}?`)) {
      return;
    }
    try {
      await api.delete(`/requirements/${reqId}`);
      addNotification(`Requirement for ${cropName} removed successfully`, 'success');
      refetchRequirements();
    } catch (err: any) {
      addNotification(err.response?.data?.detail || 'Failed to remove requirement', 'error');
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

  const TrendIcon = ({ trend }: { trend?: string }) => {
    if (trend === 'Bullish') return <TrendingUp size={14} className="text-emerald-500" />;
    if (trend === 'Bearish') return <TrendingDown size={14} className="text-red-500" />;
    return <Minus size={14} className="text-slate-400" />;
  };

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
            {/* Interactive APMC Live Sync matching Farmer Dashboard */}
            <button
              onClick={handleFindMandis}
              disabled={mandiLoading}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium cursor-pointer transition hover:shadow-xs ${
                isConnected ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100' : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
              }`}
              title="Click to fetch and sync live APMC mandi data"
            >
              <span className={`w-2 h-2 rounded-full ${isConnected ? (mandiLoading ? 'bg-emerald-500 animate-ping' : 'bg-emerald-500 animate-pulse') : 'bg-amber-500'}`}></span>
              <span className="flex items-center gap-1 font-semibold">
                <Navigation size={11} className={mandiLoading ? 'animate-spin text-emerald-600' : 'text-emerald-600'} />
                {mandiLoading ? 'Fetching...' : isConnected ? 'APMC Live Sync' : 'Connecting...'}
              </span>
            </button>
            <div className="text-right">
              <p className="text-[10px] text-slate-400 font-medium">Trust Score</p>
              <p className="text-sm font-bold text-emerald-600">4.9/5</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Stat Overview Grid (Parity with Farmer Dashboard) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard 
          icon={<ShoppingCart className="text-emerald-600" />} 
          title="Active Listings" 
          value={requirementsData?.length || 0} 
          trend="+1 this week" 
          color="emerald" 
        />
        <StatCard 
          icon={<TrendingUp className="text-blue-600" />} 
          title="Market Trend" 
          value={forecastData ? (forecastData.trend || "Stable") : (mandiData ? "Stable" : "Analyzing...")} 
          trend={radarCrop ? `${radarCrop} ${forecastData?.trend === 'Bullish' ? '+15%' : '-5%'}` : "Fetch Mandis"} 
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

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {/* All Crops Card */}
          <button
            onClick={() => {
              setSelectedCrop('');
              setSearchTerm('');
            }}
            className={`p-3.5 rounded-xl border text-left transition-all relative flex flex-col justify-between cursor-pointer ${
              !selectedCrop 
                ? 'bg-emerald-800 text-white border-emerald-900 shadow-md ring-2 ring-emerald-500/20' 
                : 'bg-white text-slate-800 border-slate-200/90 hover:border-emerald-300 hover:shadow-sm'
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <span className="text-2xl">🌱</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                !selectedCrop ? 'bg-emerald-700 text-emerald-100' : 'bg-slate-100 text-slate-600'
              }`}>
                ALL
              </span>
            </div>
            <div className="mt-2">
              <p className="font-bold text-sm truncate">All Crops</p>
              <p className={`text-[11px] mt-0.5 ${!selectedCrop ? 'text-emerald-200' : 'text-slate-400'}`}>
                {allListings.length} lots total
              </p>
            </div>
          </button>

          {/* 7 Canonical Crops */}
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
                  <p className={`text-[11px] mt-0.5 ${isSelected ? 'text-emerald-200' : 'text-slate-400'}`}>
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
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow">
                  <Compass size={20} className="text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    MandiMitra — Mandi Comparison & Radar
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Government mandis within 500km · Live APMC prices · Landed cost after freight
                  </p>
                </div>
              </div>

              {/* Location, Crop & Fetch Controls (Farmer Parity) */}
              <div className="flex items-center flex-wrap gap-2 text-xs">
                <select
                  value={buyerLocation}
                  onChange={(e) => setBuyerLocation(e.target.value)}
                  className="form-select text-xs py-1.5 px-2.5 rounded-xl border border-slate-200 bg-white font-semibold text-slate-800 focus:ring-2 focus:ring-emerald-400 outline-none cursor-pointer"
                  title="Select Buyer Hub Location"
                >
                  {MAHARASHTRA_BUYER_HUBS.map((hub) => (
                    <option key={hub} value={hub}>📍 {hub}, MH</option>
                  ))}
                </select>

                <select
                  value={radarCrop}
                  onChange={(e) => setSelectedCrop(e.target.value)}
                  className="form-select text-xs py-1.5 px-2.5 rounded-xl border border-slate-200 bg-white font-semibold text-slate-800 focus:ring-2 focus:ring-emerald-400 outline-none cursor-pointer"
                  title="Select Commodity Crop"
                >
                  {CANONICAL_CROPS.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>

                <button
                  id="find-mandis-btn"
                  onClick={handleFindMandis}
                  disabled={mandiLoading}
                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-3.5 py-2 rounded-xl text-xs font-bold transition shadow-sm cursor-pointer whitespace-nowrap active:scale-95"
                >
                  <Navigation size={13} className={mandiLoading ? 'animate-spin' : ''} />
                  {mandiLoading ? 'Fetching...' : locationStatus === 'idle' ? 'Find Mandis' : 'Refresh'}
                </button>
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
                        No active APMC mandis reporting for {radarCrop}.
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
              {forecastData?.ai_advice || `Loading procurement intelligence for ${radarCrop}...`}
            </div>

            {/* Interactive 7-Day Forecast Chart */}
            <div className="mt-5">
              <div className="flex justify-between items-center mb-1">
                <p className="text-xs font-bold text-slate-800">
                  {radarCrop} Price Forecast (Next 7 Days)
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
                      <g key={idx}>
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r={hoveredPoint === idx ? 6 : 4}
                          className="cursor-pointer transition-all fill-emerald-600 stroke-white stroke-2 hover:fill-emerald-800"
                          onMouseEnter={() => setHoveredPoint(idx)}
                          onMouseLeave={() => setHoveredPoint(null)}
                        />
                        <text
                          x={pt.x}
                          y={chartGeometry.height - 10}
                          textAnchor="middle"
                          className="text-[10px] fill-slate-500 font-medium"
                        >
                          {pt.date}
                        </text>
                      </g>
                    ))}
                  </svg>

                  {hoveredPoint !== null && (
                    <div 
                      className="absolute bg-slate-900 text-white text-[11px] px-2.5 py-1.5 rounded-lg shadow-xl pointer-events-none transform -translate-x-1/2 -translate-y-full transition-all"
                      style={{ 
                        left: `${(chartGeometry.coords[hoveredPoint].x / chartGeometry.width) * 100}%`,
                        top: `${(chartGeometry.coords[hoveredPoint].y / chartGeometry.height) * 100 - 10}%`
                      }}
                    >
                      <p className="font-bold">{chartGeometry.coords[hoveredPoint].date}</p>
                      <p className="text-emerald-400 font-semibold">₹{chartGeometry.coords[hoveredPoint].price}/kg</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-44 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400 text-xs">
                  Loading ML forecast projection...
                </div>
              )}
            </div>
          </div>
        </div>

      </div>

      {/* ── 5. Main Grid: Listings, Negotiations & Live Feed (Farmer Parity Layout matching Image 2) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Column (2 Cols): Active Listings & Active Negotiations */}
        <div className="lg:col-span-2 flex flex-col gap-6">

          {/* Card 1: Your Active Listings (Procurement Orders matching Image 2) */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex flex-wrap gap-4 justify-between items-center">
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-lg text-slate-800">Your Active Listings</h2>
                <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full border border-emerald-200">
                  Procurement Orders
                </span>
              </div>

              <div className="flex items-center gap-3">
                <input 
                  type="text" 
                  placeholder="Search..." 
                  value={listingsSearch}
                  onChange={e => setListingsSearch(e.target.value)}
                  className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                />
                <select 
                  value={listingsFilterCrop} 
                  onChange={e => setListingsFilterCrop(e.target.value)}
                  className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-400 font-medium"
                >
                  <option value="">All 7 Crops</option>
                  {CANONICAL_CROPS.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <button
                  id="new-listing-btn"
                  onClick={() => setIsPostReqModalOpen(true)}
                  className="text-sm font-medium text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg flex items-center gap-2 cursor-pointer active:scale-95"
                >
                  <Plus size={16} /> New Listing
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Crop</th>
                    <th className="px-5 py-3 font-medium">Volume</th>
                    <th className="px-5 py-3 font-medium">Base Price</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredRequirements.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-400">
                        No active procurement listings found. Click "+ New Listing" to post.
                      </td>
                    </tr>
                  ) : (
                    filteredRequirements.map((req: any) => {
                      const reqId = req.id || req.requirement_id || req._id;
                      const matchingNeg = (negotiationsData || []).find((n: any) => 
                        (n.requirement_id && (n.requirement_id === reqId || n.requirement_id === req.id || n.requirement_id === req.requirement_id)) ||
                        (matchCrops(n.crop, req.crop) && (n.status === 'ACTIVE' || n.status === 'IN_PROGRESS' || n.status === 'ROUND_1' || n.status === 'ROUND_2' || n.status === 'ROUND_3' || n.status === 'NEGOTIATING'))
                      );
                      const isNegotiating = Boolean(matchingNeg);
                      const status = isNegotiating ? 'NEGOTIATING' : (req.status || 'ACTIVE');

                      return (
                        <tr key={reqId} className="hover:bg-slate-50/50 transition">
                          <td className="px-5 py-4 font-medium text-slate-800">
                            <div className="flex flex-col">
                              <span className="font-bold text-slate-900">{req.crop}</span>
                              <span className="text-[11px] text-slate-400">{req.quality_grade || req.strategy || req.location || 'Grade A'}</span>
                            </div>
                          </td>
                          <td className="px-5 py-4 text-slate-600">
                            {Number(req.quantity || 1000).toLocaleString()} kg
                          </td>
                          <td className="px-5 py-4 font-medium text-emerald-600">
                            ₹{req.target_price || req.min_price || req.maxBudget || 45}/kg
                          </td>
                          <td className="px-5 py-4">
                            <span className={`px-2.5 py-1 text-xs rounded-full font-bold inline-flex items-center gap-1 ${
                              status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' :
                              status === 'NEGOTIATING' ? 'bg-blue-100 text-blue-700' :
                              status === 'DEAL' ? 'bg-purple-100 text-purple-700' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {status}
                            </span>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              {status === 'NEGOTIATING' ? (
                                <button
                                  onClick={() => {
                                    const negId = matchingNeg?.negotiation_id || matchingNeg?.id;
                                    if (negId) {
                                      navigate(`/negotiations/${negId}`);
                                    } else {
                                      navigate('/negotiations');
                                    }
                                  }}
                                  className="text-emerald-600 font-bold hover:underline text-xs whitespace-nowrap cursor-pointer"
                                >
                                  View Room
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleLaunchNegotiationForRequirement(req)}
                                  disabled={isStartingNeg}
                                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition shadow-sm whitespace-nowrap cursor-pointer active:scale-95 disabled:opacity-50"
                                >
                                  AI Match & Negotiate
                                </button>
                              )}

                              <button
                                title="Edit Requirement"
                                onClick={() => {
                                  setSelectedCrop(req.crop);
                                  setIsPostReqModalOpen(true);
                                }}
                                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
                              >
                                <Edit2 size={14} />
                              </button>

                              <button
                                title="Expire / Delete Listing"
                                onClick={() => handleDeleteRequirement(reqId, req.crop)}
                                className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition cursor-pointer"
                              >
                                <Trash2 size={14} />
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

          {/* Card 2: Your Active Negotiations (matching Image 2) */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center">
              <h2 className="font-bold text-lg text-slate-800">Your Active Negotiations</h2>
              <span className="text-xs bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full font-bold">
                {negotiationsData?.length || 0} Total Active
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Crop</th>
                    <th className="px-5 py-3 font-medium">Volume</th>
                    <th className="px-5 py-3 font-medium">Latest Price</th>
                    <th className="px-5 py-3 font-medium">Logistics / Carrier</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {!negotiationsData || negotiationsData.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-400">
                        No active negotiations found. Click "AI Match & Negotiate" on any listing above to start.
                      </td>
                    </tr>
                  ) : (
                    negotiationsData.map((neg: any) => {
                      const tp = typeof neg.transport_plan === 'string' && neg.transport_plan.startsWith('{')
                        ? JSON.parse(neg.transport_plan)
                        : neg.transport_plan;
                      const negId = neg.negotiation_id || neg.id;

                      return (
                        <tr key={negId} className="hover:bg-slate-50/50 transition">
                          <td className="px-5 py-4 font-medium text-slate-800">
                            <div className="flex flex-col">
                              <span className="font-bold text-slate-900">{neg.crop || 'Soybean'}</span>
                              {(neg.listing_id || neg.requirement_id) && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  Lot #{(neg.listing_id || neg.requirement_id).substring(0, 8)}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-5 py-4 text-slate-600">
                            {Number(neg.quantity || 1000).toLocaleString()} kg
                          </td>
                          <td className="px-5 py-4 font-medium text-emerald-600">
                            ₹{neg.final_price || neg.current_offer || neg.market_price || neg.min_price || neg.target_price || 0}/kg
                          </td>
                          <td className="px-5 py-4">
                            {tp ? (
                              <div className="flex flex-col">
                                <span className="font-semibold text-slate-800 text-xs flex items-center gap-1">
                                  <Truck size={12} className="text-emerald-600" />
                                  {tp.vehicle_name || tp.agent || 'Assigned Carrier'}
                                </span>
                                <span className="text-[10px] text-slate-500 font-medium">
                                  ₹{(tp.cost || tp.agreed_price || 0).toLocaleString()} • {tp.distance || '0'} km
                                </span>
                              </div>
                            ) : neg.status === 'DEAL' || neg.status === 'ACCEPTED' ? (
                              <span className="text-[11px] text-slate-400 italic">Dispatch Scheduled</span>
                            ) : (
                              <span className="text-[11px] text-slate-400">Coordinating...</span>
                            )}
                          </td>
                          <td className="px-5 py-4">
                            <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${
                              neg.status === 'DEAL' || neg.status === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-700' :
                              neg.status === 'NO_DEAL' || neg.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                              'bg-blue-100 text-blue-700'
                            }`}>
                              {neg.status || 'ACTIVE'}
                            </span>
                          </td>
                          <td className="px-5 py-4 flex items-center flex-wrap gap-2">
                            <button
                              onClick={() => navigate(`/negotiations/${negId}`)}
                              className="text-blue-600 font-bold hover:underline text-xs cursor-pointer"
                            >
                              View Room
                            </button>
                            {(neg.status === 'DEAL' || neg.status === 'ACCEPTED') && (
                              <button
                                onClick={() => {
                                  setContractModalDeal(neg);
                                  setIsContractModalOpen(true);
                                }}
                                className="text-emerald-700 font-bold hover:underline text-xs flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded-md border border-emerald-200 transition cursor-pointer"
                              >
                                <FileText size={11} /> Contract
                              </button>
                            )}
                            {tp && (
                              <button
                                onClick={() => navigate('/dashboard/transport')}
                                className="text-emerald-600 font-semibold hover:underline text-xs flex items-center gap-0.5 ml-1 cursor-pointer"
                              >
                                <Truck size={11} /> Fleet
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right Column (1 Col): Live Market Updates & Multi-Agent Engine (matching Image 2) */}
        <div className="flex flex-col gap-6">
          {/* Live Market Updates Card matching Image 2 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <h2 className="font-bold text-base text-slate-800 mb-3 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <AlertCircle size={18} className="text-emerald-600" /> Live Market Updates
              </span>
              <span className="text-[11px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-bold border border-emerald-100">
                APMC Realtime
              </span>
            </h2>
            <div className="space-y-4 text-xs">
              <div>
                <p className="font-semibold text-slate-500">Recent Activity</p>
                <p className="text-slate-800 mt-0.5 leading-relaxed font-medium">
                  Your latest requirement was indexed and matched against active farmer produce lots across Maharashtra.
                </p>
              </div>
              <div className="pt-3 border-t border-slate-100">
                <p className="font-semibold text-slate-500">Market Insight</p>
                <p className="text-slate-800 mt-0.5 leading-relaxed font-medium">
                  Local processors and solvent extractors are paying premium for Grade A low-moisture Soybean this week.
                </p>
              </div>
              <div className="pt-3 border-t border-slate-100">
                <p className="font-semibold text-slate-500">Logistics Optimization</p>
                <p className="text-slate-800 mt-0.5 leading-relaxed font-medium">
                  Average freight across Western Maharashtra stabilized at ₹1.85/kg with 15 verified carrier fleets standby.
                </p>
              </div>
            </div>
          </div>

          {/* Autonomous Multi-Agent Card */}
          <div className="bg-gradient-to-br from-emerald-900 to-slate-900 rounded-2xl p-5 text-white shadow-sm">
            <p className="text-emerald-300 text-xs font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <Activity size={14} className="text-emerald-400" /> Multi-Agent Engine
            </p>
            <h3 className="font-bold text-lg text-white">
              {negotiationsData?.length || 0} Negotiations Active
            </h3>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              LangGraph autonomous orchestrator automatically aligns buyer reservations with farmer listings.
            </p>
            <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">Contracts Executed:</span>
              <span className="font-bold text-emerald-400">
                {(negotiationsData || []).filter((n: any) => n.status === 'DEAL' || n.status === 'ACCEPTED').length} Signed
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* ── 6. Marketplace Produce Lots (Farmer Lots for Direct Discovery & Negotiation) ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/60">
          <div>
            <h2 className="font-bold text-lg text-slate-900 flex items-center gap-2">
              <ShoppingCart className="text-emerald-600" size={20} /> Verified Produce Lots (Supplier Discovery)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Direct farmgate produce lots across Maharashtra with certified moisture, quality grades, and instant AI negotiation.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative w-56">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search farmer, district..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:ring-emerald-500"
              />
            </div>
            {selectedCrop && (
              <button
                onClick={() => setSelectedCrop('')}
                className="text-[11px] text-emerald-800 hover:text-emerald-950 font-semibold bg-emerald-100/80 border border-emerald-300 px-2.5 py-1 rounded-lg flex items-center gap-1 cursor-pointer transition shadow-xs"
              >
                Clear Crop Filter
                <X size={12} className="ml-0.5 text-emerald-700" />
              </button>
            )}
          </div>
        </div>

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
                    No active lots found matching your filter.
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
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3.5 py-1.5 rounded-lg text-xs shadow-sm transition-all flex items-center gap-1.5 mx-auto cursor-pointer active:scale-95"
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
      </div>

      {/* ── 7. Autonomous Buyer Agent Negotiation Launch Modal (from Lot) ── */}
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
                className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
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
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleLaunchNegotiation}
                disabled={isStartingNeg}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-2 rounded-xl text-xs shadow-md transition flex items-center gap-2 disabled:opacity-50 cursor-pointer active:scale-95"
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

      {/* ── 8. Multi-Step Post Procurement Requirement Modal ── */}
      <PostRequirementModal
        isOpen={isPostReqModalOpen}
        onClose={() => setIsPostReqModalOpen(false)}
        initialCrop={radarCrop}
        onSuccess={(data) => {
          refetchRequirements();
          refetchNegotiations();
          if (data?.negId) {
            navigate(`/negotiations/${data.negId}`, { state: { autoStart: true } });
          }
        }}
      />

      {/* ── 9. APMC Validated Smart Contract Modal matching Farmer Dashboard ── */}
      <TransactionValidationModal
        isOpen={isContractModalOpen}
        onClose={() => setIsContractModalOpen(false)}
        dealData={contractModalDeal}
        buyerUser={user}
      />

    </div>
  );
}
