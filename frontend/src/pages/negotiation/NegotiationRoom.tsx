import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, MessageSquare, Briefcase, Zap, ShieldCheck, Database, CloudRain, Truck, AlertCircle } from 'lucide-react';
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
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  // Fetch initial state from database
  const { data: negState, isLoading, isError, error } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      const res = await api.get(`/negotiations/${id}`);
      return res.data?.data || res.data;
    }
  });

  // Populate chat history from database on first load
  useEffect(() => {
    if (!negState || historyLoaded) return;
    setHistoryLoaded(true);

    const historicMessages = [];

    // Map existing offers into chat bubbles
    const offers = negState.offers || [];
    offers.forEach(o => {
      historicMessages.push({
        agent: o.sender || 'Agent',
        message: o.message || `Offer at ₹${o.price}/kg for ${o.quantity} kg`,
        type: o.price ? 'offer' : 'text',
        price: o.price,
        quantity: o.quantity || negState.quantity,
        quality: 'A',
        deliveryDate: 'ASAP',
        transportIncluded: false,
        warehouseIncluded: false,
        validity: '24 Hours',
      });
    });

    // Map negotiation logs into system text bubbles
    const logs = negState.logs || [];
    logs.forEach(log => {
      if (typeof log === 'string') {
        historicMessages.push({ agent: 'System', message: log, type: 'text' });
      }
    });

    if (historicMessages.length > 0) {
      setMessages(historicMessages);
    }
  }, [negState, historyLoaded]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && String(lastMessage.negotiation_id) === String(id)) {
      if (lastMessage.event === 'NEGOTIATION_LOG') {
        setMessages(prev => [...prev, {
          agent: lastMessage.agent_type === 'farmer' ? 'Your AI (Farmer)' : 'Buyer Agent',
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
        const finalDeal = {
          ...negState,
          price: lastMessage.final_price,
          quantity: negState?.quantity,
          status: lastMessage.status
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
      }
    }
  }, [lastMessage, negState]);

  const activeAgent = lastMessage?.data?.agent || 'Planner';

  // Handle Offer Actions
  const handleAction = async (actionType, price) => {
    if (actionType === 'accept') {
      const finalDeal = {
        ...negState,
        price: price,
        deliveryDate: 'Next Friday',
      };
      setMessages(prev => [...prev, { agent: 'Human (You)', message: `I accept the deal at ₹${price}/kg.`, type: 'text' }]);
      setAgreementData(finalDeal);
      setShowAgreement(true);
      try {
        await api.post(`/negotiations/${id}/accept`, { final_price: price });
      } catch (e) { /* best effort */ }
    } else if (actionType === 'reject') {
      setMessages(prev => [...prev, { agent: 'Human (You)', message: `I completely reject ₹${price}/kg. We are done.`, type: 'text' }]);
      try {
        await api.post(`/negotiations/${id}/reject`);
      } catch (e) { /* best effort */ }
    } else {
      document.getElementById('humanOverride')?.focus();
    }
  };

  const interveneMutation = useMutation({
    mutationFn: async (price) => {
      const numPrice = parseFloat(price);
      if (isNaN(numPrice) || numPrice <= 0) throw new Error('Invalid price');
      try {
        await api.post(`/negotiations/${id}/intervene`, { override_price: numPrice });
      } catch (e) { /* best effort */ }
      setMessages(prev => [...prev, { 
        agent: 'Human (You)', 
        type: 'offer',
        price: numPrice, 
        quantity: negState?.quantity,
        quality: 'A',
        deliveryDate: 'As soon as possible',
        transportIncluded: false,
        warehouseIncluded: false,
        validity: '24 Hours'
      }]);
    }
  });

  if (isLoading) return (
    <div className="p-8 text-center text-slate-500 flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      Initializing LangGraph Engine...
    </div>
  );

  if (isError) return (
    <div className="p-8 text-center">
      <AlertCircle className="mx-auto text-red-500 mb-3" size={40} />
      <h3 className="font-bold text-slate-800 text-lg mb-2">Negotiation Not Found</h3>
      <p className="text-slate-500 text-sm mb-4">{error?.message || `Negotiation ${id} could not be loaded.`}</p>
      <button onClick={() => navigate('/dashboard')} className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium">
        Back to Dashboard
      </button>
    </div>
  );

  return (
    <div className="h-[calc(100vh-100px)] flex flex-col xl:flex-row gap-6 p-4">
      
      {/* COLUMN 1: Intelligence Panel */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto hidden lg:flex">
        <Link to="/dashboard" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-emerald-600">
          <ArrowLeft size={16} className="mr-1" /> Exit Workspace
        </Link>
        
        {/* Market Context */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Briefcase size={18} className="text-blue-600"/> Market Context</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Live Modal Price</span>
              <span className="font-bold text-slate-800">
                {negState?.market_price ? `₹${Number(negState.market_price).toFixed(2)}/kg` : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Your Target (Min)</span>
              <span className="font-bold text-emerald-600">
                {negState?.min_price ? `₹${Number(negState.min_price).toFixed(2)}/kg` : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Crop</span>
              <span className="font-bold text-slate-700">{negState?.crop || '—'}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Quantity</span>
              <span className="font-bold text-slate-700">{negState?.quantity ? `${negState.quantity} kg` : '—'}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Status</span>
              <span className={`font-bold text-xs px-2 py-1 rounded-full ${
                negState?.status === 'DEAL' ? 'bg-emerald-100 text-emerald-700' :
                negState?.status === 'NO_DEAL' ? 'bg-red-100 text-red-700' :
                'bg-amber-100 text-amber-700'
              }`}>{negState?.status || '—'}</span>
            </div>
            {negState?.final_price && (
              <div className="flex justify-between items-center text-sm pt-2 border-t border-slate-100">
                <span className="text-slate-500">Final Deal Price</span>
                <span className="font-bold text-emerald-700">₹{Number(negState.final_price).toFixed(2)}/kg</span>
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
                <p className="text-sm text-slate-700">Rain predicted in 48hrs. Buyer urgency is high.</p>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                <p className="text-xs font-bold text-amber-600 mb-1 flex items-center gap-1"><Truck size={14}/> TRANSPORT</p>
                <p className="text-sm text-slate-700">Fleet availability drops 30% by weekend.</p>
              </div>
              {negState?.selected_buyer?.buyer_name && (
                <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
                  <p className="text-xs font-bold text-emerald-600 mb-1">MATCHED BUYER</p>
                  <p className="text-sm text-slate-700 font-medium">{negState.selected_buyer.buyer_name}</p>
                  {negState.selected_buyer.location && (
                    <p className="text-xs text-slate-500">{negState.selected_buyer.location}</p>
                  )}
                </div>
              )}
           </div>
        </div>
      </div>

      {/* COLUMN 2: The Timeline / Chat Stream */}
      <div className="w-full xl:w-2/4 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col overflow-hidden relative">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center z-10 sticky top-0">
          <h3 className="font-bold text-slate-700 flex items-center gap-2">
            <MessageSquare size={18} className="text-emerald-600" /> AI Agent Negotiation
            {negState?.crop && <span className="text-sm font-normal text-slate-500">— {negState.crop}</span>}
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">{isConnected ? 'Live' : 'Offline'}</span>
            <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6 space-y-6">
          
          {messages.length === 0 && (
            <div className="text-center text-slate-400 py-12">
              <MessageSquare size={40} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Negotiation log will appear here.</p>
              <p className="text-xs mt-1">Click "AI Match & Negotiate" from your dashboard to start.</p>
            </div>
          )}

          {/* Dynamic Messages */}
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

        {/* Dynamic Action Area */}
        {showAgreement && agreementData ? (
           <AgreementPreview 
             dealData={agreementData} 
             onSignAndClose={() => navigate('/dashboard')} 
           />
        ) : (
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-6 text-white">
            <h3 className="font-bold mb-4 flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-400"/> Copilot Override</h3>
            <p className="text-sm text-slate-400 mb-4">
              I am negotiating strictly based on RL policy. Take manual control to force an offer.
            </p>
            <div className="space-y-3">
              <input 
                type="number" 
                id="humanOverride"
                placeholder="Enter manual price (₹/kg)..." 
                min="1"
                step="0.5"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              <button 
                onClick={() => interveneMutation.mutate(document.getElementById('humanOverride').value)}
                disabled={interveneMutation.isPending}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition shadow-sm disabled:opacity-50"
              >
                {interveneMutation.isPending ? 'Sending...' : 'Send Manual Offer'}
              </button>
              {interveneMutation.isError && (
                <p className="text-xs text-red-400 text-center">Please enter a valid price.</p>
              )}
            </div>
          </div>
        )}

      </div>
      
      {/* Floating RAG Modal */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} />
    </div>
  );
}
