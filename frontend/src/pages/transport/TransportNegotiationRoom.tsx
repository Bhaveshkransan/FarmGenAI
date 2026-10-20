import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, MessageSquare, Briefcase, Zap, ShieldCheck, Database, 
  Terminal as TerminalIcon, RefreshCw, CheckCircle,
  AlertTriangle, MapPin, Star, Trophy, ChevronDown, ChevronUp,
  Bot, Clock
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
import {
  readTransportNegotiationHistory,
  updateTransportNegotiationHistory,
  writeTransportNegotiationHistory
} from '@/features/transport/transportNegotiationHistory';

export default function TransportNegotiationRoom() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const payload = location.state?.payload;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'dealers' | 'terminal'>('dealers');
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [isParallelRunning, setIsParallelRunning] = useState(false);
  const [liveTerminalLogs, setLiveTerminalLogs] = useState<Array<{ time: string; tag: string; text: string; color?: string }>>([]);
  const [isRagOpen, setIsRagOpen] = useState(false);
  const [showAgreement, setShowAgreement] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [revealedCounts, setRevealedCounts] = useState<Record<number, number>>({});
  const [activeWinnerHistoryId, setActiveWinnerHistoryId] = useState('');

  useEffect(() => {
    if (!payload) { navigate('/dashboard/transport'); return; }
    handleParallelNegotiation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payload]);

  const handleParallelNegotiation = async () => {
    setLoading(true);
    setIsParallelRunning(true);
    setExpandedIdx(null);
    setRevealedCounts({});
    const batchId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setActiveWinnerHistoryId('');
    const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLiveTerminalLogs([
      { time: now(), tag: 'CLUSTER', color: 'text-emerald-400', text: '🚀 Initializing LangGraph Transport Orchestrator...' },
      { time: now(), tag: 'POLICY', color: 'text-purple-400', text: `Floor Price: Rs.${payload?.floor_price}/trip | Distance: Highway routing.` },
      { time: now(), tag: 'DISCOVERY', color: 'text-blue-400', text: 'Scanning candidate vehicles in Maharashtra...' }
    ]);
    try {
      const res = await api.post('/transport/parallel-negotiate', payload);
      setResults(res.data);
      const negotiations = res.data?.all_negotiations || [];
      const winnerVehicleId = String(res.data?.winner?.vehicle?.vehicle_id || res.data?.winner?.vehicle?.vehicle_name || '');
      const historyEntries = negotiations.map((neg: any, index: number) => {
        const vehicle = neg.vehicle || {};
        const vehicleId = String(vehicle.vehicle_id || vehicle.vehicle_name || index);
        const historyId = `${batchId}:${vehicleId}`;
        const isWinner = Boolean(winnerVehicleId && vehicleId === winnerVehicleId);
        if (isWinner) setActiveWinnerHistoryId(historyId);
        return {
          id: historyId,
          batchId,
          vehicleId,
          vehicleName: vehicle.vehicle_name || `Transporter ${index + 1}`,
          vehicleType: vehicle.vehicle_type || vehicle.type,
          crop: payload?.crop || 'Produce',
          quantityKg: Number(payload?.quantity_kg || 0),
          pickupLocation: payload?.pickup_location || '',
          deliveryLocation: payload?.delivery_location || '',
          floorPrice: Number(payload?.floor_price || 0),
          agreedPrice: Number(neg.agreed_price || neg.pricing_rules?.target_price) || null,
          status: neg.status === 'REJECTED' ? 'REJECTED' : 'NEGOTIATING',
          negotiationStatus: neg.status || 'NEGOTIATING',
          transcript: neg.transcript || [],
          winner: isWinner,
          createdAt: new Date().toISOString()
        };
      });
      const existingHistory = readTransportNegotiationHistory(user);
      writeTransportNegotiationHistory(user, [...historyEntries, ...existingHistory]);
      negotiations.forEach((neg: any, i: number) => {
        const delay = (i + 1) * 800;
        setTimeout(() => {
          setLiveTerminalLogs(prev => [...prev, {
            time: now(), tag: `THREAD-${i + 1}`, color: 'text-blue-400',
            text: `🔁 Negotiating with ${neg.vehicle?.vehicle_name}... Round ${neg.transcript?.length || 1}`
          }]);
        }, delay);
        const transcript = neg.transcript || [];
        transcript.forEach((_: any, rIdx: number) => {
          setTimeout(() => {
            setRevealedCounts(prev => ({ ...prev, [i]: (prev[i] || 0) + 1 }));
          }, delay + (rIdx + 1) * 500);
        });
      });
      setTimeout(() => {
        setLiveTerminalLogs(prev => [
          ...prev,
          { time: now(), tag: 'NEGOTIATION', color: 'text-amber-400', text: `Running parallel negotiations across ${negotiations.length} threads...` },
          { time: now(), tag: 'WINNER', color: 'text-emerald-400', text: `✅ Winner: ${res.data.winner?.vehicle?.vehicle_name} at Rs.${res.data.winner?.agreed_price || res.data.winner?.pricing_rules?.target_price}` }
        ]);
        setShowAgreement(true);
        setIsParallelRunning(false);
        setLoading(false);
        const winnerIdx = negotiations.findIndex((n: any) => n.vehicle?.vehicle_name === res.data.winner?.vehicle?.vehicle_name);
        if (winnerIdx >= 0) setExpandedIdx(winnerIdx);
      }, (negotiations.length + 1) * 800 + 500);
    } catch (e) {
      console.warn('Transport Negotiation Error', e);
      setLiveTerminalLogs(prev => [...prev, { time: now(), tag: 'ERROR', color: 'text-red-500', text: 'Failed to complete negotiation.' }]);
      setLoading(false);
      setIsParallelRunning(false);
    }
  };

  const winner = results?.winner;
  const allNegs: any[] = results?.all_negotiations || [];
  const sortedNegs = useMemo(() => {
    return [...allNegs].sort((a, b) => {
      const aW = a.vehicle?.vehicle_name === winner?.vehicle?.vehicle_name ? -1 : 0;
      const bW = b.vehicle?.vehicle_name === winner?.vehicle?.vehicle_name ? -1 : 0;
      if (aW !== bW) return aW - bW;
      return (a.agreed_price || 99999) - (b.agreed_price || 99999);
    });
  }, [allNegs, winner]);

  const bestNeg = sortedNegs[0];
  const bestPrice = bestNeg?.agreed_price || bestNeg?.pricing_rules?.target_price || payload?.floor_price || 0;

  const chartData = useMemo(() => {
    const base = Number(bestPrice) || 5000;
    return [
      { name: 'Day 1', price: Math.round(base * 0.94) },
      { name: 'Day 5', price: Math.round(base * 0.96) },
      { name: 'Day 10', price: Math.round(base * 0.95) },
      { name: 'Day 15', price: Math.round(base * 0.98) },
      { name: 'Day 20', price: Math.round(base * 1.02) },
      { name: 'Day 25', price: Math.round(base * 1.01) },
      { name: 'Day 30', price: Math.round(base) },
    ];
  }, [bestPrice]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [expandedIdx, results, activeTab]);
  useEffect(() => { terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [liveTerminalLogs, activeTab]);

  if (loading && !results) {
    return (
      <div className="h-[70vh] flex flex-col items-center justify-center space-y-3">
        <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-bold text-sm">Initializing LangGraph Transport Engine...</p>
        <p className="text-slate-400 text-xs">Running parallel negotiations with all top transport agents...</p>
      </div>
    );
  }

  const dealDataForModal = {
    id: bestNeg?.vehicle?.vehicle_id || 'TRN-123',
    negotiation_id: bestNeg?.vehicle?.vehicle_id || 'TRN-123',
    crop: payload?.crop || 'Produce',
    quantity: payload?.quantity_kg || 0,
    price: bestPrice,
    final_price: bestPrice,
    buyer: user?.name || user?.full_name || 'Buyer Enterprise',
    farmer: bestNeg?.vehicle?.vehicle_name || 'Transporter',
    farmer_name: bestNeg?.vehicle?.vehicle_name || 'Transporter',
    status: bestNeg?.status || 'DEAL'
  };

  const getStatusBorder = (neg: any) => {
    if (neg.vehicle?.vehicle_name === winner?.vehicle?.vehicle_name) return 'border-emerald-400 ring-2 ring-emerald-50';
    if (neg.status === 'ACCEPTED') return 'border-blue-300';
    if (neg.status === 'REJECTED') return 'border-red-200';
    return 'border-slate-200/90';
  };

  const getRoundBadge = (neg: any) => {
    const rounds = neg.transcript?.length || 0;
    if (neg.status === 'ACCEPTED') return { text: `Accepted in ${rounds} rounds`, color: 'bg-emerald-100 text-emerald-700' };
    if (neg.status === 'REJECTED') return { text: 'Rejected', color: 'bg-red-100 text-red-700' };
    return { text: `${rounds} rounds`, color: 'bg-slate-100 text-slate-600' };
  };

  const handleValidationDone = () => {
    if (activeWinnerHistoryId) {
      updateTransportNegotiationHistory(user, activeWinnerHistoryId, {
        status: 'ACCEPTED',
        decisionAt: new Date().toISOString()
      });
    }
    navigate('/dashboard/transport', { state: { activeTab: 'my_fleet' } });
  };

  return (
    <div className="h-[calc(100vh-90px)] flex flex-col xl:flex-row gap-6 p-4 max-w-[1600px] mx-auto animate-in fade-in duration-300">

      {/* ═══ COLUMN 1: Left Intelligence Panel ═══ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 overflow-y-auto">
        <Link to="/dashboard/transport" className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-emerald-700 transition">
          <ArrowLeft size={16} className="mr-1" /> Exit Workspace
        </Link>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
          <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
            <ShieldCheck size={17} className="text-indigo-600" /> AI Coordination Scope
          </h2>
          <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-xs">
            <p className="font-bold text-indigo-700 uppercase tracking-wider mb-3">TRANSPORTER &bull; TRANSPORT ONLY</p>
            <div className="flex flex-col gap-1.5">
              {[{ label: 'Buyer / Supplier', active: false }, { label: 'Transport', active: true }, { label: 'Warehouse', active: false }, { label: 'Processor', active: false }].map(({ label, active }) => (
                <div key={label} className="flex items-center gap-2">
                  {active ? <CheckCircle size={14} className="text-emerald-600" /> : <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-300" />}
                  <span className={active ? 'text-slate-800 font-bold' : 'text-slate-400'}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Briefcase size={17} className="text-blue-600" /> Logistics Context
            </h2>
            <span className="text-[11px] font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full">{payload?.crop || 'Freight'}</span>
          </div>
          <div className="space-y-2.5 pt-1">
            <div className="flex justify-between text-xs"><span className="text-slate-500">Lot Volume</span><span className="font-black text-slate-800">{payload?.quantity_kg?.toLocaleString()} kg</span></div>
            <div className="flex justify-between text-xs"><span className="text-slate-500">Route</span><span className="font-black text-slate-800 truncate max-w-[130px] text-right">{payload?.pickup_location} → {payload?.delivery_location}</span></div>
            <div className="flex justify-between text-xs"><span className="text-slate-500">Floor Price</span><span className="font-black text-purple-700">Rs.{payload?.floor_price}</span></div>
            {bestPrice > 0 && <div className="flex justify-between text-xs"><span className="text-slate-500">Best Negotiated</span><span className="font-black text-emerald-700">Rs.{bestPrice}</span></div>}
          </div>
          <div className="pt-2 border-t border-slate-100">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Freight Trend (30 Days)</p>
            <PriceChart data={chartData} isTransport={true} />
          </div>
        </div>

        {results && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-3">
            <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Database size={17} className="text-purple-600" /> Negotiation Summary
            </h2>
            <div className="space-y-2">
              <div className="flex justify-between text-xs"><span className="text-slate-500">Total Threads</span><span className="font-bold text-slate-800">{allNegs.length}</span></div>
              <div className="flex justify-between text-xs"><span className="text-slate-500">Accepted</span><span className="font-bold text-emerald-700">{allNegs.filter((n: any) => n.status === 'ACCEPTED').length}</span></div>
              <div className="flex justify-between text-xs"><span className="text-slate-500">Rejected</span><span className="font-bold text-red-600">{allNegs.filter((n: any) => n.status === 'REJECTED').length}</span></div>
              <div className="flex justify-between text-xs"><span className="text-slate-500">Best Price</span><span className="font-bold text-emerald-700">Rs.{bestPrice}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* ═══ COLUMN 2: Top Transporters + Personal Logs ═══ */}
      <div className="w-full xl:w-2/4 bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative">
        <div className="p-3.5 border-b border-slate-100 bg-slate-50 flex flex-wrap justify-between items-center z-10 sticky top-0 gap-2">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-600" /> AI Agent Negotiation
            </h3>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-slate-200/70 p-1 rounded-xl flex items-center gap-1 text-xs">
              <button onClick={() => setActiveTab('dealers')} className={`px-2.5 py-1 rounded-lg font-bold transition ${activeTab === 'dealers' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
                🚛 Top Transporters
              </button>
              <button onClick={() => setActiveTab('terminal')} className={`px-2.5 py-1 rounded-lg font-bold transition flex items-center gap-1 ${activeTab === 'terminal' ? 'bg-slate-900 text-emerald-400 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
                <TerminalIcon size={12} /> Live Terminal
              </button>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isParallelRunning ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}`}></span>
              <span className="text-[10px] font-bold text-slate-500 font-mono uppercase">{isParallelRunning ? 'RUNNING' : 'LIVE'}</span>
            </div>
          </div>
        </div>

        {activeTab === 'dealers' ? (
          <div className="flex-1 overflow-y-auto bg-slate-50/40 p-5 space-y-4">
            {isParallelRunning && sortedNegs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-slate-500 text-sm font-bold">Negotiating with all top transporters simultaneously...</p>
                <p className="text-slate-400 text-xs">Switch to Live Terminal to watch negotiations unfold</p>
              </div>
            )}

            {sortedNegs.length > 0 && (
              <div className="space-y-3">
                {sortedNegs.map((neg: any, i: number) => {
                  const isWin = neg.vehicle?.vehicle_name === winner?.vehicle?.vehicle_name;
                  const price = neg.agreed_price || neg.pricing_rules?.target_price || payload?.floor_price;
                  const transcript = neg.transcript || [];
                  const roundBadge = getRoundBadge(neg);
                  const isExpanded = expandedIdx === i;
                  const visibleCount = revealedCounts[i] ?? transcript.length;

                  return (
                    <div key={i} className={`bg-white border rounded-2xl shadow-sm overflow-hidden transition-all ${getStatusBorder(neg)}`}>
                      {/* Transporter Card Header */}
                      <button className="w-full p-4 text-left hover:bg-slate-50/60 transition" onClick={() => setExpandedIdx(isExpanded ? null : i)}>
                        <div className="flex justify-between items-center mb-2.5">
                          <div>
                            <h4 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                              <Star size={16} className={isWin ? 'text-amber-400 fill-amber-400' : 'text-slate-300'} />
                              {neg.vehicle?.vehicle_name || `Transporter ${i + 1}`}
                              {isWin && <span className="ml-1 text-[9px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full border border-emerald-200">AI Winner</span>}
                            </h4>
                            <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                              <MapPin size={10} /> {neg.vehicle?.type || 'Truck'} &bull; {(neg.vehicle?.capacity_kg || payload?.quantity_kg || 0).toLocaleString()} kg capacity
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="text-right">
                              <span className="font-black text-slate-900 text-lg">Rs.{(price || 0).toLocaleString()}</span>
                              <p className="text-[10px] text-slate-400">Agreed freight</p>
                            </div>
                            {isExpanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                          </div>
                        </div>
                        <div className="space-y-1.5 text-xs pt-2 border-t border-slate-100">
                          <div className="flex justify-between items-center">
                            <span className="text-slate-500 font-medium">Negotiation Rounds:</span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${roundBadge.color}`}>{roundBadge.text}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-slate-500 font-medium">Status:</span>
                            <span className="font-semibold flex items-center gap-1.5">
                              <span className={`w-2 h-2 rounded-full ${neg.status === 'ACCEPTED' ? 'bg-emerald-500 animate-pulse' : neg.status === 'REJECTED' ? 'bg-red-400' : 'bg-blue-500'}`}></span>
                              <span className={neg.status === 'ACCEPTED' ? 'text-emerald-700' : neg.status === 'REJECTED' ? 'text-red-600' : 'text-blue-700'}>{neg.status || 'Evaluating'}</span>
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-slate-500 font-medium">Our Floor Asked:</span>
                            <span className="font-semibold text-slate-700">Rs.{payload?.floor_price?.toLocaleString()}</span>
                          </div>
                        </div>
                        <p className="text-[10px] text-indigo-500 font-bold mt-2 flex items-center gap-1">
                          <Bot size={11} /> {isExpanded ? 'Click to hide negotiation log' : 'Click to view agent communication log'}
                        </p>
                      </button>

                      {/* Personal Negotiation Log */}
                      {isExpanded && (
                        <div className="border-t border-slate-100 bg-slate-50/70 p-4 space-y-4 max-h-[450px] overflow-y-auto">
                          <div className="flex items-center gap-2 text-xs font-bold text-indigo-700 uppercase tracking-wider pb-2 border-b border-slate-100">
                            <Bot size={13} className="text-indigo-500" />
                            Agent Communication Log — {neg.vehicle?.vehicle_name}
                          </div>
                          {transcript.length === 0 ? (
                            <div className="text-center py-6 text-slate-400 text-xs">
                              <Clock size={24} className="mx-auto mb-2 text-slate-300" />
                              No communication log available for this thread.
                            </div>
                          ) : (
                            transcript.slice(0, visibleCount).map((t: any, tIdx: number) => (
                              <React.Fragment key={tIdx}>
                                <div className="flex items-center gap-2 text-[10px] text-slate-400 font-bold uppercase">
                                  <div className="h-px flex-1 bg-slate-200" />
                                  Round {t.round || tIdx + 1}
                                  <div className="h-px flex-1 bg-slate-200" />
                                </div>
                                <OfferCard agent="Farmer / Buyer Agent" price={t.stakeholder_offer} quantity={payload.quantity_kg} quality="Standard" deliveryDate="Immediate" transportIncluded={true} warehouseIncluded={false} validity="24 Hours" isFarmer={false} isTransport={true} />
                                <ChatBubble agent="Farmer / Buyer Agent" price={t.stakeholder_offer} message={t.stakeholder_message || `I need transport for ${payload.quantity_kg}kg of ${payload.crop}. My budget is Rs.${t.stakeholder_offer}.`} isFarmer={false} isSystem={false} isInteractive={false} reasoning={t.stakeholder_reasoning || [`Round ${t.round || tIdx + 1}`]} />
                                <div className="animate-in slide-in-from-right-4 duration-500 fill-mode-both pl-4 space-y-1">
                                  <OfferCard agent="Transporter Agent (You)" price={t.transporter_counter} quantity={payload.quantity_kg} quality="Standard" deliveryDate="Immediate" transportIncluded={true} warehouseIncluded={false} validity="24 Hours" isFarmer={true} isTransport={true} />
                                  <ChatBubble agent="Transporter Agent (You)" price={t.transporter_counter} message={t.message || (t.status === 'ACCEPTED' ? `Deal accepted at Rs.${t.stakeholder_offer}. Vehicle ready to dispatch.` : `Countering at Rs.${t.transporter_counter}. Factoring route distance and fuel.`)} isFarmer={true} isSystem={false} isInteractive={false} reasoning={t.transporter_reasoning || (t.status === 'ACCEPTED' ? [`Final Deal at Rs.${t.stakeholder_offer}`, `Round ${t.round || tIdx + 1}`] : [`Round ${t.round || tIdx + 1}`, `Counter Rs.${t.transporter_counter}`])} />
                                </div>
                                {t.status === 'ACCEPTED' && (
                                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
                                    <span className="text-emerald-800 font-bold text-xs flex items-center justify-center gap-1.5">
                                      <CheckCircle size={14} className="text-emerald-600" /> Deal Finalized at Rs.{t.stakeholder_offer} — Round {t.round || tIdx + 1}
                                    </span>
                                  </div>
                                )}
                                {t.status === 'REJECTED' && (
                                  <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-center">
                                    <span className="text-red-700 font-bold text-xs flex items-center justify-center gap-1.5">
                                      <AlertTriangle size={13} className="text-red-500" /> Offer rejected at Round {t.round || tIdx + 1}
                                    </span>
                                  </div>
                                )}
                              </React.Fragment>
                            ))
                          )}
                          <div ref={messagesEndRef} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Best Deal Banner */}
            {!isParallelRunning && bestNeg && (
              <div className="bg-[#064e3b] p-4 text-white rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md mt-2">
                <div>
                  <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Trophy size={13} className="text-amber-400" /> BEST DEAL SO FAR
                  </p>
                  <div className="flex items-center flex-wrap gap-2 text-xs">
                    <span className="font-bold text-base text-white">{bestNeg.vehicle?.vehicle_name || 'Top Transporter'}</span>
                    <span className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-2 py-0.5 rounded text-xs font-bold">Rs.{bestPrice?.toLocaleString()}/trip</span>
                    <span className="text-emerald-100">{payload?.quantity_kg?.toLocaleString()} kg</span>
                    <span className="text-emerald-100">{bestNeg.transcript?.length || 0} rounds</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto flex-wrap">
                  <button onClick={() => setIsRagOpen(true)} className="px-3.5 py-2 rounded-xl border border-emerald-500/70 text-emerald-100 bg-emerald-800/40 hover:bg-emerald-800 text-xs font-bold transition flex-1 sm:flex-none text-center cursor-pointer">View Analysis</button>
                  <button onClick={() => setShowValidationModal(true)} className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-black text-xs transition shadow flex-1 sm:flex-none text-center cursor-pointer">Accept Deal</button>
                  <button onClick={handleParallelNegotiation} disabled={isParallelRunning} className="px-3.5 py-2 rounded-xl border border-emerald-500/70 text-emerald-100 bg-emerald-800/40 hover:bg-emerald-800 text-xs font-bold transition flex-1 sm:flex-none text-center cursor-pointer disabled:opacity-50">🔁 Re-Negotiate</button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 bg-slate-950 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-2 select-text text-slate-100 flex flex-col">
            <div className="text-slate-500 pb-2 border-b border-slate-800 text-[10px]">
              # LangGraph Multi-Agent Transport Negotiation<br />
              # Route: {payload?.pickup_location} to {payload?.delivery_location} | Floor: Rs.{payload?.floor_price}
            </div>
            {liveTerminalLogs.length === 0 ? (
              <div className="text-center py-16 text-slate-500 space-y-3">
                <TerminalIcon size={32} className="mx-auto text-slate-700" />
                <p>Terminal idle.</p>
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

        <div className="p-3 bg-white border-t border-slate-100 flex items-center justify-between text-xs">
          <button onClick={handleParallelNegotiation} disabled={isParallelRunning} className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50">
            <RefreshCw size={13} className={isParallelRunning ? 'animate-spin text-emerald-400' : 'text-emerald-400'} />
            <span>{isParallelRunning ? 'Negotiating Transport...' : '⚡ Auto-Parallel Negotiation'}</span>
          </button>
          <span className="text-slate-400 text-[11px]">Powered by LangGraph</span>
        </div>
      </div>

      {/* ═══ COLUMN 3: Right Panel ═══ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-6 overflow-y-auto">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 space-y-4">
          <h2 className="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Zap size={17} className="text-emerald-500" /> LangGraph Execution
          </h2>
          <AgentWorkflowStepper activeAgent={isParallelRunning ? 'Negotiator' : 'Deal Finalized'} />
          <button onClick={() => setIsRagOpen(true)} className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition text-xs flex justify-center items-center gap-2 cursor-pointer">
            <Database size={15} className="text-emerald-600" /> View RAG Context
          </button>
        </div>
        {showAgreement ? (
          <AgreementPreview dealData={dealDataForModal} onSignAndClose={() => setShowValidationModal(true)} isTransport={true} />
        ) : (
          <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-5 text-white space-y-4">
            <h3 className="font-bold text-sm flex items-center gap-2"><ShieldCheck size={18} className="text-emerald-400" /> Copilot Override</h3>
            <p className="text-xs text-slate-400 leading-relaxed">Negotiation running across {allNegs.length || '...'} parallel transport threads...</p>
            <div className="space-y-2">
              {['Floor price guardrail active', 'Maharashtra APMC cess factored', 'Multi-modal freight calculated'].map((t) => (
                <div key={t} className="flex items-center gap-2 text-xs text-emerald-300">
                  <CheckCircle size={12} className="text-emerald-400 shrink-0" /> {t}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <RagContextViewer isOpen={isRagOpen} onClose={() => setIsRagOpen(false)} crop={payload?.crop || 'Produce'} query={`transport freight ${payload?.pickup_location}`} />
      <TransactionValidationModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        onDone={handleValidationDone}
        dealData={dealDataForModal}
        buyerUser={user}
        isTransport={true}
      />
    </div>
  );
}
