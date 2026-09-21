import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, MessageSquare, Briefcase, Zap, ShieldCheck, Database, CloudRain, Truck, AlertCircle, Search, CheckCircle2 } from 'lucide-react';
import ChatBubble from '@/features/negotiation/components/ChatBubble';
import OfferCard from '@/features/negotiation/components/OfferCard';
import AgreementPreview from '@/features/negotiation/components/AgreementPreview';
import AgentWorkflowStepper from '@/features/negotiation/components/AgentWorkflowStepper';
import RagContextViewer from '@/features/negotiation/components/RagContextViewer';
import { api } from '@/services/api';
import { API_CONFIG } from '@/config/api';
import { negotiationService } from '@/features/negotiation/services/negotiationService';

export default function NegotiationRoom() {
  const { id } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('agri_token');
  const wsUrl = `${API_CONFIG.WS_URL}/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [agreementData, setAgreementData] = useState(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [selectedBuyerTab, setSelectedBuyerTab] = useState('All');
  const [expandedBuyer, setExpandedBuyer] = useState(null);

  // Fetch initial state from database
  const { data: negState, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['negotiation', id],
    queryFn: async () => {
      return await negotiationService.getNegotiation(id);
    },
    refetchInterval: (query: any) => {
      const data = query?.state?.data || query;
      if (!data) return 2000;
      if (data.status === 'QUEUED' || data.status === 'ACTIVE' || !data.market_offers || data.market_offers.length === 0) {
        return 2000;
      }
      return false;
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

    const logs = negState.logs || [];
    logs.forEach(log => {
      if (typeof log === 'string') {
        let parsedAgent = 'System';
        if (log.includes('[Farmer]')) parsedAgent = 'Your AI (Farmer)';
        else if (log.includes('[Buyer]')) parsedAgent = 'Buyer Agent';
        historicMessages.push({ agent: parsedAgent, message: log, type: 'text' });
      }
    });

    if (historicMessages.length > 0) {
      setMessages(historicMessages);
    }
    if (negState.status === 'DEAL') {
      setAgreementData(negState);
      setShowAgreement(true);
    }
  }, [negState, historyLoaded]);

  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && String(lastMessage.negotiation_id) === String(id)) {
      if (lastMessage.event === 'MARKET_OFFERS_MATCHED') {
        refetch();
      } else if (lastMessage.event === 'NEGOTIATION_LOG') {
        if (!negState?.market_offers || negState.market_offers.length === 0) {
          refetch();
        }
        setMessages(prev => [...prev, {
          agent: lastMessage.agent_name || (lastMessage.agent_type === 'farmer' ? 'Your AI (Farmer)' : 
                 (lastMessage.agent_type === 'system' ? 'System' : 'Buyer Agent')),
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
        await negotiationService.acceptOffer(id);
      } catch (e) { /* best effort */ }
    } else if (actionType === 'reject') {
      setMessages(prev => [...prev, { agent: 'Human (You)', message: `I completely reject ₹${price}/kg. We are done.`, type: 'text' }]);
      try {
        await negotiationService.rejectOffer(id);
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
        await negotiationService.intervene(id, numPrice);
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

  const filteredMessages = messages.filter(m => {
    if (selectedBuyerTab === 'All') return true;
    
    // System or Farmer/Human messages should be visible on all tabs to provide context
    if (m.agent === 'System' || m.agent === 'Your AI (Farmer)' || m.agent === 'Human (You)' || m.message?.includes('[System]') || m.message?.includes('[Farmer]') || m.message?.includes('[Planner]') || m.message?.includes('[Reflection]')) return true;
    
    // For specific buyer messages, match the log prefix (e.g. [MahaAgro])
    return m.message?.includes(`[${selectedBuyerTab}]`) || m.agent?.includes(selectedBuyerTab);
  });

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
              <span className="text-slate-500">Live Mandi Price</span>
              <span className="font-bold text-slate-800">
                {negState?.market_price ? `₹${Number(negState.market_price).toFixed(2)}/kg` : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Your Minimum</span>
              <span className="font-bold text-slate-800">
                {negState?.min_price ? `₹${Number(negState.min_price).toFixed(2)}/kg` : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Expected Price</span>
              <span className="font-bold text-emerald-600">
                {negState?.min_price ? `₹${(Number(negState.min_price) * 1.05).toFixed(2)}/kg` : '—'}
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
              <span className="text-slate-500">Shelf life</span>
              <span className="font-bold text-slate-700">12 days</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-500">Status</span>
              <span className={`font-bold text-xs px-2 py-1 rounded-full ${
                negState?.status === 'DEAL' ? 'bg-emerald-100 text-emerald-700' :
                negState?.status === 'NO_DEAL' ? 'bg-red-100 text-red-700' :
                'bg-amber-100 text-amber-700'
              }`}>{negState?.status === 'ACTIVE' ? '🟢 NEGOTIATING' : (negState?.status || 'QUEUED')}</span>
            </div>
          </div>
        </div>

        {/* Live Variables */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
           <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Database size={18} className="text-purple-600"/> Live Variables</h2>
           <div className="space-y-4">
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
                <p className="text-xs font-bold text-slate-700 mb-1 flex items-center gap-1">🌦 WEATHER</p>
                <p className="text-sm text-slate-600">Rain risk: Medium<br/>Impact: Moderate</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
                <p className="text-xs font-bold text-slate-700 mb-1 flex items-center gap-1">🚚 TRANSPORT</p>
                <p className="text-sm text-slate-600">Estimated cost: ₹1,850<br/>Availability: Good</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
                <p className="text-xs font-bold text-slate-700 mb-1 flex items-center gap-1">📈 MARKET TREND</p>
                <p className="text-sm text-slate-600">7-day: +4.8%<br/>Forecast: ↑</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex justify-between items-center">
                <p className="text-xs font-bold text-slate-700 flex items-center gap-1">🏪 STORAGE</p>
                <p className="text-xs font-bold text-emerald-600">Available ✓</p>
              </div>
           </div>
        </div>
      </div>

      {/* COLUMN 2: The Timeline / Chat Stream */}
      <div className="w-full xl:w-2/4 bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col overflow-hidden relative">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center z-10 sticky top-0">
          <div className="flex items-center gap-3">
            <Link to="/dashboard" className="lg:hidden text-slate-400 hover:text-emerald-600">
              <ArrowLeft size={20} />
            </Link>
            <h3 className="font-bold text-slate-700 flex items-center gap-2">
              <MessageSquare size={18} className="text-emerald-600" /> AI Agent Negotiation
              {negState?.crop && <span className="text-sm font-normal text-slate-500 hidden sm:inline">— {negState.crop}</span>}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">{isConnected ? 'Live' : 'Offline'}</span>
            <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
          </div>
        </div>

        {/* Main Center Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-slate-50/50 border-x border-slate-200">
          
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {/* STATE 1: QUEUED / MATCHING */}
          {(!negState?.market_offers || negState.market_offers.length === 0) ? (
            <div className="max-w-lg mx-auto w-full">
              <h2 className="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
                <Search className="text-emerald-500 animate-pulse" /> AI MATCHING
              </h2>
              <p className="text-slate-500 mb-4">🔎 Finding suitable buyers...</p>
              
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Matching against:</p>
                {['Crop & Variety', 'Quantity required', 'Quality Grade', 'Location & Distance', 'Price expectations', 'Logistics availability'].map((item, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm text-slate-700">
                    <CheckCircle2 size={16} className="text-emerald-500" /> {item}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* STATE 2: ACTIVE / DEAL (Buyers Found) */
            <div>
              <div className="mb-6">
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-1 uppercase tracking-wider">
                  Top Matches & Negotiations
                </h2>
                <p className="text-emerald-600 font-medium text-sm flex items-center gap-2">
                  <Search size={14} /> {negState.market_offers.length} matching buyers found
                </p>
              </div>

              {/* BUYER CARDS */}
              <div className="space-y-4 mb-8">
                {negState.market_offers.map((buyer, idx) => {
                  // Find latest price from WS messages if available
                  const buyerMsgs = messages.filter(m => m.type === 'offer' && m.agent?.includes(buyer.buyer_name));
                  const latestPrice = buyerMsgs.length > 0 ? buyerMsgs[buyerMsgs.length - 1].price : buyer.offered_price;
                  const isTopMatch = idx === 0;

                  return (
                    <div key={idx} className={`bg-white rounded-xl shadow-sm border transition-all ${isTopMatch ? 'border-emerald-300 ring-1 ring-emerald-100' : 'border-slate-200'}`}>
                      {/* Clickable Header for expansion */}
                      <div className="p-4 cursor-pointer hover:bg-slate-50 transition rounded-xl" onClick={() => setExpandedBuyer(expandedBuyer === buyer.buyer_name ? null : buyer.buyer_name)}>
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h4 className="font-bold text-slate-800 flex items-center gap-1.5 text-base">
                              {isTopMatch && <span>⭐</span>} {buyer.buyer_name}
                              <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full ml-2">
                                {buyer.match_score ? `${Math.round(buyer.match_score * 100)}% Match` : '96% Match'}
                              </span>
                            </h4>
                            <p className="text-slate-500 text-xs mt-1">
                              Distance: {buyer.distance_km || '42'} km • Req: {buyer.req_quantity || '300-700'} kg
                            </p>
                          </div>
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full flex items-center gap-1.5 ${
                            negState.status === 'DEAL' ? 'bg-slate-100 text-slate-500' : 'bg-emerald-100 text-emerald-700'
                          }`}>
                            {negState.status === 'DEAL' ? 'FINISHED' : <><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> LIVE</>}
                          </span>
                        </div>

                        <div className="flex items-center gap-4 bg-white border border-slate-100 p-3 rounded-lg text-sm shadow-sm">
                          <div className="flex-1">
                            <p className="text-xs text-slate-400 mb-1 font-medium">Initial Offer</p>
                            <p className="font-bold text-slate-600">₹{buyer.offered_price}/kg</p>
                          </div>
                          <div className="flex-1 text-center border-x border-slate-100 px-4">
                            <p className="text-xs text-emerald-600 mb-1 font-bold">Latest Negotiated</p>
                            <p className="font-bold text-emerald-600 text-lg">₹{latestPrice}/kg</p>
                          </div>
                          <div className="flex-1 text-right">
                            <p className="text-xs text-slate-400 mb-1 font-medium">AI Status</p>
                            <p className="font-medium text-slate-700 text-xs">
                              {negState.status === 'DEAL' ? 'Deal Reached' : '🤖 Evaluated...'}
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Expanded Chat View */}
                      {expandedBuyer === buyer.buyer_name && (
                        <div className="px-4 pb-4 border-t border-slate-100 bg-slate-50/50 rounded-b-xl">
                           <h5 className="text-xs font-bold text-slate-500 uppercase my-3 flex items-center gap-1.5"><MessageSquare size={14}/> Agent Negotiation Chat</h5>
                           <div className="space-y-3 p-3 rounded-lg max-h-60 overflow-y-auto bg-white border border-slate-200">
                             {messages.filter(m => m.agent?.toLowerCase().includes(buyer.buyer_name.toLowerCase()) || m.agent === 'System' || m.agent === 'Your AI (Farmer)' || m.agent === 'Human (You)').length === 0 && <p className="text-xs text-slate-400">No chat history yet.</p>}
                             {messages.filter(m => m.agent?.toLowerCase().includes(buyer.buyer_name.toLowerCase()) || m.agent === 'System' || m.agent === 'Your AI (Farmer)' || m.agent === 'Human (You)').map((m, i) => (
                               <div key={i} className={`flex ${m.agent === 'Your AI (Farmer)' || m.agent === 'Human (You)' ? 'justify-end' : 'justify-start'}`}>
                                 <div className={`max-w-[85%] rounded-lg p-2.5 text-xs ${m.agent === 'Your AI (Farmer)' || m.agent === 'Human (You)' ? 'bg-emerald-100 text-emerald-900 rounded-tr-none' : m.agent === 'System' ? 'bg-slate-100 text-slate-500 text-center w-full shadow-none' : 'bg-white border border-slate-200 shadow-sm rounded-tl-none'}`}>
                                    <p className="font-bold text-[10px] mb-1 opacity-60">{m.agent}</p>
                                    <p className={m.agent === 'System' ? 'italic' : ''}>{m.type === 'offer' ? `Offered ₹${m.price}/kg` : m.message}</p>
                                 </div>
                               </div>
                             ))}
                           </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

            </div>
          )}
          </div> {/* End Scroll Area */}

          <div className="shrink-0 flex flex-col bg-white border-t border-slate-200">
          {/* BEST DEAL BAR (Pinned at bottom of center column) */}
          {negState?.market_offers && negState.market_offers.length > 0 && (
            <div className="p-4 sm:p-6 pb-4">
              {(() => {
                // Compute best deal dynamically
                const allBuyers = negState.market_offers.map(b => {
                  const bMsgs = messages.filter(m => m.type === 'offer' && m.agent?.includes(b.buyer_name));
                  const lp = bMsgs.length > 0 ? bMsgs[bMsgs.length - 1].price : b.offered_price;
                  return { ...b, latestPrice: lp };
                });
                const bestDeal = allBuyers.sort((a, b) => b.latestPrice - a.latestPrice)[0];
                const gross = bestDeal.latestPrice * (negState.quantity || 500);
                const net = gross - 1850; // Mock transport cost

                return (
                  <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl p-4 shadow-lg text-white">
                    <h4 className="text-xs font-bold uppercase tracking-widest text-emerald-100 flex items-center gap-1.5 mb-2">
                      🏆 Best Deal So Far
                    </h4>
                    <div className="flex flex-wrap justify-between items-end gap-4">
                      <div>
                        <p className="font-bold text-lg">{bestDeal.buyer_name}</p>
                        <p className="text-emerald-100 text-sm">
                          ₹{bestDeal.latestPrice}/kg • {negState.quantity || 500} kg • 96% Match
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-emerald-100 mb-1">Gross: ₹{gross.toLocaleString()} — Transport: ₹1,850</p>
                        <p className="font-bold text-xl">Net: ₹{net.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
          
          {/* LIVE ACTIVITY STREAM */}
          <div className="bg-slate-900 p-3 h-32 overflow-y-auto relative">
            <h4 className="sticky top-0 bg-slate-900/90 backdrop-blur-sm text-[10px] font-bold text-emerald-500 uppercase tracking-wider mb-2 flex items-center gap-1.5 pb-1 z-10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Live Activity
            </h4>
            <div className="space-y-1.5">
              {messages.length === 0 && <p className="text-xs text-slate-500">Waiting for agent activity...</p>}
              {messages.map((m, i) => (
                <div key={i} className="text-xs font-mono text-slate-300 flex items-start gap-2">
                  <span className="text-slate-500 whitespace-nowrap">[{new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}]</span>
                  <span className={`${m.agent === 'System' ? 'text-blue-400' : m.agent?.includes('Farmer') ? 'text-emerald-400' : 'text-purple-400'} whitespace-nowrap`}>{m.agent}:</span>
                  <span className="truncate">{m.type === 'offer' ? `Offered ₹${m.price}/kg` : m.message}</span>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          </div> {/* End Pinned Area */}

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
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-5 text-white">
            <h3 className="font-bold mb-3 flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-400"/> 👨‍🌾 Farmer Copilot</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              AI is negotiating automatically based on your listing, market conditions and negotiation policy. You can intervene at any time.
            </p>
            
            <div className="flex flex-wrap gap-2 mb-4">
              <button onClick={() => {document.getElementById('humanOverride').value = "Don't go below ₹64";}} className="text-[10px] bg-slate-800 hover:bg-slate-700 px-2 py-1.5 rounded-md transition border border-slate-700 text-slate-300">Don't go below ₹64</button>
              <button onClick={() => {document.getElementById('humanOverride').value = "Counter best buyer at ₹65";}} className="text-[10px] bg-slate-800 hover:bg-slate-700 px-2 py-1.5 rounded-md transition border border-slate-700 text-slate-300">Counter best buyer</button>
              <button onClick={() => {document.getElementById('humanOverride').value = "Pause all negotiations immediately";}} className="text-[10px] bg-slate-800 hover:bg-slate-700 px-2 py-1.5 rounded-md transition border border-slate-700 text-slate-300">Pause negotiations</button>
            </div>

            <div className="space-y-3">
              <input 
                type="text" 
                id="humanOverride"
                placeholder='e.g. "Try to get ₹67 from the best buyer"' 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              <button 
                onClick={() => {
                  const val = document.getElementById('humanOverride').value;
                  if (!val) return;
                  if (confirm(`👨‍🌾 FARMER OVERRIDE\n\nInstruction: "${val}"\n\nDo you want to send this instruction to the AI?`)) {
                    interveneMutation.mutate(val);
                    document.getElementById('humanOverride').value = '';
                  }
                }}
                disabled={interveneMutation.isPending}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl transition shadow-sm disabled:opacity-50"
              >
                {interveneMutation.isPending ? 'Sending...' : 'Send Instruction'}
              </button>
              {interveneMutation.isError && (
                <p className="text-xs text-red-400 text-center">Failed to send instruction.</p>
              )}
            </div>
          </div>
        )}

      </div>
      
      {/* Floating RAG Modal */}
      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} crop={negState?.crop} />
    </div>
  );
}
