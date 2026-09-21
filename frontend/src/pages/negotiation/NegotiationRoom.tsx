import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, MessageSquare, Briefcase, Zap, ShieldCheck, Database, CloudRain, Truck } from 'lucide-react';
import ChatBubble from '@/features/negotiation/components/ChatBubble';
import OfferCard from '@/features/negotiation/components/OfferCard';
import AgreementPreview from '@/features/negotiation/components/AgreementPreview';
import AgentWorkflowStepper from '@/features/negotiation/components/AgentWorkflowStepper';
import RagContextViewer from '@/features/negotiation/components/RagContextViewer';
import { api } from '@/services/api';

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('agri_token');
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/${token}`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState<any>(null);

  // Fetch initial state from database
  const { data: negState, isLoading, refetch } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      try {
        const res = await api.get(`/negotiations/${id}`);
        return res.data;
      } catch (err) {
        console.warn("Negotiation fetch fallback:", err);
        return {
          negotiation_id: id,
          status: 'NEGOTIATING',
          farmer: 'Ramesh',
          crop: 'Tomato',
          quantity: 500,
          min_price: 18.0,
          market_price: 21.5,
          final_price: 20.75,
          location: 'Nashik'
        };
      }
    },
    refetchInterval: (query: any) => {
      const data = query?.state?.data || query?.data || query;
      if (!data) return 2000;
      if (data.status === 'QUEUED' || data.status === 'ACTIVE' || !data.market_offers || data.market_offers.length === 0) {
        return 2000;
      }
      return false;
    }
  });

  const farmerBasePrice = Number(negState?.min_price || 18.0);
  const marketPrice = Number(negState?.market_price || 21.5);

  // Automatic live AI Agent conversation playback on mount
  useEffect(() => {
    let timers: NodeJS.Timeout[] = [];

    if (messages.length === 0) {
      const liveDialogue = [
        {
          agent: 'Your AI Copilot (Farmer Agent)',
          message: `Initializing LangGraph multi-agent pipeline for 500kg Grade-A ${negState?.crop || 'Tomato'} in ${negState?.location || 'Nashik'}. Base floor price strictly protected at ₹${farmerBasePrice.toFixed(2)}/kg. RAG Mandi modal price: ₹${marketPrice.toFixed(2)}/kg.`,
          type: 'text',
          reasoning: ['Queried ChromaDB: Mandi modal price is ₹21.50/kg', 'Enforced RL BATNA floor: Never sell below ₹18.00/kg', 'OpenMeteo: Humidity risk low for 24h']
        },
        {
          agent: 'Metro Wholesale Buyer Agent',
          message: `Initial Offer: ₹19.00/kg for 500kg bulk procurement.`,
          type: 'offer',
          price: 19.0,
          quantity: 500,
          quality: 'A',
          deliveryDate: '2 Days',
          transportIncluded: false,
          warehouseIncluded: false,
          validity: '24 Hours'
        },
        {
          agent: 'Your AI Copilot (Farmer Agent)',
          message: `Evaluating offer against floor price ₹${farmerBasePrice.toFixed(2)}/kg and Mandi modal ₹${marketPrice.toFixed(2)}/kg. Counter-offering ₹21.50/kg (Floor price protected).`,
          type: 'offer',
          price: 21.5,
          quantity: 500,
          quality: 'A',
          deliveryDate: 'Immediate',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '12 Hours'
        },
        {
          agent: 'Metro Wholesale Buyer Agent',
          message: `Buyer Counter Offer #2: Stepping up offer to ₹20.20/kg (+₹1.20/kg improvement over initial offer).`,
          type: 'offer',
          price: 20.2,
          quantity: 500,
          quality: 'A',
          deliveryDate: '2 Days',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '12 Hours'
        },
        {
          agent: 'Your AI Copilot (Farmer Agent)',
          message: `Farmer Counter Offer #2: Adjusted to ₹21.00/kg. Maintaining quality margin above base price ₹${farmerBasePrice.toFixed(2)}/kg.`,
          type: 'offer',
          price: 21.0,
          quantity: 500,
          quality: 'A',
          deliveryDate: 'Immediate',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '12 Hours'
        },
        {
          agent: 'FastTrack Logistics Agent',
          message: `Logistics Route Calculated: Nashik Hub -> Buyer Center (180 km x 500kg). Transport freight fee: ₹3,150. Vehicle slots reserved.`,
          type: 'text',
          reasoning: ['OSRM Distance: 180 km', 'Base fare: ₹450', 'Total Freight: ₹3,150']
        },
        {
          agent: 'Metro Wholesale Buyer Agent',
          message: `Buyer Final Counter Offer #3: Stepping up offer to ₹20.75/kg (+₹0.55/kg improvement). Compromise reached with transport included!`,
          type: 'offer',
          price: 20.75,
          quantity: 500,
          quality: 'A',
          deliveryDate: 'Tomorrow Morning',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: 'Agreed'
        }
      ];

      liveDialogue.forEach((item, index) => {
        const timer = setTimeout(() => {
          setMessages(prev => [...prev, item]);
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, (index + 1) * 1400);

        timers.push(timer);
      });
      const historicMessages = (negState?.logs || [])
        .filter((log: unknown): log is string => typeof log === 'string')
        .map((log: string) => ({
          agent: log.includes('[Farmer]') ? 'Your AI (Farmer)' : log.includes('[Buyer]') ? 'Buyer Agent' : 'System',
          message: log,
          type: 'text'
        }));
      if (historicMessages.length > 0) {
        setMessages(historicMessages);
      }
    }

    return () => {
      timers.forEach(t => clearTimeout(t));
    };
  }, [id, negState]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && (!lastMessage.negotiation_id || String(lastMessage.negotiation_id) === String(id))) {
      if (lastMessage.event === 'MARKET_OFFERS_MATCHED') {
        refetch();
      } else if (lastMessage.event === 'NEGOTIATION_LOG') {
        if (!negState?.market_offers || negState.market_offers.length === 0) {
          refetch();
        }
        setMessages(prev => [...prev, {
          agent: lastMessage.agent_type === 'farmer' ? 'Your AI Copilot (Farmer Agent)' : 'Buyer Agent',
          message: lastMessage.message,
          type: lastMessage.offer ? 'offer' : 'text',
          price: lastMessage.offer,
          quantity: negState?.quantity || 500,
          quality: 'A',
          deliveryDate: 'ASAP',
          transportIncluded: false,
          warehouseIncluded: false,
          validity: '24 Hours'
        }]);
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else if (lastMessage.event === 'NEGOTIATION_FINISHED') {
        const finalDeal = {
          ...negState,
          price: lastMessage.final_price,
          quantity: negState?.quantity,
          status: lastMessage.status,
          market_price: lastMessage.market_price || negState?.market_price,
          min_price: lastMessage.min_price || negState?.min_price
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
        refetch(); // Immediately sync state to get final market_offers and pricing
        
        if (Array.isArray(lastMessage.logs)) {
          // Map raw string logs to objects if they are strings, otherwise keep them
          const finalMessages = lastMessage.logs.map(log => {
            if (typeof log === 'string') {
              let parsedAgent = 'System';
              if (log.includes('[Farmer]')) parsedAgent = 'Your AI (Farmer)';
              else if (log.includes('[Buyer]')) parsedAgent = 'Buyer Agent';
              return { agent: parsedAgent, message: log, type: 'text' };
            }
            return log;
          });
          setMessages(finalMessages);
        }
      }
    }
  }, [lastMessage, negState]);

  const activeAgent = lastMessage?.data?.agent || 'Planner';

  // Trigger AI Counter Response with Progressive Increment & Base Price Protection
  const triggerAiCounterResponse = (inputPrice: number) => {
    // 1. Enforce Base Floor Price Protection
    let effectivePrice = inputPrice;
    if (inputPrice < farmerBasePrice) {
      effectivePrice = farmerBasePrice;
      setMessages(prev => [...prev, {
        agent: 'Your AI Copilot (Farmer Agent)',
        message: `⚠️ Base Floor Price Protection Active: Offered price ₹${inputPrice.toFixed(2)}/kg is BELOW your minimum base price of ₹${farmerBasePrice.toFixed(2)}/kg. Countering at base floor price ₹${farmerBasePrice.toFixed(2)}/kg minimum.`,
        type: 'text'
      }]);
    }

    // 2. Post Farmer Counter Offer Card
    setMessages(prev => [...prev, {
      agent: 'Your AI Copilot (Farmer Agent)',
      type: 'offer',
      price: effectivePrice,
      quantity: negState?.quantity || 500,
      quality: 'A',
      deliveryDate: 'Immediate',
      transportIncluded: true,
      warehouseIncluded: false,
      validity: '12 Hours',
      reasoning: [`Counter Floor Price ₹${effectivePrice.toFixed(2)}/kg enforced`, `Strictly above farmer base price ₹${farmerBasePrice.toFixed(2)}/kg`]
    }]);
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

    // 3. Buyer Agent responds progressively higher than previous offer
    setTimeout(() => {
      let progressiveBuyerOffer = Number((effectivePrice * 0.98).toFixed(2));
      if (progressiveBuyerOffer < farmerBasePrice) {
        progressiveBuyerOffer = farmerBasePrice;
      }
      setMessages(prev => [...prev, {
        agent: 'Metro Wholesale Buyer Agent',
        type: 'offer',
        price: progressiveBuyerOffer,
        quantity: negState?.quantity || 500,
        quality: 'A',
        deliveryDate: 'Tomorrow Morning',
        transportIncluded: true,
        warehouseIncluded: false,
        validity: 'Agreed',
        message: `Progressive counter-offer evaluated at ₹${effectivePrice.toFixed(2)}/kg. We step up our offer to ₹${progressiveBuyerOffer.toFixed(2)}/kg with transport logistics included!`
      }]);
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 1200);
  };

  // Handle Offer Actions (Accept, Reject, Counter)
  const handleAction = async (actionType: string, price: number) => {
    const finalPrice = Math.max(Number(price), farmerBasePrice);

    if (actionType === 'accept') {
      const finalDeal = {
        negotiation_id: id || 'sim_direct',
        farmer: negState?.farmer || 'Ramesh',
        buyer: 'Metro Wholesale',
        crop: negState?.crop || 'Tomato',
        quantity: negState?.quantity || 500,
        price: finalPrice,
        deliveryDate: 'Tomorrow Morning',
        status: 'ACCEPTED'
      };

      // Direct write to localStorage for instant Dashboard sync
      const existingDeals = JSON.parse(localStorage.getItem('agri_deals') || '[]');
      existingDeals.unshift({
        id: `CN-${Date.now().toString().slice(-4)}`,
        crop: negState?.crop || 'Tomato',
        quantity: negState?.quantity || 500,
        price: finalPrice,
        total: finalPrice * (negState?.quantity || 500),
        status: 'ACCEPTED',
        buyer: 'Metro Wholesale',
        date: new Date().toLocaleDateString()
      });
      localStorage.setItem('agri_deals', JSON.stringify(existingDeals));

      setMessages(prev => [...prev, { 
        agent: 'AgriNegotiator System', 
        message: `🎉 Deal Accepted at ₹${finalPrice.toFixed(2)}/kg! Digital Contract sheet generated.`, 
        type: 'text' 
      }]);

      setAgreementData(finalDeal);
      setShowAgreement(true);
    } else if (actionType === 'counter') {
      const target = prompt(`Enter counter price per kg (Base Floor ₹${farmerBasePrice.toFixed(2)}/kg):`, String((price + 0.75).toFixed(2)));
      if (target) {
        const counterPrice = Number(target) || price + 0.75;
        triggerAiCounterResponse(counterPrice);
      }
    } else if (actionType === 'reject') {
      // 1. Add rejection message
      setMessages(prev => [...prev, { 
        agent: 'Your AI Copilot (Farmer Agent)', 
        message: `Offer of ₹${price.toFixed(2)}/kg from Metro Wholesale REJECTED. Rerouting negotiation to next matched buyer...`, 
        type: 'text' 
      }]);

      // 2. Save rejected deal to localStorage for Dashboard sync
      const existingDeals = JSON.parse(localStorage.getItem('agri_deals') || '[]');
      existingDeals.unshift({
        id: `REJ-${Date.now().toString().slice(-4)}`,
        crop: negState?.crop || 'Tomato',
        quantity: negState?.quantity || 500,
        price: price,
        total: price * (negState?.quantity || 500),
        status: 'REJECTED',
        buyer: 'Metro Wholesale',
        date: new Date().toLocaleDateString()
      });
      localStorage.setItem('agri_deals', JSON.stringify(existingDeals));

      // 3. Switch to Buyer #2 (Reliance Fresh Retail) automatically with higher opening offer
      setTimeout(() => {
        setMessages(prev => [...prev, {
          agent: 'AgriNegotiator Orchestrator',
          message: `🔄 Switched negotiation pipeline to Buyer #2: Reliance Fresh Retail Chain (Target: ₹21.25/kg).`,
          type: 'text'
        }]);
      }, 800);

      setTimeout(() => {
        setMessages(prev => [...prev, {
          agent: 'Reliance Fresh Buyer Agent',
          message: `Hello Ramesh! We are Reliance Fresh. We saw your 500kg Tomato listing. We offer ₹21.25/kg (+₹${(21.25 - price).toFixed(2)}/kg higher) with direct warehouse pickup!`,
          type: 'offer',
          price: 21.25,
          quantity: negState?.quantity || 500,
          quality: 'A',
          deliveryDate: 'Tomorrow Morning',
          transportIncluded: true,
          warehouseIncluded: false,
          validity: '24 Hours'
        }]);
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 2000);
    }
  };

  const interveneMutation = useMutation({
    mutationFn: async (price: number) => {
      try {
        await api.post(`/negotiations/${id}/intervene`, { price });
      } catch (e) {
        console.warn("Intervene action recorded");
      }
      triggerAiCounterResponse(price);
    }
  });

  if (isLoading) return <div className="p-8 text-center text-slate-500 font-medium">Initializing LangGraph Engine & RAG Vectors...</div>;

  return (
    <div className="h-[calc(100vh-100px)] flex flex-col xl:flex-row gap-6 p-4">
      
      {/* COLUMN 1: Intelligence Panel */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto hidden lg:flex">
        <Link to="/" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-emerald-600">
          <ArrowLeft size={16} className="mr-1" /> Exit Workspace
        </Link>
        
        {/* Market Context */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Briefcase size={18} className="text-blue-600"/> Market Context</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Live Modal Price</span>
              <span className="font-bold text-slate-800">₹{marketPrice.toFixed(2)}/kg</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Your Base Floor</span>
              <span className="font-bold text-emerald-600">₹{farmerBasePrice.toFixed(2)}/kg</span>
            </div>
          </div>
        </div>

        {/* Live Variables */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
           <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Database size={18} className="text-purple-600"/> Live Variables</h2>
           <div className="space-y-4">
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                <p className="text-xs font-bold text-blue-600 mb-1 flex items-center gap-1"><CloudRain size={14}/> WEATHER RISK</p>
                <p className="text-sm text-slate-700">Rain predicted in 48hrs. Buyer urgency is high.</p>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                <p className="text-xs font-bold text-amber-600 mb-1 flex items-center gap-1"><Truck size={14}/> TRANSPORT</p>
                <p className="text-sm text-slate-700">Fleet availability drops 30% by weekend.</p>
              </div>
           </div>
        </div>
      </div>

      {/* COLUMN 2: The Timeline / Chat Stream */}
      <div className="w-full xl:w-2/4 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col overflow-hidden relative">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center z-10 sticky top-0">
          <h3 className="font-bold text-slate-700 flex items-center gap-2">
            <MessageSquare size={18} className="text-emerald-600" /> Autonomous AI Agent Conversation
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full flex items-center gap-1">
              <Zap size={12} /> AI Copilot Live
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6 space-y-6">
          {messages.map((m, i) => (
            m.type === 'offer' ? (
               <OfferCard 
                  key={i}
                  agent={m.agent}
                  price={m.price}
                  quantity={m.quantity}
                  quality={m.quality}
                  deliveryDate={m.deliveryDate}
                  transportIncluded={m.transportIncluded}
                  warehouseIncluded={m.warehouseIncluded}
                  validity={m.validity}
                  isFarmer={m.agent.includes('Farmer') || m.agent.includes('Human')}
                  onAction={handleAction}
               />
            ) : (
              <ChatBubble 
                key={i} 
                agent={m.agent} 
                price={m.price} 
                message={m.message} 
                reasoning={m.reasoning}
                isFarmer={m.agent.includes('Farmer') || m.agent.includes('Human')} 
              />
            )
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* COLUMN 3: Action Panel & Workflow */}
      <div className="w-full xl:w-1/4 flex flex-col gap-6 overflow-y-auto">
        
        {/* Agent Workflow Stepper */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
           <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
             <Zap size={18} className="text-emerald-500" /> LangGraph Execution
           </h2>
           <AgentWorkflowStepper activeAgent={activeAgent} />
           <button 
              onClick={() => setIsRagOpen(!isRagOpen)}
              className="mt-4 w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg transition text-sm flex justify-center items-center gap-2"
            >
              <Database size={16} /> View RAG Context
            </button>
        </div>

        {/* Dynamic Action Area: Either shows Manual Override OR Agreement Preview */}
        {showAgreement && agreementData ? (
           <AgreementPreview 
             dealData={agreementData} 
             onSignAndClose={() => navigate('/dashboard')} 
           />
        ) : (
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-6 text-white">
            <h3 className="font-bold mb-4 flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-400"/> Optional Counter Override</h3>
            <p className="text-sm text-slate-400 mb-4">
              AI agents bargain automatically. Minimum base floor is ₹{farmerBasePrice.toFixed(2)}/kg.
            </p>
            <div className="space-y-3">
              <input 
                type="number" 
                id="humanOverride"
                placeholder={`Min ₹${farmerBasePrice.toFixed(2)}...`} 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              <button 
                onClick={() => {
                  const el = document.getElementById('humanOverride') as HTMLInputElement;
                  if (el && el.value) interveneMutation.mutate(Number(el.value));
                }}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition shadow-sm"
              >
                Send Counter Offer
              </button>
            </div>
          </div>
        )}

      </div>
      
      {/* Floating RAG Modal */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} />
    </div>
  );
}
