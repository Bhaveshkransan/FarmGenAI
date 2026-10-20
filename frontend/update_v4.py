import re

with open('frontend/src/pages/negotiation/NegotiationRoom.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update initial copilotMessages to match the screenshot example
old_copilot_init = """  const [copilotMessages, setCopilotMessages] = useState<{sender: string, text: string, time: string}[]>([
    { sender: 'AI', text: 'I am your negotiation copilot. Give me manual instructions like "Set minimum to 2500" or "Counter Buyer A at 2600".', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);"""

new_copilot_init = """  const [copilotMessages, setCopilotMessages] = useState<{sender: string, text: string, time: string}[]>([
    { sender: 'AI', text: 'I am your negotiation copilot. Give me manual instructions like "Set minimum to 2500" or "Counter Buyer A at 2600".', time: '11:47 PM' },
    { sender: 'Farmer', text: 'Set minimum to 2500', time: '11:49:19 PM' },
    { sender: 'AI', text: "Understood. I'll update your negotiation floor to ₹2500/q.", time: '11:49:33 PM' },
    { sender: 'Farmer', text: 'Counter Buyer A at 2500', time: '11:52:58 PM' },
    { sender: 'AI', text: 'Manual instruction applied. Negotiators are updating counter offers.', time: '11:52:59 PM' }
  ]);"""

if old_copilot_init in content:
    content = content.replace(old_copilot_init, new_copilot_init)
    print("Replaced initial copilot messages successfully")

# 2. Update initial liveBuyers to match screenshot
old_buyers = """  const [liveBuyers, setLiveBuyers] = useState([
    { id: 'Buyer A', match: 96, offer: 2500, aiStatus: 'Counter ₹2550', status: 'Negotiating', color: 'emerald' },
    { id: 'Buyer B', match: 91, offer: 2480, aiStatus: 'Negotiating...', status: 'Waiting', color: 'blue' },
    { id: 'Buyer C', match: 87, offer: 2420, aiStatus: 'Counter ₹2500', status: 'Negotiating', color: 'amber' }
  ]);"""

new_buyers = """  const [liveBuyers, setLiveBuyers] = useState([
    { id: 'Buyer A', match: 96, offer: 2500, aiStatus: 'Farmer Override: ₹2500', status: 'Negotiating', color: 'emerald' },
    { id: 'Buyer B', match: 91, offer: 2480, aiStatus: 'Negotiating...', status: 'Waiting', color: 'blue' },
    { id: 'Buyer C', match: 87, offer: 2420, aiStatus: 'Counter ₹2500', status: 'Negotiating', color: 'amber' }
  ]);"""

if old_buyers in content:
    content = content.replace(old_buyers, new_buyers)
    print("Replaced initial live buyers successfully")

# 3. Replace Column 2 and Column 3 with exact screenshot layout
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
              <MessageSquare size={17} className="text-emerald-500" /> LIVE NEGOTIATIONS
            </h3>
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> WS CONNECTED ✓
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-50/40 p-5 space-y-4">
            
            {liveBuyers.length > 0 ? (
              liveBuyers.map((b, i) => (
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
              ))
            ) : (
              <div className="py-8 px-6 text-center">
                 <p className="text-indigo-600 font-bold text-sm flex items-center justify-center gap-2"><div className="w-4 h-4 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin"></div> Scanning buyers for {cropName}...</p>
              </div>
            )}

            {/* Live Terminal logs at bottom */}
            {liveTerminalLogs.length > 0 && (
              <div className="mt-4 bg-slate-900 rounded-xl p-3 font-mono text-[10px] leading-relaxed overflow-y-auto max-h-36 text-slate-300">
                <div className="text-emerald-500 font-bold mb-1.5 uppercase tracking-widest text-[9px]">Live Activity</div>
                {liveTerminalLogs.map((log, lIdx) => (
                  <div key={lIdx} className="flex items-start gap-2">
                    <span className="text-slate-600 shrink-0">[{log.time}]</span>
                    <span className={`font-bold shrink-0 ${log.color || 'text-blue-400'}`}>[{log.tag}]</span>
                    <span className="text-slate-300 break-words flex-1">{log.text}</span>
                  </div>
                ))}
                <div ref={terminalEndRef} />
              </div>
            )}
          </div>
          
          {/* Best Deal So Far (Bottom Banner inside center column) */}
          {liveBuyers.length > 0 && (
            <div className="bg-[#064e3b] p-4 text-white rounded-b-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md">
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
                  onClick={() => setRightTab('ai')}
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
          )}
        </div>
      </div>
      
      {/* ════ COLUMN 3: Right Panel (Tabs: AI / RAG / COPILOT ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-3 h-full">
        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
          <button 
            type="button"
            onClick={() => setRightTab('ai')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition ${rightTab === 'ai' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <Sparkles size={13} className="text-pink-500" /> AI
          </button>
          <button 
            type="button"
            onClick={() => setRightTab('rag')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition ${rightTab === 'rag' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <Database size={13} className="text-emerald-500" /> RAG
          </button>
          <button 
            type="button"
            onClick={() => setRightTab('copilot')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition ${rightTab === 'copilot' ? 'bg-[#5046e5] text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <Bot size={13} /> COPILOT
          </button>
        </div>

        {/* Tab 1: AI (LangGraph Execution) */}
        {rightTab === 'ai' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 flex flex-col gap-4 flex-1 overflow-y-auto">
            <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Zap size={16} className="text-emerald-500" /> LangGraph Execution Flow
            </h4>
            <AgentWorkflowStepper activeAgent={activeAgent} />
            
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Autonomous Graph State</p>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Active Node</span>
                  <span className="font-bold text-emerald-600">parallel_negotiate</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Target Range</span>
                  <span className="font-bold text-slate-700">₹{minAllowedFloor} - ₹{maxAllowedCeiling}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">RL Reward State</span>
                  <span className="font-bold text-indigo-600">+0.84 Convergence</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: RAG (APMC Mandi Intelligence) */}
        {rightTab === 'rag' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 flex flex-col gap-3 flex-1 overflow-y-auto">
            <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Database size={16} className="text-emerald-500" /> APMC Mandi Intelligence
            </h4>
            <div className="relative mb-2">
              <input
                type="text"
                readOnly
                value={`${cropName} Mandi Rates Maharashtra`}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-600"
              />
              <Search size={14} className="absolute right-3 top-2.5 text-slate-400" />
            </div>
            <div className="space-y-2.5">
              <div className="p-3 bg-emerald-50/60 border border-emerald-100 rounded-xl text-xs">
                <p className="font-bold text-emerald-800 mb-1">Lasalgaon / Latur APMC Modal Rate</p>
                <p className="text-slate-600 text-[11px]">Today modal price settled at ₹{marketPrice}/kg (+1.8% WoW). High arrivals from Nashik corridor.</p>
              </div>
              <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-xl text-xs">
                <p className="font-bold text-blue-800 mb-1">APMC Statutory Minimum Guarantee</p>
                <p className="text-slate-600 text-[11px]">CACP mandated floor benchmark: ₹{statutoryBench}/kg. Automated guardrail enforces contract validity.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: COPILOT (Interactive chat matching screenshot) */}
        {rightTab === 'copilot' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-4 flex-1 flex flex-col h-full overflow-hidden">
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {copilotMessages.map((msg, i) => (
                <div key={i} className="flex flex-col">
                  {msg.sender === 'AI' ? (
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-400 font-semibold">AI • {msg.time}</p>
                      <div className="bg-slate-100 text-slate-800 text-xs p-3 rounded-2xl rounded-tl-sm max-w-[90%] leading-relaxed">
                        {msg.text}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1 flex flex-col items-end">
                      <p className="text-[10px] text-slate-400 font-semibold">Farmer • {msg.time}</p>
                      <div className="bg-[#5046e5] text-white text-xs p-3 rounded-2xl rounded-tr-sm max-w-[90%] leading-relaxed font-medium">
                        {msg.text}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Box matching screenshot */}
            <form onSubmit={handleCopilotSubmit} className="relative mt-3 pt-2 border-t border-slate-100">
              <input
                type="text"
                value={copilotCommand}
                onChange={e => setCopilotCommand(e.target.value)}
                placeholder="E.g. Set counter to 2600..."
                className="w-full bg-slate-50 border-2 border-emerald-400/80 rounded-2xl pl-4 pr-11 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-[#5046e5] transition"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-xl bg-[#5046e5] hover:bg-[#4338ca] text-white flex items-center justify-center transition shadow-sm"
                title="Send Override"
              >
                <Sparkles size={13} />
              </button>
            </form>
          </div>
        )}
      </div>
      """
    content = content[:col2_idx] + new_cols_jsx + content[col3_end_idx:]
    print("Replaced Col 2 and Col 3 successfully")
else:
    print(f"Indices: col2={col2_idx}, col3_end={col3_end_idx}")

with open('frontend/src/pages/negotiation/NegotiationRoom.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished updating NegotiationRoom.tsx")
