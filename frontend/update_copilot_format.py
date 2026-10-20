import re

with open('frontend/src/pages/negotiation/NegotiationRoom.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate Column 2 and Column 3
col2_start_marker = "{/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}"
col3_end_marker = "{/* Floating RAG Modal */}"

col2_idx = content.find(col2_start_marker)
col3_end_idx = content.find(col3_end_marker)

if col2_idx != -1 and col3_end_idx != -1:
    new_cols_jsx = """{/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}
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
            
            {liveBuyers.length > 0 ? (
              <>
                <div className="space-y-3">
                  {liveBuyers.map((b, i) => (
                    <div key={i} className={`bg-white border rounded-2xl p-4 shadow-sm relative overflow-hidden transition-all ${b.aiStatus?.includes('Override') ? 'border-indigo-400 ring-2 ring-indigo-50' : 'border-slate-200/90'}`}>
                      
                      <div className="flex justify-between items-center mb-2.5">
                        <h4 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                          <Star size={16} className="text-amber-400 fill-amber-400" /> {b.id} — {b.match}% Match
                        </h4>
                        <span className="font-black text-slate-900 text-lg">₹{b.offer}</span>
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
                            <span className={`w-2 h-2 rounded-full ${b.status === 'Negotiating' ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`}></span>
                            <span className={b.status === 'Negotiating' ? 'text-emerald-700' : 'text-blue-700'}>{b.status}</span>
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
                        ₹{liveBuyers[0].offer}/q
                      </span>
                      <span className="text-emerald-100">{cropQty.toLocaleString()} Q</span>
                      <span className="text-emerald-100">{liveBuyers[0].match}% Match</span>
                      <span className="font-bold text-emerald-200">
                        Net: ₹{(liveBuyers[0].offer * cropQty - 1850).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
                    <button 
                      onClick={() => setIsRagOpen(true)}
                      className="px-3.5 py-2 rounded-xl border border-emerald-500/70 text-emerald-100 bg-emerald-800/40 hover:bg-emerald-800 text-xs font-bold transition flex-1 sm:flex-none text-center"
                    >
                      View Analysis
                    </button>
                    <button 
                      onClick={() => {
                        setAgreementData({ ...negState, price: liveBuyers[0].offer, farmer: user?.name, buyer: liveBuyers[0].id });
                        setShowValidationModal(true);
                      }}
                      className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-black text-xs transition shadow flex-1 sm:flex-none text-center"
                    >
                      Accept Deal
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="py-8 px-6">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-2">
                  <Search className="text-emerald-500" /> AI MATCHING
                </h2>
                <p className="text-indigo-600 font-bold text-sm mb-6 flex items-center gap-2">
                  <span className="text-base">🔎</span> Finding suitable buyers...
                </p>
                
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">MATCHING AGAINST:</p>
                  <ul className="space-y-3">
                    {['Crop & Variety', 'Quantity required', 'Quality Grade', 'Location & Distance', 'Price expectations', 'Logistics availability'].map((txt, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                        <CheckCircle size={16} className="text-emerald-500" /> {txt}
                      </li>
                    ))}
                  </ul>
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
            </div>

            <div className="space-y-3 mb-5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                <span>PLANNING</span>
                <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1 border border-emerald-100">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> RUNNING
                </span>
              </div>
              <div className="text-xs font-bold text-slate-400">INTELLIGENCE</div>
              <div className="text-xs font-bold text-slate-400">NEGOTIATION</div>
              <div className="text-xs font-bold text-slate-400">VALIDATION</div>
            </div>
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

        {/* Card 2: Farmer Copilot (Dark Theme exactly matching user image) */}
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

      </div>
      """

    content = content[:col2_idx] + new_cols_jsx + content[col3_end_idx:]
    print("Replaced Col 2 and Col 3 with exact user screenshot format successfully!")
else:
    print(f"Markers not found: col2={col2_idx}, col3_end={col3_end_idx}")

with open('frontend/src/pages/negotiation/NegotiationRoom.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished writing NegotiationRoom.tsx")
