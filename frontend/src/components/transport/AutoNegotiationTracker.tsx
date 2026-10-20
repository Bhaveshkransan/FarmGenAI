import React, { useEffect, useState } from 'react';
import { TruckIcon, CheckCircleIcon, XCircleIcon, ClockIcon, CpuChipIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import { SparklesIcon } from '@heroicons/react/24/solid';

interface TranscriptItem {
  round: number;
  stakeholder_offer: number;
  transporter_counter: number | null;
  status: string;
  message: string;
}

interface NegotiationResult {
  vehicle: any;
  status: string;
  agreed_price: number | null;
  transcript: TranscriptItem[];
  pricing_rules?: {
    floor_price: number;
    market_average: number;
    target_price: number;
    initial_quote: number;
  };
}

import { useWebSocket } from '@/hooks/useWebSocket';

interface AutoNegotiationTrackerProps {
  negotiations: NegotiationResult[];
  winner: NegotiationResult | null;
  onClose: () => void;
  negotiationId?: string;
  wsUrl?: string;
}

const AutoNegotiationTracker: React.FC<AutoNegotiationTrackerProps> = ({ 
  negotiations, 
  winner, 
  onClose,
  negotiationId,
  wsUrl
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [aiLogs, setAiLogs] = useState<string[]>([]);
  const [selectedWinnerId, setSelectedWinnerId] = useState<string | null>(null);

  // Real-Time WebSocket stream connection if negotiationId provided
  const effectiveWsUrl = wsUrl || (negotiationId ? `/api/v1/ws?negotiation_id=${negotiationId}` : null);
  const { isConnected, lastMessage } = useWebSocket(effectiveWsUrl || '');

  // Handle live incoming WebSocket frames
  useEffect(() => {
    if (!lastMessage || typeof lastMessage !== 'object') return;
    const evt = lastMessage as any;
    const msgType = evt.event_type || evt.event;

    if (evt.message) {
      setAiLogs(prev => [...prev, evt.message]);
    }

    if (msgType === 'TRANSPORT_MATCHING_STARTED') {
      setAiLogs(prev => [...prev, 'Live Event: Matching started. Scanning regional fleet...']);
    } else if (msgType === 'TRANSPORT_NEGOTIATION_STARTED') {
      setActiveStep(1);
      setAiLogs(prev => [...prev, 'Live Event: Parallel negotiation channels opened.']);
    } else if (msgType === 'TRANSPORTER_RESPONSE' || msgType === 'TRANSPORT_COUNTER_OFFER') {
      setActiveStep(prev => prev + 1);
      setAiLogs(prev => [...prev, 'Live Event: Received counter-offer from candidate fleet.']);
    } else if (msgType === 'TRANSPORT_SELECTED') {
      setAiLogs(prev => [...prev, 'Live Event: Optimal transporter selected. Finalizing booking...']);
      if (evt.payload?.vehicle_id) {
        setSelectedWinnerId(evt.payload.vehicle_id);
      }
    } else if (msgType === 'TRANSPORT_COMPLETED') {
      setCompleted(true);
      setAiLogs(prev => [...prev, 'Live Event: Booking confirmed! Deal finalized.']);
      if (evt.payload?.vehicle_id) {
        setSelectedWinnerId(evt.payload.vehicle_id);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    if (completed && winner && !selectedWinnerId) {
      setSelectedWinnerId(winner.vehicle.vehicle_id);
    }
  }, [completed, winner, selectedWinnerId]);

  useEffect(() => {
    // If connected to live WebSocket, skip simulated setInterval timer playback
    if (effectiveWsUrl && isConnected) return;

    // Generate AI Logs for simulated demo mode
    const initialLogs = [
      "Initializing LangGraph Orchestrator...",
      "Connecting to OSRM API for optimal routing...",
      "Analyzing 3 alternate highway routes...",
      "Fetching live NHAI toll rates...",
      "Calculating baseline driver & fuel margins...",
      "Establishing absolute floor prices...",
      "Initiating parallel negotiation channels with top Transporter Agents..."
    ];
    
    let logIdx = 0;
    const logInterval = setInterval(() => {
      if (logIdx < initialLogs.length) {
        setAiLogs(prev => [...prev, initialLogs[logIdx]]);
        logIdx++;
      } else {
        clearInterval(logInterval);
      }
    }, 800);

    // Progression of Negotiation rounds
    const maxRounds = Math.max(...negotiations.map(n => n.transcript.length));
    let currentStep = 0;
    
    const roundInterval = setInterval(() => {
      if (currentStep < maxRounds) {
        setActiveStep(prev => prev + 1);
        setAiLogs(prev => [...prev, `Evaluating Round ${currentStep + 1} offers...`]);
        currentStep++;
      } else {
        setCompleted(true);
        setAiLogs(prev => [...prev, "Negotiation concluded. Optimal deal secured!"]);
        clearInterval(roundInterval);
      }
    }, 2500);

    return () => {
      clearInterval(logInterval);
      clearInterval(roundInterval);
    };
  }, [negotiations, effectiveWsUrl, isConnected]);

  const hasAcceptedDeal = negotiations.some(n => n.status === 'ACCEPTED');

  return (
    <div id="auto-negotiation-tracker-modal" className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-8 animate-in fade-in zoom-in-95 duration-500">
      {/* Dark blur backdrop */}
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-2xl"></div>
      
      {/* Main Command Center Container */}
      <div className="relative w-full max-w-7xl h-full max-h-[90vh] bg-slate-900 border border-slate-700/50 rounded-3xl shadow-2xl flex flex-col overflow-hidden ring-1 ring-white/10">
        
        {/* Header */}
        <div className="flex-none p-6 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-amber-500/20 rounded-xl border border-amber-500/30">
              <SparklesIcon className="h-8 w-8 text-amber-500 animate-pulse" />
            </div>
            <div>
              <h2 className="text-3xl font-extrabold text-white tracking-tight">AI Negotiation War Room</h2>
              <p 
                id="tracker-system-status"
                data-testid="tracker-status-indicator"
                data-status={completed ? (hasAcceptedDeal ? 'DEAL_SECURED' : 'DEALS_FAILED') : 'NEGOTIATING_LIVE'}
                className="text-amber-400/80 font-mono text-sm mt-1 flex items-center gap-2"
              >
                <span className="relative flex h-3 w-3">
                  {!completed && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>}
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${completed ? (hasAcceptedDeal ? 'bg-emerald-500' : 'bg-rose-500') : 'bg-amber-500'}`}></span>
                </span>
                <span id="tracker-status-text">
                  {completed ? (hasAcceptedDeal ? "SYSTEM IDLE - DEAL SECURED" : "SYSTEM IDLE - ALL DEALS FAILED") : "SYSTEM ACTIVE - NEGOTIATING LIVE"}
                </span>
                {effectiveWsUrl && (
                  <span 
                    id="tracker-connection-badge"
                    data-connected={isConnected}
                    className={`ml-3 px-2 py-0.5 rounded-full text-xs font-semibold border ${
                      isConnected
                        ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                        : 'bg-slate-700/40 border-slate-600/40 text-slate-400'
                    }`}
                  >
                    {isConnected ? '⚡ LIVE' : '○ Connecting...'}
                  </span>
                )}
              </p>
            </div>
          </div>
          {completed && (
            <div className="flex items-center gap-3">
              {hasAcceptedDeal ? (
                <button 
                  id="tracker-accept-booking-btn"
                  onClick={() => {
                    const finalWinner = negotiations.find(n => n.vehicle.vehicle_id === selectedWinnerId) || winner;
                    onClose();
                  }}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-3 rounded-xl shadow-lg hover:shadow-emerald-500/20 transition-all flex items-center gap-2"
                >
                  <CheckCircleIcon className="h-5 w-5" /> Accept & Book {selectedWinnerId && selectedWinnerId !== winner?.vehicle.vehicle_id ? '(Manual Select)' : ''}
                </button>
              ) : (
                <button 
                  onClick={() => {
                    alert('Initiating manual negotiation workflow...');
                    onClose();
                  }}
                  className="bg-amber-600 hover:bg-amber-500 text-white font-bold px-6 py-3 rounded-xl shadow-lg hover:shadow-amber-500/20 transition-all flex items-center gap-2"
                >
                  <TruckIcon className="h-5 w-5" /> Initiate Manual Negotiation
                </button>
              )}
            </div>
          )}
        </div>

        {/* Content Layout */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          
          {/* Left Panel: AI Brain Logs */}
          <div className="w-full lg:w-1/3 border-r border-slate-700/50 bg-slate-950/80 p-6 hidden md:flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl"></div>
            <h3 className="text-slate-300 font-bold uppercase text-sm tracking-widest mb-6 flex items-center gap-3 relative z-10">
              <CpuChipIcon className="h-6 w-6 text-indigo-400" /> Agent Processing Logs
            </h3>
            <div className="flex-1 overflow-y-auto font-mono text-sm space-y-4 custom-scrollbar pr-2 relative z-10 break-words whitespace-pre-wrap">
              {aiLogs.map((log, i) => (
                <div key={i} className="text-indigo-200/90 animate-in slide-in-from-left-2 fade-in bg-slate-900/50 p-3 rounded-lg border border-indigo-500/10">
                  <span className="text-slate-500 mr-2 text-xs">[{new Date().toISOString().split('T')[1].substring(0,8)}]</span>
                  <span className={log?.includes('concluded') ? 'text-emerald-400 font-bold' : ''}>{log}</span>
                </div>
              ))}
              {!completed && (
                <div className="flex items-center gap-3 text-indigo-400/70 mt-6 p-3">
                  <span className="h-2 w-2 bg-indigo-500 rounded-full animate-ping"></span> Processing strategy...
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Negotiation Channels */}
          <div className="flex-1 p-8 overflow-y-auto bg-slate-900/90 custom-scrollbar relative">
            <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-slate-950/50 to-transparent pointer-events-none"></div>
            <h3 className="text-slate-300 font-bold uppercase text-sm tracking-widest mb-8 flex items-center gap-3 relative z-10">
              <ChartBarIcon className="h-6 w-6 text-sky-400" /> Live Agent Channels
            </h3>
            
            <div className="flex flex-nowrap overflow-x-auto gap-6 relative z-10 pb-4 h-full custom-scrollbar items-start">
              {negotiations.map((neg, idx) => {
                const isSelected = completed && selectedWinnerId === neg.vehicle.vehicle_id;
                const isWinner = completed && winner && winner.vehicle.vehicle_id === neg.vehicle.vehicle_id;
                const isAccepted = completed && neg.status === 'ACCEPTED';
                const isRejected = completed && neg.status !== 'ACCEPTED';
                
                return (
                  <div 
                    key={idx} 
                    onClick={() => {
                      if (completed && isAccepted) setSelectedWinnerId(neg.vehicle.vehicle_id);
                    }}
                    className={`relative rounded-2xl p-5 transition-all duration-300 border flex flex-col min-w-[340px] max-w-[400px] flex-shrink-0 h-full max-h-full ${
                      isSelected 
                        ? 'bg-gradient-to-b from-slate-800 to-emerald-950/40 border-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.3)] ring-2 ring-emerald-500 cursor-pointer transform scale-[1.02]' 
                        : isAccepted
                          ? 'bg-slate-800 border-emerald-500/30 shadow-xl cursor-pointer hover:border-emerald-500/60'
                          : isRejected
                            ? 'bg-slate-950/50 border-slate-800 opacity-60'
                            : 'bg-slate-800 border-slate-700 shadow-xl'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute -top-4 -right-4 bg-emerald-500 text-white rounded-full p-1.5 shadow-[0_0_15px_rgba(16,185,129,0.5)] animate-bounce z-20">
                        <CheckCircleIcon className="h-8 w-8" />
                      </div>
                    )}
                    
                    {isWinner && !isSelected && (
                      <div className="absolute -top-3 left-4 bg-emerald-600 text-white text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-full shadow-sm z-20">
                        AI Recommended Deal
                      </div>
                    )}

                    {/* Transporter Header */}
                    <div className="flex justify-between items-start mb-5 pb-4 border-b border-slate-700/50">
                      <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-xl ${isSelected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-sky-400'}`}>
                          <TruckIcon className="h-6 w-6" />
                        </div>
                        <div>
                          <h4 className="font-bold text-white leading-tight text-sm truncate max-w-[140px]">{neg.vehicle.vehicle_name}</h4>
                          <span className="text-xs font-mono text-slate-400">{neg.vehicle.vehicle_type}</span>
                          {neg.route?.route_path && (
                            <div className="text-[9px] font-mono text-sky-300/80 mt-1 truncate max-w-[140px]" title={neg.route.route_path}>
                              {neg.route.route_path}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Live Market Analysis */}
                      {neg.pricing_rules && (
                        <div className="text-right flex flex-col gap-1">
                          <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">AI Target Bounds</div>
                          <div className="text-xs font-mono text-emerald-400">Mark: ₹{neg.pricing_rules.market_average}</div>
                          <div className="text-xs font-mono text-rose-400">Floor: ₹{neg.pricing_rules.floor_price}</div>
                        </div>
                      )}
                    </div>

                    {/* Chat Interface */}
                    <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar min-h-[300px]">
                      {neg.transcript.slice(0, activeStep + 1).map((round, rIdx) => (
                        <div key={rIdx} className="space-y-4 animate-in slide-in-from-bottom-4 fade-in duration-500">
                          
                          {/* Stakeholder Offer (Right Side) */}
                          <div className="flex justify-end">
                            <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-sky-600 to-blue-600 px-4 py-2.5 text-white shadow-lg border border-sky-400/30">
                              <span className="text-[9px] uppercase tracking-widest font-bold opacity-70 block mb-1 text-right">Farmer Agent</span>
                              <div className="text-sm font-medium">Offered ₹{round.stakeholder_offer}</div>
                            </div>
                          </div>
                          
                          {/* Transporter Response (Left Side) */}
                          <div className="flex justify-start">
                            <div className={`max-w-[90%] rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm shadow-md border ${
                              round.status === 'ACCEPTED' ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-100' :
                              round.status === 'REJECTED' ? 'bg-rose-950/50 border-rose-500/30 text-rose-200' :
                              'bg-slate-700/80 border-slate-600 text-slate-200'
                            }`}>
                              <span className={`text-[9px] uppercase tracking-widest font-bold block mb-1 ${round.status === 'ACCEPTED' ? 'text-emerald-400' : 'text-slate-400'}`}>
                                Transport Agent {round.status === 'ACCEPTED' ? '(ACCEPTED)' : ''}
                              </span>
                              <p className="leading-relaxed">{round.message}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                      
                      {!completed && activeStep < neg.transcript.length && (
                        <div className="flex justify-start items-center text-slate-500 text-xs font-mono gap-2 mt-4 animate-pulse">
                          <ClockIcon className="h-4 w-4" /> Analyzing counter-offer matrix...
                        </div>
                      )}
                    </div>

                    {/* Footer Status */}
                    {completed && (
                      <div className={`mt-5 pt-4 border-t flex justify-between items-center bg-slate-950/50 -mx-5 -mb-5 px-5 py-4 rounded-b-2xl flex-shrink-0 ${
                        isSelected ? 'border-emerald-500' : 'border-slate-800'
                      }`}>
                        <span className="text-xs uppercase tracking-widest font-bold text-slate-400">Final Outcome</span>
                        {neg.status === 'ACCEPTED' ? (
                          <div className="flex flex-col items-end">
                            <span className="font-black text-xl text-emerald-400 shadow-emerald-500/20 drop-shadow-md">₹{neg.agreed_price}</span>
                            {!isSelected && <span className="text-[10px] text-emerald-500/70 animate-pulse mt-0.5">Click to select</span>}
                          </div>
                        ) : (
                          <span className="font-bold text-sm text-rose-500 flex items-center gap-1"><XCircleIcon className="h-5 w-5"/> TERMINATED</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutoNegotiationTracker;
