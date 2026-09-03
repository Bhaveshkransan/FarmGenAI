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
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState(null);

  // Fetch initial state from database
  const { data: negState, isLoading, isError } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      const res = await api.get(`/negotiations/${id}`);
      return res.data?.data || res.data;
    }
  });

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
      setShowAgreement(true); // Triggers the AgreementPreview on the right column
    } else if (actionType === 'reject') {
      setMessages(prev => [...prev, { agent: 'Human (You)', message: `I completely reject ₹${price}/kg. We are done.`, type: 'text' }]);
      if (token !== 'mock_token') await api.post(`/negotiations/${id}/reject`);
    } else {
      document.getElementById('humanOverride').focus();
    }
  };

  const interveneMutation = useMutation({
    mutationFn: async (price) => {
      if (token !== 'mock_token') await api.post(`/negotiations/${id}/intervene`, { price });
      setMessages(prev => [...prev, { 
        agent: 'Human (You)', 
        type: 'offer',
        price, 
        quantity: negState.quantity,
        quality: 'A',
        deliveryDate: 'As soon as possible',
        transportIncluded: false,
        warehouseIncluded: false,
        validity: '24 Hours'
      }]);
    }
  });

  if (isLoading) return <div className="p-8 text-center text-slate-500">Initializing LangGraph Engine...</div>;

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
              <span className="font-bold text-slate-800">₹{negState?.market_price}/kg</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Your Target</span>
              <span className="font-bold text-emerald-600">₹{negState?.min_price}/kg</span>
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
            <MessageSquare size={18} className="text-emerald-600" /> AI Agent Negotiation
          </h3>
          <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
        </div>
        
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6 space-y-6">
          
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
             onSignAndClose={() => navigate('/')} 
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
                placeholder="Enter manual price..." 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              <button 
                onClick={() => interveneMutation.mutate(document.getElementById('humanOverride').value)}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition shadow-sm"
              >
                Send Manual Offer
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
