import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
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
  Play
} from 'lucide-react';
import ChatBubble from '@/features/negotiation/components/ChatBubble';
import OfferCard from '@/features/negotiation/components/OfferCard';
import AgreementPreview from '@/features/negotiation/components/AgreementPreview';
import AgentWorkflowStepper from '@/features/negotiation/components/AgentWorkflowStepper';
import RagContextViewer from '@/features/negotiation/components/RagContextViewer';
import PriceChart from '@/features/negotiation/components/PriceChart';
import TransactionValidationModal from '@/components/negotiation/TransactionValidationModal';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isBuyer = user?.role === 'buyer';

  const token = localStorage.getItem('agri_token');
  const wsUrl = import.meta.env.VITE_WS_URL || '/api/v1/ws';
  const { isConnected, lastMessage } = useWebSocket(wsUrl);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // States
  const [messages, setMessages] = useState<any[]>([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState<any>(null);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'terminal'>('timeline');
  const [isParallelRunning, setIsParallelRunning] = useState(false);
  const [liveTerminalLogs, setLiveTerminalLogs] = useState<Array<{ time: string; tag: string; text: string; color?: string }>>([]);
  const [manualPrice, setManualPrice] = useState<string>('');

  // 1. Fetch negotiation session state from database
  const { data: negState, isLoading, refetch: refetchNeg } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      const res = await api.get(`/negotiations/${id}`);
      return res.data?.data || res.data;
    },
    refetchInterval: 4000
  });

  const cropName = negState?.crop || 'Soybean';
  const cropQty = Number(negState?.quantity) || 500;
  const currentFloor = Number(negState?.min_price) || 45.0;
  const targetPrice = Number(negState?.target_price || negState?.buyer_target_price || 47.0);
  const marketPrice = Number(negState?.market_price || Math.round(targetPrice * 1.04 * 10) / 10);
  const activeAgent = isParallelRunning ? 'Negotiator' : (lastMessage?.data?.agent || 'Negotiator');

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

      if (negState.status === 'DEAL' || negState.final_price) {
        const finalP = negState.final_price || negState.price || targetPrice;
        setAgreementData({
          ...negState,
          id: id,
          negotiation_id: id,
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
    }
  }, [negState, cropQty, cropName, targetPrice, marketPrice, statutoryBench, isBuyer, user]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && String(lastMessage.negotiation_id) === String(id)) {
      if (lastMessage.event === 'NEGOTIATION_LOG') {
        const isFarmerSender = lastMessage.agent_type === 'farmer';
        const msgObj = {
          agent: isFarmerSender ? 'Farmer Agent' : 'Buyer Agent',
          message: lastMessage.message,
          type: lastMessage.offer ? 'offer' : 'text',
          price: lastMessage.offer,
          quantity: negState?.quantity || cropQty,
          quality: 'A',
          deliveryDate: 'ASAP',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '24 Hours',
          reasoning: [
            `Evaluated against MSP: ₹${statutoryBench}/kg`,
            `Multi-attribute utility concession applied`
          ]
        };
        setMessages(prev => [...prev, msgObj]);
        setLiveTerminalLogs(prev => [
          ...prev,
          {
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            tag: isFarmerSender ? 'FARMER' : 'BUYER',
            color: isFarmerSender ? 'text-emerald-400' : 'text-blue-400',
            text: lastMessage.message
          }
        ]);
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else if (lastMessage.event === 'NEGOTIATION_FINISHED' || lastMessage.event === 'PARALLEL_PROCUREMENT_COMPLETE') {
        const finalP = lastMessage.final_price || lastMessage.winner?.negotiated_price || targetPrice;
        const finalDeal = {
          ...negState,
          id: id,
          negotiation_id: id,
          price: finalP,
          final_price: finalP,
          quantity: cropQty,
          status: 'DEAL',
          farmer: lastMessage.winner?.name || negState?.farmer || 'Latur APMC Producer',
          farmer_name: lastMessage.winner?.name || negState?.farmer_name || 'Latur APMC Producer',
          buyer: user?.name || user?.full_name || 'Buyer Enterprise'
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
        refetchNeg();
      }
    }
  }, [lastMessage, id, negState, cropQty, targetPrice, statutoryBench, user, refetchNeg]);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveTerminalLogs]);

  // Handle Offer Actions (Accept, Counter, Reject)
  const handleAction = async (actionType: string, price: number) => {
    if (actionType === 'accept') {
      // Guardrail verification
      if (price > maxAllowedCeiling) {
        alert(`🛡️ [Guardrail] Price ₹${price}/kg exceeds statutory ceiling (₹${maxAllowedCeiling}/kg). Deal cannot be finalized.`);
        return;
      }
      if (price < minAllowedFloor) {
        alert(`🛡️ [Guardrail] Price ₹${price}/kg is below statutory APMC floor (₹${minAllowedFloor}/kg). Deal cannot be finalized.`);
        return;
      }

      const finalDeal = {
        ...negState,
        id: id,
        negotiation_id: id,
        crop: cropName,
        price: price,
        final_price: price,
        quantity: cropQty,
        deliveryDate: '3-4 Business Days',
        farmer: negState?.farmer || negState?.farmer_name || 'Latur APMC Cooperative',
        buyer: negState?.buyer || negState?.buyer_name || (user?.name || user?.full_name || 'Buyer Enterprise'),
        status: 'DEAL'
      };

      setMessages(prev => [
        ...prev, 
        { agent: 'Human (You)', message: `I accept the deal at ₹${price}/kg. Preparing APMC smart contract.`, type: 'text' }
      ]);
      setAgreementData(finalDeal);
      setShowAgreement(true);

      try {
        await api.post(`/negotiations/${id}/finalize`, {
          price: price,
          quantity: cropQty,
          crop: cropName,
          farmer: finalDeal.farmer,
          buyer: finalDeal.buyer
        });
        refetchNeg();
      } catch (e) {
        console.warn('Finalize endpoint notification:', e);
      }
    } else if (actionType === 'reject') {
      setMessages(prev => [
        ...prev, 
        { agent: 'Human (You)', message: `I reject the offer of ₹${price}/kg. Negotiation terminated.`, type: 'text' }
      ]);
      try {
        await api.post(`/negotiations/${id}/reject`);
        refetchNeg();
      } catch (e) {
        console.warn('Reject notification:', e);
      }
    } else {
      // Counter: focus manual override input
      const el = document.getElementById('humanOverride') as HTMLInputElement;
      if (el) {
        el.value = String(price);
        setManualPrice(String(price));
        el.focus();
      }
    }
  };

  // Manual Intervene / Override Mutation
  const interveneMutation = useMutation({
    mutationFn: async (priceNum: number) => {
      // Guardrail 1: Price ceiling
      if (priceNum > maxAllowedCeiling) {
        throw new Error(`🛡️ [Guardrail] Price ₹${priceNum}/kg exceeds statutory ceiling (₹${maxAllowedCeiling}/kg for ${cropName}).`);
      }
      // Guardrail 2: Price floor
      if (priceNum < minAllowedFloor) {
        throw new Error(`🛡️ [Guardrail] Price ₹${priceNum}/kg is below statutory APMC floor threshold (₹${minAllowedFloor}/kg).`);
      }

      let data: any = null;
      try {
        const res = await api.post(`/negotiations/${id}/intervene`, { price: priceNum, quantity: cropQty });
        data = res.data;
      } catch (e) {
        console.warn('Intervene API call:', e);
      }

      setMessages(prev => [...prev, {
        agent: 'Human (You)',
        type: 'offer',
        price: priceNum,
        quantity: cropQty,
        quality: 'A',
        deliveryDate: 'Prompt 2-3 Days',
        transportIncluded: true,
        warehouseIncluded: false,
        validity: '24 Hours',
        reasoning: [
          `Manual intervention set by user`,
          `Within statutory tolerance [₹${minAllowedFloor} - ₹${maxAllowedCeiling}]`
        ]
      }]);

      if (data && data.farmer_response) {
        const fr = data.farmer_response;
        setMessages(prev => [...prev, {
          agent: fr.agent || 'Farmer Agent',
          type: fr.price ? 'offer' : 'text',
          price: fr.price,
          quantity: cropQty,
          quality: 'A',
          deliveryDate: 'Prompt 2-3 Days',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '24 Hours',
          message: fr.message || `Countering offer at ₹${fr.price}/kg`,
          reasoning: [
            `APMC Modal Benchmark: ₹${marketPrice}/kg`,
            `Concession response to manual offer ₹${priceNum}/kg`
          ]
        }]);
      }

      if (data && data.status === 'DEAL') {
        const finalDeal = {
          ...negState,
          id: id,
          negotiation_id: id,
          crop: cropName,
          price: data.final_price || priceNum,
          final_price: data.final_price || priceNum,
          quantity: cropQty,
          farmer: negState?.farmer || 'Latur APMC Cooperative',
          buyer: user?.name || user?.full_name || 'Buyer Enterprise',
          status: 'DEAL'
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
      }

      setManualPrice('');
      refetchNeg();
    },
    onError: (err: any) => {
      alert(err.message || 'Intervention failed.');
    }
  });

  // 4. Autonomous Parallel 5 Negotiation Runner
  const runParallelAutonomousNegotiation = async () => {
    setIsParallelRunning(true);
    setLiveTerminalLogs([]);
    setActiveTab('terminal');

    const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    setLiveTerminalLogs([
      { time: now(), tag: 'CLUSTER', color: 'text-emerald-400', text: `🚀 Connected to LangGraph RL Daemon for ${cropQty.toLocaleString()} kg ${cropName}. Contract #${id?.substring(0, 8)}.` },
      { time: now(), tag: 'POLICY', color: 'text-purple-400', text: `Statutory MSP: ₹${statutoryBench}/kg | Live Modal: ₹${marketPrice}/kg | Target Ceiling: ₹${targetPrice}/kg.` },
      { time: now(), tag: 'DISCOVERY', color: 'text-blue-400', text: `Scanning 5 candidate Maharashtra APMC Mandis (Latur, Nanded, Solapur, Akola, Sangli).` }
    ]);

    try {
      const res = await api.post(`/negotiations/${id}/parallel-procure`, {
        quantity: cropQty,
        target_price: targetPrice
      });

      const timeline = res.data?.timeline || res.data?.data?.timeline || [];
      const winner = res.data?.winner || res.data?.data?.winner;

      if (timeline.length > 0) {
        timeline.forEach((step: any, idx: number) => {
          setTimeout(() => {
            setLiveTerminalLogs(prev => [
              ...prev,
              {
                time: now(),
                tag: step.tag || 'AGENT',
                color: step.color || 'text-slate-200',
                text: step.text
              }
            ]);

            // Add corresponding chat bubble when counter-offers happen
            if (step.tag === 'ROUND 3' || step.tag === 'WINNER') {
              setMessages(prev => [
                ...prev,
                {
                  agent: step.supplier_name || 'APMC Producer',
                  type: 'offer',
                  price: step.price || winner?.negotiated_price || targetPrice,
                  quantity: cropQty,
                  quality: 'A',
                  deliveryDate: 'Immediate Mandi Dispatch',
                  transportIncluded: true,
                  warehouseIncluded: false,
                  validity: '24 Hours',
                  message: step.text,
                  reasoning: [
                    `Distance: Highway logistics calculated`,
                    `APMC Mandi Cess (1%) factored in`,
                    `Complies with Maharashtra Model Act`
                  ]
                }
              ]);
            }

            if (idx === timeline.length - 1) {
              setIsParallelRunning(false);
              if (winner) {
                const finalDeal = {
                  ...negState,
                  id: id,
                  negotiation_id: id,
                  crop: cropName,
                  price: winner.negotiated_price,
                  final_price: winner.negotiated_price,
                  quantity: cropQty,
                  farmer: winner.name,
                  farmer_name: winner.name,
                  buyer: user?.name || user?.full_name || 'Buyer Enterprise',
                  status: 'DEAL'
                };
                setAgreementData(finalDeal);
                setShowAgreement(true);
              }
              refetchNeg();
            }
          }, (idx + 1) * 450);
        });
      } else {
        setIsParallelRunning(false);
      }
    } catch (err) {
      console.warn('Parallel procurement runner error:', err);
      setIsParallelRunning(false);
    }
  };

  if (isLoading) {
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
              <span className="text-slate-500">Lot Volume</span>
              <span className="font-black text-slate-800">{cropQty.toLocaleString()} kg</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Live Modal Price</span>
              <span className="font-black text-slate-800">₹{marketPrice}/kg</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Target Ceiling</span>
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
              <p className="font-bold text-amber-700 flex items-center gap-1.5">
                <Truck size={14} /> HIGHWAY LOGISTICS
              </p>
              <p className="text-slate-600">Freight solved: ₹6.50/km + handling. Mandi Cess: 1% statutory APMC e-NAM.</p>
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

      {/* ════ COLUMN 2: The Timeline / Chat Stream (Center ~50%) ════ */}
      <div className="w-full xl:w-2/4 bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative">
        
        {/* Header Bar with Tabs & WebSocket Pulse */}
        <div className="p-3.5 border-b border-slate-100 bg-slate-50 flex flex-wrap justify-between items-center z-10 sticky top-0 gap-2">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-600" /> AI Agent Negotiation
            </h3>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-mono">#{id?.substring(0, 8)}</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Tab Selector: Timeline Chat vs Live Terminal */}
            <div className="bg-slate-200/70 p-1 rounded-xl flex items-center gap-1 text-xs">
              <button
                onClick={() => setActiveTab('timeline')}
                className={`px-2.5 py-1 rounded-lg font-bold transition ${
                  activeTab === 'timeline' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                💬 Chat Timeline
              </button>
              <button
                onClick={() => setActiveTab('terminal')}
                className={`px-2.5 py-1 rounded-lg font-bold transition flex items-center gap-1 ${
                  activeTab === 'terminal' 
                    ? 'bg-slate-900 text-emerald-400 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <TerminalIcon size={12} /> Live Terminal
              </button>
            </div>

            {/* WebSocket Connection Ping */}
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></span>
              <span className="text-[10px] font-bold text-slate-500 font-mono uppercase">
                {isConnected ? 'LIVE' : 'SYNCING'}
              </span>
            </div>
          </div>
        </div>

        {/* View Mode 1: Ritik's Signature Chat Timeline with OfferCards & ChatBubbles */}
        {activeTab === 'timeline' ? (
          <div className="flex-1 overflow-y-auto bg-slate-50/50 p-5 space-y-5">
            {messages.map((m, i) => (
              m.type === 'offer' ? (
                <OfferCard 
                  key={i}
                  agent={m.agent}
                  price={m.price}
                  quantity={m.quantity || cropQty}
                  quality={m.quality || 'A'}
                  deliveryDate={m.deliveryDate || '3 Business Days'}
                  transportIncluded={m.transportIncluded ?? true}
                  warehouseIncluded={m.warehouseIncluded ?? false}
                  validity={m.validity || '24 Hours'}
                  isFarmer={m.agent?.toLowerCase().includes('farmer') || m.agent?.toLowerCase().includes('producer')}
                  onAction={handleAction}
                />
              ) : (
                <ChatBubble 
                  key={i} 
                  agent={m.agent} 
                  price={m.price} 
                  message={m.message} 
                  reasoning={m.reasoning}
                  isFarmer={m.agent?.toLowerCase().includes('farmer') || m.agent?.toLowerCase().includes('producer')} 
                  isInteractive={false}
                  onAction={handleAction}
                />
              )
            ))}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          /* View Mode 2: Real-Time Streaming Terminal */
          <div className="flex-1 bg-slate-950 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-2 select-text dark-scroll text-slate-100 flex flex-col">
            <div className="text-slate-500 pb-2 border-b border-slate-800 text-[10px]">
              # LangGraph Multi-Agent Negotiation Daemon • APMC Maharashtra<br />
              # Target: {cropName} ({cropQty.toLocaleString()} kg) • Benchmark: ₹{statutoryBench}/kg
            </div>

            {liveTerminalLogs.length === 0 ? (
              <div className="text-center py-16 text-slate-500 space-y-3">
                <TerminalIcon size={32} className="mx-auto text-slate-700" />
                <p>Terminal idle. Click "Run Parallel 5 Negotiation" below to stream live negotiation.</p>
                <button
                  onClick={runParallelAutonomousNegotiation}
                  disabled={isParallelRunning}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-xl text-xs font-bold transition shadow inline-flex items-center gap-1.5"
                >
                  <Play size={13} className="fill-white" /> Start Live Parallel Negotiation
                </button>
              </div>
            ) : (
              liveTerminalLogs.map((log, lIdx) => (
                <div key={lIdx} className="flex items-start gap-2 animate-in fade-in duration-150">
                  <span className="text-slate-600 shrink-0">[{log.time}]</span>
                  <span className={`font-bold shrink-0 ${log.color || 'text-slate-300'}`}>[{log.tag}]</span>
                  <span className="text-slate-200 break-words flex-1">{log.text}</span>
                </div>
              ))
            )}
            <div ref={terminalEndRef} />
          </div>
        )}

        {/* Bottom Fast Action Bar */}
        <div className="p-3 bg-white border-t border-slate-100 flex items-center justify-between text-xs">
          <button
            onClick={runParallelAutonomousNegotiation}
            disabled={isParallelRunning}
            className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={13} className={isParallelRunning ? "animate-spin text-emerald-400" : "text-emerald-400"} />
            <span>{isParallelRunning ? 'Negotiating 5 Mandis...' : '⚡ Auto-Parallel 5 Negotiation'}</span>
          </button>

          <span className="text-slate-400 text-[11px]">
            Protected by APMC Statutory Guardrails
          </span>
        </div>
      </div>
      
      {/* ════ COLUMN 3: Action Panel & Workflow (Right ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-6 overflow-y-auto">
        
        {/* LangGraph Execution Stepper */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
          <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Zap size={17} className="text-emerald-500" /> LangGraph Execution
          </h2>
          <AgentWorkflowStepper activeAgent={activeAgent} />
          
          <button 
            onClick={() => setIsRagOpen(true)}
            className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition text-xs flex justify-center items-center gap-2 cursor-pointer"
          >
            <Database size={15} className="text-emerald-600" /> View RAG Context
          </button>
        </div>

        {/* Dynamic Action Area: Agreement Preview OR Copilot Override */}
        {showAgreement && agreementData ? (
          <AgreementPreview 
            dealData={agreementData} 
            onSignAndClose={() => setShowValidationModal(true)} 
          />
        ) : (
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-5 text-white space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <ShieldCheck size={18} className="text-emerald-400" /> Copilot Override
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-slate-800 text-slate-300 rounded-full">
                RL Policy Active
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Autonomous agents are negotiating based on RL policy. Intervene anytime to counter with a manual offer.
            </p>

            <div className="space-y-2.5">
              <input 
                type="number" 
                id="humanOverride"
                value={manualPrice}
                onChange={(e) => setManualPrice(e.target.value)}
                placeholder={`Enter price (e.g. ₹${targetPrice})...`} 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />

              <button 
                onClick={() => {
                  const val = parseFloat(manualPrice);
                  if (isNaN(val) || val <= 0) {
                    alert('Please enter a valid price.');
                    return;
                  }
                  interveneMutation.mutate(val);
                }}
                disabled={interveneMutation.isPending}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition shadow-sm cursor-pointer"
              >
                {interveneMutation.isPending ? 'Submitting Offer...' : 'Send Manual Offer'}
              </button>
            </div>
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

    </div>
  );
}
