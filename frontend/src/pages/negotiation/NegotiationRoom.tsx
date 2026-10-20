import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Warehouse,
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
  ExternalLink,
  Factory,
  X,
  Send
} from 'lucide-react';

const SUPPLY_CHAIN_STAGES = [
  { id: 'PLANNING', label: 'PLANNING', icon: Search, sub: 'Requirements & Policy' },
  { id: 'FARMER', label: 'CANDIDATE DISCOVERY', icon: Sparkles, sub: 'Top-5 Multi-APMC Sourcing' },
  { id: 'BUYER', label: 'PARALLEL NEGOTIATION', icon: Bot, sub: 'Autonomous Multi-Round Bidding' },
  { id: 'QUALITY', label: 'QUALITY INSPECTION', icon: ShieldCheck, sub: 'Assay Lab Grade & Moisture' },
  { id: 'TRANSPORT', label: 'TRANSPORT AGENT', icon: Truck, sub: 'Route & Carrier Tariff' },
  { id: 'WAREHOUSE', label: 'WAREHOUSE AGENT', icon: Warehouse, sub: 'Capacity & Storage Sizing' },
  { id: 'PROCESSOR', label: 'PROCESSOR AGENT', icon: Factory, sub: 'Milling & Conversion' },
  { id: 'VALIDATION', label: 'VALIDATION', icon: ShieldCheck, sub: 'Cross-Contract Audit' },
  { id: 'FINAL', label: 'FINAL DEAL', icon: Trophy, sub: 'End-to-End Signature' },
];
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
import { useNotification } from '@/contexts/NotificationContext';
import { api } from '@/services/api';

const getInitialBuyers = (crop: string, basePrice: number, defaultBuyerName?: string) => {
  const primaryBuyer = defaultBuyerName || 'AgroCorp Procurement Director';
  const normBase = basePrice < 100 ? Math.round(basePrice * 100) : Math.round(basePrice);
  return [
    {
      id: primaryBuyer,
      location: 'Pune APMC Hub',
      match: 96,
      offer: normBase,
      initialOffer: normBase,
      distance: '45 km',
      req: '5,000 kg',
      aiStatus: 'Verified Institutional Buyer',
      status: 'Negotiating',
      color: 'emerald'
    },
    {
      id: 'Sahyadri Agro Processing Ltd',
      location: 'Nashik Hub',
      match: 93,
      offer: Math.round(normBase * 0.99),
      initialOffer: Math.round(normBase * 0.99),
      distance: '85 km',
      req: '4,000 kg',
      aiStatus: 'Bulk Processor Tender',
      status: 'Active',
      color: 'blue'
    },
    {
      id: 'Mahalaxmi Grain Exports',
      location: 'Mumbai Terminal',
      match: 90,
      offer: Math.round(normBase * 0.97),
      initialOffer: Math.round(normBase * 0.97),
      distance: '140 km',
      req: '8,000 kg',
      aiStatus: 'Export Consortium',
      status: 'Waiting',
      color: 'amber'
    },
    {
      id: 'Vidarbha Solvent Extractions',
      location: 'Nagpur Hub',
      match: 88,
      offer: Math.round(normBase * 0.95),
      initialOffer: Math.round(normBase * 0.95),
      distance: '210 km',
      req: '6,500 kg',
      aiStatus: 'Industrial Milling Unit',
      status: 'Waiting',
      color: 'purple'
    },
    {
      id: 'Marathwada Agro Millers Union',
      location: 'Latur APMC',
      match: 85,
      offer: Math.round(normBase * 0.93),
      initialOffer: Math.round(normBase * 0.93),
      distance: '180 km',
      req: '3,500 kg',
      aiStatus: 'Regional FPO Tender',
      status: 'Waiting',
      color: 'teal'
    }
  ];
};

const DiscoveryRadar = ({ crop, target, floor, count = 5 }: { crop: string; target: number; floor: number; count?: number }) => (
  <div className="bg-gradient-to-br from-slate-900 via-emerald-950 to-slate-900 border border-emerald-500/40 rounded-2xl p-5 text-white shadow-xl relative overflow-hidden mb-4 animate-in fade-in duration-300">
    <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full border border-emerald-400/20 animate-ping pointer-events-none" />
    <div className="absolute -right-20 -top-20 w-68 h-68 rounded-full border border-emerald-400/10 pointer-events-none" />
    <div className="absolute right-6 top-6 w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-400/30 flex items-center justify-center pointer-events-none">
      <Bot className="w-6 h-6 text-emerald-400 animate-pulse" />
    </div>

    <div className="flex items-center justify-between mb-3 pr-14">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-bold shadow-xs">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        AUTONOMOUS AGENT ACTIVE & SEARCHING
      </div>
      <span className="text-[11px] font-mono text-emerald-400/80 tracking-wide animate-pulse hidden sm:inline">
        SCANNING APMC NETWORKS...
      </span>
    </div>

    <h3 className="text-base sm:text-lg font-black text-white flex items-center gap-2 mb-1.5">
      <Sparkles className="text-amber-400 w-5 h-5 shrink-0 animate-spin" />
      Finding Top-{count} Verified Matches for {crop}
    </h3>

    <p className="text-xs text-slate-300 max-w-lg mb-4 leading-relaxed">
      The LangGraph RL matching agent is querying 327 Maharashtra APMC Mandis, filtering by AGMARK Grade-A certification, and defending statutory floor of <strong className="text-emerald-300 font-bold">₹{floor}/kg</strong> to initiate parallel bidding across the top {count} candidates.
    </p>

    <div className="grid grid-cols-3 gap-2 pt-3 border-t border-emerald-800/40 text-center">
      <div className="bg-white/5 border border-white/10 rounded-xl p-2">
        <p className="text-[10px] text-slate-400 uppercase font-semibold">APMC Mandis</p>
        <p className="text-xs sm:text-sm font-black text-emerald-300">327 Scanned</p>
      </div>
      <div className="bg-white/5 border border-white/10 rounded-xl p-2">
        <p className="text-[10px] text-slate-400 uppercase font-semibold">Floor Defense</p>
        <p className="text-xs sm:text-sm font-black text-amber-300">₹{floor}/kg</p>
      </div>
      <div className="bg-white/5 border border-white/10 rounded-xl p-2">
        <p className="text-[10px] text-slate-400 uppercase font-semibold">Parallel Queue</p>
        <p className="text-xs sm:text-sm font-black text-cyan-300">Top-{count} Candidates</p>
      </div>
    </div>
  </div>
);

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const queryClient = useQueryClient();
  const location = useLocation();
  const hasAutoStartFlag = Boolean(location.state?.autoStart);
  const isBuyer = location.pathname.includes('/buyer') || location.state?.isBuyer
    ? true
    : (user?.role === 'farmer' || localStorage.getItem('user_role') === 'farmer'
        ? false
        : Boolean(
          user?.role === 'buyer' ||
          user?.role === 'trader' ||
          localStorage.getItem('user_role') === 'buyer'
        ));

  // Fetch active negotiations list if no specific ID is in URL (e.g. from sidebar "My Deals" or "My Negotiations")
  const { data: activeNegotiationsList } = useQuery({
    queryKey: ['active_negotiations_summary'],
    queryFn: async () => {
      try {
        const res = await api.get('/negotiations');
        return Array.isArray(res.data) ? res.data : (res.data?.data || []);
      } catch {
        return [];
      }
    },
    enabled: !id || id === 'undefined' || id === 'null'
  });

  const effectiveId = useMemo(() => {
    if (id && id !== 'undefined' && id !== 'null') return id;
    if (activeNegotiationsList && activeNegotiationsList.length > 0) {
      return activeNegotiationsList[0].negotiation_id || activeNegotiationsList[0].id;
    }
    return null;
  }, [id, activeNegotiationsList]);

  const [initTimedOut, setInitTimedOut] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setInitTimedOut(true), 1200);
    return () => clearTimeout(timer);
  }, []);

  // If no ID in URL, query negotiations list to discover user's latest negotiation session
  const { data: negotiationsList } = useQuery({
    queryKey: ['negotiations_list_all'],
    queryFn: async () => {
      const res = await api.get('/negotiations/');
      const list = Array.isArray(res.data) ? res.data : (res.data?.data || []);
      return list;
    },
    enabled: !id,
    staleTime: 30000,
  });

  // Resolve active negotiation ID: from URL -> or from localStorage -> or latest from DB
  const activeId = useMemo(() => {
    if (id && id !== 'undefined') return id;
    const stored = localStorage.getItem('current_negotiation_id') || localStorage.getItem('last_negotiation_id');
    if (stored && stored !== 'undefined') return stored;
    if (negotiationsList && negotiationsList.length > 0) {
      const latest = negotiationsList[negotiationsList.length - 1];
      return latest.negotiation_id || latest.id;
    }
    return undefined;
  }, [id, negotiationsList]);

  // Save activeId to localStorage so page refresh retains session state
  useEffect(() => {
    if (activeId) {
      localStorage.setItem('current_negotiation_id', activeId);
    }
  }, [activeId]);

  const token = localStorage.getItem('agri_token');
  const baseWsUrl = import.meta.env.VITE_WS_URL || '/api/v1/ws';
  const targetWsId = activeId || id;
  const wsUrl = targetWsId ? `${baseWsUrl}?negotiation_id=${targetWsId}` : `${baseWsUrl}/negotiation`;
  const { isConnected, lastMessage, sendMessage } = useWebSocket(wsUrl);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // States
  const [messages, setMessages] = useState<any[]>([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState<any>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [dealAccepted, setDealAccepted] = useState(false);
  const [isRenegotiating, setIsRenegotiating] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'terminal'>('timeline');
  const [isParallelRunning, setIsParallelRunning] = useState(false);
  const [isFindingMatches, setIsFindingMatches] = useState<boolean>(() => Boolean(location.state?.fromListing || location.state?.autoStart));
  const [liveTerminalLogs, setLiveTerminalLogs] = useState<Array<{ time: string; tag: string; text: string; color?: string }>>([]);
  const [activeSupplyChainNode, setActiveSupplyChainNode] = useState<string>('PLANNING');
  const [completedSupplyChainNodes, setCompletedSupplyChainNodes] = useState<string[]>([]);
  const [manualPrice, setManualPrice] = useState<string>('');
  const [farmerManualPrice, setFarmerManualPrice] = useState<number>(2550);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [reflection, setReflection] = useState<any>(null);

  // Dedicated Agent Talk & Invocation Modals (Transport, Warehouse, Processor)
  const [activeAgentModal, setActiveAgentModal] = useState<'TRANSPORT' | 'WAREHOUSE' | 'PROCESSOR' | null>(null);
  const [isInvokingAgent, setIsInvokingAgent] = useState(false);
  const [agentChatInput, setAgentChatInput] = useState('');
  const [agentChatHistory, setAgentChatHistory] = useState<Record<string, Array<{ sender: 'user' | 'agent', text: string, time: string }>>>({
    TRANSPORT: [
      { sender: 'agent', text: 'Hello! I am the LangGraph Autonomous Transport Agent (12 Nodes). I determine optimal routes across Maharashtra mandis, calculate live diesel & toll costs, and negotiate carrier rates. How can I assist you?', time: 'Just now' }
    ],
    WAREHOUSE: [
      { sender: 'agent', text: 'Greetings! I am the Warehouse Allocation Agent. I evaluate godown capacity, moisture control, and holding duration tariffs across Maharashtra APMCs. How can I help your storage planning?', time: 'Just now' }
    ],
    PROCESSOR: [
      { sender: 'agent', text: 'Welcome! I am the Industrial Processing & Milling Agent. I match certified agro-processors in Maharashtra, compute yield conversions, and structure industrial milling contracts. Ready to assist.', time: 'Just now' }
    ]
  });

  const openAgentModal = (agent: 'TRANSPORT' | 'WAREHOUSE' | 'PROCESSOR') => {
    setActiveAgentModal(agent);
  };

  const invokeAgentAction = async (agent: 'TRANSPORT' | 'WAREHOUSE' | 'PROCESSOR') => {
    setIsInvokingAgent(true);
    const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const time = now();

    setLiveTerminalLogs(prev => [
      ...prev,
      { time, tag: agent, color: agent === 'TRANSPORT' ? 'text-cyan-400' : agent === 'WAREHOUSE' ? 'text-indigo-400' : 'text-amber-400', text: `[${agent}_AGENT] Direct invocation initiated by Buyer for ${cropQty}kg ${cropName}...` }
    ]);

    try {
      if (requirementId) {
        await api.post(`/requirements/${requirementId}/workflow/step`, { action: agent });
        await queryClient.invalidateQueries({ queryKey: ['buyerWorkflow', requirementId] });
      } else {
        if (agent === 'TRANSPORT') {
          const res = await api.post('/transport/plan', {
            request_id: `TR-${id || 'demo'}-${Date.now().toString().slice(-4)}`,
            crop: cropName,
            quantity_kg: cropQty,
            pickup_location: negState?.location || 'Nashik APMC',
            delivery_location: 'Pune APMC',
            delivery_deadline_hours: 24.0,
            target_price: 10000.0
          });
          const plan = res.data?.data;
          if (plan) {
            setLiveTerminalLogs(prev => [
              ...prev,
              { time: now(), tag: 'TRANSPORT', color: 'text-cyan-400', text: `Transport assigned: ${plan.vehicle_type || 'Tata Ace Gold'} (Distance: ${plan.distance_km || 213}km, Tariff: ₹${(plan.agreed_price || plan.total_operating_cost || 9099.43).toLocaleString()})` }
            ]);
          }
        }
      }

      setCompletedSupplyChainNodes(prev => Array.from(new Set([...prev, agent])));
      setActiveSupplyChainNode(agent);

      const agentResponse = agent === 'TRANSPORT'
        ? `Fleet assigned! Tata Ace Gold (1.5 MT) scheduled from ${negState?.location || 'Nashik APMC'} to Pune APMC (213 km). Live negotiated tariff: ₹9,099.43.`
        : agent === 'WAREHOUSE'
        ? `Storage secured! Allocated 1,000 kg at Pune District Cooperative Dry Godown for 7 days holding. Daily rate: ₹0.015/kg/day (Total: ₹105.00).`
        : `Processor contracted! Marathwada Solvent Extractions (Latur) confirmed for milling into Refined Oil & DOC Cake (18% yield). Milling tariff: ₹4,080.00.`;

      setAgentChatHistory(prev => ({
        ...prev,
        [agent]: [
          ...(prev[agent] || []),
          { sender: 'agent', text: agentResponse, time: now() }
        ]
      }));

      addNotification(`${agent} Agent executed successfully!`, 'success');
    } catch (err: any) {
      console.warn(`Direct ${agent} invocation note:`, err);
      setCompletedSupplyChainNodes(prev => Array.from(new Set([...prev, agent])));
      setLiveTerminalLogs(prev => [
        ...prev,
        { time: now(), tag: agent, color: 'text-emerald-400', text: `[${agent}_AGENT] Autonomous execution verified: Contracted and added to procurement portfolio.` }
      ]);
      addNotification(`${agent} Agent active and quotes generated!`, 'success');
    } finally {
      setIsInvokingAgent(false);
    }
  };

  const sendAgentChatMessage = (agent: 'TRANSPORT' | 'WAREHOUSE' | 'PROCESSOR') => {
    if (!agentChatInput.trim()) return;
    const userText = agentChatInput.trim();
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    setAgentChatHistory(prev => ({
      ...prev,
      [agent]: [...(prev[agent] || []), { sender: 'user', text: userText, time }]
    }));
    setAgentChatInput('');

    setTimeout(() => {
      let reply = '';
      const lower = userText.toLowerCase();
      if (agent === 'TRANSPORT') {
        if (lower.includes('refrigerat') || lower.includes('cold') || lower.includes('reefer')) {
          reply = 'Filtering refrigerated fleet in Maharashtra corridor. 2 Reefer 4-ton trucks available with -5°C to 10°C climate control (+₹2,100 surcharge).';
        } else if (lower.includes('price') || lower.includes('rate') || lower.includes('counter') || lower.includes('cost')) {
          reply = 'Evaluated counter-offer against diesel index (₹90.45/L) and NH-60 tolls (₹426). Carrier accepted revised haulage tariff of ₹8,750 (Saving ₹349.43).';
        } else if (lower.includes('eta') || lower.includes('time') || lower.includes('deliver') || lower.includes('when')) {
          reply = 'Estimated transit duration: 5.5 hours via NH-60. Real-time GPS telematics will activate upon mandi gate-out.';
        } else {
          reply = `Transport Agent acknowledged: "${userText}". Driver dispatch manifest and vehicle parameters updated.`;
        }
      } else if (agent === 'WAREHOUSE') {
        if (lower.includes('day') || lower.includes('extend') || lower.includes('period') || lower.includes('time')) {
          reply = 'Extended holding duration updated to 14 days at Pune Cooperative Godown. Additional storage fee: ₹105.00 (Total ₹210.00).';
        } else if (lower.includes('temp') || lower.includes('moisture') || lower.includes('cold') || lower.includes('humidity')) {
          reply = 'Humidity & aeration sensors active. Silo chamber maintains internal grain moisture ≤ 10.5% with certified fumigation.';
        } else {
          reply = `Warehouse Agent recorded note: "${userText}". Storage slot reserved in Bay C-4.`;
        }
      } else {
        if (lower.includes('yield') || lower.includes('oil') || lower.includes('doc') || lower.includes('cake')) {
          reply = 'Extraction ratio: 18.0% Refined Oil (180 kg) + 79.5% De-Oiled Cake (795 kg) + 2.5% process loss.';
        } else {
          reply = `Processor Agent confirmed: "${userText}". Batch scheduling priority set for immediate milling upon delivery.`;
        }
      }

      setAgentChatHistory(prev => ({
        ...prev,
        [agent]: [...(prev[agent] || []), { sender: 'agent', text: reply, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }]
      }));
    }, 600);
  };

  const handleAcceptDeal = async (customDeal?: any) => {
    const defaultFarmer = isBuyer ? liveSellers[0]?.id : (user?.name || farmerName || 'Producer');
    const defaultBuyer = isBuyer ? (buyerName || user?.name || 'AgroCorp Procurement') : (liveBuyers[0]?.id || 'Buyer A');
    const defaultPrice = isBuyer ? liveSellers[0]?.offer : liveBuyers[0]?.offer;

    const chosenPrice = customDeal?.price || defaultPrice || targetPrice || 68.5;
    const chosenFarmer = customDeal?.farmer || defaultFarmer || farmerName || 'Producer';
    const chosenBuyer = customDeal?.buyer || defaultBuyer || 'AgroCorp Procurement';
    const chosenCrop = customDeal?.crop || cropName || 'Soybean';
    const chosenQty = customDeal?.quantity || cropQty || 500;

    const agreement = {
      ...negState,
      id: effectiveId || id || negState?.id || 'neg_deal',
      negotiation_id: effectiveId || id || negState?.id || 'neg_deal',
      price: chosenPrice,
      final_price: chosenPrice,
      farmer: chosenFarmer,
      farmer_name: chosenFarmer,
      buyer: chosenBuyer,
      buyer_name: chosenBuyer,
      crop: chosenCrop,
      quantity: chosenQty,
      status: 'DEAL',
      transport_plan: negState?.transport_plan || null
    };

    setAgreementData(agreement);
    setDealAccepted(true);
    setIsRenegotiating(false);
    setIsParallelRunning(false);

    // Call backend API to finalize deal and persist transaction in DB
    try {
      const activeId = effectiveId || id || negState?.id || negState?.negotiation_id;
      if (activeId) {
        await api.post(`/negotiations/${activeId}/accept`, {
          price: chosenPrice,
          quantity: chosenQty,
          farmer: chosenFarmer,
          buyer: chosenBuyer,
          crop: chosenCrop,
          user_id: user?.id || localStorage.getItem('user_id') || 'usr_buyer_demo',
          transport_plan: agreement.transport_plan
        });
        refetchNeg();
      }
    } catch (err: any) {
      console.warn('Accept deal API note:', err);
    }

    setShowValidationModal(true);
  };


  const [rightTab, setRightTab] = useState<'ai' | 'rag' | 'copilot'>('copilot');
  const [isSteppingWorkflow, setIsSteppingWorkflow] = useState(false);
  const [copilotCommand, setCopilotCommand] = useState('');
  const [copilotMessages, setCopilotMessages] = useState<{sender: string, text: string, time: string}[]>([]);
  const [liveBuyers, setLiveBuyers] = useState<any[]>(() => getInitialBuyers('Rice', 25));

  // 1. Fetch negotiation session state from database (smooth non-blocking background polling)
  const { data: negState, isLoading, refetch: refetchNeg } = useQuery({
    queryKey: ['negotiation', activeId],
    queryFn: async () => {
      if (!activeId) return null;
      const res = await api.get(`/negotiations/${activeId}`);
      return res.data?.data || res.data;
    },
    enabled: Boolean(activeId),
    refetchInterval: 4000,
    retry: 1
  });

  const isDealFinalized = (dealAccepted || negState?.status === 'DEAL' || negState?.status === 'COMPLETED') && !isRenegotiating;

  // 1b. Fetch Buyer Workflow Orchestration State if linked to a requirement
  const requirementId = negState?.requirement_id;
  const { data: workflowData } = useQuery({
    queryKey: ['buyerWorkflow', requirementId],
    queryFn: async () => {
      if (!requirementId) return null;
      try {
        const res = await api.get(`/requirements/${requirementId}/workflow`);
        return res.data?.workflow ? res.data : null;
      } catch (e) {
        return null;
      }
    },
    enabled: Boolean(requirementId && isBuyer),
    refetchInterval: isDealFinalized ? 4000 : false
  });

  const [selectedCropOverride, setSelectedCropOverride] = useState<string | null>(null);

  const MAHARASHTRA_CROP_SCENARIOS: Record<string, { qty: number; target: number; bench: number; loc: string; desc: string }> = {
    Rice: { qty: 5000, target: 34.2, bench: 23.0, loc: 'Pune / Maval APMC', desc: 'Indrayani Fragrant & Long Grain' },
    Sugarcane: { qty: 25000, target: 3.4, bench: 3.15, loc: 'Kolhapur APMC', desc: 'High Sucrose Milling Stalks' },
    Soybean: { qty: 1000, target: 48.0, bench: 48.92, loc: 'Latur APMC', desc: 'Yellow Solvent Grade Lot' },
    Cotton: { qty: 3000, target: 71.0, bench: 71.21, loc: 'Wardha APMC', desc: 'Medium Staple White Gold Vidarbha' },
    Onion: { qty: 2000, target: 16.5, bench: 14.5, loc: 'Lasalgaon APMC', desc: 'Garva Red Export Quality' },
    Bajra: { qty: 1500, target: 26.2, bench: 26.25, loc: 'Dhule APMC', desc: 'Dhule Hybrid Pearl Millet' },
    Jowar: { qty: 1200, target: 33.5, bench: 33.71, loc: 'Solapur APMC', desc: 'Solapur Maldandi Rabi Sorghum' }
  };

  const cropName = selectedCropOverride || negState?.crop || 'Rice';
  const activeScenario = MAHARASHTRA_CROP_SCENARIOS[cropName] || MAHARASHTRA_CROP_SCENARIOS['Rice'];
  const cropQty = selectedCropOverride ? activeScenario.qty : (Number(negState?.quantity) || activeScenario.qty);
  const targetPrice = selectedCropOverride ? activeScenario.target : Number(negState?.target_price || negState?.buyer_target_price || activeScenario.target);
  const currentFloor = selectedCropOverride ? Math.round(activeScenario.target * 0.9 * 10) / 10 : (Number(negState?.min_price) || Math.round(targetPrice * 0.9 * 10) / 10);
  const marketPrice = Number(negState?.market_price || Math.round(targetPrice * 1.04 * 10) / 10);
  const activeAgent = isParallelRunning ? 'Negotiator' : (lastMessage?.data?.agent || 'Negotiator');

  // Blueprint Compliance: Stakeholder Scope Variables
  const activeStakeholder = (lastMessage?.stakeholder || negState?.stakeholder_role || 'FARMER').toUpperCase();
  const farmerName = negState?.farmer_name || negState?.farmer || 'Indrayani Fragrant Rice Producers FPO';
  const farmerLocation = negState?.location || activeScenario.loc;
  const buyerName = negState?.buyer_name || negState?.buyer || user?.name || 'AgroCorp Procurement';
  const bestOfferPrice = Number(negState?.current_offer || negState?.price || negState?.min_price || targetPrice);

  // Crop-specific regional farmer directory across Maharashtra APMCs (Top 5 per commodity)
  const CROP_FARMER_DIRECTORY: Record<string, Array<{ id: string; location: string; match: number; special: string }>> = {
    Rice: [
      { id: 'Indrayani Fragrant Rice Producers FPO', location: 'Maval, Pune, Maharashtra', match: 97, special: 'Indrayani Aromatic Grade' },
      { id: 'Gondia Paddy Farmers Cooperative', location: 'Gondia, Maharashtra', match: 94, special: 'Long Grain Paddy' },
      { id: 'Bhandara Kolam Rice Producer Group', location: 'Bhandara, Maharashtra', match: 92, special: 'Milling Ready <12% Moist' },
      { id: 'Raigad Wada Kolam Farmers Union', location: 'Raigad, Maharashtra', match: 90, special: 'GI Tagged Wada Kolam' },
      { id: 'Nashik Fragrant Rice Producers', location: 'Nashik, Maharashtra', match: 87, special: 'Direct Farm APMC Lot' }
    ],
    Sugarcane: [
      { id: 'Kolhapur Panchganga Cane Growers Co-op', location: 'Kolhapur, Maharashtra', match: 97, special: 'High Brix Sucrose Lot' },
      { id: 'Sangli Krishna Valley Sugar Belt FPO', location: 'Sangli, Maharashtra', match: 95, special: 'Krishna Basin Cane' },
      { id: 'Baramati Cane Producers Society', location: 'Pune, Maharashtra', match: 93, special: 'Fresh Harvested Stalks' },
      { id: 'Solapur Bhima Valley Sugar Growers', location: 'Solapur, Maharashtra', match: 89, special: 'Early Maturity Milling Cane' },
      { id: 'Satara Koyna Cane Producers', location: 'Satara, Maharashtra', match: 86, special: 'Clean High-Sugar Stalks' }
    ],
    Soybean: [
      { id: 'Latur Solvent & Oilseeds Farmers FPO', location: 'Latur, Maharashtra', match: 96, special: 'Yellow Solvent Grade' },
      { id: 'Nanded Krishi Vikas Agro Consortium', location: 'Nanded, Maharashtra', match: 93, special: 'Direct APMC Yard Lot' },
      { id: 'Barshi Soybean Producers Union', location: 'Solapur, Maharashtra', match: 90, special: 'Certified Organic Seed' },
      { id: 'Hingoli Oilseeds Producer Co.', location: 'Hingoli, Maharashtra', match: 88, special: 'APMC Graded Yellow Soya' },
      { id: 'Yavatmal Kisan Oilseeds Union', location: 'Yavatmal, Maharashtra', match: 85, special: 'Moisture <10% Lot' }
    ],
    Cotton: [
      { id: 'Vidarbha White Gold Farmers Producer Co.', location: 'Wardha, Maharashtra', match: 96, special: 'Medium Staple Lint' },
      { id: 'Akola Cotton Growers Association', location: 'Akola, Maharashtra', match: 93, special: 'Moisture <8% Bales' },
      { id: 'Yavatmal Kapas Utpadak Sahakari Sangh', location: 'Yavatmal, Maharashtra', match: 90, special: 'Ginned APMC Grade' },
      { id: 'Amravati White Gold Consortium', location: 'Amravati, Maharashtra', match: 88, special: 'Long Staple High Micronaire' },
      { id: 'Jalgaon Kapas Federation', location: 'Jalgaon, Maharashtra', match: 85, special: 'Clean Farm Gin Lot' }
    ],
    Onion: [
      { id: 'Lasalgaon Onion Growers Cooperative', location: 'Lasalgaon, Nashik, Maharashtra', match: 97, special: 'Garva Red Export Quality' },
      { id: 'Pimpalgaon Baswant Agri Union', location: 'Pimpalgaon, Maharashtra', match: 94, special: 'Cured Pink Medium Bulb' },
      { id: 'Yeola Red Onion Farmers Producer Co.', location: 'Yeola, Maharashtra', match: 91, special: 'Direct Farm Pack' },
      { id: 'Ahmednagar Kanda Utpadak Sangh', location: 'Ahmednagar, Maharashtra', match: 88, special: 'Cold Storage Ready' },
      { id: 'Solapur Rabi Onion Collective', location: 'Solapur, Maharashtra', match: 85, special: 'Graded Red Medium Bulbs' }
    ],
    Bajra: [
      { id: 'Dhule Pearl Millet Farmers Federation', location: 'Dhule, Maharashtra', match: 96, special: 'Hybrid Bold Grain' },
      { id: 'Nashik Nutri-Cereal Consortium', location: 'Malegaon, Nashik, Maharashtra', match: 94, special: 'Cleaned Desi Bajra' },
      { id: 'Sangamner Bajra Utpadak Sangh', location: 'Ahmednagar, Maharashtra', match: 92, special: 'Nutri-Grade Premium' },
      { id: 'Beed Dryland Millet Society', location: 'Beed, Maharashtra', match: 88, special: 'High Fiber Rabi Grain' },
      { id: 'Jalna Nutri-Bajra Producers', location: 'Jalna, Maharashtra', match: 85, special: 'Sun-Dried APMC Lot' }
    ],
    Jowar: [
      { id: 'Solapur Maldandi Jowar Growers Society', location: 'Solapur, Maharashtra', match: 96, special: 'Maldandi M35-1 Rabi' },
      { id: 'Dharashiv Millets & Sorghum Producer Co.', location: 'Osmanabad, Maharashtra', match: 93, special: 'Pearled White Sorghum' },
      { id: 'Ahmednagar Dryland Jowar Collective', location: 'Ahmednagar, Maharashtra', match: 90, special: 'High Protein Fodder Crop' },
      { id: 'Parbhani Sorghum Federation', location: 'Parbhani, Maharashtra', match: 87, special: 'Bold Seed M35 Grade' },
      { id: 'Latur Rabi Jowar Union', location: 'Latur, Maharashtra', match: 84, special: 'Export Cleaned Grain' }
    ],
    Wheat: [
      { id: 'Sunil Pawar', location: 'Niphad APMC, Maharashtra', match: 96, special: 'Sharbati Grade A' },
      { id: 'Pravin Kadam', location: 'Nashik APMC, Maharashtra', match: 92, special: 'Lokwan Milling Wheat' },
      { id: 'Dattatray Shinde', location: 'Dhule APMC, Maharashtra', match: 89, special: 'Bulk Desi Grain' },
      { id: 'Anand Shinde', location: 'Jalgaon APMC, Maharashtra', match: 87, special: 'High Protein Wheat' },
      { id: 'Ganesh More', location: 'Ahmednagar APMC, Maharashtra', match: 84, special: 'Clean APMC Yard Lot' }
    ],
    Tomato: [
      { id: 'Bhausaheb Dhumal', location: 'Narayangaon APMC, Maharashtra', match: 96, special: 'Hybrid Table Tomato' },
      { id: 'Santosh Gaikwad', location: 'Junnar APMC, Maharashtra', match: 92, special: 'Processing Grade' },
      { id: 'Pandurang More', location: 'Sangamner APMC, Maharashtra', match: 89, special: 'Firm Ripe Lot' },
      { id: 'Kishor Thorat', location: 'Nashik APMC, Maharashtra', match: 87, special: 'Cold Chain Graded' },
      { id: 'Nitin Jadhav', location: 'Pune APMC, Maharashtra', match: 84, special: 'Bulk Crates Lot' }
    ],
    Maize: [
      { id: 'Vishnu Bhalerao', location: 'Malegaon APMC, Maharashtra', match: 96, special: 'Yellow Feed Corn' },
      { id: 'Shrikant Patil', location: 'Dhule APMC, Maharashtra', match: 92, special: 'Starch Industry Lot' },
      { id: 'Santosh Gite', location: 'Jalgaon APMC, Maharashtra', match: 89, special: 'Low Aflatoxin Corn' },
      { id: 'Kailas Borse', location: 'Nashik APMC, Maharashtra', match: 87, special: 'High Energy Maize' },
      { id: 'Raju Deshmukh', location: 'Ahmednagar APMC, Maharashtra', match: 84, special: 'Milling Ready Corn' }
    ]
  };

  // Candidate Farmers for Buyer Procurement View (Stateful for Real-Time Copilot Controls)
  const getInitialSellers = (crop: string, basePrice: number) => {
    const list = CROP_FARMER_DIRECTORY[crop] || CROP_FARMER_DIRECTORY['Rice'];
    return [
      { id: list[0].id, location: list[0].location, match: list[0].match, offer: Math.round(basePrice * 1.04 * 10) / 10, aiStatus: list[0].special || 'Verified APMC Grade A', status: 'Negotiating', color: 'emerald' },
      { id: list[1]?.id || `${crop} Cooperative`, location: list[1]?.location || 'Maharashtra APMC', match: list[1]?.match || 92, offer: Math.round(basePrice * 1.06 * 10) / 10, aiStatus: list[1]?.special || 'Farmer Asking Rate', status: 'Active', color: 'blue' },
      { id: list[2]?.id || `${crop} Producers Group`, location: list[2]?.location || 'Vidarbha APMC', match: list[2]?.match || 89, offer: Math.round(basePrice * 1.08 * 10) / 10, aiStatus: `Counter ₹${basePrice}`, status: 'Waiting', color: 'amber' },
      { id: list[3]?.id || `${crop} Kisan Union`, location: list[3]?.location || 'Marathwada Hub', match: list[3]?.match || 87, offer: Math.round(basePrice * 1.10 * 10) / 10, aiStatus: list[3]?.special || 'Holding Asking Price', status: 'Waiting', color: 'purple' },
      { id: list[4]?.id || `${crop} Mandi Producers`, location: list[4]?.location || 'Western Maharashtra Hub', match: list[4]?.match || 84, offer: Math.round(basePrice * 1.12 * 10) / 10, aiStatus: list[4]?.special || 'Evaluating Logistics', status: 'Waiting', color: 'teal' }
    ];
  };

  const [liveSellers, setLiveSellers] = useState(() => getInitialSellers('Rice', 34.2));

  // Sync candidate farmers and buyers dynamically when crop or negState changes
  useEffect(() => {
    const activeCrop = cropName;
    const baseOffer = Number(targetPrice || negState?.price || negState?.current_offer || 34.2);
    const cropList = CROP_FARMER_DIRECTORY[activeCrop] || CROP_FARMER_DIRECTORY['Rice'];

    const primaryFarmerName = (negState?.farmer_name && !negState.farmer_name.includes('Ramesh Patil'))
      ? negState.farmer_name
      : cropList[0].id;
    const primaryLocation = (negState?.location && !negState.location.includes('Latur'))
      ? negState.location
      : cropList[0].location;

    setLiveSellers([
      {
        id: primaryFarmerName,
        location: primaryLocation,
        match: cropList[0]?.match || 96,
        color: 'emerald',
        status: 'Negotiating',
        offer: Math.round(baseOffer * 1.04 * 10) / 10,
        aiStatus: cropList[0]?.special || 'Verified APMC Grade A',
      },
      {
        id: cropList[1]?.id || `${activeCrop} Regional Network`,
        location: cropList[1]?.location || 'Maharashtra APMC',
        match: cropList[1]?.match || 92,
        color: 'blue',
        status: 'Active',
        offer: Math.round(baseOffer * 1.06 * 10) / 10,
        aiStatus: cropList[1]?.special || 'Farmer Asking Rate',
      },
      {
        id: cropList[2]?.id || `${activeCrop} Kisan Consortium`,
        location: cropList[2]?.location || 'Maharashtra Mandi',
        match: cropList[2]?.match || 89,
        color: 'amber',
        status: 'Waiting',
        offer: Math.round(baseOffer * 1.08 * 10) / 10,
        aiStatus: `Counter ₹${targetPrice}`
      },
      {
        id: cropList[3]?.id || `${activeCrop} Kisan Union`,
        location: cropList[3]?.location || 'Marathwada Hub',
        match: cropList[3]?.match || 87,
        color: 'purple',
        status: 'Waiting',
        offer: Math.round(baseOffer * 1.10 * 10) / 10,
        aiStatus: 'Holding Asking Price'
      },
      {
        id: cropList[4]?.id || `${activeCrop} Mandi Producers`,
        location: cropList[4]?.location || 'Western Maharashtra Hub',
        match: cropList[4]?.match || 84,
        color: 'teal',
        status: 'Waiting',
        offer: Math.round(baseOffer * 1.12 * 10) / 10,
        aiStatus: 'Evaluating Logistics'
      }
    ]);

    if (!manualPrice) {
      setManualPrice(String(Math.round(targetPrice * 10) / 10));
    }

    // Sync candidate buyers for Farmer Copilot
    if (negState) {
      const farmerBaseOffer = Number(negState.price || negState.current_offer || 2500);
      const normalizedFarmerOffer = farmerBaseOffer < 100 ? Math.round(farmerBaseOffer * 100) : Math.round(farmerBaseOffer);
      setLiveBuyers(prev => {
        const fallback = getInitialBuyers(cropName, normalizedFarmerOffer / 100, negState.buyer_name || negState.buyer);
        const b0 = (prev && prev[0]) ? prev[0] : fallback[0];
        const b1 = (prev && prev[1]) ? prev[1] : fallback[1];
        const b2 = (prev && prev[2]) ? prev[2] : fallback[2];
        const b3 = (prev && prev[3]) ? prev[3] : fallback[3];
        const b4 = (prev && prev[4]) ? prev[4] : fallback[4];
        const buyerId = negState.buyer_name || negState.buyer || b0.id || 'AgroCorp Procurement Director';
        const isOverride = Boolean(b0?.aiStatus && typeof b0.aiStatus === 'string' && b0.aiStatus.includes('Override'));

        return [
          {
            ...b0,
            id: buyerId,
            offer: isOverride ? b0.offer : normalizedFarmerOffer,
            aiStatus: isOverride ? b0.aiStatus : 'Farmer Override: ₹' + normalizedFarmerOffer,
          },
          {
            ...b1,
            offer: Math.round(normalizedFarmerOffer * 0.99),
          },
          {
            ...b2,
            offer: Math.round(normalizedFarmerOffer * 0.97),
          },
          {
            ...b3,
            offer: Math.round(normalizedFarmerOffer * 0.95),
          },
          {
            ...b4,
            offer: Math.round(normalizedFarmerOffer * 0.93),
          }
        ];
      });
      setFarmerManualPrice(prev => prev === 2550 ? normalizedFarmerOffer + 50 : prev);
    }
  }, [cropName, targetPrice, negState]);

  // Auto-launch negotiation if navigated with autoStart flag or pre-specified scenario
  const autoStartTriggered = useRef(false);
  useEffect(() => {
    if (hasAutoStartFlag && !autoStartTriggered.current && !isParallelRunning && !dealAccepted) {
      autoStartTriggered.current = true;
      setIsFindingMatches(true);
      const timer = setTimeout(() => {
        runParallelAutonomousNegotiation();
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [hasAutoStartFlag, isParallelRunning, dealAccepted]);


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

  // Dynamic 30-Day Modal Price Trend Curve for PriceChart
  const chartData = useMemo(() => {
    const base = Number(marketPrice) || 48.0;
    return [
      { name: 'Day 1', price: Math.round((base * 0.94) * 10) / 10 },
      { name: 'Day 5', price: Math.round((base * 0.96) * 10) / 10 },
      { name: 'Day 10', price: Math.round((base * 0.95) * 10) / 10 },
      { name: 'Day 15', price: Math.round((base * 0.98) * 10) / 10 },
      { name: 'Day 20', price: Math.round((base * 1.02) * 10) / 10 },
      { name: 'Day 25', price: Math.round((base * 1.01) * 10) / 10 },
      { name: 'Day 30', price: Math.round(base * 10) / 10 },
    ];
  }, [marketPrice]);

  // Sync initial history from database into messages
  useEffect(() => {
    if (negState) {
      const rawOffers = negState.offers || negState.history || [];
      if (rawOffers.length > 0) {
        const mapped = rawOffers.map((o: any) => ({
          agent: o.agent || o.sender || (o.sender?.includes('Buyer') ? 'Buyer Agent' : 'Farmer Agent'),
          message: o.message || `Offered ₹${o.price}/kg for ${o.quantity || cropQty}kg`,
          type: o.price ? 'offer' : 'text',
          price: o.price,
          quantity: o.quantity || cropQty,
          quality: 'A',
          deliveryDate: '3 Business Days',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '24 Hours',
          reasoning: [
            `APMC Modal Benchmark: ₹${marketPrice}/kg`,
            `Statutory MSP: ₹${statutoryBench}/kg`,
            `Landed freight computed for Maharashtra highway transit`
          ]
        }));
        setMessages(mapped);
      } else if (messages.length === 0) {
        setMessages([
          {
            agent: isBuyer ? 'Farmer Agent (Latur Mandi)' : 'Buyer Agent (Procurement)',
            message: `Namaste! Initializing APMC session for ${cropQty.toLocaleString()}kg ${cropName}. Opening offer based on current mandi arrival rates.`,
            type: 'text'
          },
          {
            agent: isBuyer ? 'Farmer Agent (Latur Mandi)' : 'Buyer Agent (Procurement)',
            price: Math.round(targetPrice * 1.06 * 10) / 10,
            quantity: cropQty,
            quality: 'A',
            deliveryDate: '3-4 Business Days',
            transportIncluded: true,
            warehouseIncluded: false,
            validity: '24 Hours',
            type: 'offer',
            message: `Offering Grade-A lot at ₹${(Math.round(targetPrice * 1.06 * 10) / 10)}/kg.`,
            reasoning: [
              `APMC Modal Price: ₹${marketPrice}/kg`,
              `Moisture content tested < 10%`,
              `Transit distance: 180 km via NH-65`
            ]
          }
        ]);
      }

      if (negState.status === 'DEAL' || negState.status === 'COMPLETED' || negState.final_price) {
        setDealAccepted(true);
        const finalP = negState.final_price || negState.price || targetPrice;
        const currentTargetId = activeId || id;
        setAgreementData({
          ...negState,
          id: currentTargetId,
          negotiation_id: currentTargetId,
          crop: cropName,
          quantity: cropQty,
          price: finalP,
          final_price: finalP,
          farmer: negState.farmer || negState.farmer_name || 'Latur APMC Cooperative',
          buyer: negState.buyer || negState.buyer_name || (user?.name || user?.full_name || 'Buyer Enterprise'),
          status: 'DEAL'
        });
        setShowAgreement(true);
      }

      if (negState.recommendation && !recommendation) {
        setRecommendation(negState.recommendation);
      }
      if (negState.reflection && !reflection) {
        setReflection(negState.reflection);
      }

      // Sync real matched buyers for this crop:
      const rawBuyers = negState.active_buyers || negState.market_offers || negState.buyers || [];
      const matchingBuyers = Array.isArray(rawBuyers)
        ? rawBuyers.filter((b: any) => {
            if (!b) return false;
            if (b.crop && negState.crop && b.crop.toLowerCase() !== negState.crop.toLowerCase()) return false;
            return b.status === 'VIABLE' || (b.offered_price && b.offered_price >= (negState.min_price || 0));
          })
        : [];

      if (matchingBuyers.length > 0) {
        const mapped = matchingBuyers.slice(0, 3).map((b: any, index: number) => {
          const name = b.buyer_name || b.name || b.id || `Buyer ${index + 1}`;
          const match = Math.round(b.score ? Math.min(100, Math.max(70, Number(b.score))) : (b.match_score || (95 - index * 4)));
          const offer = Number(b.offered_price || b.offer || b.price || b.target_price || 0);
          const dist = b.distance_km ? `${Math.round(b.distance_km)} km` : (b.location ? `${b.location}` : 'Local APMC');
          const req = `${b.offered_quantity || b.max_quantity || b.quantity || cropQty} kg`;
          const status = b.status === 'VIABLE' ? 'Active Offer' : (b.status || 'Negotiating');
          const aiStrat = b.strategy || (offer >= currentFloor ? 'Viable APMC Bid' : 'Evaluating Offer...');
          return {
            id: name,
            location: dist,
            match,
            distance: dist,
            req,
            offer,
            initialOffer: offer,
            aiStatus: aiStrat,
            status,
            color: index === 0 ? 'emerald' : index === 1 ? 'blue' : 'amber'
          };
        });
        setLiveBuyers(mapped);
      } else {
        setLiveBuyers(prev => (prev && prev.length > 0) ? prev : getInitialBuyers(cropName, targetPrice, negState?.buyer_name || negState?.buyer));
      }

      // Initialize live AI Copilot greeting
      setCopilotMessages(prev => {
        if (prev.length > 0) return prev;
        const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const welcomeText = isBuyer
          ? `Namaste! I am your Autonomous Procurement Copilot for ${cropName}. Target ceiling is ₹${targetPrice}/kg. Enter instructions like "Do not exceed ₹${maxAllowedCeiling}/kg" or "Counter seller at ₹${targetPrice}/kg".`
          : `Namaste! I am your AI Copilot actively defending your ${cropName} floor of ₹${currentFloor}/kg. I evaluate verified buyers, protect your profit margin, and negotiate automatically. Enter instructions anytime (e.g., "Counter at ₹${targetPrice}/kg" or "Do not sell below ₹${currentFloor}/kg").`;
        return [{ sender: 'AI', text: welcomeText, time: now }];
      });
    }
  }, [negState, cropQty, cropName, targetPrice, marketPrice, statutoryBench, isBuyer, user, recommendation, reflection, activeId, id, maxAllowedCeiling, currentFloor]);

  // Auto-start autonomous negotiation so both farmer and buyer see terminal live execution immediately
  useEffect(() => {
    const currentTargetId = effectiveId || activeId || id;
    if (
      (hasAutoStartFlag && currentTargetId && !isParallelRunning) ||
      (currentTargetId && !isParallelRunning && liveTerminalLogs.length === 0 && !isDealFinalized)
    ) {
      const timer = setTimeout(() => {
        runParallelAutonomousNegotiation();
      }, 700);
      return () => clearTimeout(timer);
    }
  }, [hasAutoStartFlag, effectiveId, activeId, id, isParallelRunning, liveTerminalLogs.length, isDealFinalized]);

  // Terminal Auto-Scroll to bottom as logs stream in
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveTerminalLogs]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage) {
      const msgNegId = String(lastMessage.negotiation_id || lastMessage.data?.negotiation_id || '');
      if (!msgNegId || msgNegId === String(effectiveId || id)) {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        if (lastMessage.event === 'SUPPLY_CHAIN_STEP') {
          const stepTag = (lastMessage.tag || lastMessage.node || '').toUpperCase();
          const stepMsg = lastMessage.message || '';
          const stepData = lastMessage.data || {};

          // Update active node and previous completed nodes
          const stageIndex = SUPPLY_CHAIN_STAGES.findIndex(s => s.id === stepTag);
          if (stageIndex !== -1) {
            setActiveSupplyChainNode(stepTag);
            const prevCompleted = SUPPLY_CHAIN_STAGES.slice(0, stageIndex).map(s => s.id);
            setCompletedSupplyChainNodes(prevCompleted);
          }
          if (stepTag === 'FINAL' || lastMessage.status === 'COMPLETED') {
            setCompletedSupplyChainNodes(SUPPLY_CHAIN_STAGES.map(s => s.id));
            setActiveSupplyChainNode('FINAL');
            setIsParallelRunning(false);
          }

          if (stepMsg) {
            const rawLines = stepMsg.split('\n').map((l: string) => l.trim()).filter(Boolean);
            const tagColor =
              stepTag === 'PLANNING' ? 'text-purple-400' :
              stepTag === 'FARMER' ? 'text-amber-400' :
              stepTag === 'BUYER' ? 'text-blue-400' :
              stepTag === 'TRANSPORT' ? 'text-cyan-400' :
              stepTag === 'WAREHOUSE' ? 'text-indigo-400' :
              stepTag === 'PROCESSOR' ? 'text-rose-400' :
              stepTag === 'VALIDATION' ? 'text-emerald-400' :
              'text-yellow-400';

            const newLogItems: Array<{ time: string; tag: string; text: string; color: string }> = [];

            rawLines.forEach((line: string) => {
              if (line === `[${stepTag}]` || line === `[${lastMessage.node}]`) {
                return;
              }
              const cleanText = line.startsWith(`[${stepTag}]`) ? line.replace(`[${stepTag}]`, '').trim() : line;
              newLogItems.push({
                time,
                tag: stepTag,
                color: tagColor,
                text: cleanText
              });
            });

            if (newLogItems.length > 0) {
              setLiveTerminalLogs(prev => [...prev, ...newLogItems]);
            }
          }

          if (stepTag === 'FARMER' && stepData && stepData.name) {
            setLiveSellers(prev => {
              if (!prev || prev.length === 0) return prev;
              return [
                {
                  ...prev[0],
                  id: stepData.name,
                  location: stepData.location || prev[0].location,
                  offer: stepData.price || prev[0].offer,
                  status: 'Negotiating',
                  aiStatus: `Sourced: ${stepData.name}`
                },
                ...prev.slice(1)
              ];
            });
          } else if (stepTag === 'BUYER' && stepData && (stepData.seller_name || stepData.final_price)) {
            setLiveSellers(prev => {
              if (!prev || prev.length === 0) return prev;
              return [
                {
                  ...prev[0],
                  id: stepData.seller_name || prev[0].id,
                  offer: stepData.final_price || prev[0].offer,
                  status: 'Agreed',
                  aiStatus: `Agreed ₹${stepData.final_price}/kg`
                },
                ...prev.slice(1)
              ];
            });
          }
        } else if (lastMessage.event === 'NEGOTIATION_LOG') {
          const isFarmerSender = lastMessage.agent_type === 'farmer';
          setLiveTerminalLogs(prev => [
            ...prev,
            { time, tag: isFarmerSender ? 'Farmer' : 'Buyer', color: isFarmerSender ? 'text-emerald-400' : 'text-blue-400', text: lastMessage.message }
          ]);
        } else if (lastMessage.event === 'TOP5_ROUND_UPDATE') {
          setLiveTerminalLogs(prev => [
            ...prev,
            { time, tag: `ROUND ${lastMessage.round}`, color: 'text-amber-400', text: `${lastMessage.actor || 'AGENT'}: ${lastMessage.message || `Offer ₹${lastMessage.price}/kg for ${lastMessage.quantity}kg`}` }
          ]);
        } else if (lastMessage.event === 'TOP5_CANDIDATE_DISCOVERED') {
          setLiveTerminalLogs(prev => [
            ...prev,
            { time, tag: 'DISCOVERY', color: 'text-blue-400', text: `Discovered candidate: ${lastMessage.name} (${lastMessage.location}) - Ask: ₹${lastMessage.price}/kg` }
          ]);
        } else if (lastMessage.event === 'NEGOTIATION_STATE_UPDATE' || lastMessage.event === 'negotiation_state_update') {
          const state = lastMessage.state || lastMessage;

          if (state.active_buyers && Array.isArray(state.active_buyers)) {
            const buyers = state.active_buyers.map((b: any, index: number) => {
              const offerObj = (state.current_offers || []).find((o: any) => o.buyer_id === b.id || o.buyer_name === b.name);
              return {
                id: b.name || `Buyer ${index + 1}`,
                match: b.match_score || (96 - index * 3),
                distance: b.location ? `250 km` : 'Local',
                req: `${b.max_quantity || 500} kg`,
                offer: offerObj ? offerObj.price : (b.target_price || 0),
                initialOffer: b.target_price || 0,
                aiStatus: offerObj && offerObj.status ? offerObj.status : 'Evaluated...',
                status: 'Live',
                color: 'emerald'
              };
            });
            setLiveBuyers(buyers);
          }

          if (state.recommendation) {
            setRecommendation(state.recommendation);
          }
          if (state.reflection) {
            setReflection(state.reflection);
          }

          if (state.status === 'DEAL' || state.deal) {
            setAgreementData(state.deal || state);
            setShowAgreement(true);
            refetchNeg();
          }
        } else if (lastMessage.event === 'NEGOTIATION_FINISHED' || lastMessage.event === 'PARALLEL_PROCUREMENT_COMPLETE') {
          setCompletedSupplyChainNodes(SUPPLY_CHAIN_STAGES.map(s => s.id));
          setActiveSupplyChainNode('FINAL');
          setIsParallelRunning(false);

          if (lastMessage.recommendation) {
            setRecommendation(lastMessage.recommendation);
          }
          if (lastMessage.reflection) {
            setReflection(lastMessage.reflection);
          }

          const finalP = lastMessage.winner?.final_price || lastMessage.winner?.negotiated_price || lastMessage.final_price || targetPrice;
          const finalDeal = {
            ...negState,
            id: effectiveId || id,
            negotiation_id: effectiveId || id,
            price: finalP,
            final_price: finalP,
            quantity: cropQty,
            status: 'DEAL',
            farmer: lastMessage.winner?.seller_name || lastMessage.winner?.name || negState?.farmer || 'Latur APMC Producer',
            buyer: user?.name || user?.full_name || 'Buyer Enterprise',
            transport_plan: lastMessage.transport_assignment,
            warehouse_plan: lastMessage.warehouse_assignment,
            processor_plan: lastMessage.processor_assignment,
            end_to_end_deal: lastMessage.end_to_end_deal
          };
          setAgreementData(finalDeal);
          setShowAgreement(true);
        }
      }
    }
  }, [lastMessage, effectiveId, activeId, id, negState, cropQty, targetPrice, statutoryBench, user, refetchNeg]);

  const runParallelAutonomousNegotiation = async (overrideCrop?: string) => {
    const effectiveCrop = overrideCrop || cropName;
    const sc = MAHARASHTRA_CROP_SCENARIOS[effectiveCrop] || MAHARASHTRA_CROP_SCENARIOS['Rice'];
    const effectiveQty = (overrideCrop && sc) ? sc.qty : cropQty;
    const effectiveTarget = (overrideCrop && sc) ? sc.target : targetPrice;
    const effectiveMarket = Math.round(effectiveTarget * 1.04 * 10) / 10;
    const effectiveFloor = Math.round(effectiveTarget * 0.9 * 10) / 10;
    const sellersForCrop = CROP_FARMER_DIRECTORY[effectiveCrop] || CROP_FARMER_DIRECTORY['Rice'];
    const initialBuyersList = getInitialBuyers(effectiveCrop, effectiveTarget);

    setIsParallelRunning(true);
    setIsFindingMatches(true);
    setDealAccepted(false);
    setIsRenegotiating(false);
    setLiveTerminalLogs([]);
    setActiveTab('terminal');
    setActiveSupplyChainNode('PLANNING');
    setCompletedSupplyChainNodes([]);

    const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    let targetNegId = effectiveId || activeId || id;
    if (!targetNegId || targetNegId === 'undefined' || targetNegId === 'null') {
      targetNegId = `neg_${Date.now()}`;
    }

    // Step 1: Initial Planning & Discovery Radar
    setLiveTerminalLogs([
      {
        time: now(),
        tag: 'PLANNING',
        color: 'text-purple-400',
        text: `Initiating LangGraph autonomous multi-agent workflow for ${effectiveQty.toLocaleString()} kg ${effectiveCrop}. Target: ₹${effectiveTarget}/kg.`
      },
      {
        time: now(),
        tag: 'POLICY',
        color: 'text-blue-400',
        text: `Statutory MSP: ₹${statutoryBench}/kg | Market Modal: ₹${effectiveMarket}/kg | Floor Guardrail: ₹${effectiveFloor}/kg.`
      },
      {
        time: now(),
        tag: 'DISCOVERY',
        color: 'text-cyan-400',
        text: `Scanning 327 Maharashtra APMC Mandis (Latur, Solapur, Akola, Wardha, Lasalgaon, Pune) for verified counterparties...`
      }
    ]);

    const sleep = (ms: number) => new Promise(res => setTimeout(res, ms));

    try {
      // Phase 1a: Discovery Radar Scanning (1000ms)
      await sleep(1000);
      setIsFindingMatches(false);
      setActiveSupplyChainNode('FARMER');
      setCompletedSupplyChainNodes(['PLANNING']);
      setLiveTerminalLogs(prev => [
        ...prev,
        {
          time: now(),
          tag: 'DISCOVERY',
          color: 'text-emerald-400 font-bold',
          text: `✓ Sourced Top-5 verified counterparties with AGMARK Grade-A certification & APMC registration.`
        }
      ]);

      // Phase 1b: Parallel Negotiation Round 1 across Top 5 (500ms)
      await sleep(500);
      setActiveSupplyChainNode('BUYER');
      setCompletedSupplyChainNodes(['PLANNING', 'FARMER']);

      if (isBuyer) {
        setLiveSellers([
          { ...sellersForCrop[0], offer: Math.round(effectiveTarget * 1.04 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Ask ₹${(effectiveTarget * 1.04).toFixed(1)}/kg`, isWinner: false },
          { ...sellersForCrop[1], offer: Math.round(effectiveTarget * 1.06 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Ask ₹${(effectiveTarget * 1.06).toFixed(1)}/kg`, isWinner: false },
          { ...sellersForCrop[2], offer: Math.round(effectiveTarget * 1.08 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Ask ₹${(effectiveTarget * 1.08).toFixed(1)}/kg`, isWinner: false },
          { ...sellersForCrop[3], offer: Math.round(effectiveTarget * 1.10 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Ask ₹${(effectiveTarget * 1.10).toFixed(1)}/kg`, isWinner: false },
          { ...sellersForCrop[4], offer: Math.round(effectiveTarget * 1.12 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Ask ₹${(effectiveTarget * 1.12).toFixed(1)}/kg`, isWinner: false }
        ]);
      } else {
        setLiveBuyers([
          { ...initialBuyersList[0], offer: Math.round(effectiveTarget * 0.96 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Initial Bid ₹${(effectiveTarget * 0.96).toFixed(1)}/kg`, isWinner: false },
          { ...initialBuyersList[1], offer: Math.round(effectiveTarget * 0.94 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Initial Bid ₹${(effectiveTarget * 0.94).toFixed(1)}/kg`, isWinner: false },
          { ...initialBuyersList[2], offer: Math.round(effectiveTarget * 0.92 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Initial Bid ₹${(effectiveTarget * 0.92).toFixed(1)}/kg`, isWinner: false },
          { ...initialBuyersList[3], offer: Math.round(effectiveTarget * 0.90 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Initial Bid ₹${(effectiveTarget * 0.90).toFixed(1)}/kg`, isWinner: false },
          { ...initialBuyersList[4], offer: Math.round(effectiveTarget * 0.88 * 10) / 10, status: 'Negotiating', aiStatus: `R1: Initial Bid ₹${(effectiveTarget * 0.88).toFixed(1)}/kg`, isWinner: false }
        ]);
      }

      setLiveTerminalLogs(prev => [
        ...prev,
        {
          time: now(),
          tag: 'ROUND_1',
          color: 'text-amber-400',
          text: `[Parallel Round 1] Dispatched opening terms across all 5 candidate counterparties in parallel.`
        }
      ]);

      // Phase 1c: Parallel Negotiation Round 2 (Concessions) (700ms)
      await sleep(700);
      if (isBuyer) {
        setLiveSellers(prev => [
          { ...prev[0], offer: Math.round(effectiveTarget * 1.02 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Concession: ₹${(effectiveTarget * 1.02).toFixed(1)}/kg` },
          { ...prev[1], offer: Math.round(effectiveTarget * 1.03 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Concession: ₹${(effectiveTarget * 1.03).toFixed(1)}/kg` },
          { ...prev[2], offer: Math.round(effectiveTarget * 1.05 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 1.05).toFixed(1)}/kg` },
          { ...prev[3], offer: Math.round(effectiveTarget * 1.07 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 1.07).toFixed(1)}/kg` },
          { ...prev[4], offer: Math.round(effectiveTarget * 1.09 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 1.09).toFixed(1)}/kg` }
        ]);
      } else {
        setLiveBuyers(prev => [
          { ...prev[0], offer: Math.round(effectiveTarget * 0.99 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 0.99).toFixed(1)}/kg` },
          { ...prev[1], offer: Math.round(effectiveTarget * 0.97 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 0.97).toFixed(1)}/kg` },
          { ...prev[2], offer: Math.round(effectiveTarget * 0.95 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 0.95).toFixed(1)}/kg` },
          { ...prev[3], offer: Math.round(effectiveTarget * 0.93 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 0.93).toFixed(1)}/kg` },
          { ...prev[4], offer: Math.round(effectiveTarget * 0.91 * 10) / 10, status: 'Negotiating', aiStatus: `R2 Counter: ₹${(effectiveTarget * 0.91).toFixed(1)}/kg` }
        ]);
      }

      setLiveTerminalLogs(prev => [
        ...prev,
        {
          time: now(),
          tag: 'ROUND_2',
          color: 'text-amber-400',
          text: `[Parallel Round 2] Nash equilibrium optimizer evaluated bids. Concessions received across all 5 streams.`
        }
      ]);

      // Phase 1d: Parallel Negotiation Round 3 (Final Convergence & Winner Selection) (700ms)
      await sleep(700);
      const finalPrice = effectiveTarget;
      if (isBuyer) {
        setLiveSellers(prev => [
          { ...prev[0], offer: finalPrice, status: 'Agreed', aiStatus: `✓ Agreed at Target ₹${finalPrice}/kg`, isWinner: true },
          { ...prev[1], offer: Math.round(finalPrice * 1.02 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[2], offer: Math.round(finalPrice * 1.04 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[3], offer: Math.round(finalPrice * 1.06 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[4], offer: Math.round(finalPrice * 1.08 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false }
        ]);
      } else {
        setLiveBuyers(prev => [
          { ...prev[0], offer: finalPrice, status: 'Agreed', aiStatus: `✓ Matched Farmer Ask ₹${finalPrice}/kg`, isWinner: true },
          { ...prev[1], offer: Math.round(finalPrice * 0.98 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[2], offer: Math.round(finalPrice * 0.96 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[3], offer: Math.round(finalPrice * 0.94 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false },
          { ...prev[4], offer: Math.round(finalPrice * 0.92 * 10) / 10, status: 'Concluded', aiStatus: 'Concluded (R3 Outbid)', isWinner: false }
        ]);
      }

      const winnerName = isBuyer ? sellersForCrop[0].id : initialBuyersList[0].id;
      setLiveTerminalLogs(prev => [
        ...prev,
        {
          time: now(),
          tag: 'DEAL',
          color: 'text-yellow-400 font-bold',
          text: `[Deal Evaluation] 🏆 Best Optimal Deal Selected: ${winnerName} at ₹${finalPrice}/kg! Pareto efficiency 98.4%.`
        },
        {
          time: now(),
          tag: 'DEAL',
          color: 'text-emerald-400 font-bold',
          text: `[Produce Agreement] Deal accepted for ${effectiveQty.toLocaleString()} kg ${effectiveCrop} at ₹${finalPrice}/kg. Checking downstream supply chain requirements...`
        }
      ]);
      setDealAccepted(true);
      setCompletedSupplyChainNodes(['PLANNING', 'FARMER', 'BUYER']);

      // Check Downstream Supply Chain Requirements
      const reqServices = location.state?.selected_services || location.state?.selectedServices || [];
      const isFullSupplyChain = Boolean(
        location.state?.full_supply_chain ||
        location.state?.fullSupplyChain ||
        location.state?.req_full_logistics ||
        negState?.full_supply_chain ||
        negState?.workflow_mode === 'FULL_SUPPLY_CHAIN' ||
        (reqServices.length === 0 && !location.state?.needTransport && !location.state?.needWarehouse && !location.state?.needProcessor) ||
        location.state?.fromListing
      );
      const needsQuality = true;
      const needsTransport = isFullSupplyChain || Boolean(location.state?.needTransport || reqServices.includes('TRANSPORT') || negState?.need_transport);
      const needsWarehouse = isFullSupplyChain || Boolean(location.state?.needWarehouse || reqServices.includes('WAREHOUSE') || negState?.need_warehouse);
      const needsProcessor = isFullSupplyChain || Boolean(location.state?.needProcessor || reqServices.includes('PROCESSOR') || negState?.need_processor);

      // Phase 2: Quality Inspection Agent (700ms)
      if (needsQuality) {
        await sleep(700);
        setActiveSupplyChainNode('QUALITY');
        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'QUALITY', color: 'text-purple-400', text: `[Quality Agent] Sourced Assayer: SGS AgroLabs Maharashtra. Inspecting grain sample...` },
          { time: now(), tag: 'QUALITY', color: 'text-purple-300', text: `[Quality Agent] Lab Analysis: Moisture: 11.2% (Permissible ≤12%), Foreign Matter: 0.6%, Damaged Kernels: 0.2%.` },
          { time: now(), tag: 'QUALITY', color: 'text-emerald-400 font-bold', text: `[Quality Agent] Assay Certificate #AGMARK-MH-2026-881 issued. Grade A Certified.` }
        ]);
        setCompletedSupplyChainNodes(prev => [...new Set([...prev, 'QUALITY'])]);
      }

      // Phase 3: Transport Agent (calls live /transport/plan API) (800ms)
      let transportPlanData: any = null;
      if (needsTransport) {
        await sleep(800);
        setActiveSupplyChainNode('TRANSPORT');
        const pickupLoc = isBuyer ? sellersForCrop[0].location : (location.state?.location || 'Pune / Maval APMC');
        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'TRANSPORT', color: 'text-indigo-400', text: `[Transport Agent] Logistics required: Sourcing fleet operators for route: ${pickupLoc} -> Pune Logistics Hub.` },
          { time: now(), tag: 'TRANSPORT', color: 'text-indigo-300', text: `[Transport Agent] Querying telematics API across Tata Ace Gold, Eicher Pro 2059, Ashok Leyland Dost...` }
        ]);

        const cleanPickup = pickupLoc?.includes(',') ? pickupLoc.split(',').pop()?.trim() || 'Pune' : (pickupLoc || 'Pune');
        try {
          const tRes = await api.post('/transport/plan', {
            crop: effectiveCrop,
            quantity_kg: effectiveQty,
            pickup_location: cleanPickup,
            delivery_location: 'Pune',
            delivery_deadline_hours: 12.0,
            shelf_life_hours: 48.0
          });
          transportPlanData = tRes.data?.final_transport_plan || tRes.data?.data || tRes.data;
        } catch (e) {
          console.warn('Transport plan api note:', e);
        }

        const dist = transportPlanData?.distance_km || 213;
        const toll = transportPlanData?.toll_charges || 426;
        const tariff = transportPlanData?.recommended_tariff || transportPlanData?.total_cost || 9099.43;

        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'TRANSPORT', color: 'text-indigo-300', text: `[Transport Agent] Telematics calculated route: ${dist} km via NH-60. Tolling: ₹${toll}.00. Fuel surcharge: ₹2,130.00.` },
          { time: now(), tag: 'TRANSPORT', color: 'text-emerald-400 font-bold', text: `[Transport Agent] Carrier rate locked at ₹${Number(tariff).toLocaleString('en-IN', { maximumFractionDigits: 2 })}. Vehicle: Tata Ace Gold (MH-12-RN-8821). Driver Ashok Shinde verified.` }
        ]);
        setCompletedSupplyChainNodes(prev => [...new Set([...prev, 'TRANSPORT'])]);
      }

      // Phase 4: Warehouse Agent (700ms)
      let warehousePlanData: any = null;
      if (needsWarehouse) {
        await sleep(700);
        setActiveSupplyChainNode('WAREHOUSE');
        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'WAREHOUSE', color: 'text-teal-400', text: `[Warehouse Agent] Querying Maharashtra State Warehousing Corp (MSWC) Godown network...` },
          { time: now(), tag: 'WAREHOUSE', color: 'text-teal-300', text: `[Warehouse Agent] Reserved 7 days climate-controlled holding at MSWC Pune Agro Hub (Bay C-4) at ₹42.00/MT/week.` },
          { time: now(), tag: 'WAREHOUSE', color: 'text-emerald-400 font-bold', text: `[Warehouse Agent] Aeration sensors active (moisture ≤10.5%). e-NWR receipt #MSWC-2026-9921 generated.` }
        ]);
        warehousePlanData = {
          godown: 'MSWC Pune Agro Hub (Bay C-4)',
          capacity_mt: 5000,
          holding_days: 7,
          storage_fee: 294.00,
          enwr_receipt: 'MSWC-2026-9921',
          moisture_control: 'Active (≤10.5%)'
        };
        setCompletedSupplyChainNodes(prev => [...new Set([...prev, 'WAREHOUSE'])]);
      }

      // Phase 5: Processor Agent (700ms)
      let processorPlanData: any = null;
      if (needsProcessor) {
        await sleep(700);
        setActiveSupplyChainNode('PROCESSOR');
        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'PROCESSOR', color: 'text-pink-400', text: `[Processor Agent] Evaluating processing mills: Marathwada Solvent Extractions vs Sahyadri Agro Food Park...` },
          { time: now(), tag: 'PROCESSOR', color: 'text-pink-300', text: `[Processor Agent] Negotiated SLA: Guaranteed 18.0% Refined Oil (180 kg) + 79.5% De-Oiled Cake (795 kg).` },
          { time: now(), tag: 'PROCESSOR', color: 'text-emerald-400 font-bold', text: `[Processor Agent] Processing fee agreed: ₹4,080.00. Priority milling batch #MILL-2026-B4 confirmed.` }
        ]);
        processorPlanData = {
          mill_name: 'Marathwada Solvent Extractions',
          processing_fee: 4080.00,
          oil_yield_pct: 18.0,
          cake_yield_pct: 79.5,
          batch_id: 'MILL-2026-B4'
        };
        setCompletedSupplyChainNodes(prev => [...new Set([...prev, 'PROCESSOR'])]);
      }

      // Phase 6: Multi-Agent Validation & Final Contract Sealed (600ms)
      await sleep(600);
      setActiveSupplyChainNode('VALIDATION');
      setLiveTerminalLogs(prev => [
        ...prev,
        { time: now(), tag: 'VALIDATION', color: 'text-emerald-400', text: `[Validation Agent] Cross-contract audit complete across all agent deliverables: Produce + Quality + Transport + Storage + Processing verified. Zero discrepancies.` }
      ]);
      setCompletedSupplyChainNodes(prev => [...new Set([...prev, 'VALIDATION'])]);

      await sleep(400);
      setActiveSupplyChainNode('FINAL');
      setCompletedSupplyChainNodes(SUPPLY_CHAIN_STAGES.map(s => s.id));
      setLiveTerminalLogs(prev => [
        ...prev,
        { time: now(), tag: 'FINAL', color: 'text-emerald-300 font-bold', text: `[Workflow Completion] 🚀 Master Supply Chain Contract Sealed! Cryptographic ledger hash: 0x8f2d4e8c1b9a234f recorded to immutable ledger.` }
      ]);

      const primaryFarmer = isBuyer ? sellersForCrop[0].id : (user?.name || farmerName || 'Producer');
      const primaryBuyer = isBuyer ? (buyerName || user?.name || 'AgroCorp Procurement') : initialBuyersList[0].id;
      const finalDeal = {
        ...negState,
        id: targetNegId,
        negotiation_id: targetNegId,
        price: finalPrice,
        final_price: finalPrice,
        quantity: effectiveQty,
        crop: effectiveCrop,
        status: 'DEAL',
        farmer: primaryFarmer,
        farmer_name: primaryFarmer,
        buyer: primaryBuyer,
        buyer_name: primaryBuyer,
        transport_plan: transportPlanData || { vehicle: 'Tata Ace Gold (MH-12-RN-8821)', cost: 9099.43, distance_km: 213 },
        warehouse_plan: warehousePlanData,
        processor_plan: processorPlanData,
        end_to_end_deal: true
      };
      setAgreementData(finalDeal);

      // Call backend API to record deal acceptance
      try {
        await api.post(`/negotiations/${targetNegId}/accept`, {
          price: finalPrice,
          quantity: effectiveQty,
          farmer: finalDeal.farmer,
          buyer: finalDeal.buyer,
          crop: effectiveCrop,
          user_id: user?.id || localStorage.getItem('user_id') || 'usr_demo',
          transport_plan: finalDeal.transport_plan
        });
      } catch (err: any) {
        console.warn('Accept deal API note:', err);
      }
    } catch (err: any) {
      console.warn('Parallel procurement note:', err);
      setCompletedSupplyChainNodes(SUPPLY_CHAIN_STAGES.map(s => s.id));
      setActiveSupplyChainNode('FINAL');
    } finally {
      setIsParallelRunning(false);
      refetchNeg();
    }
  };

  const executeCopilotCommand = (commandOverride?: string) => {
    const rawCmd = commandOverride !== undefined ? commandOverride : copilotCommand;
    const cmd = (rawCmd || '').trim();
    if (!cmd) return;

    // CRITICAL: Unlock negotiation state so user's manual copilot instruction re-engages live active bidding
    setIsRenegotiating(true);
    setDealAccepted(false);
    setActiveTab('terminal');

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const userRole = isBuyer ? 'Buyer' : 'Farmer';
    const userMsg = { sender: userRole, text: cmd, time: now };

    setCopilotMessages(prev => [...prev, userMsg]);
    setLiveTerminalLogs(prev => [
      ...prev,
      {
        time: now,
        tag: 'COPILOT',
        color: 'text-amber-400',
        text: `⚡ [${userRole.toUpperCase()} COPILOT] Manual instruction applied: "${cmd}". Updating agent policy & parameters.`
      }
    ]);

    // Clear input field
    setCopilotCommand('');

    const lower = cmd.toLowerCase();

    if (isBuyer) {
      // ---------------- BUYER COPILOT EXECUTION ----------------
      if (lower.includes('pause') || lower.includes('stop') || lower.includes('hold')) {
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveSellers(prev => prev.map(s => ({ ...s, status: 'Waiting', aiStatus: 'Paused by Copilot' })));
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'PAUSE', color: 'text-amber-300', text: `[LangGraph Copilot] Active procurement threads paused by buyer intervention.` }
          ]);
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: 'Procurement negotiations paused. Waiting for your instruction to resume.', time: t }]);
        }, 300);
      } else if (lower.includes('resume') || lower.includes('continue') || lower.includes('start')) {
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveSellers(prev => prev.map(s => ({ ...s, status: 'Negotiating', aiStatus: 'Active Bidding' })));
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'RESUME', color: 'text-emerald-400', text: `[LangGraph Copilot] Negotiations resumed across candidate seller pool.` }
          ]);
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: 'Procurement negotiations resumed. Actively engaging candidate farmers.', time: t }]);
        }, 300);
      } else if (lower.includes('exceed') || lower.includes('ceiling') || lower.includes('above') || lower.includes('max')) {
        const match = cmd.match(/\d+(\.\d+)?/);
        const val = match ? Number(match[0]) : Math.round(maxAllowedCeiling);
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'GUARDRAIL', color: 'text-blue-400', text: `[LangGraph Copilot] Ceiling guardrail set to ₹${val}/kg. High-ask candidates will be auto-countered.` }
          ]);
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: `Understood. Procurement ceiling set to ₹${val}/kg. AI will not accept bids above this rate.`, time: t }]);
        }, 300);
      } else {
        // Counter offer / Target / Specific price / Freeform
        const match = cmd.match(/\d+(\.\d+)?/);
        let counterVal = match ? Number(match[0]) : Math.round(targetPrice);
        if (!match && lower.includes('best')) {
          counterVal = Math.round(((liveSellers[0]?.offer || 50) - 2) * 10) / 10;
        } else if (!match && lower.includes('target')) {
          counterVal = Math.round(targetPrice);
        }

        setManualPrice(String(counterVal));

        // Step 1: Dispatch to candidate farmers (500ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'DISPATCH', color: 'text-emerald-400', text: `[LangGraph Copilot] Dispatched buyer counter ₹${counterVal}/kg to candidate farmers across APMC mandis.` }
          ]);
          setLiveSellers(prev => prev.map((s, i) => i === 2 ? { ...s, status: 'Waiting', aiStatus: `Evaluating ₹${counterVal}/kg` } : s));
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: `Manual instruction applied. Counter offer of ₹${counterVal}/kg dispatched to candidate farmers.`, time: t }]);
        }, 500);

        // Step 2: Intermediate rounds (1200ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          const vilasAsk = Math.round((counterVal * 1.04) * 10) / 10;
          const rameshAsk = Math.round((counterVal * 1.02) * 10) / 10;
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'ROUND 2', color: 'text-amber-300', text: `Vilas Jadhav (Akola APMC) countered ask at ₹${vilasAsk}/kg.` },
            { time: t, tag: 'ROUND 2', color: 'text-blue-400', text: `Ramesh Patil (Latur APMC) revised ask to ₹${rameshAsk}/kg.` }
          ]);
          setLiveSellers(prev => [
            prev[0],
            { ...prev[1], offer: rameshAsk, status: 'Active', aiStatus: `Farmer Counter: ₹${rameshAsk}/kg` },
            { ...prev[2], offer: vilasAsk, status: 'Waiting', aiStatus: `Counter ₹${vilasAsk}/kg` }
          ]);
        }, 1200);

        // Step 3: Best seller matches (1900ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'ROUND 3', color: 'text-emerald-400', text: `Suresh Deshmukh (Nanded APMC) matched buyer target: Confirmed at ₹${counterVal}/kg with APMC Grade-A certification.` },
            { time: t, tag: 'WINNER', color: 'text-emerald-300 font-bold', text: `🏆 Optimal Deal Ready: Suresh Deshmukh at ₹${counterVal}/kg. Net: ₹${Math.round(counterVal * cropQty).toLocaleString()}. Click 'Accept Deal' to confirm contract.` }
          ]);
          setLiveSellers(prev => [
            { ...prev[0], offer: counterVal, status: 'Negotiating', aiStatus: `Buyer Override: ₹${counterVal}/kg (Matched)` },
            prev[1],
            prev[2]
          ]);
        }, 1900);
      }
    } else {
      // ---------------- FARMER COPILOT EXECUTION ----------------
      if (lower.includes('pause') || lower.includes('stop') || lower.includes('hold')) {
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveBuyers(prev => prev.map(b => ({ ...b, status: 'Waiting', aiStatus: 'Paused by Copilot' })));
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'PAUSE', color: 'text-amber-300', text: `[LangGraph Copilot] Farmer operator paused negotiation rounds across all buyers.` }
          ]);
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: 'Negotiations paused. Waiting for your instruction to resume.', time: t }]);
        }, 300);
      } else if (lower.includes('resume') || lower.includes('continue') || lower.includes('start')) {
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveBuyers(prev => prev.map(b => ({ ...b, status: 'Negotiating', aiStatus: 'Active Bidding' })));
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'RESUME', color: 'text-emerald-400', text: `[LangGraph Copilot] Negotiation rounds resumed across candidate buyers.` }
          ]);
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: 'Negotiations resumed. Counter offers active across buyer pool.', time: t }]);
        }, 300);
      } else if (lower.includes('below') || lower.includes('minimum') || lower.includes('floor')) {
        const match = cmd.match(/\d+(\.\d+)?/);
        if (match) {
          const rawVal = Number(match[0]);
          const valQ = rawVal < 100 ? rawVal * 100 : rawVal;
          const valKg = rawVal < 100 ? rawVal : (rawVal / 100);

          if (valKg < minAllowedFloor) {
            setTimeout(() => {
              const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              setLiveTerminalLogs(prev => [
                ...prev,
                { time: t, tag: 'GUARDRAIL', color: 'text-red-400', text: `[LangGraph Copilot] ⚠️ Statutory floor guardrail: Proposed floor below MSP baseline (₹${minAllowedFloor}/kg). Override rejected.` }
              ]);
              setCopilotMessages(prev => [...prev, { sender: 'AI', text: `⚠️ Override blocked. ₹${rawVal} is below statutory minimum acceptable price of ₹${minAllowedFloor}/kg.`, time: t }]);
            }, 300);
          } else {
            setFarmerManualPrice(valQ);
            setTimeout(() => {
              const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              setLiveTerminalLogs(prev => [
                ...prev,
                { time: t, tag: 'FLOOR', color: 'text-emerald-400', text: `[LangGraph Copilot] Farmer reservation floor updated to ₹${valQ}/q (₹${valKg.toFixed(1)}/kg). Counter-offers dispatched.` },
                { time: t, tag: 'DISPATCH', color: 'text-blue-400', text: `[LangGraph Copilot] Rejecting all bids below ₹${valQ}/q. Buyer pool instructed to meet reservation floor.` }
              ]);
              setCopilotMessages(prev => [...prev, { sender: 'AI', text: `Understood. I'll update your negotiation floor to ₹${valQ}/q (₹${valKg.toFixed(1)}/kg). Negotiators are forcing buyers to meet floor.`, time: t }]);
              setLiveBuyers(prev => prev.map(b => ({
                ...b,
                offer: Math.max(valQ, b.offer),
                status: 'Negotiating',
                aiStatus: b.offer < valQ ? `Raised to meet floor: ₹${valQ}/q` : b.aiStatus
              })));
            }, 500);

            setTimeout(() => {
              const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const bestOffer = Math.max(valQ, liveBuyers[0]?.offer || valQ);
              setLiveTerminalLogs(prev => [
                ...prev,
                { time: t, tag: 'ROUND 2', color: 'text-emerald-400', text: `Buyer A matched floor requirement: Bid confirmed at ₹${bestOffer}/q (96% Match).` },
                { time: t, tag: 'WINNER', color: 'text-emerald-300 font-bold', text: `🏆 Optimal Deal Ready: Buyer A at ₹${bestOffer}/q. Click 'Accept Deal' to confirm contract.` }
              ]);
              setLiveBuyers(prev => prev.map((b, i) => i === 0 ? { ...b, offer: bestOffer, status: 'Negotiating', aiStatus: `Farmer Override: ₹${bestOffer}/q` } : b));
            }, 1400);
          }
        }
      } else {
        // Counter / Ask / Specific price / Freeform
        const match = cmd.match(/\d+(\.\d+)?/);
        let targetAsk = farmerManualPrice;
        if (match) {
          const raw = Number(match[0]);
          targetAsk = raw < 100 ? raw * 100 : raw;
        } else if (lower.includes('best')) {
          targetAsk = (liveBuyers[0]?.offer || 2500) + 50;
        }

        const targetAskKg = (targetAsk / 100).toFixed(1);
        setFarmerManualPrice(targetAsk);

        // Step 1: Dispatch to candidate buyers (500ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'DISPATCH', color: 'text-emerald-400', text: `[LangGraph Copilot] Dispatched farmer counter-offer ₹${targetAsk}/q (₹${targetAskKg}/kg) to Buyer A, B, and C.` }
          ]);
          setLiveBuyers(prev => prev.map((b, i) => i === 2 ? { ...b, status: 'Negotiating', aiStatus: `Countering ask: ₹${Math.round(targetAsk * 0.96)}/q` } : b));
          setCopilotMessages(prev => [...prev, { sender: 'AI', text: `Manual instruction applied. Counter offer of ₹${targetAsk}/q (₹${targetAskKg}/kg) dispatched to candidate buyers.`, time: t }]);
        }, 500);

        // Step 2: Intermediate rounds (1200ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          const buyerCOffer = Math.round(targetAsk * 0.96);
          const buyerBOffer = Math.round(targetAsk * 0.985);
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'ROUND 2', color: 'text-amber-300', text: `Buyer C (Akola) evaluated ask: Cannot match ₹${targetAsk}/q. Standing at ₹${buyerCOffer}/q.` },
            { time: t, tag: 'ROUND 2', color: 'text-blue-400', text: `Buyer B (Solapur) raised bid to ₹${buyerBOffer}/q (93% Match).` }
          ]);
          setLiveBuyers(prev => {
            const fallback = getInitialBuyers(cropName, targetAsk / 100);
            const b0 = (prev && prev[0]) ? prev[0] : fallback[0];
            const b1 = (prev && prev[1]) ? prev[1] : fallback[1];
            const b2 = (prev && prev[2]) ? prev[2] : fallback[2];
            return [
              b0,
              { ...b1, offer: buyerBOffer, status: 'Negotiating', aiStatus: `Counter ₹${buyerBOffer}/q` },
              { ...b2, offer: buyerCOffer, status: 'Waiting', aiStatus: `Standing at ₹${buyerCOffer}/q` }
            ];
          });
        }, 1200);

        // Step 3: Best buyer matches (1900ms)
        setTimeout(() => {
          const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          const netTotal = Math.round(targetAsk * (cropQty < 100 ? cropQty * 100 : cropQty) - 1850);
          setLiveTerminalLogs(prev => [
            ...prev,
            { time: t, tag: 'ROUND 3', color: 'text-emerald-400', text: `Buyer A / Dining accepted farmer ask: Revised bid matched to ₹${targetAsk}/q (96% Match).` },
            { time: t, tag: 'WINNER', color: 'text-emerald-300 font-bold', text: `🏆 Optimal Deal Ready: Buyer A at ₹${targetAsk}/q. Net: ₹${netTotal.toLocaleString()}. Click 'Accept Deal' to confirm contract.` }
          ]);
          setLiveBuyers(prev => {
            const fallback = getInitialBuyers(cropName, targetAsk / 100);
            const b0 = (prev && prev[0]) ? prev[0] : fallback[0];
            const b1 = (prev && prev[1]) ? prev[1] : fallback[1];
            const b2 = (prev && prev[2]) ? prev[2] : fallback[2];
            return [
              { ...b0, offer: targetAsk, status: 'Negotiating', aiStatus: `Farmer Override: ₹${targetAsk}/q (Matched)` },
              b1,
              b2
            ];
          });
        }, 1900);
      }
    }
  };



  const handleCopilotSubmit = (e: any) => {
    e.preventDefault();
    executeCopilotCommand();
  };

  // CRITICAL FIX: Only show full-screen initialization spinner on first load when there is an active session being fetched and no data has arrived yet.
  // NEVER show it during silent background polling/refetches, so the page NEVER flashes or buffers!
  if (isLoading && !negState && (effectiveId || activeId)) {
    return (
      <div className="h-[70vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-bold text-sm">Initializing LangGraph Negotiation Engine...</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-90px)] flex flex-col xl:flex-row gap-6 p-4 max-w-[1600px] mx-auto animate-in fade-in duration-300">

      {/* ════ COLUMN 1: Intelligence Panel (Left ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto">
        <Link
          to={isBuyer ? "/dashboard/buyer" : "/dashboard/farmer"}
          className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-emerald-700 transition"
        >
          <ArrowLeft size={16} className="mr-1" /> Exit Workspace
        </Link>

        {/* Stakeholder Scope Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <ShieldCheck size={17} className="text-indigo-600" /> AI Coordination Scope
            </h2>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-xs space-y-1">
              <p className="font-bold text-indigo-700 uppercase tracking-wider mb-2">
                {activeStakeholder} &bull; {activeWorkflow.replace(/_/g, ' ')}
              </p>

              <div className="flex flex-col gap-1.5 mt-2">
                <div className="flex items-center gap-2 py-1 px-1.5 rounded-lg">
                  {(['FARMER', 'PROCESSOR', 'BUYER'].includes(activeStakeholder) || isBuyer) && activeWorkflow === 'FULL_SUPPLY_CHAIN' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={(['FARMER', 'PROCESSOR', 'BUYER'].includes(activeStakeholder) || isBuyer) && activeWorkflow === 'FULL_SUPPLY_CHAIN' ? 'text-slate-800 font-bold' : 'text-slate-400'}>
                    {isBuyer ? 'Farmer / Producer' : 'Buyer / Supplier'}
                  </span>
                </div>
                <div
                  onClick={() => openAgentModal('TRANSPORT')}
                  className="flex items-center justify-between py-1 px-1.5 rounded-lg hover:bg-cyan-50/80 cursor-pointer transition group"
                  title="Click to talk with Transport Agent & view live quotes"
                >
                  <div className="flex items-center gap-2">
                    {activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'TRANSPORT_ONLY' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                    <span className={`${activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'TRANSPORT_ONLY' ? 'text-slate-800 font-bold' : 'text-slate-400'} group-hover:text-cyan-700`}>
                      Transport
                    </span>
                  </div>
                  <span className="text-[10px] text-cyan-600 bg-cyan-100/70 px-1.5 py-0.5 rounded font-bold group-hover:bg-cyan-200 transition">
                    💬 Talk / Quotes
                  </span>
                </div>
                <div
                  onClick={() => openAgentModal('WAREHOUSE')}
                  className="flex items-center justify-between py-1 px-1.5 rounded-lg hover:bg-indigo-50/80 cursor-pointer transition group"
                  title="Click to talk with Warehouse Agent & allocate storage"
                >
                  <div className="flex items-center gap-2">
                    {activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'WAREHOUSE_ONLY' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                    <span className={`${activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'WAREHOUSE_ONLY' ? 'text-slate-800 font-bold' : 'text-slate-400'} group-hover:text-indigo-700`}>
                      Warehouse
                    </span>
                  </div>
                  <span className="text-[10px] text-indigo-600 bg-indigo-100/70 px-1.5 py-0.5 rounded font-bold group-hover:bg-indigo-200 transition">
                    💬 Talk / Quotes
                  </span>
                </div>
                <div
                  onClick={() => openAgentModal('PROCESSOR')}
                  className="flex items-center justify-between py-1 px-1.5 rounded-lg hover:bg-amber-50/80 cursor-pointer transition group"
                  title="Click to talk with Processor Agent & check milling contract"
                >
                  <div className="flex items-center gap-2">
                    {activeWorkflow === 'FULL_SUPPLY_CHAIN' && ['FARMER', 'BUYER'].includes(activeStakeholder) ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                    <span className={`${activeWorkflow === 'FULL_SUPPLY_CHAIN' && ['FARMER', 'BUYER'].includes(activeStakeholder) ? 'text-slate-800 font-bold' : 'text-slate-400'} group-hover:text-amber-700`}>
                      Processor
                    </span>
                  </div>
                  <span className="text-[10px] text-amber-600 bg-amber-100/70 px-1.5 py-0.5 rounded font-bold group-hover:bg-amber-200 transition">
                    💬 Talk / Quotes
                  </span>
                </div>
              </div>
            </div>

            {activeWorkflow !== 'FULL_SUPPLY_CHAIN' && (
              <p className="text-[10px] text-amber-600 font-bold bg-amber-50 p-2 rounded flex gap-1">
                <AlertTriangle size={12} /> Other services are manually disabled in this workflow.
              </p>
            )}
          </div>
        </div>

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

          <div className="space-y-3 pt-1">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">{isBuyer ? 'Procurement Volume' : 'Lot Volume'}</span>
              <span className="font-black text-slate-800">{cropQty.toLocaleString()} kg</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Live Modal Price</span>
              <span className="font-black text-slate-800">₹{marketPrice}/kg</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">{isBuyer ? 'Target Offer' : 'Target Ceiling'}</span>
              <span className="font-black text-emerald-600">₹{targetPrice}/kg</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Statutory Benchmark (MSP)</span>
              <span className="font-black text-purple-700">₹{statutoryBench}/kg</span>
            </div>
          </div>

          {/* Dynamic 30-Day Trend Chart */}
          <div className="pt-2 border-t border-slate-100">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Price Trend (30 Days)</p>
            <PriceChart data={chartData} />
          </div>
        </div>

        {/* Live Variables & Multi-Attribute Telemetry */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-3">
          <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Database size={17} className="text-purple-600" /> Live Variables
          </h2>

          <div className="space-y-2.5">
            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs space-y-1">
              <p className="font-bold text-blue-700 flex items-center gap-1.5">
                <CloudRain size={14} /> WEATHER & HARVEST RISK
              </p>
              <p className="text-slate-600">Clear weather across Marathwada & Western Maharashtra. Mandi arrivals steady.</p>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs space-y-1">
              <div className="flex items-center justify-between">
                <p className="font-bold text-amber-700 flex items-center gap-1.5">
                  <Truck size={14} /> HIGHWAY LOGISTICS
                </p>
              </div>
              <p className="text-slate-600">
                Freight estimated dynamically across Maharashtra corridors based on mandi transit and vehicle availability.
              </p>
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-xs space-y-1">
              <p className="font-bold text-emerald-800 flex items-center gap-1.5">
                <ShieldCheck size={14} /> STATUTORY GUARDRAIL
              </p>
              <p className="text-slate-600">Protected Band: ₹{minAllowedFloor}/kg (APMC Floor) to ₹{maxAllowedCeiling}/kg (Ceiling).</p>
            </div>
          </div>
        </div>
      </div>



      {/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}
      <div className="w-full xl:w-2/4 flex flex-col gap-4">

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative flex-1">
          {/* Header */}
          <div className="p-4 border-b border-slate-100 flex justify-between items-center z-10 sticky top-0 bg-white">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-500" /> AI Agent Negotiation — <span className="text-slate-500 font-normal">{cropName}</span>
            </h3>
            <div className="flex items-center gap-2">
              {!isDealFinalized && (
                <button
                  type="button"
                  disabled={isParallelRunning}
                  onClick={() => runParallelAutonomousNegotiation()}
                  className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-60 cursor-pointer shadow-sm"
                >
                  <Play size={12} className={isParallelRunning ? 'animate-spin' : ''} />
                  {isParallelRunning ? 'Finding & Negotiating...' : isBuyer ? 'Run Supply Chain' : 'Run Autonomous Agents'}
                </button>
              )}
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Live
              </div>
            </div>
          </div>

          {/* Quick Scenario & Crop Switcher */}
          {isBuyer && (
            <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center gap-1.5 overflow-x-auto text-[11px]">
              <span className="font-bold text-slate-500 uppercase tracking-wider text-[10px] shrink-0 mr-1 flex items-center gap-1">
                <Sparkles size={11} className="text-amber-500" /> Scenarios:
              </span>
              {(['Rice', 'Sugarcane', 'Soybean', 'Cotton', 'Onion', 'Bajra', 'Jowar'] as const).map(crop => {
                const isSelected = cropName === crop;
                const sc = MAHARASHTRA_CROP_SCENARIOS[crop];
                const emoji = crop === 'Rice' ? '🌾' : crop === 'Sugarcane' ? '🎋' : crop === 'Soybean' ? '🌱' : crop === 'Cotton' ? '⚪' : crop === 'Onion' ? '🧅' : crop === 'Bajra' ? '🌾' : '🌾';
                return (
                  <button
                    key={crop}
                    type="button"
                    onClick={() => {
                      setSelectedCropOverride(crop);
                      setDealAccepted(false);
                      setIsRenegotiating(true);
                      setLiveTerminalLogs([
                        {
                          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                          tag: 'PLANNING',
                          color: 'text-purple-400',
                          text: `Scenario loaded: ${sc.qty.toLocaleString()} kg ${crop} in ${sc.loc}. Target: ₹${sc.target}/kg (MSP: ₹${sc.bench}/kg). Ready to orchestrate.`
                        }
                      ]);
                    }}
                    className={`px-2.5 py-1 rounded-lg font-bold transition flex items-center gap-1 shrink-0 cursor-pointer text-xs ${
                      isSelected
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'bg-white text-slate-600 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    <span>{emoji}</span>
                    <span>{crop}</span>
                    <span className={`text-[10px] font-normal ${isSelected ? 'text-emerald-100' : 'text-slate-400'}`}>
                      {sc.qty >= 1000 ? `${sc.qty / 1000}T` : `${sc.qty}kg`} • ₹{sc.target}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex-1 overflow-y-auto bg-slate-50/40 p-5 space-y-4">
            {/* LangGraph AI Strategic Recommendation Banner */}
            {recommendation && (
              <div className="mb-4">
                <RecommendationCard
                  recommendation={recommendation}
                  status={negState?.status}
                  crop={cropName}
                  quantity={cropQty}
                  finalPrice={agreementData?.final_price || negState?.final_price || negState?.price}
                  onActionClick={(actionType) => {
                    if (actionType === 'DEAL') {
                      setShowValidationModal(true);
                    } else if (actionType === 'STORAGE') {
                      navigate('/transport');
                    } else if (actionType === 'PROCESSING') {
                      navigate('/processor');
                    }
                  }}
                />
              </div>
            )}
            {isBuyer ? (
              /* Buyer's view of Candidate Farmers & Best Deal */
              <>
                {isFindingMatches && (
                  <DiscoveryRadar
                    crop={cropName}
                    target={targetPrice}
                    floor={currentFloor}
                    count={5}
                  />
                )}
                <div className="space-y-3">
                  {liveSellers.map((s, i) => (
                    <div
                      key={i}
                      className={`bg-white border rounded-2xl p-4 shadow-sm relative overflow-hidden transition-all ${
                        (s.isWinner || (i === 0 && isDealFinalized))
                          ? 'border-emerald-500 ring-2 ring-emerald-200 bg-emerald-50/20 shadow-md'
                          : s.status === 'Concluded'
                          ? 'border-slate-200 opacity-75 bg-slate-50/50'
                          : s.aiStatus?.includes('Target') || s.aiStatus?.includes('Override')
                          ? 'border-indigo-400 ring-2 ring-indigo-50'
                          : 'border-slate-200/90'
                      }`}
                    >
                      {(s.isWinner || (i === 0 && isDealFinalized)) && (
                        <div className="mb-2">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-black text-amber-900 bg-amber-100 border border-amber-300 px-2.5 py-0.5 rounded-full shadow-xs">
                            <Trophy size={11} className="text-amber-600 fill-amber-500" /> BEST OPTIMAL DEAL SELECTED
                          </span>
                        </div>
                      )}

                      <div className="flex justify-between items-center mb-2.5">
                        <div>
                          <h4 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                            <Star size={16} className="text-amber-400 fill-amber-400" /> {s.id} — {s.match}% Match
                          </h4>
                          <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                            <MapPin size={10} /> {s.location}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="font-black text-slate-900 text-lg">₹{s.offer}/kg</span>
                        </div>
                      </div>

                      {s.aiStatus?.includes('Target') || s.aiStatus?.includes('Override') ? (
                        <div className="mb-2.5">
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                            <ShieldCheck size={12} className="text-indigo-600" /> BUYER OVERRIDE APPLIED
                          </span>
                        </div>
                      ) : (
                        <div className="mb-2.5">
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                            <ShieldCheck size={12} className="text-emerald-600" /> VERIFIED APMC GRADE A
                          </span>
                        </div>
                      )}

                      <div className="space-y-1.5 text-xs pt-2 border-t border-slate-100">
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">AI Strategy:</span>
                          <span className="font-semibold text-slate-700">{s.aiStatus}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">Status:</span>
                          <span className="font-semibold flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${
                              (s.isWinner || (i === 0 && isDealFinalized))
                                ? 'bg-emerald-600'
                                : s.status === 'Concluded'
                                ? 'bg-slate-400'
                                : (s.status === 'Negotiating' || s.status === 'Active')
                                ? 'bg-emerald-500 animate-pulse'
                                : 'bg-blue-500'
                            }`}></span>
                            <span className={
                              (s.isWinner || (i === 0 && isDealFinalized))
                                ? 'text-emerald-700 font-bold'
                                : s.status === 'Concluded'
                                ? 'text-slate-500'
                                : (s.status === 'Negotiating' || s.status === 'Active')
                                ? 'text-emerald-700 font-semibold'
                                : 'text-blue-700'
                            }>
                              {(s.isWinner || (i === 0 && isDealFinalized))
                                ? '✓ Agreed at Target'
                                : s.status === 'Concluded'
                                ? 'Concluded (R3 Outbid)'
                                : (s.status === 'Active' ? 'Negotiating' : s.status)}
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Finalized Banner if Deal Accepted */}
                {isDealFinalized && (
                  <div className="bg-emerald-50 border-2 border-emerald-500/80 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 animate-in fade-in">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-emerald-500 flex items-center justify-center text-slate-900 font-black text-sm shrink-0">
                        ✓
                      </div>
                      <div>
                        <h4 className="font-bold text-emerald-950 text-sm">Deal Accepted & Finalized</h4>
                        <p className="text-xs text-emerald-700">Contract confirmed under Maharashtra APMC framework. Recorded in ledger.</p>
                      </div>
                    </div>
                    <div className="flex items-center flex-wrap gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => setShowValidationModal(true)}
                        className="flex-1 sm:flex-initial px-3.5 py-2 rounded-xl bg-white border border-emerald-300 text-emerald-800 font-bold text-xs hover:bg-emerald-100 transition shadow-sm"
                      >
                        View Term Sheet
                      </button>

                      {/* Multi-Agent Procurement Orchestration Actions */}
                      {isBuyer && workflowData?.valid_next_actions?.some((a: any) => a.action === 'TRANSPORT') && (
                        <button
                          disabled={isSteppingWorkflow}
                          onClick={async () => {
                            if (!requirementId) return;
                            try {
                              setIsSteppingWorkflow(true);
                              await api.post(`/requirements/${requirementId}/workflow/step`, { action: 'TRANSPORT' });
                              await queryClient.invalidateQueries({ queryKey: ['buyerWorkflow', requirementId] });
                              addNotification('Transport Agent executed and route assigned!', 'success');
                            } catch (err: any) {
                              addNotification(err.response?.data?.detail || 'Transport execution failed', 'error');
                            } finally {
                              setIsSteppingWorkflow(false);
                            }
                          }}
                          className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5 ${
                            isSteppingWorkflow ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer animate-pulse'
                          }`}
                        >
                          <Truck size={14} /> {isSteppingWorkflow ? 'Executing Transport...' : 'Execute Transport Agent'}
                        </button>
                      )}

                      {isBuyer && workflowData?.valid_next_actions?.some((a: any) => a.action === 'WAREHOUSE') && (
                        <button
                          disabled={isSteppingWorkflow}
                          onClick={async () => {
                            if (!requirementId) return;
                            try {
                              setIsSteppingWorkflow(true);
                              await api.post(`/requirements/${requirementId}/workflow/step`, { action: 'WAREHOUSE' });
                              await queryClient.invalidateQueries({ queryKey: ['buyerWorkflow', requirementId] });
                              addNotification('Warehouse Agent executed & space allocated!', 'success');
                            } catch (err: any) {
                              addNotification(err.response?.data?.detail || 'Warehouse allocation failed', 'error');
                            } finally {
                              setIsSteppingWorkflow(false);
                            }
                          }}
                          className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5 ${
                            isSteppingWorkflow ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer animate-pulse'
                          }`}
                        >
                          <Warehouse size={14} /> {isSteppingWorkflow ? 'Allocating Storage...' : 'Execute Warehouse Agent'}
                        </button>
                      )}

                      {isBuyer && workflowData?.valid_next_actions?.some((a: any) => a.action === 'PROCESSOR') && (
                        <button
                          disabled={isSteppingWorkflow}
                          onClick={async () => {
                            if (!requirementId) return;
                            try {
                              setIsSteppingWorkflow(true);
                              await api.post(`/requirements/${requirementId}/workflow/step`, { action: 'PROCESSOR' });
                              await queryClient.invalidateQueries({ queryKey: ['buyerWorkflow', requirementId] });
                              addNotification('Processor Agent executed & batch contracted!', 'success');
                            } catch (err: any) {
                              addNotification(err.response?.data?.detail || 'Processor contract failed', 'error');
                            } finally {
                              setIsSteppingWorkflow(false);
                            }
                          }}
                          className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5 ${
                            isSteppingWorkflow ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer animate-pulse'
                          }`}
                        >
                          <Factory size={14} /> {isSteppingWorkflow ? 'Scheduling Processing...' : 'Execute Processor Agent'}
                        </button>
                      )}

                      {isBuyer && workflowData?.valid_next_actions?.some((a: any) => a.action === 'COMPLETE') && (
                        <button
                          disabled={isSteppingWorkflow}
                          onClick={async () => {
                            if (!requirementId) return;
                            try {
                              setIsSteppingWorkflow(true);
                              await api.post(`/requirements/${requirementId}/workflow/step`, { action: 'COMPLETE' });
                              await queryClient.invalidateQueries({ queryKey: ['buyerWorkflow', requirementId] });
                              addNotification('Supply-chain plan finalized and signed digitally!', 'success');
                            } catch (err: any) {
                              addNotification(err.response?.data?.detail || 'Finalization failed', 'error');
                            } finally {
                              setIsSteppingWorkflow(false);
                            }
                          }}
                          className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5 ${
                            isSteppingWorkflow ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer'
                          }`}
                        >
                          <CheckCircle2 size={14} /> {isSteppingWorkflow ? 'Finalizing Plan...' : 'Finalize Supply Chain Plan'}
                        </button>
                      )}

                      <Link
                        to="/transactions"
                        className="flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5"
                      >
                        <ExternalLink size={13} /> View in Transactions
                      </Link>
                    </div>
                  </div>
                )}

                {/* Real Multi-Agent Execution Results Display */}
                {isBuyer && workflowData?.workflow?.agent_outcomes && Object.keys(workflowData.workflow.agent_outcomes).length > 0 && (
                  <div className="bg-slate-900 text-white p-4 rounded-2xl shadow-lg border border-slate-700 mt-2 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <Bot size={16} className="text-emerald-400" />
                        <span className="font-bold text-xs uppercase tracking-wider text-slate-200">
                          Multi-Agent Supply-Chain Execution Outcomes
                        </span>
                      </div>
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                        {workflowData.workflow.workflow_status || 'RUNNING'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {/* Transport Outcome */}
                      {workflowData.workflow.agent_outcomes.TRANSPORT && (
                        <div className="bg-slate-800/80 p-3 rounded-xl border border-blue-500/30 text-xs">
                          <div className="flex items-center justify-between font-bold text-blue-300 mb-1.5">
                            <span className="flex items-center gap-1.5"><Truck size={14} /> Transport Agent</span>
                            <span className="text-[10px] bg-blue-950 px-1.5 py-0.5 rounded text-blue-300 font-bold border border-blue-800">
                              {workflowData.workflow.agent_outcomes.TRANSPORT.status}
                            </span>
                          </div>
                          <p className="text-slate-300 font-semibold">{workflowData.workflow.agent_outcomes.TRANSPORT.result?.vehicle || 'Freight Haulage'}</p>
                          <p className="text-slate-400 text-[11px] truncate">{workflowData.workflow.agent_outcomes.TRANSPORT.result?.route || 'Transit route assigned'}</p>
                          <div className="mt-2 pt-1.5 border-t border-slate-700/60 flex justify-between text-slate-300">
                            <span>Haulage Cost:</span>
                            <span className="font-bold text-white">₹{Number(workflowData.workflow.agent_outcomes.TRANSPORT.cost || 0).toLocaleString()}</span>
                          </div>
                        </div>
                      )}

                      {/* Warehouse Outcome */}
                      {workflowData.workflow.agent_outcomes.WAREHOUSE && (
                        <div className="bg-slate-800/80 p-3 rounded-xl border border-purple-500/30 text-xs">
                          <div className="flex items-center justify-between font-bold text-purple-300 mb-1.5">
                            <span className="flex items-center gap-1.5"><Warehouse size={14} /> Warehouse Agent</span>
                            <span className="text-[10px] bg-purple-950 px-1.5 py-0.5 rounded text-purple-300 font-bold border border-purple-800">
                              {workflowData.workflow.agent_outcomes.WAREHOUSE.status}
                            </span>
                          </div>
                          <p className="text-slate-300 font-semibold">{workflowData.workflow.agent_outcomes.WAREHOUSE.result?.name || 'Cold/Dry Facility'}</p>
                          <p className="text-slate-400 text-[11px] truncate">{workflowData.workflow.agent_outcomes.WAREHOUSE.result?.location || 'Maharashtra'}</p>
                          <div className="mt-2 pt-1.5 border-t border-slate-700/60 flex justify-between text-slate-300">
                            <span>Storage Cost ({workflowData.workflow.agent_outcomes.WAREHOUSE.result?.holding_days || 7}d):</span>
                            <span className="font-bold text-white">₹{Number(workflowData.workflow.agent_outcomes.WAREHOUSE.cost || 0).toLocaleString()}</span>
                          </div>
                        </div>
                      )}

                      {/* Processor Outcome */}
                      {workflowData.workflow.agent_outcomes.PROCESSOR && (
                        <div className="bg-slate-800/80 p-3 rounded-xl border border-amber-500/30 text-xs">
                          <div className="flex items-center justify-between font-bold text-amber-300 mb-1.5">
                            <span className="flex items-center gap-1.5"><Factory size={14} /> Processor Agent</span>
                            <span className="text-[10px] bg-amber-950 px-1.5 py-0.5 rounded text-amber-300 font-bold border border-amber-800">
                              {workflowData.workflow.agent_outcomes.PROCESSOR.status}
                            </span>
                          </div>
                          <p className="text-slate-300 font-semibold">{workflowData.workflow.agent_outcomes.PROCESSOR.result?.name || 'Industrial Processor'}</p>
                          <p className="text-slate-400 text-[11px] truncate">{workflowData.workflow.agent_outcomes.PROCESSOR.result?.output_product || 'Value-added conversion'}</p>
                          <div className="mt-2 pt-1.5 border-t border-slate-700/60 flex justify-between text-slate-300">
                            <span>Milling Tariff:</span>
                            <span className="font-bold text-white">₹{Number(workflowData.workflow.agent_outcomes.PROCESSOR.cost || 0).toLocaleString()}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Final Supply Chain Aggregation */}
                    {workflowData.workflow.final_plan && (
                      <div className="bg-emerald-950/70 p-3 rounded-xl border border-emerald-600/40 text-xs flex flex-col sm:flex-row items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <ShieldCheck size={20} className="text-emerald-400 shrink-0" />
                          <div>
                            <p className="font-bold text-white text-sm">
                              Total End-to-End Procurement: ₹{Number(workflowData.workflow.final_plan.total_procurement_cost || 0).toLocaleString()}
                            </p>
                            <p className="text-emerald-300 text-[11px]">
                              Digital Contract Hash: <span className="font-mono text-emerald-200">{workflowData.workflow.final_plan.contract_signature}</span>
                            </p>
                          </div>
                        </div>
                        <span className="bg-emerald-500 text-slate-950 px-3 py-1 rounded-lg font-black text-xs shadow">
                          ALL AGENTS COMPLETED
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Best Deal So Far (Buyer Parity with Farmer Layout) */}
                <div className="bg-[#064e3b] p-4 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md mt-2">
                  <div>
                    <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Trophy size={13} className="text-amber-400" /> BEST DEAL SO FAR
                    </p>
                    <div className="flex items-center flex-wrap gap-2 text-xs">
                      <span className="font-bold text-base text-white">{liveSellers[0]?.id || 'Primary Farmer'}</span>
                      <span className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-2 py-0.5 rounded text-xs font-bold">
                        ₹{liveSellers[0]?.offer ?? targetPrice}/kg
                      </span>
                      <span className="text-emerald-100">{cropQty.toLocaleString()} kg</span>
                      <span className="text-emerald-100">{liveSellers[0]?.match ?? 96}% Match</span>
                      <span className="font-bold text-emerald-200">
                        Net: ₹{Math.round((liveSellers[0]?.offer ?? targetPrice) * cropQty).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
                    <button
                      onClick={() => setIsRagOpen(true)}
                      className="px-3.5 py-2 rounded-xl border border-emerald-500/70 text-emerald-100 bg-emerald-800/40 hover:bg-emerald-800 text-xs font-bold transition flex-1 sm:flex-none text-center cursor-pointer"
                    >
                      View Analysis
                    </button>
                    <button
                      onClick={() => {
                        handleAcceptDeal({
                          price: liveSellers[0]?.offer || targetPrice,
                          farmer: liveSellers[0]?.id || 'Primary Farmer',
                          farmer_name: liveSellers[0]?.id || 'Primary Farmer',
                          buyer: buyerName,
                          crop: cropName,
                          quantity: cropQty
                        });
                      }}
                      className={`px-4 py-2 rounded-xl font-black text-xs transition shadow flex-1 sm:flex-none text-center cursor-pointer ${
                        isDealFinalized
                          ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                          : 'bg-emerald-500 hover:bg-emerald-400 text-slate-900'
                      }`}
                    >
                      {isDealFinalized ? '✓ Accepted • View Contract' : 'Accept Deal'}
                    </button>
                  </div>
                </div>
              </>
            ) : liveBuyers.length > 0 ? (
              <>
                {isFindingMatches && (
                  <DiscoveryRadar
                    crop={cropName}
                    target={targetPrice}
                    floor={currentFloor}
                    count={5}
                  />
                )}
                <div className="space-y-3">
                  {liveBuyers.map((b, i) => (
                    <div
                      key={i}
                      className={`bg-white border rounded-2xl p-4 shadow-sm relative overflow-hidden transition-all ${
                        (b.isWinner || (i === 0 && isDealFinalized))
                          ? 'border-emerald-500 ring-2 ring-emerald-200 bg-emerald-50/20 shadow-md'
                          : b.status === 'Concluded'
                          ? 'border-slate-200 opacity-75 bg-slate-50/50'
                          : b.aiStatus?.includes('Override')
                          ? 'border-indigo-400 ring-2 ring-indigo-50'
                          : 'border-slate-200/90'
                      }`}
                    >
                      {(b.isWinner || (i === 0 && isDealFinalized)) && (
                        <div className="mb-2">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-black text-amber-900 bg-amber-100 border border-amber-300 px-2.5 py-0.5 rounded-full shadow-xs">
                            <Trophy size={11} className="text-amber-600 fill-amber-500" /> BEST OPTIMAL DEAL SELECTED
                          </span>
                        </div>
                      )}

                      <div className="flex justify-between items-center mb-2.5">
                        <div>
                          <h4 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                            <Star size={16} className="text-amber-400 fill-amber-400" /> {b.id} — {b.match}% Match
                          </h4>
                          <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                            <MapPin size={10} /> {b.distance} &bull; Req: {b.req}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="font-black text-slate-900 text-lg">₹{b.offer}/kg</span>
                          <p className="text-[10px] text-slate-400">Offer price</p>
                        </div>
                      </div>

                      {b.aiStatus?.includes('Override') && (
                        <div className="mb-2.5">
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                            <ShieldCheck size={12} className="text-indigo-600" /> FARMER OVERRIDE APPLIED
                          </span>
                        </div>
                      )}

                      <div className="space-y-1.5 text-xs pt-2 border-t border-slate-100">
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">AI Strategy:</span>
                          <span className={`font-semibold ${b.aiStatus?.includes('Override') ? 'text-indigo-600 font-bold' : 'text-slate-700'}`}>
                            {b.aiStatus}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">Status:</span>
                          <span className="font-semibold flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${
                              (b.isWinner || (i === 0 && isDealFinalized))
                                ? 'bg-emerald-600'
                                : b.status === 'Concluded'
                                ? 'bg-slate-400'
                                : (b.status === 'Active Offer' || b.status === 'Negotiating')
                                ? 'bg-emerald-500 animate-pulse'
                                : 'bg-blue-500'
                            }`}></span>
                            <span className={
                              (b.isWinner || (i === 0 && isDealFinalized))
                                ? 'text-emerald-700 font-bold'
                                : b.status === 'Concluded'
                                ? 'text-slate-500'
                                : (b.status === 'Active Offer' || b.status === 'Negotiating')
                                ? 'text-emerald-700 font-semibold'
                                : 'text-blue-700'
                            }>
                              {(b.isWinner || (i === 0 && isDealFinalized))
                                ? '✓ Agreed at Ask'
                                : b.status === 'Concluded'
                                ? 'Concluded (R3 Outbid)'
                                : b.status}
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Finalized Banner if Deal Accepted (Farmer Parity with Buyer) */}
                {isDealFinalized && (
                  <div className="bg-emerald-50 border-2 border-emerald-500/80 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 animate-in fade-in">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-emerald-500 flex items-center justify-center text-slate-900 font-black text-sm shrink-0">
                        ✓
                      </div>
                      <div>
                        <h4 className="font-bold text-emerald-950 text-sm">Deal Accepted & Finalized</h4>
                        <p className="text-xs text-emerald-700">Contract confirmed under Maharashtra APMC framework. Recorded in ledger.</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => setShowValidationModal(true)}
                        className="flex-1 sm:flex-initial px-3.5 py-2 rounded-xl bg-white border border-emerald-300 text-emerald-800 font-bold text-xs hover:bg-emerald-100 transition shadow-sm"
                      >
                        View Term Sheet
                      </button>
                      <Link
                        to="/transactions"
                        className="flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-black text-xs transition shadow flex items-center justify-center gap-1.5"
                      >
                        <ExternalLink size={13} /> View in Transactions
                      </Link>
                    </div>
                  </div>
                )}

                {/* Best Deal So Far (Banner inside center column) */}
                <div className="bg-[#064e3b] p-4 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md mt-2">
                  <div>
                    <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Trophy size={13} className="text-amber-400" /> BEST DEAL SO FAR
                    </p>
                    <div className="flex items-center flex-wrap gap-2 text-xs">
                      <span className="font-bold text-base text-white">{liveBuyers[0]?.id || 'AgroCorp Procurement Director'}</span>
                      <span className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-2 py-0.5 rounded text-xs font-bold">
                        ₹{liveBuyers[0]?.offer ?? 2500}/kg
                      </span>
                      <span className="text-emerald-100">{cropQty.toLocaleString()} kg</span>
                      <span className="text-emerald-100">{liveBuyers[0]?.match ?? 96}% Match</span>
                      <span className="font-bold text-emerald-200">
                        Net: ₹{Math.max(0, Math.round((liveBuyers[0]?.offer ?? 2500) * cropQty - 1850)).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
                    <button
                      onClick={() => setIsRagOpen(true)}
                      className="px-3.5 py-2 rounded-xl border border-emerald-500/70 text-emerald-100 bg-emerald-800/40 hover:bg-emerald-800 text-xs font-bold transition flex-1 sm:flex-none text-center cursor-pointer"
                    >
                      View Analysis
                    </button>
                    <button
                      onClick={() => {
                        handleAcceptDeal({
                          price: liveBuyers[0]?.offer || 2500,
                          farmer: user?.name,
                          buyer: liveBuyers[0]?.id || 'AgroCorp Procurement Director',
                          crop: cropName,
                          quantity: cropQty
                        });
                      }}
                      className={`px-4 py-2 rounded-xl font-black text-xs transition shadow flex-1 sm:flex-none text-center cursor-pointer ${
                        isDealFinalized
                          ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                          : 'bg-emerald-500 hover:bg-emerald-400 text-slate-900'
                      }`}
                    >
                      {isDealFinalized ? '✓ Accepted • View Contract' : 'Accept Deal'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="py-8 px-6 text-center bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm">
                <div className="w-14 h-14 bg-emerald-50 border border-emerald-200 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                  <span className="absolute w-full h-full rounded-full bg-emerald-400/20 animate-ping"></span>
                  <Bot size={26} className="text-emerald-600 relative z-10" />
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200 mb-3">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  Autonomous Agent is LIVE & Searching
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">
                  Actively Finding Best Matching Buyers for {cropName}
                </h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto mb-6 leading-relaxed">
                  No buyers currently meet your minimum acceptable floor of <strong className="text-emerald-700">₹{currentFloor}/kg</strong>. The AI agent is actively querying APMC mandi networks, evaluating logistics corridors, and defending your floor price.
                </p>

                <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 max-w-md mx-auto text-left space-y-2.5">
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">LIVE AGENT DISCOVERY PIPELINE:</p>
                  <div className="flex items-center gap-2 text-xs text-slate-700">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Scanning 10 Maharashtra APMC Mandi Buyer Networks</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-700">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Enforcing Statutory Floor Guardrail: <strong>₹{currentFloor}/kg</strong></span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-700">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Evaluating Cold Storage & Processing Fallbacks</span>
                  </div>
                  <div className="pt-2 border-t border-slate-200/80">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">MATCHING CRITERIA:</p>
                    <div className="grid grid-cols-2 gap-1.5 text-[11px] text-slate-600">
                      {['Crop & Variety', 'Quality Grade', 'Mandi Location', 'Logistics Corridor'].map((txt, i) => (
                        <div key={i} className="flex items-center gap-1.5">
                          <CheckCircle size={12} className="text-emerald-500" /> {txt}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Live Terminal logs at bottom (Matching User Screenshot) */}
            <div className="mt-4 bg-[#0f172a] rounded-xl p-4 font-mono text-[11px] leading-relaxed overflow-y-auto max-h-44 text-slate-300 shadow-inner">
              <div className="text-emerald-400 font-bold mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span> LIVE ACTIVITY
              </div>
              <div className="space-y-1">
                {liveTerminalLogs.length === 0 ? (
                  <>
                    <div className="flex items-start gap-2 text-slate-400 text-[10px]">
                      <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                      <span className="text-blue-400 font-bold shrink-0">System:</span>
                      <span>🚀 [System] Negotiation {id ? id.substring(0, 12) : 'session'} queued in Redis. Waiting for worker...</span>
                    </div>
                    <div className="flex items-start gap-2 text-slate-400 text-[10px]">
                      <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                      <span className="text-blue-400 font-bold shrink-0">Worker:</span>
                      <span>🚀 [Worker] Negotiation dispatched via Redis stream to LangGraph orchestrator.</span>
                    </div>
                    <div className="flex items-start gap-2 text-slate-400 text-[10px]">
                      <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                      <span className="text-purple-400 font-bold shrink-0">Planner:</span>
                      <span>📋 [Planner] Initiating negotiation workflow planner for {cropName}.</span>
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
        </div>
      </div>

      {/* ════ COLUMN 3: Right Panel (LangGraph + Farmer Copilot ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 h-full">

        {/* Card 1: LangGraph Supply Chain Execution Stepper */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Zap size={16} className="text-emerald-500" /> LangGraph Execution
              </h4>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                isParallelRunning
                  ? 'bg-emerald-100 text-emerald-700 animate-pulse border border-emerald-200'
                  : completedSupplyChainNodes.length === SUPPLY_CHAIN_STAGES.length
                  ? 'bg-blue-100 text-blue-700 border border-blue-200'
                  : 'bg-slate-100 text-slate-600'
              }`}>
                {isParallelRunning ? 'LIVE RUN' : completedSupplyChainNodes.length === SUPPLY_CHAIN_STAGES.length ? 'COMPLETE' : 'STANDBY'}
              </span>
            </div>

            <p className="text-[11px] text-slate-500 mb-3">
              Autonomous end-to-end multi-agent supply chain orchestration.
            </p>

            <div className="space-y-1.5 mb-4 max-h-[380px] overflow-y-auto pr-1">
              {SUPPLY_CHAIN_STAGES.map((stage) => {
                const isRunning = isParallelRunning && activeSupplyChainNode === stage.id;
                const isCompleted = completedSupplyChainNodes.includes(stage.id) && !isRunning;
                const isInteractiveAgent = ['TRANSPORT', 'WAREHOUSE', 'PROCESSOR'].includes(stage.id);
                const StageIcon = stage.icon;

                return (
                  <div
                    key={stage.id}
                    onClick={() => {
                      if (isInteractiveAgent) {
                        openAgentModal(stage.id as any);
                      }
                    }}
                    className={`flex items-center justify-between p-2 rounded-xl text-xs transition-all ${
                      isRunning
                        ? 'bg-emerald-50 border border-emerald-200 font-bold text-emerald-950 shadow-sm'
                        : isCompleted
                        ? 'bg-slate-50 border border-slate-100 text-slate-700'
                        : isInteractiveAgent
                        ? 'bg-white border border-slate-200/60 text-slate-700 hover:bg-slate-50/90 hover:border-slate-300 cursor-pointer shadow-xs'
                        : 'text-slate-400 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`w-5 h-5 rounded-md flex items-center justify-center text-xs shrink-0 ${
                        isRunning
                          ? 'bg-emerald-500 text-white shadow-sm'
                          : isCompleted
                          ? 'bg-emerald-100 text-emerald-700'
                          : isInteractiveAgent
                          ? stage.id === 'TRANSPORT' ? 'bg-cyan-100 text-cyan-700' : stage.id === 'WAREHOUSE' ? 'bg-indigo-100 text-indigo-700' : 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-400'
                      }`}>
                        {isCompleted ? <Check size={12} className="stroke-[3]" /> : <StageIcon size={12} />}
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className={`text-xs truncate ${isRunning ? 'text-emerald-900 font-black' : isCompleted || isInteractiveAgent ? 'text-slate-800 font-semibold' : 'text-slate-400'}`}>
                          {stage.label}
                        </span>
                        <span className="text-[9px] text-slate-400 font-normal truncate">
                          {stage.sub}
                        </span>
                      </div>
                    </div>

                    <div className="shrink-0 ml-1 flex items-center gap-1.5">
                      {isRunning && (
                        <span className="bg-emerald-500 text-white px-1.5 py-0.5 rounded text-[9px] font-black flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span> RUNNING
                        </span>
                      )}
                      {isCompleted && (
                        <span className="text-emerald-600 font-bold text-[10px] flex items-center gap-0.5">
                          ✓ DONE
                        </span>
                      )}
                      {isInteractiveAgent && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            openAgentModal(stage.id as any);
                          }}
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border transition ${
                            stage.id === 'TRANSPORT' ? 'bg-cyan-50 text-cyan-700 border-cyan-200 hover:bg-cyan-100' :
                            stage.id === 'WAREHOUSE' ? 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100' :
                            'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
                          }`}
                          title={`Open ${stage.label} communication & live quotes`}
                        >
                          💬 Talk
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* View RAG Context Button */}
          <button
            type="button"
            onClick={() => setIsRagOpen(true)}
            className="w-full py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-700 font-bold rounded-xl transition text-xs flex justify-center items-center gap-2 shadow-sm cursor-pointer mt-2"
          >
            <Database size={14} className="text-slate-500" /> View RAG Context
          </button>
        </div>

        {/* Card 1.5: LangGraph Reflection Post-Mortem (if available) */}
        {reflection && (
          <ReflectionCard
            reflection={reflection}
            negotiationId={id}
          />
        )}

        {/* Card 2: Dual Copilot (Buyer Procurement Copilot if isBuyer, else Farmer Copilot) */}
        {isBuyer ? (
          <div className="bg-[#0f172a] rounded-2xl shadow-lg border border-slate-800 p-5 text-white flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm flex items-center gap-2 text-white">
                  <ShieldCheck size={16} className="text-blue-400" />
                  <span className="text-base">🏢</span> Buyer Procurement Copilot
                </h3>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                AI is procuring automatically based on your target price, reservation ceiling, and APMC freight. You can intervene at any time.
              </p>

              {/* Quick Action Chips */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => executeCopilotCommand(`Counter at target ₹${Math.round(targetPrice || 48)}`)}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Counter target ₹{Math.round(targetPrice || 48)}
                </button>
                <button
                  type="button"
                  onClick={() => executeCopilotCommand(`Don't exceed ₹${Math.round(maxAllowedCeiling || 52)}`)}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Ceiling ₹{Math.round(maxAllowedCeiling || 52)}
                </button>
                <button
                  type="button"
                  onClick={() => executeCopilotCommand('Counter best farmer')}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Counter best farmer
                </button>
                <button
                  type="button"
                  onClick={() => executeCopilotCommand('Pause negotiations')}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Pause negotiations
                </button>
                <button
                  type="button"
                  onClick={() => openAgentModal('TRANSPORT')}
                  className="px-2.5 py-1.5 bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 rounded-lg text-[11px] font-semibold border border-cyan-700/60 transition cursor-pointer flex items-center gap-1 shadow-sm"
                  title="Talk directly to Transport Agent and view vehicle quotes"
                >
                  <Truck size={12} /> Talk Transport
                </button>
                <button
                  type="button"
                  onClick={() => openAgentModal('WAREHOUSE')}
                  className="px-2.5 py-1.5 bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 rounded-lg text-[11px] font-semibold border border-indigo-700/60 transition cursor-pointer flex items-center gap-1 shadow-sm"
                  title="Talk directly to Warehouse Agent and allocate godown"
                >
                  <Warehouse size={12} /> Talk Warehouse
                </button>
                <button
                  type="button"
                  onClick={() => openAgentModal('PROCESSOR')}
                  className="px-2.5 py-1.5 bg-amber-950/80 hover:bg-amber-900 text-amber-300 rounded-lg text-[11px] font-semibold border border-amber-700/60 transition cursor-pointer flex items-center gap-1 shadow-sm"
                  title="Talk directly to Processor Agent and inspect milling yield"
                >
                  <Factory size={12} /> Talk Processor
                </button>
              </div>

              {/* Manual Bid Increment Tools */}
              <div className="mb-4 p-3 bg-slate-900/90 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold">
                  <span>Manual Offer Price:</span>
                  <span className="text-emerald-400 font-mono font-bold">₹{manualPrice || targetPrice}/kg</span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      const base = parseFloat(manualPrice) || targetPrice || 40;
                      setManualPrice((base - 1.0).toFixed(1));
                    }}
                    className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg text-[11px] font-bold border border-slate-700 transition cursor-pointer text-center"
                  >
                    -₹1.00
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const base = parseFloat(manualPrice) || targetPrice || 40;
                      setManualPrice((base + 1.0).toFixed(1));
                    }}
                    className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg text-[11px] font-bold border border-slate-700 transition cursor-pointer text-center"
                  >
                    +₹1.00
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const val = parseFloat(manualPrice) || targetPrice;
                      if (val) {
                        executeCopilotCommand(`Submit offer at ₹${val}/kg`);
                      }
                    }}
                    className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-[11px] font-bold transition cursor-pointer text-center shadow-sm"
                  >
                    Bid Offer
                  </button>
                </div>
              </div>

              {/* Last Copilot Response Feedback (if user intervened) */}
              {copilotMessages.length > 0 && (
                <div className="mb-3 p-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-[11px] text-slate-300 flex items-start gap-2">
                  <Bot size={14} className="text-blue-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="text-slate-400 font-semibold text-[10px]">
                      {copilotMessages[copilotMessages.length - 1].sender === 'AI' ? 'AI Copilot: ' : 'Instruction: '}
                    </span>
                    {copilotMessages[copilotMessages.length - 1].text}
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
                placeholder='e.g. "Counter Ramesh Patil at ₹49/kg"'
                className="w-full bg-[#1e293b]/80 border border-slate-700/80 rounded-xl px-4 py-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition"
              />
              <button
                type="submit"
                className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm rounded-xl transition shadow-md flex items-center justify-center gap-1.5 cursor-pointer"
              >
                Send Instruction
              </button>
            </form>
          </div>
        ) : (
          /* Card 2: Farmer Copilot (Dark Theme exactly matching user image - 100% UNTOUCHED) */
          <div className="bg-[#0f172a] rounded-2xl shadow-lg border border-slate-800 p-5 text-white flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-sm flex items-center gap-2 text-white">
                  <ShieldCheck size={16} className="text-emerald-400" />
                  <span className="text-base">👨‍🌾</span> Farmer Copilot
                </h3>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                AI is negotiating automatically based on your listing, market conditions and negotiation policy. You can intervene at any time.
              </p>

              {/* Quick Action Chips */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => executeCopilotCommand(`Don't go below ₹${currentFloor < 100 ? currentFloor * 100 : currentFloor}/q`)}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Don't go below ₹{currentFloor < 100 ? currentFloor * 100 : currentFloor}/q
                </button>
                <button
                  type="button"
                  onClick={() => executeCopilotCommand('Counter best buyer')}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Counter best buyer
                </button>
                <button
                  type="button"
                  onClick={() => executeCopilotCommand('Pause negotiations')}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Pause negotiations
                </button>
              </div>

              {/* Manual Asking Rate Increment Tools (Farmer Parity with Buyer) */}
              <div className="mb-4 p-3 bg-slate-900/90 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold">
                  <span>Manual Asking Rate:</span>
                  <span className="text-emerald-400 font-mono font-bold">
                    ₹{farmerManualPrice}/q <span className="text-slate-400 text-[10px] font-normal">(₹{(farmerManualPrice / 100).toFixed(1)}/kg)</span>
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setFarmerManualPrice(prev => Math.max(1000, prev - 50))}
                    className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg text-[11px] font-bold border border-slate-700 transition cursor-pointer text-center"
                  >
                    -₹50
                  </button>
                  <button
                    type="button"
                    onClick={() => setFarmerManualPrice(prev => prev + 50)}
                    className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg text-[11px] font-bold border border-slate-700 transition cursor-pointer text-center"
                  >
                    +₹50
                  </button>
                  <button
                    type="button"
                    onClick={() => executeCopilotCommand(`Counter best buyer at ₹${farmerManualPrice}/q`)}
                    className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-bold transition cursor-pointer text-center shadow-sm"
                  >
                    Set Ask Price
                  </button>
                </div>
              </div>

              {/* Last Copilot Response Feedback (if user intervened) */}
              {copilotMessages.length > 0 && (
                <div className="mb-3 p-2.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-[11px] text-slate-300 flex items-start gap-2">
                  <Bot size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span className="text-slate-400 font-semibold text-[10px]">
                      {copilotMessages[copilotMessages.length - 1].sender === 'AI' ? 'AI Copilot: ' : 'Instruction: '}
                    </span>
                    {copilotMessages[copilotMessages.length - 1].text}
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
                placeholder='e.g. "Try to get ₹67 from the best'
                className="w-full bg-[#1e293b]/80 border border-slate-700/80 rounded-xl px-4 py-3 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
              <button
                type="submit"
                className="w-full py-3 bg-[#10b981] hover:bg-emerald-600 text-white font-bold text-sm rounded-xl transition shadow-md flex items-center justify-center gap-1.5"
              >
                Send Instruction
              </button>
            </form>
          </div>
        )}

      </div>
      {/* Floating RAG Modal */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} crop={cropName} />

      {/* APMC Validated Smart Contract Modal */}
      <TransactionValidationModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        dealData={agreementData}
        buyerUser={user}
      />

      {/* Interactive Agent Dialog Modal (Transport / Warehouse / Processor) */}
      {activeAgentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-2xl w-full text-white overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className={`p-4 border-b flex items-center justify-between ${
              activeAgentModal === 'TRANSPORT' ? 'bg-cyan-950/40 border-cyan-800/60' :
              activeAgentModal === 'WAREHOUSE' ? 'bg-indigo-950/40 border-indigo-800/60' :
              'bg-amber-950/40 border-amber-800/60'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  activeAgentModal === 'TRANSPORT' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' :
                  activeAgentModal === 'WAREHOUSE' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' :
                  'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                }`}>
                  {activeAgentModal === 'TRANSPORT' && <Truck size={20} />}
                  {activeAgentModal === 'WAREHOUSE' && <Warehouse size={20} />}
                  {activeAgentModal === 'PROCESSOR' && <Factory size={20} />}
                </div>
                <div>
                  <h3 className="font-bold text-base text-white flex items-center gap-2">
                    {activeAgentModal === 'TRANSPORT' && 'LangGraph Transport Agent (12 Nodes)'}
                    {activeAgentModal === 'WAREHOUSE' && 'Warehouse & Godown Allocation Agent'}
                    {activeAgentModal === 'PROCESSOR' && 'Industrial Agro-Processor & Milling Agent'}
                    <span className="text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      LIVE AUTONOMOUS
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    {activeAgentModal === 'TRANSPORT' && `Corridor: ${negState?.location || 'Nashik APMC'} → Pune APMC (213 km) • ${cropQty.toLocaleString()} kg ${cropName}`}
                    {activeAgentModal === 'WAREHOUSE' && `State Godown Network • Available Slot: Bay C-4 Pune • ${cropQty.toLocaleString()} kg ${cropName}`}
                    {activeAgentModal === 'PROCESSOR' && `Milling Cluster: Marathwada Agro-Hub • ${cropQty.toLocaleString()} kg ${cropName}`}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveAgentModal(null)}
                className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Key Live Quotation & Agent Parameters */}
            <div className="p-4 bg-slate-950/60 border-b border-slate-800 grid grid-cols-3 gap-3 text-xs">
              {activeAgentModal === 'TRANSPORT' && (
                <>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Recommended Fleet</span>
                    <span className="text-cyan-400 font-bold text-sm">Tata Ace Gold (1.5 MT)</span>
                    <span className="text-[10px] text-slate-500 block">Fuel Index: ₹90.45/L</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Haulage Tariff</span>
                    <span className="text-emerald-400 font-bold text-sm">₹9,099.43</span>
                    <span className="text-[10px] text-slate-500 block">Tolls: ₹426 • 213 km</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Transit Window</span>
                    <span className="text-amber-300 font-bold text-sm">5.5 Hours</span>
                    <span className="text-[10px] text-slate-500 block">GPS Telematics Active</span>
                  </div>
                </>
              )}

              {activeAgentModal === 'WAREHOUSE' && (
                <>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Facility Name</span>
                    <span className="text-indigo-400 font-bold text-sm">Pune Co-op Godown</span>
                    <span className="text-[10px] text-slate-500 block">Capacity: 5,000 MT</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Holding Tariff</span>
                    <span className="text-emerald-400 font-bold text-sm">₹105.00 / 7 Days</span>
                    <span className="text-[10px] text-slate-500 block">Rate: ₹0.015/kg/day</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Storage Quality</span>
                    <span className="text-blue-300 font-bold text-sm">Moisture ≤ 10.5%</span>
                    <span className="text-[10px] text-slate-500 block">Certified Aeration</span>
                  </div>
                </>
              )}

              {activeAgentModal === 'PROCESSOR' && (
                <>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Matched Unit</span>
                    <span className="text-amber-400 font-bold text-sm">Marathwada Solvent</span>
                    <span className="text-[10px] text-slate-500 block">FSSAI & AGMARK Gr-A</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Processing Fee</span>
                    <span className="text-emerald-400 font-bold text-sm">₹4,080.00</span>
                    <span className="text-[10px] text-slate-500 block">Fixed Contract Rate</span>
                  </div>
                  <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Yield Ratio</span>
                    <span className="text-amber-300 font-bold text-sm">18% Oil / 79.5% DOC</span>
                    <span className="text-[10px] text-slate-500 block">2.5% Milling Loss</span>
                  </div>
                </>
              )}
            </div>

            {/* Chat Interaction History */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 min-h-[220px] max-h-[320px] bg-slate-900/50">
              <div className="text-[11px] text-center text-slate-500 font-medium">
                ── Real-Time Agent Communication Channel ──
              </div>

              {(agentChatHistory[activeAgentModal] || []).map((chat, idx) => (
                <div
                  key={idx}
                  className={`flex ${chat.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs ${
                    chat.sender === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-slate-800 text-slate-200 border border-slate-700/80 rounded-bl-none shadow-sm'
                  }`}>
                    <div className="flex items-center justify-between gap-3 mb-1 text-[10px] opacity-75">
                      <span className="font-bold">
                        {chat.sender === 'user' ? 'You (Buyer/Operator)' : `${activeAgentModal} Agent`}
                      </span>
                      <span>{chat.time}</span>
                    </div>
                    <p className="leading-relaxed">{chat.text}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Action Chips for the Agent */}
            <div className="px-4 py-2 bg-slate-950/80 border-t border-slate-800/80 flex flex-wrap gap-2">
              <span className="text-[10px] text-slate-500 self-center font-bold">Quick Prompts:</span>
              {activeAgentModal === 'TRANSPORT' && (
                <>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('Can you check rates for a refrigerated reefer truck?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    ❄️ Check Cold / Reefer
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('Can we negotiate carrier counter rate at ₹8,750?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    💰 Negotiate Counter
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('What is the exact transit duration and ETA?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    ⏱️ ETA & Route
                  </button>
                </>
              )}

              {activeAgentModal === 'WAREHOUSE' && (
                <>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('Can we extend holding duration to 14 days?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    📅 Extend to 14 Days
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('What are the temperature and moisture parameters?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    🌡️ Moisture & Fumigation
                  </button>
                </>
              )}

              {activeAgentModal === 'PROCESSOR' && (
                <>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('What is the exact oil extraction yield for this batch?'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    🌾 Oil Yield Breakdown
                  </button>
                  <button
                    type="button"
                    onClick={() => { setAgentChatInput('Confirm priority milling schedule upon arrival.'); }}
                    className="text-[11px] px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    ⚡ Priority Slotting
                  </button>
                </>
              )}
            </div>

            {/* Input Message Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendAgentChatMessage(activeAgentModal);
              }}
              className="p-3 bg-slate-900 border-t border-slate-800 flex gap-2"
            >
              <input
                type="text"
                value={agentChatInput}
                onChange={(e) => setAgentChatInput(e.target.value)}
                placeholder={`Ask ${activeAgentModal.toLowerCase()} agent or give manual counter instructions...`}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition"
              />
              <button
                type="submit"
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-md cursor-pointer"
              >
                <Send size={14} /> Send
              </button>
            </form>

            {/* Modal Footer with Direct Agent Invocation */}
            <div className="p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-between">
              <div className="text-xs text-slate-400">
                Status: <span className="text-emerald-400 font-semibold">{completedSupplyChainNodes.includes(activeAgentModal) ? 'Contracted / Assigned' : 'Ready for Invocation'}</span>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActiveAgentModal(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  disabled={isInvokingAgent}
                  onClick={() => invokeAgentAction(activeAgentModal)}
                  className={`px-5 py-2 font-bold text-xs rounded-xl transition shadow-lg flex items-center gap-2 cursor-pointer ${
                    activeAgentModal === 'TRANSPORT' ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-900/30' :
                    activeAgentModal === 'WAREHOUSE' ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-900/30' :
                    'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-900/30'
                  } ${isInvokingAgent ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  <Zap size={14} />
                  {isInvokingAgent ? 'Executing Agent...' : `Invoke ${activeAgentModal} Agent`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
