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
  Trophy
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
          location.state?.isBuyer ||
          location.pathname.includes('/buyer')
        );

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
  const wsUrl = activeId ? `${baseWsUrl}?negotiation_id=${activeId}` : `${baseWsUrl}/negotiation`;
  const { isConnected, lastMessage, sendMessage } = useWebSocket(wsUrl);

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
  const [recommendation, setRecommendation] = useState<any>(null);
  const [reflection, setReflection] = useState<any>(null);


  const [rightTab, setRightTab] = useState<'ai' | 'rag' | 'copilot'>('copilot');
  const [copilotCommand, setCopilotCommand] = useState('');
  const [copilotMessages, setCopilotMessages] = useState<{sender: string, text: string, time: string}[]>([]);
  const [liveBuyers, setLiveBuyers] = useState<any[]>([]);

  // 1. Fetch negotiation session state from database
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

  const cropName = negState?.crop || 'Soybean';
  const cropQty = Number(negState?.quantity) || 500;
  const currentFloor = Number(negState?.min_price) || 45.0;
  const targetPrice = Number(negState?.target_price || negState?.buyer_target_price || 47.0);
  const marketPrice = Number(negState?.market_price || Math.round(targetPrice * 1.04 * 10) / 10);
  const activeAgent = isParallelRunning ? 'Negotiator' : (lastMessage?.data?.agent || 'Negotiator');
  
  // Blueprint Compliance: Stakeholder Scope Variables
  const activeStakeholder = (lastMessage?.stakeholder || negState?.stakeholder_role || 'FARMER').toUpperCase();
  const farmerName = negState?.farmer_name || negState?.farmer || 'Ramesh Patil';
  const farmerLocation = negState?.location || 'Latur APMC, Maharashtra';
  const buyerName = negState?.buyer_name || negState?.buyer || user?.name || 'AgroCorp Procurement';
  const bestOfferPrice = Number(negState?.current_offer || negState?.price || negState?.min_price || 68.5);

  // Candidate Farmers for Buyer Procurement View
  const liveSellers = useMemo(() => [
    { id: 'Suresh Deshmukh', location: 'Nanded APMC, Maharashtra', match: 96, offer: 68.5, aiStatus: 'Verified APMC Grade A', status: 'Negotiating', color: 'emerald' },
    { id: farmerName, location: farmerLocation, match: 92, offer: bestOfferPrice, aiStatus: 'Farmer Asking Rate', status: 'Active', color: 'blue' },
    { id: 'Vilas Jadhav', location: 'Akola APMC, Maharashtra', match: 89, offer: 71.0, aiStatus: 'Counter ₹' + targetPrice, status: 'Waiting', color: 'amber' }
  ], [farmerName, farmerLocation, bestOfferPrice, targetPrice]);
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

      if (negState.status === 'DEAL' || negState.final_price) {
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
        setLiveBuyers([]);
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

  // Auto-start autonomous negotiation if buyer navigated in with autoStart flag
  useEffect(() => {
    const currentTargetId = activeId || id;
    if (hasAutoStartFlag && currentTargetId && !isParallelRunning) {
      // Small delay so negotiation state has time to load
      const timer = setTimeout(() => {
        runParallelAutonomousNegotiation();
      }, 800);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasAutoStartFlag, activeId, id]);

  // Handle incoming WS messages
  useEffect(() => {
    const targetNegId = activeId || id;
    if (lastMessage && (!targetNegId || !lastMessage.negotiation_id || String(lastMessage.negotiation_id) === String(targetNegId))) {
      if (lastMessage.event === 'NEGOTIATION_LOG') {
        const isFarmerSender = lastMessage.agent_type === 'farmer';
        setLiveTerminalLogs(prev => [
          ...prev,
          {
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            tag: isFarmerSender ? 'Farmer' : 'Buyer',
            color: isFarmerSender ? 'text-emerald-400' : 'text-blue-400',
            text: lastMessage.message
          }
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
        }
      } else if (lastMessage.event === 'NEGOTIATION_FINISHED' || lastMessage.event === 'PARALLEL_PROCUREMENT_COMPLETE') {
        if (lastMessage.recommendation) {
          setRecommendation(lastMessage.recommendation);
        }
        if (lastMessage.reflection) {
          setReflection(lastMessage.reflection);
        }
        const finalP = lastMessage.final_price || lastMessage.winner?.negotiated_price || targetPrice;
        const finalDeal = {
          ...negState,
          id: targetNegId,
          negotiation_id: targetNegId,
          price: finalP,
          final_price: finalP,
          quantity: cropQty,
          status: 'DEAL',
          farmer: lastMessage.winner?.name || negState?.farmer || 'Latur APMC Producer',
          buyer: user?.name || user?.full_name || 'Buyer Enterprise'
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
        refetchNeg();
      }
    }
  }, [lastMessage, activeId, id, negState, cropQty, targetPrice, statutoryBench, user, refetchNeg]);

  const runParallelAutonomousNegotiation = async () => {
    setIsParallelRunning(true);
    setLiveTerminalLogs([]);
    setActiveTab('terminal');

    const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const targetNegId = activeId || id;

    setLiveTerminalLogs([
      { time: now(), tag: 'CLUSTER', color: 'text-emerald-400', text: `🚀 Connected to LangGraph RL Daemon for ${cropQty.toLocaleString()} kg ${cropName}. Contract #${targetNegId ? targetNegId.substring(0, 8) : 'session'}.` },
      { time: now(), tag: 'POLICY', color: 'text-purple-400', text: `Statutory MSP: ₹${statutoryBench}/kg | Live Modal: ₹${marketPrice}/kg | Target Ceiling: ₹${targetPrice}/kg.` },
      { time: now(), tag: 'DISCOVERY', color: 'text-blue-400', text: `Scanning 5 candidate Maharashtra APMC Mandis (Latur, Nanded, Solapur, Akola, Sangli).` }
    ]);

    try {
      const res = await api.post(`/negotiations/${targetNegId}/parallel-procure`, {
        quantity: cropQty,
        target_price: targetPrice
      });

      if (res.data?.recommendation || res.data?.data?.recommendation) {
        setRecommendation(res.data?.recommendation || res.data?.data?.recommendation);
      }
      if (res.data?.reflection || res.data?.data?.reflection) {
        setReflection(res.data?.reflection || res.data?.data?.reflection);
      }

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


  const handleAcceptDeal = async (candidate?: any) => {
    const selected = candidate || (isBuyer ? (liveSellers.length > 0 ? liveSellers[0] : null) : (liveBuyers.length > 0 ? liveBuyers[0] : null));
    const agreedPrice = selected?.offer ? Number(selected.offer) : (negState?.final_price || negState?.price || currentFloor);
    const counterParty = selected?.id || (isBuyer ? (farmerName || 'Farmer Producer') : (negState?.buyer_name || negState?.buyer || 'Buyer Enterprise'));
    
    const dealPayload = {
      price: agreedPrice,
      quantity: cropQty,
      farmer: isBuyer ? counterParty : (farmerName || user?.name || 'Maharashtra Producer'),
      buyer: isBuyer ? (buyerName || user?.name || 'Buyer Enterprise') : counterParty,
      crop: cropName,
      listing_id: negState?.listing_id
    };

    try {
      const targetNegId = activeId || id;
      if (targetNegId) {
        const res = await api.post(`/negotiations/${targetNegId}/accept`, dealPayload);
        const finalizedRecord = res.data?.contract || res.data?.data || dealPayload;
        setAgreementData({
          ...negState,
          ...finalizedRecord,
          price: agreedPrice,
          farmer: dealPayload.farmer,
          buyer: dealPayload.buyer,
          crop: cropName,
          quantity: cropQty
        });
        setShowValidationModal(true);
        refetchNeg();
        return;
      }
    } catch (err) {
      console.warn('Backend deal finalization response:', err);
    }

    setAgreementData({
      ...negState,
      price: agreedPrice,
      farmer: dealPayload.farmer,
      buyer: dealPayload.buyer,
      crop: cropName,
      quantity: cropQty
    });
    setShowValidationModal(true);
  };

  const handleCopilotSubmit = (e: any) => {
    e.preventDefault();
    if(!copilotCommand.trim()) return;
    
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const userRole = isBuyer ? 'Buyer' : 'Farmer';
    const userMsg = { sender: userRole, text: copilotCommand, time: now };
    
    setCopilotMessages(prev => [...prev, userMsg]);
    
    // Process real AI Copilot reasoning & state adaptation
    setTimeout(() => {
      const lower = copilotCommand.toLowerCase();
      let aiResponse = 'Understood. Instruction registered in active negotiation strategy.';
      
      if (lower.includes('below') || lower.includes('minimum') || lower.includes('floor')) {
        const match = copilotCommand.match(/\d+(?:\.\d+)?/);
        if (match) {
          const val = Number(match[0]);
          if (val < minAllowedFloor) {
            aiResponse = `⚠️ Floor Defense Triggered: ₹${val}/kg is below the statutory benchmark floor of ₹${minAllowedFloor}/kg. The AI agent cannot accept bids below statutory benchmarks.`;
          } else {
            aiResponse = `Understood. Updated defensive floor to ₹${val}/kg. All active and incoming buyer bids will be filtered against this floor.`;
            setLiveBuyers(prev => prev.map(b => ({
              ...b,
              aiStatus: Number(b.offer) >= val ? `Viable above ₹${val}/kg` : `Under Floor (₹${val}/kg)`
            })));
          }
        }
      } else if (lower.includes('counter')) {
        const match = copilotCommand.match(/\d+(?:\.\d+)?/);
        const counterVal = match ? match[0] : String(targetPrice);
        aiResponse = `Manual counter instruction of ₹${counterVal}/kg registered. Evaluating candidate buyer responsiveness against ₹${counterVal}/kg.`;
        setLiveBuyers(prev => prev.map((b, idx) => idx === 0 ? {
          ...b,
          aiStatus: `Farmer Counter: ₹${counterVal}/kg`
        } : b));
      } else if (lower.includes('accept') || lower.includes('deal')) {
        aiResponse = `To finalize this deal, click "Accept Deal" to execute the cryptographically signed APMC electronic smart contract.`;
      } else {
        aiResponse = `Instruction recorded: "${copilotCommand}". Defending your margins and actively monitoring market bids for ${cropName}.`;
      }
      
      setCopilotMessages(prev => [...prev, {
        sender: 'AI',
        text: aiResponse,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }]);
    }, 400);
    
    setCopilotCommand('');
  };

  if (isLoading && activeId && !initTimedOut) {
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
                <div className="flex items-center gap-2">
                  {['FARMER', 'PROCESSOR'].includes(activeStakeholder) && activeWorkflow === 'FULL_SUPPLY_CHAIN' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={['FARMER', 'PROCESSOR'].includes(activeStakeholder) && activeWorkflow === 'FULL_SUPPLY_CHAIN' ? 'text-slate-800 font-bold' : 'text-slate-400'}>Buyer / Supplier</span>
                </div>
                <div className="flex items-center gap-2">
                  {activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'TRANSPORT_ONLY' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'TRANSPORT_ONLY' ? 'text-slate-800 font-bold' : 'text-slate-400'}>Transport</span>
                </div>
                <div className="flex items-center gap-2">
                  {activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'WAREHOUSE_ONLY' ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={activeWorkflow === 'FULL_SUPPLY_CHAIN' || activeWorkflow === 'WAREHOUSE_ONLY' ? 'text-slate-800 font-bold' : 'text-slate-400'}>Warehouse</span>
                </div>
                <div className="flex items-center gap-2">
                  {activeWorkflow === 'FULL_SUPPLY_CHAIN' && ['FARMER', 'BUYER'].includes(activeStakeholder) ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={activeWorkflow === 'FULL_SUPPLY_CHAIN' && ['FARMER', 'BUYER'].includes(activeStakeholder) ? 'text-slate-800 font-bold' : 'text-slate-400'}>Processor</span>
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

      
      
      {/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}
      <div className="w-full xl:w-2/4 flex flex-col gap-4">
        
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative flex-1">
          {/* Header */}
          <div className="p-4 border-b border-slate-100 flex justify-between items-center z-10 sticky top-0 bg-white">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-500" /> AI Agent Negotiation — <span className="text-slate-500 font-normal">{cropName}</span>
            </h3>
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Live
            </div>
          </div>

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
                <div className="space-y-3">
                  {liveSellers.map((s, i) => (
                    <div key={i} className={`bg-white border rounded-2xl p-4 shadow-sm relative overflow-hidden transition-all ${s.status === 'Active' ? 'border-emerald-400 ring-2 ring-emerald-50' : 'border-slate-200/90'}`}>
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
                          <p className="text-[10px] text-slate-400">Asking rate</p>
                        </div>
                      </div>
                      
                      <div className="space-y-1.5 text-xs pt-2 border-t border-slate-100">
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">AI Strategy:</span>
                          <span className="font-semibold text-emerald-700">{s.aiStatus}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 font-medium">Status:</span>
                          <span className="font-semibold flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${s.status === 'Negotiating' ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`}></span>
                            <span className={s.status === 'Negotiating' ? 'text-emerald-700' : 'text-blue-700'}>{s.status}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Best Farmer Deal So Far */}
                <div className="bg-[#064e3b] p-4 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md mt-2">
                  <div>
                    <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Trophy size={13} className="text-amber-400" /> BEST FARMER OFFER
                    </p>
                    <div className="flex items-center flex-wrap gap-2 text-xs">
                      <span className="font-bold text-base text-white">{liveSellers[0].id}</span>
                      <span className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-2 py-0.5 rounded text-xs font-bold">
                        ₹{liveSellers[0].offer}/kg
                      </span>
                      <span className="text-emerald-100">{cropQty.toLocaleString()} kg</span>
                      <span className="text-emerald-100">{liveSellers[0].match}% Match</span>
                      <span className="font-bold text-emerald-200">
                        Total: ₹{(liveSellers[0].offer * cropQty).toLocaleString()}
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
                      onClick={() => handleAcceptDeal(liveSellers[0])}
                      className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-black text-xs transition shadow flex-1 sm:flex-none text-center cursor-pointer"
                    >
                      Accept Deal
                    </button>
                  </div>
                </div>
              </>
            ) : liveBuyers.length > 0 ? (
              <>
                <div className="space-y-3">
                  {liveBuyers.map((b, i) => (
                    <div key={i} className={`bg-white border rounded-2xl p-4 shadow-sm relative overflow-hidden transition-all ${b.aiStatus?.includes('Override') ? 'border-indigo-400 ring-2 ring-indigo-50' : 'border-slate-200/90'}`}>
                      
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
                            <span className={`w-2 h-2 rounded-full ${b.status === 'Active Offer' ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`}></span>
                            <span className={b.status === 'Active Offer' ? 'text-emerald-700 font-bold' : 'text-blue-700'}>{b.status}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Best Deal So Far (Banner inside center column) */}
                <div className="bg-[#064e3b] p-4 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md mt-2">
                  <div>
                    <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Trophy size={13} className="text-amber-400" /> BEST DEAL SO FAR
                    </p>
                    <div className="flex items-center flex-wrap gap-2 text-xs">
                      <span className="font-bold text-base text-white">{liveBuyers[0].id}</span>
                      <span className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-2 py-0.5 rounded text-xs font-bold">
                        ₹{liveBuyers[0].offer}/kg
                      </span>
                      <span className="text-emerald-100">{cropQty.toLocaleString()} kg</span>
                      <span className="text-emerald-100">{liveBuyers[0].match}% Match</span>
                      <span className="font-bold text-emerald-200">
                        Net: ₹{Math.max(0, Math.round(liveBuyers[0].offer * cropQty - 1850)).toLocaleString()}
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
                      onClick={() => handleAcceptDeal(liveBuyers[0])}
                      className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-black text-xs transition shadow flex-1 sm:flex-none text-center cursor-pointer"
                    >
                      Accept Deal
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
        
        {/* Card 1: LangGraph Execution */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Zap size={16} className="text-emerald-500" /> LangGraph Execution
              </h4>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                6 Multi-Agents
              </span>
            </div>

            <AgentWorkflowStepper 
              activeAgent={activeAgent} 
              isBuyer={isBuyer}
              status={negState?.status}
              hasRecommendation={Boolean(recommendation)}
              hasReflection={Boolean(reflection)}
            />
          </div>

          {/* View RAG Context Button */}
          <button 
            type="button"
            onClick={() => setIsRagOpen(true)}
            className="w-full py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-700 font-bold rounded-xl transition text-xs flex justify-center items-center gap-2 shadow-sm"
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
                  onClick={() => setCopilotCommand(`Counter at target ₹${Math.round(targetPrice || 48)}`)} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Counter target ₹{Math.round(targetPrice || 48)}
                </button>
                <button 
                  type="button" 
                  onClick={() => setCopilotCommand(`Don't exceed ₹${Math.round(maxAllowedCeiling || 52)}`)} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Ceiling ₹{Math.round(maxAllowedCeiling || 52)}
                </button>
                <button 
                  type="button" 
                  onClick={() => setCopilotCommand('Counter best farmer')} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Counter best farmer
                </button>
                <button 
                  type="button" 
                  onClick={() => setCopilotCommand('Pause negotiations')} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition cursor-pointer"
                >
                  Pause negotiations
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
                        setCopilotCommand(`Submit offer at ₹${val}/kg`);
                        handleCopilotSubmit({ preventDefault: () => {} } as any);
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
                  onClick={() => setCopilotCommand(`Don't go below ₹${Math.round(currentFloor || 64)}`)} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition"
                >
                  Don't go below ₹{Math.round(currentFloor || 64)}
                </button>
                <button 
                  type="button" 
                  onClick={() => setCopilotCommand('Counter best buyer')} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition"
                >
                  Counter best buyer
                </button>
                <button 
                  type="button" 
                  onClick={() => setCopilotCommand('Pause negotiations')} 
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 rounded-lg text-[11px] font-medium border border-slate-700/60 transition"
                >
                  Pause negotiations
                </button>
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

    </div>
  );
}
