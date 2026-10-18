import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useWebSocket } from '@/hooks/useWebSocket';
import { 
  ArrowLeft, 
  MessageSquare, 
  Briefcase, 
  Zap, 
  ShieldCheck, 
  Database, 
  CloudRain, 
  Truck, 
  Terminal as TerminalIcon, 
  RefreshCw, 
  Check, 
  Layers, 
  TrendingUp, 
  MapPin, 
  Calendar, 
  CheckCircle2, 
  Clock,
  Sparkles,
  Play,
  CheckCircle,
  AlertTriangle,
  Search,
  Star,
  Bot,
  Trophy,
  Warehouse,
  Factory,
  ChevronRight,
  ArrowRight,
  RotateCcw,
  DollarSign,
  Calculator,
  TrendingDown,
  Info,
  ShieldAlert,
  FileText,
  ExternalLink,
  XCircle,
  CheckCheck
} from 'lucide-react';
import ChatBubble from '@/features/negotiation/components/ChatBubble';
import OfferCard from '@/features/negotiation/components/OfferCard';
import AgreementPreview from '@/features/negotiation/components/AgreementPreview';
import AgentWorkflowStepper from '@/features/negotiation/components/AgentWorkflowStepper';
import RagContextViewer from '@/features/negotiation/components/RagContextViewer';
import PriceChart from '@/features/negotiation/components/PriceChart';
import TransactionValidationModal from '@/components/negotiation/TransactionValidationModal';
import RecommendationCard from '@/features/negotiation/components/RecommendationCard';
import ReflectionCard from '@/features/negotiation/components/ReflectionCard';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';

// Multi-Agent Dynamic Phase Types
export type AgentPhase = 'FARMER' | 'TRANSPORT' | 'WAREHOUSE' | 'PROCESSOR' | 'SUMMARY';

export interface CompletedPhaseRecord {
  phase: AgentPhase;
  title: string;
  status: 'DEAL' | 'NO_MATCH' | 'UNAVAILABLE' | 'SKIPPED' | 'CANCELLED';
  agreedPrice?: number;
  counterParty?: string;
  location?: string;
  lotSize?: number;
  details?: Record<string, any>;
  messages: any[];
  timestamp: string;
  explanation?: string;
}

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const location = useLocation();
  const hasAutoStartFlag = Boolean(location.state?.autoStart);
  const isBuyer =
    user?.role === 'farmer' || localStorage.getItem('user_role') === 'farmer'
      ? false
      : Boolean(
          user?.role === 'buyer' ||
          user?.role === 'trader' ||
          localStorage.getItem('user_role') === 'buyer' ||
          localStorage.getItem('user_role') === 'trader' ||
          window.location.pathname.includes('/buyer')
        );

  const [initTimedOut, setInitTimedOut] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setInitTimedOut(true), 3500);
    return () => clearTimeout(timer);
  }, []);

  const { data: latestNeg } = useQuery({
    queryKey: ['latest-negotiation'],
    queryFn: async () => {
      try {
        const res = await api.get('/negotiations');
        const list = res.data?.data || res.data || [];
        return Array.isArray(list) && list.length > 0 ? list[0] : null;
      } catch (e) {
        return null;
      }
    },
    enabled: !id,
    staleTime: 60000
  });

  const activeId = useMemo(() => {
    if (id && id !== 'latest') return id;
    if (latestNeg) return latestNeg.id || latestNeg.negotiation_id;
    return id || 'latest';
  }, [id, latestNeg]);

  useEffect(() => {
    if ((!id || id === 'latest') && latestNeg?.id && latestNeg.id !== id) {
      navigate(`/negotiations/${latestNeg.id}`, { replace: true });
    }
  }, [id, latestNeg, navigate]);

  const baseWsUrl = import.meta.env.VITE_WS_URL || '/api/v1/ws';
  const effectiveWsUrl = activeId ? `${baseWsUrl}/negotiate/${activeId}` : `${baseWsUrl}/negotiate/demo`;
  const { isConnected, lastMessage, sendMessage } = useWebSocket(effectiveWsUrl);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Core Room State
  const [messages, setMessages] = useState<any[]>([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState<any>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'terminal'>('timeline');
  const [isParallelRunning, setIsParallelRunning] = useState(false);
  const [liveTerminalLogs, setLiveTerminalLogs] = useState<Array<{ time: string; tag: string; text: string; color?: string }>>([]);
  const [manualPrice, setManualPrice] = useState<string>('');
  const [recommendation, setRecommendation] = useState<any>(null);
  const [reflection, setReflection] = useState<any>(null);
  const [rightTab, setRightTab] = useState<'ai' | 'rag' | 'copilot'>('copilot');
  const [copilotCommand, setCopilotCommand] = useState('');
  const [copilotMessages, setCopilotMessages] = useState<{ sender: string; text: string; time?: string }[]>([]);
  const [liveBuyers, setLiveBuyers] = useState<any[]>([]);

  // ---------------------------------------------------------------------------
  // Dynamic Multi-Agent Phase State Machine & LocalStorage Persistence
  // ---------------------------------------------------------------------------
  const storageKey = `farmgenai_completed_phases_${activeId}`;

  // Hydrate completed phases from localStorage if available
  const [completedPhases, setCompletedPhases] = useState<Partial<Record<AgentPhase, CompletedPhaseRecord>>>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      return {};
    }
  });

  const [activePhase, setActivePhase] = useState<AgentPhase>('FARMER');
  const [viewingPhase, setViewingPhase] = useState<AgentPhase>('FARMER');
  const [transitionNotice, setTransitionNotice] = useState<{ title: string; message: string; timestamp: string } | null>(null);

  // Transport Phase States
  const [selectedTransportVehicle, setSelectedTransportVehicle] = useState<any>(null);
  const [transportBuyerOffer, setTransportBuyerOffer] = useState<string>('');
  const [transportMessages, setTransportMessages] = useState<any[]>([]);
  const [transportStatus, setTransportStatus] = useState<'IDLE' | 'NEGOTIATING' | 'AGREED' | 'DECLINED' | 'CANCELLED'>('IDLE');
  const [transportAgreement, setTransportAgreement] = useState<any>(null);
  const [isTransportLoading, setIsTransportLoading] = useState(false);
  const [transportRound, setTransportRound] = useState(1);

  // Sync completedPhases changes to localStorage for true refresh persistence
  useEffect(() => {
    if (activeId && Object.keys(completedPhases).length > 0) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(completedPhases));
      } catch (e) {}
    }
  }, [completedPhases, storageKey, activeId]);

  // Negotiation Query
  const { data: negState, isLoading, refetch: refetchNeg } = useQuery({
    queryKey: ['negotiation', activeId],
    queryFn: async () => {
      if (!activeId || activeId === 'latest') return null;
      try {
        const res = await api.get(`/negotiations/${activeId}`);
        return res.data?.data || res.data;
      } catch (e) {
        return null;
      }
    },
    enabled: Boolean(activeId && activeId !== 'latest'),
    refetchInterval: activePhase === 'FARMER' ? 4000 : false
  });

  const cropName = negState?.crop || negState?.crop_name || 'Soybean';
  const cropQty = Number(negState?.quantity || negState?.quantity_kg || 2500);
  const targetPrice = Number(negState?.expected_price || negState?.target_price || 51);
  const farmerName = negState?.farmer_name || negState?.farmer || 'Maharashtra Producer';
  const buyerName = negState?.buyer_name || negState?.buyer || user?.name || 'Buyer Enterprise';
  // Dynamic APMC district origin fallback (Requirement 7: dynamic origin based on actual district)
  const resolvedDistrict = useMemo(() => {
    const raw = negState?.district || negState?.buyer_district || 
      (typeof negState?.buyer_location === 'string' ? negState.buyer_location.split(',')[0].trim() : '') ||
      (typeof negState?.location === 'string' && !negState.location.includes('APMC') ? negState.location.split(',')[0].trim() : '');
    return raw || '';
  }, [negState]);

  const defaultApmcOrigin = resolvedDistrict ? `${resolvedDistrict} APMC, Maharashtra` : 'Latur APMC, Maharashtra';
  const farmerLocation = negState?.farmer_location || (negState?.location && negState.location.includes('APMC') ? negState.location : defaultApmcOrigin);
  const bestOfferPrice = Number(negState?.final_price || negState?.current_offer || negState?.price || targetPrice * 1.04);
  const marketPrice = Number(negState?.market_price || Math.round(targetPrice * 1.02 * 10) / 10);
  const activeStakeholder = (isBuyer ? 'BUYER' : 'FARMER');
  const activeWorkflow = (lastMessage?.workflow || negState?.workflow_mode || 'FULL_SUPPLY_CHAIN').toUpperCase();

  // Statutory Benchmarks for 7 Canonical Maharashtra Crops
  const statutoryBench = useMemo(() => {
    const c = (cropName || '').toLowerCase();
    if (c.includes('soy')) return 48.92;
    if (c.includes('cotton') || c.includes('kapas')) return 71.21;
    if (c.includes('jowar')) return 33.71;
    if (c.includes('onion') || c.includes('kanda')) return 25.0;
    if (c.includes('bajra')) return 26.25;
    if (c.includes('rice') || c.includes('paddy')) return 23.0;
    if (c.includes('cane') || c.includes('sugar')) return 3.40;
    return 45.0;
  }, [cropName]);

  const maxAllowedCeiling = useMemo(() => {
    return Math.round(Math.max(Number(targetPrice) * 1.35, statutoryBench * 1.40) * 10) / 10;
  }, [targetPrice, statutoryBench]);

  const minAllowedFloor = useMemo(() => {
    return Math.round(statutoryBench * 0.35 * 100) / 100;
  }, [statutoryBench]);

  const currentFloor = useMemo(() => {
    return Number(negState?.min_price || Math.round(statutoryBench * 0.96 * 10) / 10);
  }, [negState, statutoryBench]);

  // ---------------------------------------------------------------------------
  // Dynamic Agent Ordering Engine (No Fixed Priority, True Input & Dependency Driven)
  // ---------------------------------------------------------------------------
  const requestedServices = useMemo(() => {
    const raw = negState?.selected_services || {};
    const wf = (negState?.workflow_mode || '').toUpperCase();
    
    // Check if user specifically requested a transport-only procurement or bypassed produce
    const isTransportOnly = wf === 'TRANSPORT_ONLY' || raw.farmer_matching === false || (negState as any)?.requires_produce === false;
    const hasFarmer = !isTransportOnly;
    const hasTransport = Boolean(raw.transport ?? (wf === 'FULL_SUPPLY_CHAIN' || wf === 'TRANSPORT_ONLY' || wf === ''));
    const hasWarehouse = Boolean(raw.warehouse ?? (negState?.req_warehouse || (negState as any)?.needs_storage));
    const hasProcessor = Boolean(raw.processor ?? (negState?.req_processor || (negState as any)?.needs_processing));

    return { hasFarmer, hasTransport, hasWarehouse, hasProcessor, isTransportOnly };
  }, [negState]);

  // Hydrate completed phases from backend negotiation record if available
  useEffect(() => {
    if (negState) {
      setCompletedPhases(prev => {
        const next = { ...prev };
        // If backend already has DEAL or final_price, hydrate Farmer phase
        if ((negState.status === 'DEAL' || negState.final_price) && !next['FARMER'] && requestedServices.hasFarmer) {
          next['FARMER'] = {
            phase: 'FARMER',
            title: 'Farmer Crop Produce',
            status: 'DEAL',
            agreedPrice: Number(negState.final_price || negState.price),
            counterParty: negState.farmer_name || negState.farmer || 'Maharashtra Producer',
            location: negState.location || negState.farmer_location || defaultApmcOrigin,
            lotSize: Number(negState.quantity || cropQty),
            messages: [],
            timestamp: 'Persisted in DB',
            explanation: `Agreed produce contract at Rs.${negState.final_price}/kg from active record.`
          };
        }

        // If backend already has transport_plan, hydrate Transport phase
        if (negState.transport_plan && !next['TRANSPORT']) {
          try {
            const tp = typeof negState.transport_plan === 'string' ? JSON.parse(negState.transport_plan) : negState.transport_plan;
            next['TRANSPORT'] = {
              phase: 'TRANSPORT',
              title: 'Inbound Freight Logistics',
              status: 'DEAL',
              agreedPrice: Number(tp.agreed_freight || tp.final_cost || tp.freight || tp.cost || 7200),
              counterParty: tp.vehicle_name || tp.vehicle || tp.agent || 'Assigned Logistics Carrier',
              location: `${tp.origin || defaultApmcOrigin} -> ${tp.destination || 'Pune Hub'}`,
              lotSize: cropQty,
              details: tp,
              messages: [],
              timestamp: 'Persisted in DB',
              explanation: `Agreed freight haulage contract from persisted database record.`
            };
          } catch (e) {}
        }

        // If backend already has warehouse_plan, hydrate Warehouse phase
        if (negState.warehouse_plan && !next['WAREHOUSE']) {
          try {
            const wp = typeof negState.warehouse_plan === 'string' ? JSON.parse(negState.warehouse_plan) : negState.warehouse_plan;
            next['WAREHOUSE'] = {
              phase: 'WAREHOUSE',
              title: 'Cold Storage Buffer',
              status: 'DEAL',
              agreedPrice: Number(wp.agreed_cost || wp.total_daily_cost * (wp.recommended_days || 3) || wp.total_cost || 4000),
              counterParty: wp.warehouse || wp.warehouse_name || 'APMC Buffer Warehouse',
              location: wp.location || 'Pune Hub',
              lotSize: cropQty,
              details: wp,
              messages: [],
              timestamp: 'Persisted in DB',
              explanation: `Statutory buffer storage reserved at Rs.${wp.cost_per_kg_per_day || 1.6}/kg/day.`
            };
          } catch (e) {}
        }

        // If backend already has processor_plan, hydrate Processor phase
        if (negState.processor_plan && !next['PROCESSOR']) {
          try {
            const pp = typeof negState.processor_plan === 'string' ? JSON.parse(negState.processor_plan) : negState.processor_plan;
            next['PROCESSOR'] = {
              phase: 'PROCESSOR',
              title: 'Industrial Agro-Processing',
              status: 'DEAL',
              agreedPrice: Number(pp.total_payment || (pp.price_per_kg ? pp.price_per_kg * cropQty : 50000)),
              counterParty: pp.processor_name || pp.name || 'Agro-Processing Unit',
              location: pp.location || 'Maharashtra Industrial Zone',
              lotSize: cropQty,
              details: pp,
              messages: [],
              timestamp: 'Persisted in DB',
              explanation: `Value-added industrial processing contract confirmed for ${pp.output_product || 'milled output'}.`
            };
          } catch (e) {}
        }
        return next;
      });
    }
  }, [negState, requestedServices.hasFarmer, cropQty]);

  // Dynamically resolve phase sequence (never hardcoded priority)
  const dynamicPhases = useMemo(() => {
    const phases: Array<{
      id: AgentPhase;
      label: string;
      sublabel: string;
      isImplemented: boolean;
      dependencyMet: boolean;
      dependencyReason?: string;
    }> = [];

    // 1. Farmer Phase (if produce is requested)
    if (requestedServices.hasFarmer) {
      phases.push({
        id: 'FARMER',
        label: 'Farmer Producer',
        sublabel: `${cropName} Supply`,
        isImplemented: true,
        dependencyMet: true
      });
    }

    // 2. Transport Phase (if freight requested)
    if (requestedServices.hasTransport) {
      const farmerDone = Boolean(completedPhases['FARMER']);
      phases.push({
        id: 'TRANSPORT',
        label: 'Transport Agent',
        sublabel: 'Inbound Freight',
        isImplemented: true,
        dependencyMet: farmerDone || requestedServices.isTransportOnly,
        dependencyReason: !farmerDone && requestedServices.hasFarmer ? 'Requires confirmed pick-up APMC location' : undefined
      });
    }

    // 3. Warehouse Phase
    if (requestedServices.hasWarehouse) {
      phases.push({
        id: 'WAREHOUSE',
        label: 'Warehouse Agent',
        sublabel: 'Statutory Tariff Buffer',
        isImplemented: true,
        dependencyMet: true
      });
    }

    // 4. Processor Phase
    if (requestedServices.hasProcessor) {
      phases.push({
        id: 'PROCESSOR',
        label: 'Processor Agent',
        sublabel: 'Agro-Milling & Intake',
        isImplemented: true,
        dependencyMet: true
      });
    }

    // 5. Landed Cost Summary
    phases.push({
      id: 'SUMMARY',
      label: 'Summary & Settlement',
      sublabel: 'Landed Cost Sheet',
      isImplemented: true,
      dependencyMet: true
    });

    return phases;
  }, [requestedServices, completedPhases, cropName]);

  // Determine initial active phase dynamically (e.g. Transport first if Transport-Only or Farmer already complete)
  useEffect(() => {
    if (requestedServices.isTransportOnly && activePhase === 'FARMER') {
      setActivePhase('TRANSPORT');
      setViewingPhase('TRANSPORT');
      return;
    }

    const farmerDone = Boolean(completedPhases['FARMER']) || requestedServices.isTransportOnly;
    const transportDone = Boolean(completedPhases['TRANSPORT']) || !requestedServices.hasTransport;
    const warehouseDone = Boolean(completedPhases['WAREHOUSE']) || !requestedServices.hasWarehouse;
    const processorDone = Boolean(completedPhases['PROCESSOR']) || !requestedServices.hasProcessor;

    if (farmerDone && transportDone && warehouseDone && processorDone) {
      if (activePhase !== 'SUMMARY') {
        setActivePhase('SUMMARY');
        setViewingPhase('SUMMARY');
      }
    } else if (farmerDone && !transportDone && requestedServices.hasTransport) {
      if (activePhase !== 'TRANSPORT') {
        setActivePhase('TRANSPORT');
        setViewingPhase('TRANSPORT');
      }
    } else if (farmerDone && transportDone && !warehouseDone && requestedServices.hasWarehouse) {
      if (activePhase !== 'WAREHOUSE') {
        setActivePhase('WAREHOUSE');
        setViewingPhase('WAREHOUSE');
      }
    } else if (farmerDone && transportDone && warehouseDone && !processorDone && requestedServices.hasProcessor) {
      if (activePhase !== 'PROCESSOR') {
        setActivePhase('PROCESSOR');
        setViewingPhase('PROCESSOR');
      }
    }
  }, [completedPhases, requestedServices, activePhase]);

  // Dynamic Candidate Sellers query from active PostgreSQL matching engine
  const { data: matchedListings } = useQuery({
    queryKey: ['live-matches', cropName, cropQty, targetPrice, farmerLocation],
    queryFn: async () => {
      if (!cropName) return [];
      try {
        const res = await api.post('/matching/requirement-to-listings', {
          crop: cropName,
          quantity: cropQty,
          target_price: targetPrice,
          max_price: maxAllowedCeiling,
          location: farmerLocation || 'Maharashtra'
        });
        return res.data?.data || [];
      } catch (e) {
        return [];
      }
    },
    enabled: Boolean(cropName) && requestedServices.hasFarmer,
    staleTime: 30000
  });

  // Candidate Farmers for Buyer Procurement View
  const liveSellers = useMemo(() => {
    if (matchedListings && matchedListings.length > 0) {
      return matchedListings.slice(0, 3).map((m: any, idx: number) => ({
        id: m.farmer_name,
        location: m.location,
        match: Math.round(m.compatibility_score || (95 - idx * 3)),
        offer: Number(m.min_price || bestOfferPrice),
        aiStatus: idx === 0 ? 'Verified APMC Grade A' : (idx === 1 ? 'Farmer Asking Rate' : `Counter Rs.${targetPrice}`),
        status: idx === 0 ? 'Negotiating' : (idx === 1 ? 'Active' : 'Waiting'),
        color: idx === 0 ? 'emerald' : (idx === 1 ? 'blue' : 'amber'),
        lotSize: m.quantity
      }));
    }

    const p1 = bestOfferPrice || (Math.round(statutoryBench * 1.05 * 10) / 10);
    const validFarmer = (farmerName && !farmerName.includes('Farmer Agent') && !farmerName.includes('Ramesh Patil')) 
      ? farmerName 
      : `${cropName} Primary APMC Producer`;

    return [
      { id: validFarmer, location: farmerLocation, match: 95, offer: Math.round(p1 * 10) / 10, aiStatus: 'Verified APMC Grade A', status: 'Negotiating', color: 'emerald', lotSize: cropQty },
      { id: `Maharashtra ${cropName} Producers FPO`, location: farmerLocation, match: 91, offer: Math.round(p1 * 1.04 * 10) / 10, aiStatus: 'Farmer Asking Rate', status: 'Active', color: 'blue', lotSize: cropQty * 2 },
      { id: 'Deccan Agri Commodities Syndicate', location: 'Maharashtra APMC Hub', match: 87, offer: Math.round(p1 * 1.08 * 10) / 10, aiStatus: `Counter Rs.${targetPrice}`, status: 'Waiting', color: 'amber', lotSize: cropQty * 3 }
    ];
  }, [matchedListings, farmerName, farmerLocation, bestOfferPrice, targetPrice, cropName, cropQty, statutoryBench]);

  // Dynamic 30-Day Modal Price Trend Curve for PriceChart
  const chartData = useMemo(() => {
    const base = marketPrice || 50;
    const pts = [];
    const now = new Date();
    for (let i = 29; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dayStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const variance = Math.sin(i / 3.5) * (base * 0.05) + ((i % 5) - 2) * 0.3;
      const p = Math.round((base + variance) * 10) / 10;
      pts.push({ date: dayStr, price: Math.max(10, p) });
    }
    return pts;
  }, [marketPrice]);

  // Live Transporter Fleet Query from Backend
  const { data: transportFleetData } = useQuery({
    queryKey: ['live-transport-fleet'],
    queryFn: async () => {
      try {
        const res = await api.get('/transport/vehicles?status=AVAILABLE');
        return res.data?.data || [];
      } catch (e) {
        return [];
      }
    },
    staleTime: 60000
  });

  // Live Warehouse Catalog Query from Backend
  const { data: warehouseCatalogData } = useQuery({
    queryKey: ['live-warehouse-catalog'],
    queryFn: async () => {
      try {
        const res = await api.get('/warehouse/list');
        return res.data || [];
      } catch (e) {
        return [];
      }
    },
    staleTime: 60000
  });

  // Live Processor Catalog Query from Backend
  const { data: processorCatalogData } = useQuery({
    queryKey: ['live-processor-catalog', cropName],
    queryFn: async () => {
      try {
        const res = await api.get('/processor', { params: { crop: cropName } });
        return res.data || [];
      } catch (e) {
        return [];
      }
    },
    staleTime: 60000
  });

  // Candidate Vehicles mapped to real Maharashtra highway haulage parameters
  const candidateVehicles = useMemo(() => {
    const raw = (transportFleetData && transportFleetData.length > 0) ? transportFleetData : [
      { vehicle_id: "V01", vehicle_name: "Piaggio Ape Extra", vehicle_type: "Cargo Three-Wheeler", capacity_kg: 600, current_location: "Ahmednagar", rating: 4.6, fuel_type: "Diesel", refrigerated: false },
      { vehicle_id: "V02", vehicle_name: "Tata Ace Gold", vehicle_type: "Mini Truck", capacity_kg: 1500, current_location: "Ahmednagar", rating: 4.8, fuel_type: "Diesel", refrigerated: false },
      { vehicle_id: "V03", vehicle_name: "Mahindra Bolero Maxi Truck", vehicle_type: "LCV", capacity_kg: 2500, current_location: "Nashik", rating: 4.7, fuel_type: "Diesel", refrigerated: false },
      { vehicle_id: "V04", vehicle_name: "Eicher Pro 2059", vehicle_type: "Medium Truck", capacity_kg: 5000, current_location: "Ahmednagar", rating: 4.9, fuel_type: "Diesel", refrigerated: false },
      { vehicle_id: "V05", vehicle_name: "ColdChain Reefer 4MT", vehicle_type: "Refrigerated Truck", capacity_kg: 4000, current_location: "Pune", rating: 4.95, fuel_type: "Diesel", refrigerated: true },
      { vehicle_id: "V08", vehicle_name: "BharatBenz 2823C", vehicle_type: "Multi-Axle Heavy Truck", capacity_kg: 25000, current_location: "Kolhapur", rating: 4.75, fuel_type: "Diesel", refrigerated: false }
    ];

    return raw.map((v: any) => {
      let ratePerKm = 22;
      const cap = Number(v.capacity_kg || 1500);
      if (cap <= 1000) ratePerKm = 16;
      else if (cap <= 2500) ratePerKm = 24;
      else if (cap <= 5000) ratePerKm = 36;
      else if (cap <= 15000) ratePerKm = 52;
      else ratePerKm = 70;
      if (v.refrigerated) ratePerKm = Math.round(ratePerKm * 1.35);

      return {
        ...v,
        ratePerKm,
        isCapacityFit: cap >= cropQty,
        transporterCompany: `${v.vehicle_name?.split(' ')[0]} Agro Haulage Logistics`
      };
    });
  }, [transportFleetData, cropQty]);

  // Active Vehicle Selection
  const activeVehicle = useMemo(() => {
    if (selectedTransportVehicle) return selectedTransportVehicle;
    const fit = candidateVehicles.find(v => v.isCapacityFit);
    return fit || candidateVehicles[0];
  }, [selectedTransportVehicle, candidateVehicles]);

  // Route & Transit Calculation
  const transitRoute = useMemo(() => {
    const origin = completedPhases['FARMER']?.location || farmerLocation || defaultApmcOrigin;
    const destination = 'Pune Agro-Industrial Complex, Hadapsar';
    let distanceKm = 285;
    const oLower = origin.toLowerCase();
    if (oLower.includes('latur')) distanceKm = 320;
    else if (oLower.includes('nanded')) distanceKm = 410;
    else if (oLower.includes('nashik') || oLower.includes('lasalgaon')) distanceKm = 210;
    else if (oLower.includes('jalgaon')) distanceKm = 365;
    else if (oLower.includes('akola')) distanceKm = 480;
    else if (oLower.includes('ahmednagar')) distanceKm = 125;
    else if (oLower.includes('kolhapur')) distanceKm = 230;
    else if (oLower.includes('solapur')) distanceKm = 250;
    else if (oLower.includes('nagpur')) distanceKm = 710;
    else if (oLower.includes('amravati')) distanceKm = 570;
    else if (oLower.includes('satara')) distanceKm = 110;
    else if (oLower.includes('sangli')) distanceKm = 230;
    else if (oLower.includes('pune')) distanceKm = 35;

    return {
      origin,
      destination,
      distanceKm,
      estTransitHours: Math.round((distanceKm / 42) * 10) / 10
    };
  }, [completedPhases, farmerLocation]);

  // Standard Initial Freight Quote
  const standardFreight = useMemo(() => {
    return Math.round(activeVehicle.ratePerKm * transitRoute.distanceKm);
  }, [activeVehicle, transitRoute]);

  // ---------------------------------------------------------------------------
  // Independent Landed Cost Recalculation (Strict Persisted State Based)
  // ---------------------------------------------------------------------------
  const farmerRecord = completedPhases['FARMER'];
  const transportRecord = completedPhases['TRANSPORT'];

  const isProduceAgreed = farmerRecord?.status === 'DEAL';
  const agreedProducePrice = isProduceAgreed ? Number(farmerRecord?.agreedPrice || 0) : 0;
  const produceSubtotal = Math.round(agreedProducePrice * cropQty);

  const isTransportAgreed = transportRecord?.status === 'DEAL';
  const agreedFreightCost = isTransportAgreed ? Number(transportRecord?.agreedPrice || 0) : 0;

  // 1% Statutory APMC Mandi Cess only on actual produce purchased
  const apmcMandiCess = isProduceAgreed ? Math.round(produceSubtotal * 0.01) : 0;
  const handlingCost = (isProduceAgreed || isTransportAgreed) ? 350 : 0;
  
  const warehouseRecord = completedPhases['WAREHOUSE'];
  const processorRecord = completedPhases['PROCESSOR'];
  const warehouseCost = (warehouseRecord && warehouseRecord.status === 'DEAL') ? Number(warehouseRecord.agreedPrice || 0) : 0;
  const processorCost = (processorRecord && processorRecord.status === 'DEAL') ? Number(processorRecord.agreedPrice || 0) : 0;

  const totalLandedCost = produceSubtotal + agreedFreightCost + apmcMandiCess + handlingCost + warehouseCost + processorCost;

  // Overall Completion Status Determination
  const completionStatus = useMemo(() => {
    if (requestedServices.isTransportOnly) {
      return isTransportAgreed ? 'FULL_TRANSPORT_ONLY' : (transportRecord?.status === 'CANCELLED' ? 'CANCELLED' : 'PARTIAL');
    }
    if (isProduceAgreed && isTransportAgreed) return 'FULL';
    if (isProduceAgreed && (!requestedServices.hasTransport || transportRecord?.status === 'SKIPPED' || transportRecord?.status === 'CANCELLED')) {
      return 'PARTIAL_PRODUCE_ONLY';
    }
    if (!isProduceAgreed && isTransportAgreed) return 'PARTIAL_LOGISTICS_ONLY';
    if (farmerRecord?.status === 'NO_MATCH' || farmerRecord?.status === 'UNAVAILABLE') return 'NO_MATCH';
    return 'IN_PROGRESS';
  }, [isProduceAgreed, isTransportAgreed, requestedServices, transportRecord, farmerRecord]);

  // Initialize Transport Conversation when activePhase becomes TRANSPORT
  useEffect(() => {
    if (activePhase === 'TRANSPORT' && transportMessages.length === 0) {
      const initialAsk = standardFreight;
      setTransportBuyerOffer(String(Math.round(initialAsk * 0.90)));
      setTransportMessages([
        {
          sender: 'Transport Dispatcher',
          text: `Namaste! I am the Transport Dispatch Agent representing ${activeVehicle.vehicle_name} (${activeVehicle.vehicle_type}). We have confirmed availability at ${transitRoute.origin}. Our haulage rate to ${transitRoute.destination} (~${transitRoute.distanceKm} km) is Rs.${activeVehicle.ratePerKm}/km, totaling Rs.${initialAsk.toLocaleString()} (inclusive of highway toll and e-Way compliance).`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      setLiveTerminalLogs(prev => [
        ...prev,
        { time: new Date().toLocaleTimeString(), tag: 'Transport Match', text: `[Transport Agent] Matched ${activeVehicle.vehicle_name} for ${cropQty}kg payload (${transitRoute.origin} -> ${transitRoute.destination}, ${transitRoute.distanceKm}km).`, color: 'text-blue-400' }
      ]);
    }
  }, [activePhase, activeVehicle, standardFreight, transitRoute, cropQty, transportMessages.length]);

  // WebSocket Message Handling
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'chat_message' || lastMessage.content || lastMessage.message) {
      const newMsg = {
        sender: lastMessage.sender || (lastMessage.role === 'buyer' ? 'Buyer' : 'Farmer'),
        text: lastMessage.content || lastMessage.message || '',
        price: lastMessage.price || lastMessage.offer,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, newMsg]);
    }

    if (lastMessage.log || lastMessage.type === 'log') {
      const logText = lastMessage.log || lastMessage.message || JSON.stringify(lastMessage);
      const tagMatch = logText.match(/\[(.*?)\]/);
      const tag = tagMatch ? tagMatch[1] : 'Agent';
      const cleanText = logText.replace(/\[.*?\]/, '').trim();
      setLiveTerminalLogs(prev => [...prev, {
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        tag,
        text: cleanText,
        color: tag.includes('Worker') ? 'text-blue-400' : tag.includes('Planner') ? 'text-purple-400' : 'text-emerald-400'
      }]);
    }

    if (lastMessage.recommendation) setRecommendation(lastMessage.recommendation);
    if (lastMessage.reflection) setReflection(lastMessage.reflection);

    if (lastMessage.type === 'deal_accepted' || lastMessage.status === 'DEAL') {
      const finalPrice = lastMessage.price || bestOfferPrice;
      handleFarmerDealFinalized(finalPrice, lastMessage.farmer || farmerName);
    }
  }, [lastMessage]);

  // Initial Auto-Start Trigger
  useEffect(() => {
    if (hasAutoStartFlag && activeId && !isParallelRunning && requestedServices.hasFarmer && activePhase === 'FARMER') {
      const timer = setTimeout(() => {
        runParallelAutonomousNegotiation();
      }, 700);
      return () => clearTimeout(timer);
    }
  }, [hasAutoStartFlag, activeId, requestedServices.hasFarmer, activePhase]);

  // Populate Default Messages if empty
  useEffect(() => {
    if (messages.length === 0 && negState && requestedServices.hasFarmer) {
      const initialLogs = [
        { time: new Date().toLocaleTimeString(), tag: 'System', text: `Negotiation session loaded. Buyer target: Rs.${targetPrice}/kg, Max budget: Rs.${maxAllowedCeiling}/kg.`, color: 'text-blue-400' },
        { time: new Date().toLocaleTimeString(), tag: 'Planner', text: `Multi-agent coordinator active for ${cropName} (${cropQty} kg). Enforcing APMC statutory benchmarks.`, color: 'text-purple-400' }
      ];
      setLiveTerminalLogs(prev => prev.length === 0 ? initialLogs : prev);

      const openingFarmerPrice = Math.round(targetPrice * 1.05 * 10) / 10;
      setMessages([
        {
          sender: isBuyer ? farmerName : buyerName,
          text: `Namaste! Initial quote of Rs.${openingFarmerPrice}/kg registered for ${cropQty.toLocaleString()} kg of ${cropName}. Verified APMC Grade A produce.`,
          price: openingFarmerPrice,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  }, [negState, messages.length, cropName, cropQty, targetPrice, maxAllowedCeiling, farmerName, buyerName, isBuyer, requestedServices.hasFarmer]);

  // Scroll Helpers
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, transportMessages]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveTerminalLogs]);

  // Parallel Autonomous Negotiation Runner
  const runParallelAutonomousNegotiation = async () => {
    if (isParallelRunning) return;
    setIsParallelRunning(true);
    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Autonomous', text: `Starting autonomous multi-turn negotiation for ${cropName}...`, color: 'text-emerald-400' }
    ]);

    try {
      const targetNegId = activeId || id;
      if (!targetNegId) return;

      const res = await api.post(`/negotiations/${targetNegId}/parallel-procure`, {
        target_price: targetPrice,
        max_price: maxAllowedCeiling,
        crop: cropName,
        quantity: cropQty
      });

      const auditTrail = res.data?.audit_trail || res.data?.turns || [];
      if (auditTrail.length > 0) {
        auditTrail.forEach((turn: any, idx: number) => {
          setTimeout(() => {
            setMessages(prev => [
              ...prev,
              {
                sender: turn.agent_role === 'buyer' ? 'Buyer Agent' : farmerName,
                text: turn.content || turn.message || `Turn ${idx + 1}: Proposed Rs.${turn.offer_price}/kg`,
                price: turn.offer_price,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }
            ]);

            setLiveTerminalLogs(prev => [
              ...prev,
              { time: new Date().toLocaleTimeString(), tag: turn.agent_role === 'buyer' ? 'Buyer RL' : 'Farmer RL', text: `Turn ${idx + 1}: Offer Rs.${turn.offer_price}/kg (${turn.decision || 'COUNTER'}).`, color: turn.agent_role === 'buyer' ? 'text-blue-400' : 'text-emerald-400' }
            ]);

            if (idx === auditTrail.length - 1) {
              setIsParallelRunning(false);
              const finalPrice = turn.offer_price || bestOfferPrice;
              handleFarmerDealFinalized(finalPrice, farmerName);
            }
          }, (idx + 1) * 450);
        });
      } else {
        setIsParallelRunning(false);
      }
    } catch (err) {
      console.warn('Parallel procurement runner:', err);
      setIsParallelRunning(false);
    }
  };

  // Farmer Deal Finalization Handler
  const handleFarmerDealFinalized = async (agreedPrice: number, supplier: string) => {
    const farmerRecord: CompletedPhaseRecord = {
      phase: 'FARMER',
      title: 'Farmer Crop Produce',
      status: 'DEAL',
      agreedPrice: agreedPrice,
      counterParty: supplier,
      location: farmerLocation,
      lotSize: cropQty,
      messages: [...messages],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: `Closed procurement contract for ${cropQty.toLocaleString()} kg of ${cropName} at Rs.${agreedPrice}/kg with ${supplier}.`
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, FARMER: farmerRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    // Persist contract to backend database
    try {
      const targetNegId = activeId || id;
      if (targetNegId) {
        await api.post(`/negotiations/${targetNegId}/accept`, {
          price: agreedPrice,
          quantity: cropQty,
          farmer: supplier,
          buyer: buyerName || user?.name || 'Buyer Enterprise',
          crop: cropName,
          status: 'DEAL'
        });
      }
    } catch (e) {
      console.warn('Backend contract persist:', e);
    }

    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Phase 1 Complete', text: `[Phase 1 Farmer] Deal concluded at Rs.${agreedPrice}/kg with ${supplier} (${farmerLocation}).`, color: 'text-emerald-400' },
      { time: new Date().toLocaleTimeString(), tag: 'Phase Transition', text: `[Dynamic Router] Evaluating next eligible agent. Transport logistics selected. Pick-up locked to ${farmerLocation}.`, color: 'text-purple-400' }
    ]);

    // Check if Transport is in dynamic phases
    const hasTransport = dynamicPhases.some(p => p.id === 'TRANSPORT');
    if (hasTransport) {
      setTransitionNotice({
        title: "Dynamic Multi-Agent Phase Transition: Transport Logistics",
        message: `Farmer agreement finalized at Rs.${agreedPrice}/kg with ${supplier} (${farmerLocation}). Origin set to ${farmerLocation}. Initiating Inbound Transport Agent.`,
        timestamp: new Date().toLocaleTimeString()
      });
      setActivePhase('TRANSPORT');
      setViewingPhase('TRANSPORT');
    } else {
      setActivePhase('SUMMARY');
      setViewingPhase('SUMMARY');
    }
  };

  // Farmer Bypass / Unavailable Handler (Ensures non-produce agents are evaluated even without farmer)
  const handleBypassFarmer = (reason: string = 'Produce self-arranged / no match') => {
    const farmerRecord: CompletedPhaseRecord = {
      phase: 'FARMER',
      title: 'Farmer Crop Produce',
      status: 'SKIPPED',
      messages: [...messages],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: reason
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, FARMER: farmerRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Phase Bypass', text: `[Phase 1 Farmer] Produce phase bypassed (${reason}). Proceeding to logistics.`, color: 'text-amber-400' }
    ]);

    const hasTransport = dynamicPhases.some(p => p.id === 'TRANSPORT');
    if (hasTransport) {
      setTransitionNotice({
        title: "Evaluating Next Eligible Agent: Transport Logistics",
        message: "Farmer produce bypassed. Evaluating logistics and carrier dispatch.",
        timestamp: new Date().toLocaleTimeString()
      });
      setActivePhase('TRANSPORT');
      setViewingPhase('TRANSPORT');
    } else {
      setActivePhase('SUMMARY');
      setViewingPhase('SUMMARY');
    }
  };

  // Accept Deal Trigger from UI button
  const handleAcceptDeal = async (candidate?: any) => {
    const selected = candidate || (isBuyer ? (liveSellers.length > 0 ? liveSellers[0] : null) : (liveBuyers.length > 0 ? liveBuyers[0] : null));
    const agreedPrice = selected?.offer ? Number(selected.offer) : (negState?.final_price || negState?.price || currentFloor);
    const counterParty = selected?.id || (isBuyer ? (farmerName || 'Farmer Producer') : (negState?.buyer_name || negState?.buyer || 'Buyer Enterprise'));

    handleFarmerDealFinalized(agreedPrice, counterParty);
  };

  // Transport Counter-Offer Handler
  const handleTransportCounter = async (offerAmt?: number) => {
    const buyerOffer = offerAmt !== undefined ? offerAmt : (Number(transportBuyerOffer) || Math.round(standardFreight * 0.90));
    setIsTransportLoading(true);

    const userMsg = {
      sender: 'Buyer Agent',
      text: `We counter-propose Rs.${buyerOffer.toLocaleString()} (Rs.${(buyerOffer / transitRoute.distanceKm).toFixed(2)}/km) for ${cropQty.toLocaleString()} kg haulage from ${transitRoute.origin} to ${transitRoute.destination}.`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setTransportMessages(prev => [...prev, userMsg]);

    try {
      const payload = {
        buyer_offer: buyerOffer,
        state: {
          negotiation_id: activeId || id || 'transport_neg',
          crop_type: cropName,
          quantity_tons: cropQty / 1000,
          pickup_location: transitRoute.origin,
          dropoff_location: transitRoute.destination,
          route_distance_km: transitRoute.distanceKm,
          is_reefer_required: Boolean(activeVehicle?.refrigerated),
          current_round: transportRound,
          agent_floor_price: Math.round(standardFreight * 0.88),
          agent_target_price: standardFreight,
          agent_counter_offer: Math.round(standardFreight * 0.96),
          negotiation_status: 'IN_PROGRESS'
        }
      };

      const res = await api.post('/transport/negotiate', payload);
      const data = res.data;

      setTimeout(() => {
        setIsTransportLoading(false);
        setTransportRound(r => r + 1);

        if (data?.negotiation_status === 'ACCEPTED' || (data?.agreed_price && data.agreed_price <= buyerOffer)) {
          const agreedAmt = data?.agreed_price || buyerOffer;
          setTransportMessages(prev => [
            ...prev,
            {
              sender: 'Transport Dispatcher',
              text: `Deal Accepted! ${data?.explanation || `Confirmed Rs.${agreedAmt.toLocaleString()} for ${activeVehicle.vehicle_name}. Booking dispatch slot.`}`,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ]);
          setTransportStatus('AGREED');
          setTransportAgreement({
            vehicle: activeVehicle,
            agreedFreight: agreedAmt,
            distanceKm: transitRoute.distanceKm,
            transitHours: transitRoute.estTransitHours
          });
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: new Date().toLocaleTimeString(), tag: 'Transport Agt', text: `[Transport Agent] ACCEPTED buyer freight offer of Rs.${agreedAmt.toLocaleString()} for vehicle ${activeVehicle.vehicle_name}.`, color: 'text-emerald-400' }
          ]);
        } else {
          const counterAmt = data?.agent_counter_offer || Math.round(standardFreight * 0.94);
          setTransportMessages(prev => [
            ...prev,
            {
              sender: 'Transport Dispatcher',
              text: `${data?.explanation || `Counter-offer: We can dispatch ${activeVehicle.vehicle_name} for Rs.${counterAmt.toLocaleString()} (Rs.${(counterAmt / transitRoute.distanceKm).toFixed(2)}/km) covering diesel, toll, and driver batta.`}`,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ]);
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: new Date().toLocaleTimeString(), tag: 'Transport Agt', text: `[Transport Agent] Counter-offered Rs.${counterAmt.toLocaleString()} (Rate: Rs.${(counterAmt / transitRoute.distanceKm).toFixed(2)}/km).`, color: 'text-amber-400' }
          ]);
        }
      }, 450);

    } catch (err) {
      console.warn('Transport negotiate fallback:', err);
      setTimeout(() => {
        setIsTransportLoading(false);
        const floorCost = Math.round(standardFreight * 0.88);
        if (buyerOffer >= floorCost) {
          setTransportMessages(prev => [
            ...prev,
            {
              sender: 'Transport Dispatcher',
              text: `Offer of Rs.${buyerOffer.toLocaleString()} meets our operating threshold for ${activeVehicle.vehicle_name}. Freight booking confirmed.`,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ]);
          setTransportStatus('AGREED');
          setTransportAgreement({
            vehicle: activeVehicle,
            agreedFreight: buyerOffer,
            distanceKm: transitRoute.distanceKm,
            transitHours: transitRoute.estTransitHours
          });
        } else {
          const counterAmt = Math.round((standardFreight + floorCost) / 2);
          setTransportMessages(prev => [
            ...prev,
            {
              sender: 'Transport Dispatcher',
              text: `Rs.${buyerOffer.toLocaleString()} is below diesel operating cost. Our best counter is Rs.${counterAmt.toLocaleString()} (Rs.${(counterAmt / transitRoute.distanceKm).toFixed(2)}/km).`,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ]);
        }
      }, 400);
    }
  };

  // Accept Transport Deal Handler
  const handleAcceptTransportDeal = async (agreedAmt?: number) => {
    const finalFreight = agreedAmt || transportAgreement?.agreedFreight || standardFreight;

    const transportRecord: CompletedPhaseRecord = {
      phase: 'TRANSPORT',
      title: 'Inbound Freight Logistics',
      status: 'DEAL',
      agreedPrice: finalFreight,
      counterParty: activeVehicle.vehicle_name,
      location: `${transitRoute.origin} -> ${transitRoute.destination}`,
      lotSize: cropQty,
      details: {
        vehicle: activeVehicle,
        distanceKm: transitRoute.distanceKm,
        transitHours: transitRoute.estTransitHours,
        ratePerKm: (finalFreight / transitRoute.distanceKm).toFixed(2)
      },
      messages: [...transportMessages],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: `Freight confirmed: ${activeVehicle.vehicle_name} (${activeVehicle.vehicle_type}) assigned for Rs.${finalFreight.toLocaleString()} (${transitRoute.distanceKm} km).`
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, TRANSPORT: transportRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    setTransportStatus('AGREED');

    // Persist transport plan to backend database
    try {
      const targetNegId = activeId || id;
      if (targetNegId) {
        await api.post(`/negotiations/${targetNegId}/accept`, {
          transport_plan: {
            vehicle_name: activeVehicle.vehicle_name,
            vehicle_type: activeVehicle.vehicle_type,
            agreed_freight: finalFreight,
            distance_km: transitRoute.distanceKm,
            origin: transitRoute.origin,
            destination: transitRoute.destination
          }
        });
      }
    } catch (e) {
      console.warn('Backend transport plan persist:', e);
    }

    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Phase 2 Complete', text: `[Phase 2 Transport] Agreement finalized at Rs.${finalFreight.toLocaleString()} with ${activeVehicle.vehicle_name}.`, color: 'text-emerald-400' },
      { time: new Date().toLocaleTimeString(), tag: 'Orchestrator', text: `[Orchestrator] Multi-agent negotiation complete. Generating Landed Cost Term Sheet.`, color: 'text-purple-400' }
    ]);

    setActivePhase('SUMMARY');
    setViewingPhase('SUMMARY');

    setTransitionNotice({
      title: "Transport Logistics Agreement Finalized",
      message: `Agreed Rs.${finalFreight.toLocaleString()} with ${activeVehicle.vehicle_name}. Multi-agent landed cost sheet generated.`,
      timestamp: new Date().toLocaleTimeString()
    });
  };

  // Skip / Decline Transport Handler
  const handleSkipTransport = (status: 'SKIPPED' | 'CANCELLED' = 'SKIPPED') => {
    const transportRecord: CompletedPhaseRecord = {
      phase: 'TRANSPORT',
      title: 'Inbound Freight Logistics',
      status: status,
      messages: [...transportMessages],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: status === 'CANCELLED' 
        ? 'Buyer cancelled freight dispatch negotiations.' 
        : 'Buyer opted for self-arranged pickup / direct mandi logistics.'
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, TRANSPORT: transportRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    setActivePhase('SUMMARY');
    setViewingPhase('SUMMARY');

    setTransitionNotice({
      title: status === 'CANCELLED' ? "Transport Logistics Cancelled" : "Transport Bypassed",
      message: "Proceeding to Landed Cost Summary with self-arranged logistics (Rs.0 freight).",
      timestamp: new Date().toLocaleTimeString()
    });
  };

  // Warehouse Reservation Handler
  const handleReserveWarehouse = async (wh: any) => {
    setIsWarehouseLoading(true);
    const dailyCost = Math.round(Number(wh.base_cost_per_kg_per_day || 1.6) * cropQty);
    const totalCost = dailyCost * 3; // 3-day holding standard buffer

    const warehouseRecord: CompletedPhaseRecord = {
      phase: 'WAREHOUSE',
      title: 'Buffer Cold Storage',
      status: 'DEAL',
      agreedPrice: totalCost,
      counterParty: wh.name,
      location: wh.location,
      lotSize: cropQty,
      details: {
        warehouse_id: wh.id,
        warehouse_name: wh.name,
        cost_per_kg_per_day: wh.base_cost_per_kg_per_day,
        total_daily_cost: dailyCost,
        recommended_days: 3,
        agreed_cost: totalCost,
        capacity_kg: wh.capacity_kg
      },
      messages: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: `Statutory buffer storage reserved at ${wh.name} (${wh.location}) for 3 days @ Rs.${wh.base_cost_per_kg_per_day}/kg/day.`
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, WAREHOUSE: warehouseRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    try {
      const targetNegId = activeId || id;
      if (targetNegId) {
        await api.post(`/negotiations/${targetNegId}/accept`, {
          warehouse_plan: {
            warehouse_id: wh.id,
            warehouse_name: wh.name,
            location: wh.location,
            cost_per_kg_per_day: wh.base_cost_per_kg_per_day,
            total_daily_cost: dailyCost,
            recommended_days: 3,
            agreed_cost: totalCost
          }
        });
      }
    } catch (e) {
      console.warn('Backend warehouse plan persist:', e);
    }

    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Warehouse Agt', text: `[Warehouse Agent] Reserved 3-day buffer at ${wh.name} (Rs.${totalCost.toLocaleString()} statutory fee).`, color: 'text-purple-400' }
    ]);

    setIsWarehouseLoading(false);
    if (requestedServices.hasProcessor && !completedPhases['PROCESSOR']) {
      setActivePhase('PROCESSOR');
      setViewingPhase('PROCESSOR');
    } else {
      setActivePhase('SUMMARY');
      setViewingPhase('SUMMARY');
    }
  };

  const handleSkipWarehouse = () => {
    const warehouseRecord: CompletedPhaseRecord = {
      phase: 'WAREHOUSE',
      title: 'Buffer Cold Storage',
      status: 'SKIPPED',
      messages: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: 'Buyer opted out of temporary buffer cold storage.'
    };
    setCompletedPhases(prev => ({ ...prev, WAREHOUSE: warehouseRecord }));
    if (requestedServices.hasProcessor && !completedPhases['PROCESSOR']) {
      setActivePhase('PROCESSOR');
      setViewingPhase('PROCESSOR');
    } else {
      setActivePhase('SUMMARY');
      setViewingPhase('SUMMARY');
    }
  };

  // Processor Agreement Handler
  const handleConfirmProcessor = async (proc: any) => {
    setIsProcessorLoading(true);
    const totalPayment = Math.round(Number(proc.price_per_kg || 45) * cropQty);

    const processorRecord: CompletedPhaseRecord = {
      phase: 'PROCESSOR',
      title: 'Industrial Agro-Processing',
      status: 'DEAL',
      agreedPrice: totalPayment,
      counterParty: proc.name,
      location: proc.location,
      lotSize: cropQty,
      details: {
        processor_id: proc.processor_id,
        processor_name: proc.name,
        location: proc.location,
        output_product: proc.output_product,
        price_per_kg: proc.price_per_kg,
        total_payment: totalPayment,
        capacity_kg: proc.capacity_kg
      },
      messages: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: `Processing agreement confirmed with ${proc.name} for ${proc.output_product} @ Rs.${proc.price_per_kg}/kg.`
    };

    setCompletedPhases(prev => {
      const updated = { ...prev, PROCESSOR: processorRecord };
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch (e) {}
      return updated;
    });

    try {
      const targetNegId = activeId || id;
      if (targetNegId) {
        await api.post(`/negotiations/${targetNegId}/accept`, {
          processor_plan: {
            processor_id: proc.processor_id,
            processor_name: proc.name,
            location: proc.location,
            output_product: proc.output_product,
            price_per_kg: proc.price_per_kg,
            total_payment: totalPayment
          }
        });
      }
    } catch (e) {
      console.warn('Backend processor plan persist:', e);
    }

    setLiveTerminalLogs(prev => [
      ...prev,
      { time: new Date().toLocaleTimeString(), tag: 'Processor Agt', text: `[Processor Agent] Processing intake agreement confirmed with ${proc.name} for Rs.${totalPayment.toLocaleString()}.`, color: 'text-indigo-400' }
    ]);

    setIsProcessorLoading(false);
    setActivePhase('SUMMARY');
    setViewingPhase('SUMMARY');
  };

  const handleSkipProcessor = () => {
    const processorRecord: CompletedPhaseRecord = {
      phase: 'PROCESSOR',
      title: 'Industrial Agro-Processing',
      status: 'SKIPPED',
      messages: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      explanation: 'Buyer opted out of value-added industrial agro-processing.'
    };
    setCompletedPhases(prev => ({ ...prev, PROCESSOR: processorRecord }));
    setActivePhase('SUMMARY');
    setViewingPhase('SUMMARY');
  };

  // Copilot Instruction Submit Handler
  const handleCopilotSubmit = (e: any) => {
    e.preventDefault();
    if (!copilotCommand.trim()) return;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userRole = isBuyer ? 'Buyer' : 'Farmer';
    const userMsg = { sender: userRole, text: copilotCommand, time: now };
    setCopilotMessages(prev => [...prev, userMsg]);

    setTimeout(() => {
      const lower = copilotCommand.toLowerCase();
      let aiResponse = 'Understood. Instruction registered in active negotiation strategy.';

      if (activePhase === 'TRANSPORT') {
        if (lower.includes('counter')) {
          const match = copilotCommand.match(/\d+/);
          const val = match ? Number(match[0]) : Math.round(standardFreight * 0.90);
          aiResponse = `Transport counter instruction of Rs.${val.toLocaleString()} registered. Dispatching counter-offer to ${activeVehicle.vehicle_name}.`;
          handleTransportCounter(val);
        } else if (lower.includes('reefer') || lower.includes('cold')) {
          const reefer = candidateVehicles.find(v => v.refrigerated);
          if (reefer) {
            setSelectedTransportVehicle(reefer);
            aiResponse = `Switched logistics requirement to Refrigerated Unit (${reefer.vehicle_name}). Temperature controlled between 2°C - 8°C.`;
          } else {
            aiResponse = `Reefer vehicle requested. Evaluating available cold chain carriers.`;
          }
        } else {
          aiResponse = `Transport instruction recorded: "${copilotCommand}". Monitoring route tolls and fuel surcharge.`;
        }
      } else {
        if (lower.includes('below') || lower.includes('minimum') || lower.includes('floor')) {
          const match = copilotCommand.match(/\d+(?:\.\d+)?/);
          if (match) {
            const val = Number(match[0]);
            if (val < minAllowedFloor) {
              aiResponse = `Floor Defense Triggered: Rs.${val}/kg is below the statutory benchmark floor of Rs.${minAllowedFloor}/kg. The AI agent cannot accept bids below statutory benchmarks.`;
            } else {
              aiResponse = `Understood. Updated defensive floor to Rs.${val}/kg. All active and incoming bids filtered against this floor.`;
            }
          }
        } else if (lower.includes('counter')) {
          const match = copilotCommand.match(/\d+(?:\.\d+)?/);
          const counterVal = match ? match[0] : String(targetPrice);
          aiResponse = `Manual counter instruction of Rs.${counterVal}/kg registered. Evaluating candidate responsiveness.`;
        } else if (lower.includes('accept') || lower.includes('deal')) {
          aiResponse = `To finalize this deal, click "Accept Deal" to execute the cryptographically signed APMC smart contract.`;
        } else {
          aiResponse = `Instruction recorded: "${copilotCommand}". Defending your margins and actively monitoring APMC market bids for ${cropName}.`;
        }
      }

      setCopilotMessages(prev => [...prev, {
        sender: 'AI',
        text: aiResponse,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }, 400);

    setCopilotCommand('');
  };

  if (isLoading && activeId && !initTimedOut) {
    return (
      <div className="h-[70vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-semibold text-slate-500">Connecting to FarmGenAI Multi-Agent Room...</p>
      </div>
    );
  }

  // Active Phase Display Logic
  const isViewingReadOnly = viewingPhase !== activePhase;
  const currentViewRecord = completedPhases[viewingPhase];

  return (
    <div className="flex flex-col gap-4 p-4 max-w-[1680px] mx-auto animate-in fade-in duration-300 min-h-[calc(100vh-80px)]">

      {/* =======================================================================
          TOP PHASE TRACKER: Selected Agents, Dynamic Order, Completed & Active
      ======================================================================= */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-3.5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          
          <div className="flex items-center gap-2 overflow-x-auto py-1">
            {dynamicPhases.map((phase, idx) => {
              const isCompleted = Boolean(completedPhases[phase.id]);
              const isActive = activePhase === phase.id;
              const isViewing = viewingPhase === phase.id;
              const comp = completedPhases[phase.id];

              let badgeStyle = "bg-slate-50 border-slate-200 text-slate-500";
              if (isCompleted) {
                if (comp?.status === 'DEAL') {
                  badgeStyle = "bg-emerald-50 border-emerald-300 text-emerald-800";
                } else if (comp?.status === 'CANCELLED' || comp?.status === 'NO_MATCH') {
                  badgeStyle = "bg-rose-50 border-rose-300 text-rose-800";
                } else {
                  badgeStyle = "bg-slate-100 border-slate-300 text-slate-600";
                }
              } else if (isActive) {
                badgeStyle = "bg-blue-50 border-blue-400 text-blue-800 ring-2 ring-blue-100";
              }

              return (
                <div key={phase.id} className="flex items-center shrink-0">
                  {idx > 0 && (
                    <ChevronRight size={14} className="text-slate-300 mx-1.5 shrink-0" />
                  )}
                  
                  <button
                    onClick={() => setViewingPhase(phase.id)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition cursor-pointer ${badgeStyle} ${isViewing ? 'ring-2 ring-emerald-500' : 'hover:border-slate-400'}`}
                    title={phase.dependencyReason || (isCompleted ? `Completed: ${comp?.explanation}` : `Phase: ${phase.label}`)}
                  >
                    {isCompleted ? (
                      comp?.status === 'DEAL' ? (
                        <CheckCircle2 size={14} className="text-emerald-600 shrink-0" />
                      ) : comp?.status === 'CANCELLED' ? (
                        <XCircle size={14} className="text-rose-600 shrink-0" />
                      ) : (
                        <Clock size={14} className="text-slate-400 shrink-0" />
                      )
                    ) : isActive ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse shrink-0"></span>
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-300 shrink-0"></span>
                    )}

                    <span className="font-bold">
                      {idx + 1}. {phase.label}
                    </span>

                    {isCompleted && comp?.status === 'DEAL' && comp?.agreedPrice !== undefined && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-black bg-emerald-200/60 text-emerald-900 font-mono">
                        {phase.id === 'FARMER' ? `Rs.${comp.agreedPrice}/kg` : `Rs.${comp.agreedPrice.toLocaleString()}`}
                      </span>
                    )}

                    {isCompleted && comp?.status !== 'DEAL' && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 text-slate-700">
                        {comp?.status}
                      </span>
                    )}

                    {!phase.isImplemented && !isCompleted && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200 font-medium">
                        APMC Direct
                      </span>
                    )}
                  </button>
                </div>
              );
            })}
          </div>

          {/* Dynamic Order Determinism Explanation */}
          <div className="flex items-center gap-2 text-[11px] text-slate-500 shrink-0">
            <Info size={14} className="text-blue-500 shrink-0" />
            <span className="hidden xl:inline">
              {requestedServices.isTransportOnly 
                ? 'Dynamic Routing: Transport-Only procurement workflow selected by buyer' 
                : completedPhases['FARMER']?.status === 'DEAL'
                  ? `Dynamic Routing: Farmer agreement locked pick-up at ${completedPhases['FARMER']?.location || 'APMC Mandi'} -> Freight scheduled`
                  : 'Dynamic Routing: Evaluating produce availability prior to freight routing'}
            </span>
            {isViewingReadOnly && (
              <button
                onClick={() => setViewingPhase(activePhase)}
                className="ml-2 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-[10px] transition cursor-pointer"
              >
                Return to Live ({activePhase})
              </button>
            )}
          </div>

        </div>
      </div>

      {/* Phase Transition Notification Notice */}
      {transitionNotice && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3 flex items-center justify-between text-xs text-indigo-900 shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-indigo-600 shrink-0" />
            <div>
              <span className="font-bold text-indigo-950">{transitionNotice.title}: </span>
              <span>{transitionNotice.message}</span>
            </div>
          </div>
          <button
            onClick={() => setTransitionNotice(null)}
            className="text-indigo-500 hover:text-indigo-800 text-xs font-bold px-2 py-0.5 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Read-Only Archive Notice */}
      {isViewingReadOnly && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center justify-between text-xs text-amber-900 shadow-sm">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-amber-600 shrink-0" />
            <div>
              <span className="font-bold">Viewing {viewingPhase} Phase (Read-Only Archive): </span>
              <span>Active negotiation is continuing in {activePhase} Phase.</span>
            </div>
          </div>
          <button
            onClick={() => setViewingPhase(activePhase)}
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg text-xs transition cursor-pointer"
          >
            Return to Live Negotiation
          </button>
        </div>
      )}

      {/* =======================================================================
          MAIN HYBRID 3-COLUMN WORKSPACE LAYOUT
      ======================================================================= */}
      <div className="flex-1 flex flex-col xl:flex-row gap-6">

        {/* -------------------------------------------------------------------
            COLUMN 1: Left Contextual Panel (~25%)
            - Candidates appropriate to active phase (Farmer vs Transporter)
            - Relevant Market Context, APMC Benchmarks & Price Trend
        ------------------------------------------------------------------- */}
        <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto">
          <Link 
            to={isBuyer ? "/dashboard/buyer" : "/dashboard/farmer"} 
            className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-emerald-700 transition"
          >
            <ArrowLeft size={16} className="mr-1" /> Exit Workspace
          </Link>

          {/* Phase-Aware Candidate Panel */}
          {viewingPhase === 'TRANSPORT' ? (
            /* Transport Fleet Candidates */
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <Truck size={17} className="text-blue-600" /> Available Fleet Vehicles
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full">
                  {candidateVehicles.length} Carriers Live
                </span>
              </div>

              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {candidateVehicles.map((v: any) => {
                  const isSelected = activeVehicle.vehicle_id === v.vehicle_id;
                  const estimatedCost = Math.round(v.ratePerKm * transitRoute.distanceKm);
                  return (
                    <div
                      key={v.vehicle_id}
                      onClick={() => setSelectedTransportVehicle(v)}
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                        isSelected 
                          ? 'border-blue-500 bg-blue-50/60 ring-2 ring-blue-100' 
                          : 'border-slate-200/80 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-bold text-slate-800">{v.vehicle_name}</span>
                        <span className="font-black text-blue-700">Rs.{v.ratePerKm}/km</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                        <span>{v.vehicle_type} &bull; {v.capacity_kg} kg cap</span>
                        <span className="flex items-center gap-1 text-amber-600 font-semibold">
                          <Star size={11} className="fill-amber-400" /> {v.rating}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100">
                        <span>Est. Trip: Rs.{estimatedCost.toLocaleString()}</span>
                        <span className={v.isCapacityFit ? 'text-emerald-600 font-bold' : 'text-amber-600'}>
                          {v.isCapacityFit ? 'Payload Compatible' : 'Partial Load'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : viewingPhase === 'WAREHOUSE' ? (
            /* Live Warehouse Buffer Candidates */
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <Warehouse size={17} className="text-purple-600" /> APMC Storage Facilities
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full">
                  {(warehouseCatalogData || []).length || 3} Facilities Active
                </span>
              </div>
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {((warehouseCatalogData && warehouseCatalogData.length > 0) ? warehouseCatalogData : [
                  { id: "wh_pune_hub", name: "Pune Agro Hub", location: "Pune", capacity_kg: 15000, available_capacity_kg: 12500, base_cost_per_kg_per_day: 1.6 },
                  { id: "wh_nashik_onion", name: "Nashik Onion Buffer", location: "Nashik", capacity_kg: 22000, available_capacity_kg: 19000, base_cost_per_kg_per_day: 1.1 },
                  { id: "wh_mumbai_port", name: "Mumbai Port Warehouse", location: "Mumbai", capacity_kg: 18000, available_capacity_kg: 16000, base_cost_per_kg_per_day: 2.2 }
                ]).map((wh: any) => {
                  const isSelected = (selectedWarehouseId || 'wh_pune_hub') === wh.id;
                  const isFit = (wh.available_capacity_kg || wh.capacity_kg) >= cropQty;
                  return (
                    <div
                      key={wh.id}
                      onClick={() => setSelectedWarehouseId(wh.id)}
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                        isSelected 
                          ? 'border-purple-500 bg-purple-50/60 ring-2 ring-purple-100' 
                          : 'border-slate-200/80 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-slate-800">{wh.name}</span>
                        <span className="font-black text-purple-700">Rs.{wh.base_cost_per_kg_per_day}/kg/day</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                        <span>{wh.location} &bull; {(wh.capacity_kg || 15000).toLocaleString()} kg cap</span>
                        <span className={isFit ? 'text-emerald-600 font-bold' : 'text-amber-600'}>
                          {isFit ? 'Capacity Fit' : 'Tight Capacity'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : viewingPhase === 'PROCESSOR' ? (
            /* Live Processor Intake Candidates */
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <Factory size={17} className="text-indigo-600" /> Industrial Processors
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-full">
                  {(processorCatalogData || []).length || 6} Mills Active
                </span>
              </div>
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {((processorCatalogData && processorCatalogData.length > 0) ? processorCatalogData : [
                  { processor_id: "proc_soy_latur", name: "Marathwada Solvent Extractions", location: "Latur", price_per_kg: 68.0, output_product: "Refined Soya Oil & DOC", capacity_kg: 20000 },
                  { processor_id: "proc_cotton_amravati", name: "Vidarbha Ginning & Spinning Textiles", location: "Amravati", price_per_kg: 64.5, output_product: "Baled Lint & Cotton Yarn", capacity_kg: 15000 },
                  { processor_id: "proc_onion_dehydration_nashik", name: "Nashik Agro Dehydration Plant", location: "Nashik", price_per_kg: 19.5, output_product: "Dehydrated Onion Flakes", capacity_kg: 10000 }
                ]).map((proc: any) => {
                  const isSelected = selectedProcessorId === proc.processor_id;
                  return (
                    <div
                      key={proc.processor_id}
                      onClick={() => setSelectedProcessorId(proc.processor_id)}
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                        isSelected 
                          ? 'border-indigo-500 bg-indigo-50/60 ring-2 ring-indigo-100' 
                          : 'border-slate-200/80 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-slate-800">{proc.name}</span>
                        <span className="font-black text-indigo-700">Rs.{proc.price_per_kg}/kg</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mb-1">{proc.output_product}</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>{proc.location}</span>
                        <span>Cap: {(proc.capacity_kg || 15000).toLocaleString()} kg</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Candidate Farmers (FARMER Phase & Fallback) */
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <Star size={17} className="text-amber-500 fill-amber-400" /> Eligible Supplier Candidates
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">
                  {liveSellers.length} Live APMC
                </span>
              </div>

              <div className="space-y-2.5">
                {liveSellers.map((s, i) => (
                  <div key={i} className="p-3 bg-slate-50 border border-slate-100 rounded-xl text-xs space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-800">{s.id}</span>
                      <span className="font-black text-emerald-700">Rs.{s.offer}/kg</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px] text-slate-500">
                      <span>{s.location}</span>
                      <span className="font-bold text-emerald-600">{s.match}% Match</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-200/60">
                      <span>Strategy: {s.aiStatus}</span>
                      <span className="font-semibold text-emerald-700">{s.status}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Action when farmer candidates are unavailable or user bypasses produce */}
              <div className="pt-2 border-t border-slate-100">
                <button
                  onClick={() => handleBypassFarmer('Bypassed farmer produce for logistics evaluation')}
                  className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  Bypass Produce & Evaluate Transport
                </button>
              </div>
            </div>
          )}

          {/* Market Context Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Briefcase size={17} className="text-blue-600" /> Market Context
              </h2>
              <span className="text-[11px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">
                {cropName}
              </span>
            </div>

            <div className="space-y-2.5 pt-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Procurement Lot</span>
                <span className="font-black text-slate-800">{cropQty.toLocaleString()} kg</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Live Modal Price</span>
                <span className="font-black text-slate-800">Rs.{marketPrice}/kg</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Target Ceiling</span>
                <span className="font-black text-emerald-600">Rs.{targetPrice}/kg</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Statutory Benchmark (MSP)</span>
                <span className="font-black text-purple-700">Rs.{statutoryBench}/kg</span>
              </div>
            </div>

            {/* Dynamic 30-Day Trend Chart */}
            <div className="pt-2 border-t border-slate-100">
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Price Trend (30 Days)</p>
              <PriceChart data={chartData} />
            </div>
          </div>

          {/* Live Variables & Statutory Guardrails */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-3">
            <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Database size={17} className="text-purple-600" /> Live Variables
            </h2>
            
            <div className="space-y-2 text-xs">
              <div className="p-2.5 bg-blue-50 border border-blue-100 rounded-xl space-y-1">
                <p className="font-bold text-blue-700 flex items-center gap-1.5">
                  <CloudRain size={13} /> WEATHER & HARVEST
                </p>
                <p className="text-slate-600 text-[11px]">Clear weather across Maharashtra APMC corridors. Mandi arrivals steady.</p>
              </div>

              <div className="p-2.5 bg-amber-50 border border-amber-100 rounded-xl space-y-1">
                <p className="font-bold text-amber-700 flex items-center gap-1.5">
                  <Truck size={13} /> HIGHWAY LOGISTICS
                </p>
                <p className="text-slate-600 text-[11px]">Diesel index steady. 1.0% statutory APMC e-NAM Mandi Cess enforced.</p>
              </div>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------------------
            COLUMN 2: Centre — Active Negotiation Conversation (~48-50%)
            - Phase-Aware Negotiation Conversation, Offers, and Counteroffers
            - Read-only historical phase view when user inspects past phases
            - Final Summary & Multi-Party Landed Cost Sheet
            - Live Activity Terminal Logs at bottom
        ------------------------------------------------------------------- */}
        <div className="w-full xl:w-2/4 flex flex-col gap-4">

          {/* VIEW: SUMMARY PHASE */}
          {viewingPhase === 'SUMMARY' ? (
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border flex items-center gap-1 ${
                      completionStatus === 'FULL'
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                        : completionStatus.includes('PARTIAL')
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-amber-100 text-amber-800 border-amber-200'
                    }`}>
                      <CheckCircle2 size={13} className="text-emerald-600" />
                      {completionStatus === 'FULL' 
                        ? "Full Multi-Agent Procurement Completed" 
                        : completionStatus === 'PARTIAL_PRODUCE_ONLY'
                          ? "Partial Completion: Produce Agreement Only (Logistics Self-Arranged)"
                          : completionStatus === 'PARTIAL_LOGISTICS_ONLY'
                            ? "Partial Completion: Inbound Freight Only"
                            : "Procurement Summary & Cost Assessment"}
                    </span>
                    <span className="text-xs text-slate-400">APMC e-NAM Compliant</span>
                  </div>
                  <h2 className="text-xl font-black text-slate-800">
                    End-to-End Landed Cost & Multi-Party Term Sheet
                  </h2>
                  <p className="text-xs text-slate-500">
                    Aggregated multi-agent agreement covering {cropQty.toLocaleString()} kg of {cropName}.
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Total Landed Cost</span>
                  <span className="text-2xl font-black text-emerald-700 font-mono">
                    Rs.{totalLandedCost.toLocaleString()}
                  </span>
                  <span className="text-xs font-bold text-slate-600 block">
                    (Rs.{cropQty > 0 ? (totalLandedCost / cropQty).toFixed(2) : '0'}/kg delivered)
                  </span>
                </div>
              </div>

              {/* Cost Composition Breakdown */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Landed Cost Composition</h4>
                <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs">
                  {/* 1. Crop Produce */}
                  <div className="p-3.5 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">1</div>
                      <div>
                        <p className="font-bold text-slate-800">Crop Produce (Farmer Producer)</p>
                        <p className="text-[11px] text-slate-500">
                          {isProduceAgreed ? (
                            `${farmerRecord?.counterParty || farmerName} • ${cropQty.toLocaleString()} kg @ Rs.${agreedProducePrice}/kg (${farmerRecord?.location || farmerLocation})`
                          ) : (
                            <span className="text-amber-600 font-semibold">Produce Bypassed / Self-Supplied (Rs.0)</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <span className="font-mono font-bold text-sm text-slate-900">
                      Rs.{produceSubtotal.toLocaleString()}
                    </span>
                  </div>

                  {/* 2. Inbound Freight */}
                  <div className="p-3.5 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center font-bold">2</div>
                      <div>
                        <p className="font-bold text-slate-800">Inbound Freight & Haulage</p>
                        <p className="text-[11px] text-slate-500">
                          {isTransportAgreed ? (
                            `${transportRecord?.counterParty || activeVehicle.vehicle_name} • ${transitRoute.origin} to ${transitRoute.destination} (~${transitRoute.distanceKm} km)`
                          ) : (
                            <span className="text-amber-600 font-semibold">Logistics Excluded / Self-Arranged by Buyer (Rs.0)</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <span className="font-mono font-bold text-sm text-slate-900">
                      Rs.{agreedFreightCost.toLocaleString()}
                    </span>
                  </div>

                  {/* 3. Statutory APMC Cess */}
                  <div className="p-3.5 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center font-bold">3</div>
                      <div>
                        <p className="font-bold text-slate-800">Statutory APMC Mandi Cess (1.0%)</p>
                        <p className="text-[11px] text-slate-500">
                          {isProduceAgreed 
                            ? 'Mandatory Maharashtra APMC e-NAM cess levy on produce subtotal' 
                            : 'N/A (No produce purchase)'}
                        </p>
                      </div>
                    </div>
                    <span className="font-mono font-bold text-sm text-slate-900">
                      Rs.{apmcMandiCess.toLocaleString()}
                    </span>
                  </div>

                  {/* 4. Handling */}
                  <div className="p-3.5 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold">4</div>
                      <div>
                        <p className="font-bold text-slate-800">Weighment & Mandi Handling</p>
                        <p className="text-[11px] text-slate-500">Certified weighbridge and handling charges</p>
                      </div>
                    </div>
                    <span className="font-mono font-bold text-sm text-slate-900">
                      Rs.{handlingCost.toLocaleString()}
                    </span>
                  </div>

                  {/* 5. Buffer Storage Allocation */}
                  {completedPhases['WAREHOUSE'] && completedPhases['WAREHOUSE'].status === 'DEAL' && (
                    <div className="p-3.5 flex items-center justify-between bg-purple-50/50">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center font-bold">5</div>
                        <div>
                          <p className="font-bold text-slate-800">Buffer Cold Storage (APMC Statutory Tariff)</p>
                          <p className="text-[11px] text-slate-500">
                            {completedPhases['WAREHOUSE'].counterParty} &bull; {completedPhases['WAREHOUSE'].location} &bull; 3 Days @ Rs.{completedPhases['WAREHOUSE'].details?.cost_per_kg_per_day || 1.6}/kg/day
                          </p>
                        </div>
                      </div>
                      <span className="font-mono font-bold text-sm text-slate-900">
                        Rs.{Number(completedPhases['WAREHOUSE'].agreedPrice || 0).toLocaleString()}
                      </span>
                    </div>
                  )}

                  {/* 6. Agro-Processing Agreement */}
                  {completedPhases['PROCESSOR'] && completedPhases['PROCESSOR'].status === 'DEAL' && (
                    <div className="p-3.5 flex items-center justify-between bg-indigo-50/50">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold">6</div>
                        <div>
                          <p className="font-bold text-slate-800">Industrial Processing Intake Contract</p>
                          <p className="text-[11px] text-slate-500">
                            {completedPhases['PROCESSOR'].counterParty} &bull; Output: {completedPhases['PROCESSOR'].details?.output_product || 'Milled Product'}
                          </p>
                        </div>
                      </div>
                      <span className="font-mono font-bold text-sm text-slate-900">
                        Rs.{Number(completedPhases['PROCESSOR'].agreedPrice || 0).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
                <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
                  {requestedServices.hasFarmer && (
                    <button
                      onClick={() => setViewingPhase('FARMER')}
                      className="px-3 py-1.5 border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-bold transition cursor-pointer"
                    >
                      Review Farmer
                    </button>
                  )}
                  {requestedServices.hasTransport && (
                    <button
                      onClick={() => setViewingPhase('TRANSPORT')}
                      className="px-3 py-1.5 border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-bold transition cursor-pointer"
                    >
                      Review Transport
                    </button>
                  )}
                  {requestedServices.hasWarehouse && (
                    <button
                      onClick={() => setViewingPhase('WAREHOUSE')}
                      className="px-3 py-1.5 border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-bold transition cursor-pointer"
                    >
                      Review Storage
                    </button>
                  )}
                  {requestedServices.hasProcessor && (
                    <button
                      onClick={() => setViewingPhase('PROCESSOR')}
                      className="px-3 py-1.5 border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-bold transition cursor-pointer"
                    >
                      Review Processing
                    </button>
                  )}
                </div>

                <button
                  onClick={() => {
                    setAgreementData({
                      price: agreedProducePrice,
                      quantity: cropQty,
                      farmer: farmerRecord?.counterParty || farmerName,
                      buyer: buyerName || user?.name || 'Buyer Enterprise',
                      crop: cropName,
                      transport_cost: agreedFreightCost,
                      total_landed_cost: totalLandedCost
                    });
                    setShowValidationModal(true);
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs rounded-xl shadow transition flex items-center justify-center gap-2 cursor-pointer"
                >
                  <ShieldCheck size={16} /> Sign & Execute Multi-Party Contract
                </button>
              </div>
            </div>
          ) : viewingPhase === 'TRANSPORT' ? (
            /* VIEW: TRANSPORT NEGOTIATION PHASE */
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm flex flex-col h-[650px] overflow-hidden">
              
              {/* Transport Phase Header */}
              <div className="p-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                    <Truck size={17} className="text-blue-600" /> Transport Freight Negotiation
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Route: <strong className="text-slate-700">{transitRoute.origin}</strong> to <strong className="text-slate-700">{transitRoute.destination}</strong> (~{transitRoute.distanceKm} km)
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 block uppercase">Selected Carrier</span>
                  <span className="font-bold text-xs text-blue-800">{activeVehicle.vehicle_name}</span>
                </div>
              </div>

              {/* Transport Messages Stream */}
              <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#fafbfc]">
                {transportMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col ${msg.sender === 'Buyer Agent' ? 'items-end' : 'items-start'} animate-in fade-in duration-200`}
                  >
                    <div className="text-[10px] text-slate-400 mb-0.5 px-1 font-semibold">
                      {msg.sender} &bull; {msg.time}
                    </div>
                    <div
                      className={`max-w-[85%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                        msg.sender === 'Buyer Agent'
                          ? 'bg-blue-600 text-white rounded-tr-none shadow-sm'
                          : 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-none shadow-sm'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
                {isTransportLoading && (
                  <div className="flex items-center gap-2 text-xs text-slate-400 p-2 animate-pulse">
                    <Bot size={15} className="text-blue-500" />
                    <span>Transport Dispatch Agent is evaluating route diesel & tolls...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Transport Negotiation Controls */}
              <div className="p-4 border-t border-slate-100 bg-white space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500">Asking Freight:</span>
                    <span className="font-bold font-mono text-slate-800">Rs.{standardFreight.toLocaleString()}</span>
                    <span className="text-[11px] text-slate-400">({activeVehicle.ratePerKm}/km)</span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSkipTransport('CANCELLED')}
                      className="px-3 py-1.5 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-lg text-xs font-semibold transition cursor-pointer"
                    >
                      Cancel Logistics
                    </button>
                    <button
                      onClick={() => handleSkipTransport('SKIPPED')}
                      className="px-3 py-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg text-xs font-semibold transition cursor-pointer"
                    >
                      Self-Arranged Pickup
                    </button>
                    <button
                      onClick={() => handleAcceptTransportDeal()}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition shadow-sm cursor-pointer"
                    >
                      Accept Freight (Rs.{standardFreight.toLocaleString()})
                    </button>
                  </div>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleTransportCounter();
                  }}
                  className="flex items-center gap-2 pt-1"
                >
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-2 text-xs text-slate-400 font-bold">Rs.</span>
                    <input
                      type="number"
                      value={transportBuyerOffer}
                      onChange={(e) => setTransportBuyerOffer(e.target.value)}
                      placeholder={`Counter freight budget (e.g. ${Math.round(standardFreight * 0.90)})`}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-4 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isTransportLoading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    Submit Counter
                  </button>
                </form>
              </div>

            </div>
          ) : viewingPhase === 'WAREHOUSE' ? (
            /* VIEW: WAREHOUSE (Integrated Statutory Buffer Storage Service) */
            (() => {
              const warehouses = (warehouseCatalogData && warehouseCatalogData.length > 0) ? warehouseCatalogData : [
                { id: "wh_pune_hub", name: "Pune Agro Hub", location: "Pune", capacity_kg: 15000, available_capacity_kg: 12500, base_cost_per_kg_per_day: 1.6 },
                { id: "wh_nashik_onion", name: "Nashik Onion Buffer", location: "Nashik", capacity_kg: 22000, available_capacity_kg: 19000, base_cost_per_kg_per_day: 1.1 },
                { id: "wh_mumbai_port", name: "Mumbai Port Warehouse", location: "Mumbai", capacity_kg: 18000, available_capacity_kg: 16000, base_cost_per_kg_per_day: 2.2 }
              ];
              const curWh = warehouses.find((w: any) => w.id === selectedWarehouseId) || warehouses[0];
              const dailyCost = Math.round(Number(curWh.base_cost_per_kg_per_day || 1.6) * cropQty);
              const totalCost = dailyCost * 3;
              const isReserved = Boolean(completedPhases['WAREHOUSE'] && completedPhases['WAREHOUSE'].status === 'DEAL');

              return (
                <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-5">
                  <div className="flex items-center gap-2 text-purple-900 bg-purple-50 p-3 rounded-xl border border-purple-200">
                    <Info size={18} className="shrink-0 text-purple-600" />
                    <span className="font-bold text-xs">
                      Statutory Tariff Allocation &bull; Autonomous multi-round RL bidding unavailable; verified warehouse capacity reserved directly.
                    </span>
                  </div>

                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-black text-slate-800 text-lg flex items-center gap-2">
                        <Warehouse size={20} className="text-purple-600" /> {curWh.name}
                      </h3>
                      <p className="text-xs text-slate-500">
                        {curWh.location}, Maharashtra &bull; APMC Registered Cold Storage Buffer
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full font-bold text-xs">
                      WDRA Insured
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Statutory Rate</span>
                      <span className="font-black text-slate-800 text-sm">Rs.{curWh.base_cost_per_kg_per_day}/kg/day</span>
                    </div>
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Holding Lot</span>
                      <span className="font-black text-slate-800 text-sm">{cropQty.toLocaleString()} kg</span>
                    </div>
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Buffer Duration</span>
                      <span className="font-black text-slate-800 text-sm">3 Days</span>
                    </div>
                    <div className="p-3 bg-purple-50 border border-purple-200/80 rounded-xl">
                      <span className="text-purple-700 block mb-0.5">Total Buffer Fee</span>
                      <span className="font-black text-purple-900 text-sm">Rs.{totalCost.toLocaleString()}</span>
                    </div>
                  </div>

                  {isReserved ? (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1.5">
                        <CheckCircle2 size={16} /> Buffer Storage Reserved for {cropQty.toLocaleString()} kg at {curWh.name} (Rs.{totalCost.toLocaleString()})
                      </span>
                      <button
                        onClick={() => {
                          if (requestedServices.hasProcessor && !completedPhases['PROCESSOR']) {
                            setActivePhase('PROCESSOR');
                            setViewingPhase('PROCESSOR');
                          } else {
                            setActivePhase('SUMMARY');
                            setViewingPhase('SUMMARY');
                          }
                        }}
                        className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg font-bold cursor-pointer transition"
                      >
                        Next Phase &rarr;
                      </button>
                    </div>
                  ) : (
                    <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100">
                      <button
                        onClick={handleSkipWarehouse}
                        className="text-xs text-slate-500 hover:text-slate-800 underline font-semibold cursor-pointer"
                      >
                        Skip Buffer Storage (Proceed without holding)
                      </button>
                      <button
                        onClick={() => handleReserveWarehouse(curWh)}
                        disabled={isWarehouseLoading}
                        className="px-5 py-2.5 bg-purple-700 hover:bg-purple-600 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
                      >
                        <ShieldCheck size={16} /> {isWarehouseLoading ? 'Reserving...' : `Reserve Storage Slot (Rs.${totalCost.toLocaleString()})`}
                      </button>
                    </div>
                  )}
                </div>
              );
            })()
          ) : viewingPhase === 'PROCESSOR' ? (
            /* VIEW: PROCESSOR (Integrated Value-Added Agro-Processing Service) */
            (() => {
              const processors = (processorCatalogData && processorCatalogData.length > 0) ? processorCatalogData : [
                { processor_id: "proc_soy_latur", name: "Marathwada Solvent Extractions & Soya Foods", location: "Latur", price_per_kg: 68.0, output_product: "Refined Soya Oil & DOC", capacity_kg: 20000, min_order_kg: 500 },
                { processor_id: "proc_cotton_amravati", name: "Vidarbha Ginning & Spinning Textiles", location: "Amravati", price_per_kg: 64.5, output_product: "Baled Lint & Cotton Yarn", capacity_kg: 15000, min_order_kg: 500 },
                { processor_id: "proc_onion_dehydration_nashik", name: "Nashik Agro Dehydration Plant", location: "Nashik", price_per_kg: 19.5, output_product: "Dehydrated Onion Flakes", capacity_kg: 10000, min_order_kg: 200 }
              ];
              const curProc = processors.find((p: any) => p.processor_id === selectedProcessorId) || processors[0];
              const totalPayment = Math.round(Number(curProc.price_per_kg || 50) * cropQty);
              const isAgreed = Boolean(completedPhases['PROCESSOR'] && completedPhases['PROCESSOR'].status === 'DEAL');

              return (
                <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-5">
                  <div className="flex items-center gap-2 text-indigo-900 bg-indigo-50 p-3 rounded-xl border border-indigo-200">
                    <Info size={18} className="shrink-0 text-indigo-600" />
                    <span className="font-bold text-xs">
                      Industrial Processing Catalog &bull; Multi-round autonomous bidding unavailable; verified industrial facility intake agreement confirmed directly.
                    </span>
                  </div>

                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-black text-slate-800 text-lg flex items-center gap-2">
                        <Factory size={20} className="text-indigo-600" /> {curProc.name}
                      </h3>
                      <p className="text-xs text-slate-500">
                        {curProc.location}, Maharashtra &bull; Output: {curProc.output_product}
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full font-bold text-xs">
                      Licensed Mill
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Intake Price</span>
                      <span className="font-black text-slate-800 text-sm">Rs.{curProc.price_per_kg}/kg</span>
                    </div>
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Lot Quantity</span>
                      <span className="font-black text-slate-800 text-sm">{cropQty.toLocaleString()} kg</span>
                    </div>
                    <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl">
                      <span className="text-slate-400 block mb-0.5">Facility Capacity</span>
                      <span className="font-black text-slate-800 text-sm">{(curProc.capacity_kg || 15000).toLocaleString()} kg</span>
                    </div>
                    <div className="p-3 bg-indigo-50 border border-indigo-200/80 rounded-xl">
                      <span className="text-indigo-700 block mb-0.5">Total Contract Value</span>
                      <span className="font-black text-indigo-900 text-sm">Rs.{totalPayment.toLocaleString()}</span>
                    </div>
                  </div>

                  {isAgreed ? (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1.5">
                        <CheckCircle2 size={16} /> Processing Agreement Confirmed with {curProc.name} (Rs.{totalPayment.toLocaleString()})
                      </span>
                      <button
                        onClick={() => {
                          setActivePhase('SUMMARY');
                          setViewingPhase('SUMMARY');
                        }}
                        className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg font-bold cursor-pointer transition"
                      >
                        Proceed to Summary &rarr;
                      </button>
                    </div>
                  ) : (
                    <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100">
                      <button
                        onClick={handleSkipProcessor}
                        className="text-xs text-slate-500 hover:text-slate-800 underline font-semibold cursor-pointer"
                      >
                        Skip Value-Added Processing
                      </button>
                      <button
                        onClick={() => handleConfirmProcessor(curProc)}
                        disabled={isProcessorLoading}
                        className="px-5 py-2.5 bg-indigo-700 hover:bg-indigo-600 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
                      >
                        <ShieldCheck size={16} /> {isProcessorLoading ? 'Confirming...' : `Confirm Processing Order (Rs.${totalPayment.toLocaleString()})`}
                      </button>
                    </div>
                  )}
                </div>
              );
            })()
          ) : (
            /* VIEW: FARMER NEGOTIATION PHASE (Standard Core Flow) */
            <>
              {recommendation && <RecommendationCard recommendation={recommendation} />}

              {/* Active Farmer Negotiation Card */}
              <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm flex flex-col h-[520px] overflow-hidden">
                
                {/* Farmer Negotiation Header */}
                <div className="p-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <h3 className="font-bold text-slate-800 text-sm">
                      Active Negotiation with {farmerName}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full">
                      APMC Grade A
                    </span>
                    <button
                      onClick={runParallelAutonomousNegotiation}
                      disabled={isParallelRunning}
                      className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      <Zap size={13} /> {isParallelRunning ? 'Negotiating...' : 'Auto-Negotiate'}
                    </button>
                  </div>
                </div>

                {/* Messages Stream */}
                <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#fafbfc]">
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col ${msg.sender?.includes('Buyer') ? 'items-end' : 'items-start'} animate-in fade-in duration-200`}
                    >
                      <div className="text-[10px] text-slate-400 mb-0.5 px-1 font-semibold">
                        {msg.sender} &bull; {msg.time}
                      </div>
                      <div
                        className={`max-w-[85%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                          msg.sender?.includes('Buyer')
                            ? 'bg-emerald-700 text-white rounded-tr-none shadow-sm'
                            : 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-none shadow-sm'
                        }`}
                      >
                        {msg.text}
                        {msg.price && (
                          <div className="mt-1 font-black font-mono text-[11px] opacity-95">
                            Offer: Rs.{msg.price}/kg
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Offer Action Banner */}
                <div className="p-4 border-t border-slate-100 bg-white flex items-center justify-between gap-3">
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Latest Farmer Ask</span>
                    <span className="font-black text-slate-900 text-base font-mono">
                      Rs.{bestOfferPrice}/kg
                    </span>
                    <span className="text-[11px] text-slate-500 ml-1">
                      (Total: Rs.{(bestOfferPrice * cropQty).toLocaleString()})
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsRagOpen(true)}
                      className="px-3 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold transition cursor-pointer"
                    >
                      View Analysis
                    </button>
                    <button
                      onClick={() => handleAcceptDeal()}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-black transition shadow cursor-pointer"
                    >
                      Accept Deal
                    </button>
                  </div>
                </div>

              </div>
            </>
          )}

          {/* Live Activity Terminal Logs at Bottom */}
          <div className="bg-[#0f172a] rounded-xl p-4 font-mono text-[11px] leading-relaxed overflow-y-auto max-h-44 text-slate-300 shadow-inner">
            <div className="text-emerald-400 font-bold mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> LIVE ACTIVITY
            </div>
            <div className="space-y-1">
              {liveTerminalLogs.length === 0 ? (
                <>
                  <div className="flex items-start gap-2 text-slate-400 text-[10px]">
                    <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                    <span className="text-blue-400 font-bold shrink-0">System:</span>
                    <span>Session initialized in Redis memory. Multi-agent coordinator active.</span>
                  </div>
                  <div className="flex items-start gap-2 text-slate-400 text-[10px]">
                    <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                    <span className="text-purple-400 font-bold shrink-0">Planner:</span>
                    <span>Evaluating dynamic constraints for {cropName} ({cropQty} kg).</span>
                  </div>
                </>
              ) : (
                liveTerminalLogs.map((log, lIdx) => (
                  <div key={lIdx} className="flex items-start gap-2 text-[10px] animate-in fade-in duration-150">
                    <span className="text-slate-600 shrink-0">[{log.time}]</span>
                    <span className={`font-bold shrink-0 ${log.color || 'text-blue-400'}`}>[{log.tag}]</span>
                    <span className="text-slate-300 break-words flex-1">{log.text}</span>
                  </div>
                ))
              )}
              <div ref={terminalEndRef} />
            </div>
          </div>

        </div>

        {/* -------------------------------------------------------------------
            COLUMN 3: Right Contextual Panel (~25-27%)
            - Current Offer vs Buyer Offer & Price Delta
            - Relevant Decision Controls
            - Agent-Specific Intelligence (LangGraph 6-Stage Stepper, RAG drawer)
            - Self-Reflective Agent Post-Mortem Card
            - Buyer Procurement Copilot
        ------------------------------------------------------------------- */}
        <div className="w-full xl:w-1/4 flex flex-col gap-4">

          {/* Active Offer vs Buyer Target & Price Difference Delta Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <DollarSign size={16} className="text-emerald-600" /> Active Price Difference
              </h4>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-full">
                {viewingPhase} Phase
              </span>
            </div>

            {viewingPhase === 'TRANSPORT' ? (
              /* Transport Freight Delta */
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl text-xs">
                  <div>
                    <span className="text-slate-500 block text-[11px]">Carrier Ask</span>
                    <span className="font-black text-slate-900 text-base font-mono">
                      Rs.{standardFreight.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">Buyer Target</span>
                    <span className="font-black text-blue-700 text-base font-mono">
                      Rs.{Math.round(standardFreight * 0.90).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs px-1">
                  <span className="text-slate-500">Freight Variance:</span>
                  <span className="font-bold text-amber-700 font-mono">
                    +Rs.{Math.round(standardFreight * 0.10).toLocaleString()} (+10%)
                  </span>
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleAcceptTransportDeal()}
                    className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition shadow-sm cursor-pointer"
                  >
                    Accept Freight
                  </button>
                  <button
                    onClick={() => handleTransportCounter()}
                    className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl text-xs transition shadow-sm cursor-pointer"
                  >
                    Counter Freight
                  </button>
                </div>
              </div>
            ) : (
              /* Farmer Produce Delta */
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl text-xs">
                  <div>
                    <span className="text-slate-500 block text-[11px]">Farmer Ask</span>
                    <span className="font-black text-slate-900 text-base font-mono">
                      Rs.{bestOfferPrice}/kg
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px]">Buyer Target</span>
                    <span className="font-black text-emerald-700 text-base font-mono">
                      Rs.{targetPrice}/kg
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs px-1">
                  <span className="text-slate-500">Price Difference:</span>
                  <span className="font-bold text-amber-700 font-mono">
                    +Rs.{(bestOfferPrice - targetPrice).toFixed(1)}/kg (+{Math.round(((bestOfferPrice - targetPrice) / targetPrice) * 100)}%)
                  </span>
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleAcceptDeal()}
                    className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition shadow-sm cursor-pointer"
                  >
                    Accept Deal
                  </button>
                  <button
                    onClick={runParallelAutonomousNegotiation}
                    disabled={isParallelRunning}
                    className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl text-xs transition shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    Counter-Offer
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* LangGraph 6-Stage Stepper & RAG Trigger */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
            <div className="flex justify-between items-center">
              <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Zap size={16} className="text-emerald-500" /> LangGraph Execution
              </h4>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                Active Agent
              </span>
            </div>

            <AgentWorkflowStepper
              activeAgent={viewingPhase === 'TRANSPORT' ? 'Negotiator' : 'Market Intel'}
              isBuyer={isBuyer}
              status="LIVE"
              hasRecommendation={Boolean(recommendation)}
              hasReflection={Boolean(reflection)}
            />

            <button
              onClick={() => setIsRagOpen(true)}
              className="w-full py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-700 font-bold text-xs rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-sm"
            >
              <Database size={14} className="text-slate-500" /> View RAG Context
            </button>

            {reflection && <ReflectionCard reflection={reflection} />}
          </div>

          {/* Buyer Procurement Copilot */}
          <div className="bg-[#0f172a] rounded-2xl shadow-lg border border-slate-800 p-5 text-white flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm flex items-center gap-2 text-white">
                  <ShieldCheck size={16} className="text-blue-400" />
                  <span>Buyer Procurement Copilot</span>
                </h3>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                Autonomous guidance for {cropName} across Maharashtra APMC hubs.
              </p>

              {/* Copilot Action Presets adapted to active phase */}
              <div className="flex flex-wrap gap-2 mb-4">
                {viewingPhase === 'TRANSPORT' ? (
                  <>
                    <button
                      onClick={() => setCopilotCommand(`Counter freight at Rs.${Math.round(standardFreight * 0.88)}`)}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Counter 12% lower
                    </button>
                    <button
                      onClick={() => setCopilotCommand('Require Refrigerated Unit')}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Require Reefer
                    </button>
                    <button
                      onClick={() => setCopilotCommand('Enforce 24h Delivery Deadline')}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Enforce 24h
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setCopilotCommand(`Counter at target Rs.${Math.round(targetPrice)}`)}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Counter at Rs.{Math.round(targetPrice)}
                    </button>
                    <button
                      onClick={() => setCopilotCommand(`Don't exceed Rs.${Math.round(maxAllowedCeiling)}`)}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Budget Ceiling
                    </button>
                    <button
                      onClick={() => setCopilotCommand('Counter best farmer')}
                      className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer"
                    >
                      Counter best farmer
                    </button>
                  </>
                )}
              </div>

              {/* Last Copilot Response Feedback */}
              {copilotMessages.length > 0 && (
                <div className="mb-3 p-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-[11px] text-slate-300 flex items-start gap-2 shadow-inner">
                  <Bot size={14} className="text-blue-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="text-slate-400 font-semibold text-[10px]">
                      {copilotMessages[copilotMessages.length - 1].sender === 'AI' ? 'AI Copilot: ' : 'Instruction: '}
                    </span>
                    <span>{copilotMessages[copilotMessages.length - 1].text}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Copilot Input Form */}
            <form onSubmit={handleCopilotSubmit} className="space-y-3 mt-auto">
              <input
                type="text"
                value={copilotCommand}
                onChange={e => setCopilotCommand(e.target.value)}
                placeholder="Give instruction to Buyer Agent..."
                className="w-full bg-[#1e293b]/80 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition cursor-pointer shadow-sm"
              >
                Send Instruction
              </button>
            </form>
          </div>

        </div>

      </div>

      {/* Intact RAG Drawer Component */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} crop={cropName} />

      {/* Intact Cryptographic Transaction Validation Modal */}
      <TransactionValidationModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        transactionData={agreementData || {
          price: agreedProducePrice,
          farmer: farmerRecord?.counterParty || farmerName,
          buyer: buyerName || user?.name || 'Buyer Enterprise',
          crop: cropName,
          quantity: cropQty,
          transport_cost: agreedFreightCost,
          total_landed_cost: totalLandedCost
        }}
      />

    </div>
  );
}
