import re

with open('c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the useEffect for WebSocket handling to listen to NEGOTIATION_STATE_UPDATE
ws_effect_code = """
  // Handle incoming WS messages
  useEffect(() => {
    if (lastMessage && String(lastMessage.negotiation_id) === String(id)) {
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
        
        if (state.status === 'DEAL' || state.deal) {
          setAgreementData(state.deal || state);
          setShowAgreement(true);
        }
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
          buyer: user?.name || user?.full_name || 'Buyer Enterprise'
        };
        setAgreementData(finalDeal);
        setShowAgreement(true);
        refetchNeg();
      }
    }
  }, [lastMessage, id, negState, cropQty, targetPrice, statutoryBench, user, refetchNeg]);
"""
# Replace the old useEffect
start_idx = content.find('// Handle incoming WS messages')
end_idx = content.find('const runParallelAutonomousNegotiation', start_idx)
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + ws_effect_code + content[end_idx:]


# 2. Replace the JSX Layout
jsx_replacement = """
      {/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}
      <div className="w-full xl:w-2/4 flex flex-col gap-4">
        
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative flex-1">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center z-10 sticky top-0 bg-white">
            <h3 className="font-bold text-slate-700 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-600" /> AI Agent Negotiation — <span className="text-slate-400 font-normal">{cropName}</span>
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Live</span>
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-50/30 p-6 space-y-4">
            
            {liveBuyers.length > 0 ? (
              <>
                <div className="mb-2">
                  <h3 className="font-black text-slate-800 tracking-wide text-sm uppercase">Top Matches & Negotiations</h3>
                  <p className="text-xs text-emerald-600 font-bold flex items-center gap-1 mt-1">
                    <Search size={12} /> {liveBuyers.length} matching buyers found
                  </p>
                </div>
                
                {liveBuyers.map((b, i) => (
                  <div key={i} className={`bg-white border rounded-2xl p-5 shadow-sm relative overflow-hidden transition-all ${b.aiStatus.includes('Override') ? 'border-emerald-500 ring-2 ring-emerald-100' : 'border-slate-200'}`}>
                    
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                          <Star size={16} className="text-amber-400 fill-amber-400" /> {b.id}
                          <span className="text-emerald-600 font-bold text-xs ml-1">{b.match}% Match</span>
                        </h4>
                        <p className="text-[11px] text-slate-500 mt-1">Distance: {b.distance} • Req: {b.req}</p>
                      </div>
                      <span className="text-[10px] font-bold bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full flex items-center gap-1.5 uppercase tracking-wider">
                         <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> {b.status}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 pt-3 border-t border-slate-100">
                      <div>
                        <p className="text-[10px] text-slate-400 uppercase font-bold mb-1">Initial Offer</p>
                        <p className="font-bold text-slate-700 text-sm">₹{b.initialOffer}/kg</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-400 uppercase font-bold mb-1">Latest Negotiated</p>
                        <p className="font-black text-emerald-600 text-base">₹{b.offer}/kg</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] text-slate-400 uppercase font-bold mb-1">AI Status</p>
                        <p className="font-bold text-slate-700 text-xs flex items-center justify-end gap-1">
                          {b.aiStatus.includes('Override') ? <ShieldCheck size={12} className="text-indigo-600" /> : <Bot size={12} className="text-slate-500" />}
                          {b.aiStatus}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </>
            ) : (
              <div className="py-8 px-6">
                 <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-2"><Search className="text-emerald-500" /> AI MATCHING</h2>
                 <p className="text-indigo-600 font-bold text-sm mb-6 flex items-center gap-2"><div className="w-4 h-4 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin"></div> Finding suitable buyers...</p>
                 
                 <div className="bg-white border border-slate-200 rounded-2xl p-6">
                   <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Matching Against:</p>
                   <ul className="space-y-3">
                     {['Crop & Variety', 'Quantity required', 'Quality Grade', 'Location & Distance', 'Price expectations', 'Logistics availability'].map((txt, i) => (
                       <li key={i} className="flex items-center gap-2 text-sm text-slate-700"><CheckCircle size={16} className="text-emerald-500" /> {txt}</li>
                     ))}
                   </ul>
                 </div>
              </div>
            )}
            
            {/* Live Terminal inside the scrolling panel at the bottom */}
            <div className="mt-6 bg-slate-900 rounded-xl p-4 font-mono text-[10px] leading-relaxed overflow-y-auto max-h-48 text-slate-300">
              <div className="text-emerald-500 font-bold mb-2 uppercase tracking-widest text-[9px]">Live Activity</div>
              {liveTerminalLogs.length === 0 ? (
                <div className="text-slate-600 italic">Waiting for negotiation streams...</div>
              ) : (
                liveTerminalLogs.map((log, lIdx) => (
                  <div key={lIdx} className="flex items-start gap-2 animate-in fade-in duration-150">
                    <span className="text-slate-600 shrink-0">[{log.time}]</span>
                    <span className={`font-bold shrink-0 ${log.color || 'text-blue-400'}`}>[{log.tag}]</span>
                    <span className="text-slate-300 break-words flex-1">{log.text}</span>
                  </div>
                ))
              )}
              <div ref={terminalEndRef} />
            </div>

          </div>
          
          {/* Best Deal So Far (Bottom fixed inside center column) */}
          {liveBuyers.length > 0 && (
            <div className="bg-emerald-700 p-4 text-white flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <p className="text-emerald-200 text-[10px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5"><Trophy size={12} className="text-yellow-400" /> BEST DEAL SO FAR</p>
                <div className="flex items-center gap-4">
                  <span className="font-bold text-lg">{liveBuyers[0].id}</span>
                  <div className="text-xs text-emerald-100 flex gap-3">
                     <span>Gross: ₹{(liveBuyers[0].offer * cropQty).toLocaleString()}</span>
                     <span>Transport: -₹1,850</span>
                  </div>
                </div>
                <div className="mt-1 flex items-center gap-2">
                   <span className="text-xl font-black">₹{liveBuyers[0].offer}/kg</span>
                   <span className="text-xs">• {cropQty.toLocaleString()} kg • {liveBuyers[0].match}% Match</span>
                   <span className="ml-4 font-black text-lg bg-emerald-800 px-3 py-0.5 rounded-lg border border-emerald-600">Net: ₹{(liveBuyers[0].offer * cropQty - 1850).toLocaleString()}</span>
                </div>
              </div>
              <button onClick={() => {
                  setAgreementData({...negState, price: liveBuyers[0].offer, farmer: user?.name, buyer: liveBuyers[0].id});
                  setShowValidationModal(true);
              }} className="px-6 py-3 bg-white text-emerald-800 hover:bg-emerald-50 font-black text-sm rounded-xl transition shadow-lg shrink-0 w-full sm:w-auto">
                Accept Deal
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* ════ COLUMN 3: Right Panel (Stacked: LangGraph / RAG / Copilot ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 h-full">
        
        {/* LangGraph Execution */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5">
           <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2 mb-4">
             <Zap size={16} className="text-emerald-500" /> LangGraph Execution
           </h4>
           <AgentWorkflowStepper activeAgent={activeAgent} />
        </div>

        {/* View RAG Context Button */}
        <button 
          onClick={() => setIsRagOpen(true)}
          className="w-full py-3.5 bg-white hover:bg-slate-50 border border-slate-200/80 text-slate-700 font-bold rounded-2xl transition text-sm flex justify-center items-center gap-2 shadow-sm"
        >
          <Database size={16} className="text-slate-500" /> View RAG Context
        </button>

        {/* Copilot OR Agreement Preview */}
        {showAgreement ? (
          <div className="bg-emerald-600 rounded-2xl shadow-sm border border-emerald-500 p-5 text-white flex-1 flex flex-col">
            <h3 className="font-bold flex items-center gap-2 mb-2"><ShieldCheck size={18} /> Final Agreement Preview</h3>
            <p className="text-emerald-100 text-xs mb-4">Smart Contract execution pending signature.</p>
            <div className="bg-white rounded-xl p-4 text-slate-800 flex-1 overflow-y-auto text-sm space-y-4">
               <p className="font-bold text-center text-xs uppercase tracking-wider text-slate-400 pb-2 border-b">Term Sheet - {cropName}</p>
               <div className="flex justify-between">
                 <div>
                   <p className="text-[10px] text-slate-400 font-bold uppercase">Seller</p>
                   <p className="font-bold">{user?.name || 'Farmer'}</p>
                 </div>
                 <div className="text-right">
                   <p className="text-[10px] text-slate-400 font-bold uppercase">Buyer</p>
                   <p className="font-bold">{agreementData?.buyer || 'Buyer'}</p>
                 </div>
               </div>
               <div>
                 <p className="text-[10px] text-slate-400 font-bold uppercase mb-1">Commodity Terms</p>
                 <p className="font-bold text-slate-700 bg-slate-50 p-2 rounded">{cropQty} kg of {cropName} (Grade A)</p>
               </div>
            </div>
            <button onClick={() => setShowValidationModal(true)} className="mt-4 w-full py-3 bg-emerald-800 hover:bg-emerald-900 text-white font-bold rounded-xl transition">Sign & Execute</button>
          </div>
        ) : (
          <div className="bg-[#0f172a] rounded-2xl shadow-lg border border-slate-800 p-5 text-white flex-1 flex flex-col relative overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <Bot size={18} className="text-emerald-400" /> Farmer Copilot
              </h3>
              <ShieldCheck size={14} className="text-slate-500" />
            </div>

            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              AI is negotiating automatically based on your listing, market conditions and negotiation policy. You can intervene at any time.
            </p>

            <div className="flex-1 overflow-y-auto space-y-3 pr-2 mb-4">
              {copilotMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.sender === 'Farmer' ? 'items-end' : 'items-start'}`}>
                  <div className={`p-2.5 max-w-[90%] text-xs leading-relaxed rounded-xl ${msg.sender === 'Farmer' ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-300 rounded-bl-none border border-slate-700'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-3 mt-auto relative z-10">
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => setCopilotCommand(`Don't go below ${statutoryBench || targetPrice}`)} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-bold border border-slate-700 transition">Don't go below ₹{statutoryBench || targetPrice}</button>
                <button type="button" onClick={() => setCopilotCommand('Counter best buyer')} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-bold border border-slate-700 transition">Counter best buyer</button>
                <button type="button" onClick={() => setCopilotCommand('Pause negotiations')} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[10px] font-bold border border-slate-700 transition">Pause negotiations</button>
              </div>

              <form onSubmit={handleCopilotSubmit}>
                <input 
                  type="text" 
                  value={copilotCommand}
                  onChange={e => setCopilotCommand(e.target.value)}
                  placeholder="e.g. \\"Try to get ₹67 from the best...\\"" 
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500 transition mb-3"
                />
                <button type="submit" className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition shadow">
                  Send Instruction
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
"""

start_idx = content.find('{/* ════ COLUMN 2:')
end_idx = content.find('{/* Floating RAG Modal */}')
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + jsx_replacement + content[end_idx:]

with open('c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Update V3 applied.")
