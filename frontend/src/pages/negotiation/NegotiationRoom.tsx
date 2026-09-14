import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, MessageSquare, Briefcase, Zap, ShieldCheck, Database, CloudRain, Truck, Check, X, ArrowRightLeft, Bot, FileText } from 'lucide-react';
import ChatBubble from '@/features/negotiation/components/ChatBubble';
import OfferCard from '@/features/negotiation/components/OfferCard';
import AgreementPreview from '@/features/negotiation/components/AgreementPreview';
import AgentWorkflowStepper from '@/features/negotiation/components/AgentWorkflowStepper';
import RagContextViewer from '@/features/negotiation/components/RagContextViewer';
import TransactionValidationModal from '@/components/negotiation/TransactionValidationModal';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isBuyer = user?.role === 'buyer';
  const token = localStorage.getItem('agri_token');
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const defaultWs = `${protocol}//${window.location.host}/ws/negotiation${token ? `?token=${token}` : ''}`;
  const wsUrl = import.meta.env.VITE_WS_URL || defaultWs;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState(null);
  const [overridePrice, setOverridePrice] = useState('');
  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [tentativePrice, setTentativePrice] = useState<number | null>(null);

  // Fetch initial state from database with auto-poll while active
  const { data: negState, isLoading, isError, refetch: refetchNeg } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      const res = await api.get(`/negotiations/${id}`);
      return res.data?.data || res.data;
    },
    refetchInterval: (query: any) => {
      const s = query?.state?.data?.status;
      return (s === 'DEAL' || s === 'REJECT' || s === 'FAILED' || s === 'ESCALATED_STORAGE' || s === 'ESCALATED_PROCESSING' || s === 'ESCALATED_COMPOST') ? false : 2000;
    }
  });

  const isConcluded = Boolean(
    showAgreement || 
    negState?.status === 'DEAL' || 
    negState?.status === 'REJECT' || 
    negState?.status === 'FAILED' || 
    negState?.deal ||
    negState?.final_price
  );

  const isMsgFromMe = (agentName: string) => {
    if (!agentName) return false;
    const lower = agentName.toLowerCase();
    if (lower.includes('human') || lower.includes('you')) return true;
    if (isBuyer) {
      return lower.includes('buyer') || (user?.name && lower.includes(user.name.toLowerCase()));
    } else {
      return lower.includes('farmer') || (user?.name && lower.includes(user.name.toLowerCase()));
    }
  };

  // Sync messages with offers from negState
  useEffect(() => {
    if (negState?.offers && Array.isArray(negState.offers) && negState.offers.length > 0) {
      const syncd = negState.offers.map((o: any) => ({
        agent: o.agent || (o.round % 2 === 1 ? (isBuyer ? 'Buyer Agent (You)' : 'Buyer Agent') : (isBuyer ? 'Farmer Agent' : 'Farmer Agent (You)')),
        message: o.message || `Round ${o.round}: ₹${o.price}/kg (${o.decision || 'COUNTER'})`,
        type: 'offer',
        price: o.price,
        quantity: o.quantity || negState?.quantity || 0,
        quality: 'A',
        deliveryDate: 'ASAP',
        transportIncluded: false,
        warehouseIncluded: false,
        validity: '24 Hours'
      }));
      setMessages(syncd);
    }
    const finalP = negState?.final_price || negState?.price;
    if ((negState?.status === 'DEAL' || negState?.deal || finalP) && finalP) {
      const finalDeal = {
        ...negState,
        id: id,
        farmer: negState?.farmer || negState?.farmer_name || 'Farmer Agent',
        buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Agent',
        price: finalP,
        quantity: negState?.quantity || 500,
        status: negState?.status || 'DEAL'
      };
      setAgreementData(finalDeal);
      setTentativePrice(finalP);
    }
  }, [negState?.offers, negState?.status, negState?.final_price, isBuyer, user?.name, id]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && String(lastMessage.negotiation_id) === String(id)) {
      if (lastMessage.event === 'NEGOTIATION_LOG') {
        const agentLabel = lastMessage.agent_type === 'farmer' 
          ? (isBuyer ? 'Farmer Agent' : 'Farmer Agent (You)') 
          : (isBuyer ? 'Buyer Agent (You)' : 'Buyer Agent');

        setMessages(prev => [...prev, {
          agent: agentLabel,
          message: lastMessage.message,
          type: lastMessage.offer ? 'offer' : 'text',
          price: lastMessage.offer,
          quantity: negState?.quantity || 0,
          quality: 'A',
          deliveryDate: 'ASAP',
          transportIncluded: false,
          warehouseIncluded: false,
          validity: '24 Hours'
        }]);
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } else if (lastMessage.event === 'NEGOTIATION_FINISHED') {
        const finalP = lastMessage.final_price || negState?.final_price;
        const finalDeal = {
          ...negState,
          id: id,
          farmer: negState?.farmer || negState?.farmer_name || 'Farmer Agent',
          buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Agent',
          price: finalP,
          quantity: negState?.quantity || 500,
          status: lastMessage.status || 'DEAL'
        };
        setAgreementData(finalDeal);
        setTentativePrice(finalP);
      }
    }
  }, [lastMessage, negState, id, isBuyer, user?.name]);

  const activeAgent = lastMessage?.data?.agent || 'Planner';

  // Handle Offer Actions
  const handleAction = async (actionType: string, price: any) => {
    if (isConcluded) return;
    if (actionType === 'accept') {
      const p = Number(price) || activeOfferPrice;
      setTentativePrice(p);
      const finalDeal = {
        ...negState,
        id: id,
        farmer: negState?.farmer || negState?.farmer_name || 'Farmer Agent',
        buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Agent',
        price: p,
        quantity: negState?.quantity || 500,
        deliveryDate: 'Next Friday',
        status: 'DEAL'
      };
      setAgreementData(finalDeal);
      setShowFinalizeConfirm(true);
    } else if (actionType === 'reject') {
      setMessages(prev => [...prev, { agent: 'Human (You)', message: `I completely reject ₹${price}/kg. We are done.`, type: 'text' }]);
      if (token !== 'mock_token') {
        try { await api.post(`/negotiations/${id}/reject`); } catch (e) {}
      }
      refetchNeg();
    } else {
      document.getElementById('humanOverride')?.focus();
    }
  };

  const syncOffersList = (offersList: any[]) => {
    if (!Array.isArray(offersList)) return;
    const syncd = offersList.map((o: any) => ({
      agent: o.agent || (o.round % 2 === 1 ? (isBuyer ? 'Buyer Agent (You)' : 'Buyer Agent') : (isBuyer ? 'Farmer Agent' : 'Farmer Agent (You)')),
      message: o.message || `Round ${o.round}: ₹${o.price}/kg (${o.decision || 'COUNTER'})`,
      type: 'offer',
      price: o.price,
      quantity: o.quantity || negState?.quantity || 500,
      quality: 'A',
      deliveryDate: 'ASAP',
      transportIncluded: false,
      warehouseIncluded: false,
      validity: '24 Hours'
    }));
    setMessages(syncd);
  };

  const interveneMutation = useMutation({
    mutationFn: async (price: number) => {
      const res = await api.post(`/negotiations/${id}/intervene`, { 
        price: Number(price), 
        quantity: negState?.quantity || 500 
      });
      return res.data;
    },
    onSuccess: (data) => {
      refetchNeg();
      if (data?.offers) syncOffersList(data.offers);
      if (data?.status === 'DEAL') {
        const agreedP = data.final_price || data?.farmer_response?.price || tentativePrice;
        setTentativePrice(Number(agreedP));
        setAgreementData({
          ...negState,
          id: id,
          farmer: negState?.farmer || negState?.farmer_name || 'Farmer Agent',
          buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Agent',
          price: Number(agreedP),
          quantity: negState?.quantity || 500,
          status: 'DEAL'
        });
        setShowFinalizeConfirm(true);
      }
    }
  });

  const autoBargainMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/negotiations/${id}/autonomous-step`);
      return res.data;
    },
    onSuccess: (data) => {
      refetchNeg();
      if (data?.offers) syncOffersList(data.offers);
      if (data?.status === 'DEAL') {
        const agreedP = data.final_price || data?.farmer_response?.price;
        setTentativePrice(Number(agreedP));
        setAgreementData({
          ...negState,
          id: id,
          farmer: negState?.farmer || negState?.farmer_name || 'Farmer Agent',
          buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Agent',
          price: Number(agreedP),
          quantity: negState?.quantity || 500,
          status: 'DEAL'
        });
        setShowFinalizeConfirm(true);
      }
    }
  });

  const opponentOffers = messages.filter((m: any) => m.type === 'offer' && !isMsgFromMe(m.agent));
  const latestOpponentOffer = opponentOffers.length > 0 ? opponentOffers[opponentOffers.length - 1] : null;
  const anyOffers = messages.filter((m: any) => m.type === 'offer');
  const latestAnyOffer = anyOffers.length > 0 ? anyOffers[anyOffers.length - 1] : null;
  const activeOfferPrice = latestOpponentOffer?.price || negState?.latest_farmer_ask || negState?.min_price || latestAnyOffer?.price || 18;

  if (isLoading) return <div className="p-8 text-center text-slate-500">Initializing LangGraph Engine...</div>;

  return (
    <div className="h-[calc(100vh-100px)] flex flex-col xl:flex-row gap-6 p-4">
      
      {/* COLUMN 1: Intelligence Panel */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto hidden lg:flex">
        <Link to={isBuyer ? "/dashboard/buyer" : "/dashboard/farmer"} className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-emerald-600">
          <ArrowLeft size={16} className="mr-1" /> Exit Workspace
        </Link>
        
        {/* Market Context */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Briefcase size={18} className="text-blue-600"/> Market Context</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Live Modal Price</span>
              <span className="font-bold text-slate-800">₹{negState?.market_price || 20}/kg</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">{isBuyer ? 'Your Target' : 'Farmer Floor'}</span>
              <span className="font-bold text-emerald-600">
                ₹{isBuyer ? (negState?.target_price || negState?.buyer_target_price || negState?.min_price || 18) : (negState?.min_price || 18)}/kg
              </span>
            </div>
            {isBuyer && negState?.min_price && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">Farmer Ask</span>
                <span className="font-bold text-slate-700">₹{negState.min_price}/kg</span>
              </div>
            )}
          </div>
        </div>

        {/* Live Variables */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
           <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Database size={18} className="text-purple-600"/> Live Variables</h2>
           <div className="space-y-4">
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                <p className="text-xs font-bold text-blue-600 mb-1 flex items-center gap-1"><CloudRain size={14}/> WEATHER RISK</p>
                <p className="text-sm font-medium text-slate-700">Monsoon Alert: High Spoilage Probability</p>
              </div>
              <div className="p-3 bg-purple-50 border border-purple-100 rounded-xl">
                <p className="text-xs font-bold text-purple-600 mb-1 flex items-center gap-1"><Truck size={14}/> LOGISTICS CAPACITY</p>
                <p className="text-sm font-medium text-slate-700">Multi-Modal Freight: 140 KM radius</p>
              </div>
           </div>
        </div>
      </div>

      {/* COLUMN 2: Multi-Turn Offer Stream */}
      <div className="w-full xl:w-2/4 flex flex-col bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h1 className="font-bold text-slate-800 text-lg flex items-center gap-2">
              <MessageSquare size={18} className="text-emerald-500" />
              {negState?.crop || 'Crop'} Strategic Room
            </h1>
            <p className="text-xs text-slate-500">
              Contract Ref: #{id?.substring(0, 8)} • Volume: {negState?.quantity || 500}kg
            </p>
          </div>
          <div className="flex items-center gap-2">
             <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
             <span className="text-xs font-medium text-slate-500">{isConnected ? 'Live WebSocket' : 'Connecting...'}</span>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6 space-y-6">
          {/* Concluded Agreement Banner */}
          {isConcluded && (agreementData?.price || negState?.final_price) && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-black shrink-0 shadow-sm">
                  ✓
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-slate-900 text-sm">Deal Agreed at ₹{agreementData?.price || negState?.final_price}/kg</p>
                    <span className="px-2 py-0.5 bg-emerald-200 text-emerald-900 text-[10px] font-black rounded-full uppercase tracking-wider">
                      AGREED
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">Official Smart Contract generated & Maharashtra APMC validated.</p>
                </div>
              </div>
              <button
                onClick={() => setShowValidationModal(true)}
                className="w-full sm:w-auto px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center justify-center gap-1.5 shrink-0"
              >
                <FileText size={15} /> View Validated Term Sheet
              </button>
            </div>
          )}

          {/* Dynamic WS Messages */}
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
                  isFarmer={isMsgFromMe(m.agent)}
                  onAction={isConcluded ? undefined : handleAction}
               />
            ) : (
              <ChatBubble 
                key={i} 
                agent={m.agent} 
                price={m.price} 
                message={m.message} 
                reasoning={m.reasoning}
                isFarmer={isMsgFromMe(m.agent)} 
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
             onSignAndClose={() => navigate(isBuyer ? '/dashboard/buyer' : '/dashboard/farmer')} 
           />
        ) : (
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-6 text-white">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold flex items-center gap-2 text-sm">
                <ShieldCheck size={18} className="text-emerald-400"/> Copilot Actions & Override
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {isConcluded ? 'CONCLUDED' : 'ACTIVE'}
              </span>
            </div>

            {/* Autonomous Bargaining Trigger - Buyer Agent Bargains for you */}
            {!isConcluded && (
              <button 
                disabled={autoBargainMutation.isPending}
                onClick={() => autoBargainMutation.mutate()}
                className="w-full py-2.5 px-3 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-bold text-xs rounded-xl transition shadow-md flex items-center justify-center gap-2 mb-4 active:scale-95 disabled:opacity-50"
              >
                <Bot size={15} />
                {autoBargainMutation.isPending ? "Buyer Agent Bargaining..." : "⚡ Let AI Agent Bargain Next Round"}
              </button>
            )}

            {/* Quick Action Decision Panel (Always visible when active) */}
            {!isConcluded && (
              <div className="space-y-3 mb-5 p-3.5 bg-slate-800/80 rounded-xl border border-slate-700/60">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Current Offer on Table:</span>
                  <span className="font-extrabold text-emerald-400 text-sm">₹{activeOfferPrice}/kg</span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button 
                    onClick={() => handleAction('accept', activeOfferPrice)}
                    className="flex justify-center items-center gap-1.5 py-2.5 px-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition shadow-sm active:scale-95"
                  >
                    <Check size={15}/> Accept Deal
                  </button>
                  <button 
                    onClick={() => handleAction('reject', activeOfferPrice)}
                    className="flex justify-center items-center gap-1.5 py-2.5 px-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 font-bold text-xs rounded-lg transition active:scale-95"
                  >
                    <X size={15}/> Reject
                  </button>
                </div>
              </div>
            )}

            {isConcluded ? (
              <div className="p-4 bg-slate-800/80 rounded-xl border border-emerald-500/30 text-center space-y-3 mt-2">
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                  <Check size={20} />
                </div>
                <div>
                  <p className="font-bold text-white text-sm">Deal Concluded & Finalized</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Settled at <span className="text-emerald-400 font-extrabold text-sm">₹{activeOfferPrice}/kg</span>
                  </p>
                </div>
                <div className="pt-2 border-t border-slate-700/60 flex flex-col gap-2">
                  <button
                    onClick={() => setShowValidationModal(true)}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20"
                  >
                    <FileText size={15} /> View Validated Term Sheet & TXN ID
                  </button>
                  <button
                    onClick={() => navigate(isBuyer ? '/dashboard/buyer' : '/dashboard/farmer')}
                    className="w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold text-xs rounded-lg transition"
                  >
                    Return to Marketplace →
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-xs text-slate-400 mb-2 font-medium">
                  Manual Counter Offer (RL Override)
                </p>
                <div className="space-y-3">
                  <input 
                    type="number" 
                    id="humanOverride"
                    value={overridePrice}
                    onChange={(e) => setOverridePrice(e.target.value)}
                    placeholder="Enter counter price (e.g. 17.5)..." 
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 !text-white text-white font-semibold placeholder-slate-400 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    style={{ color: '#ffffff', WebkitTextFillColor: '#ffffff' }}
                  />
                  <button 
                    disabled={!overridePrice || interveneMutation.isPending}
                    onClick={() => {
                      const val = Number(overridePrice);
                      if (val > 0) {
                        interveneMutation.mutate(val);
                        setOverridePrice('');
                      }
                    }}
                    className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-slate-500 text-slate-200 hover:text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-1.5 disabled:opacity-50 active:scale-95"
                  >
                    <ArrowRightLeft size={14}/> {interveneMutation.isPending ? "Sending Counter..." : "Send Counter Offer"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

      </div>
      
      {/* Floating RAG Modal */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} />

      {/* Confirmation Modal: "Do you want to finalize this deal?" */}
      {showFinalizeConfirm && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-100 text-center animate-in zoom-in-95">
            <div className="w-14 h-14 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-4 font-bold shadow-sm">
              <Check size={28} />
            </div>
            <h3 className="text-xl font-black text-slate-900 mb-1">
              Do you want to finalize this deal?
            </h3>
            <p className="text-slate-500 text-sm mb-6">
              The Farmer and Buyer Agent agreed on the procurement terms below:
            </p>
            
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 text-left space-y-2.5 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Agreed Price:</span>
                <span className="font-extrabold text-emerald-600 text-base">₹{tentativePrice || agreementData?.price || activeOfferPrice}/kg</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Produce & Volume:</span>
                <span className="font-bold text-slate-800">{negState?.crop || 'Tomato'} • {negState?.quantity || 500} kg</span>
              </div>
              <div className="flex justify-between text-sm border-t border-slate-200 pt-2">
                <span className="text-slate-600 font-semibold">Total Settlement:</span>
                <span className="font-black text-slate-900 text-base">
                  ₹{(((tentativePrice || agreementData?.price || activeOfferPrice) as number) * (negState?.quantity || 500)).toLocaleString()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setShowFinalizeConfirm(false)}
                className="w-full py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-sm transition"
              >
                Keep Negotiating
              </button>
              <button
                onClick={async () => {
                  setShowFinalizeConfirm(false);
                  setShowAgreement(true);
                  setShowValidationModal(true);
                  if (token !== 'mock_token') {
                    try { await api.post(`/negotiations/${id}/accept`); } catch (e) {}
                  }
                }}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-sm transition shadow-md shadow-emerald-600/20"
              >
                Yes, Finalize Deal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Official Transaction Validation & Term Sheet Modal */}
      <TransactionValidationModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        dealData={agreementData || {
          ...negState,
          id: id,
          price: tentativePrice || negState?.final_price || activeOfferPrice,
          quantity: negState?.quantity || 3000,
          crop: negState?.crop || 'Produce',
          farmer: negState?.farmer || negState?.farmer_name || 'Gurpreet Singh',
          buyer: negState?.buyer || negState?.buyer_name || user?.name || 'Buyer Enterprise'
        }}
        buyerUser={user}
      />
    </div>
  );
}
