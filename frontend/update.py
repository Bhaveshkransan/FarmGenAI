import re

with open('c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add states
new_states = """
  const [rightTab, setRightTab] = useState<'ai' | 'rag' | 'copilot'>('copilot');
  const [copilotCommand, setCopilotCommand] = useState('');
  const [copilotMessages, setCopilotMessages] = useState<{sender: string, text: string, time: string}[]>([
    { sender: 'AI', text: 'I am your negotiation copilot. Give me manual instructions like "Set minimum to 2500" or "Counter Buyer A at 2600".', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [liveBuyers, setLiveBuyers] = useState([
    { id: 'Buyer A', match: 96, offer: 2500, aiStatus: 'Counter ₹2550', status: 'Negotiating', color: 'emerald' },
    { id: 'Buyer B', match: 91, offer: 2480, aiStatus: 'Negotiating...', status: 'Waiting', color: 'blue' },
    { id: 'Buyer C', match: 87, offer: 2420, aiStatus: 'Counter ₹2500', status: 'Negotiating', color: 'amber' }
  ]);
"""

content = content.replace('  // 1. Fetch negotiation session state', new_states + '\n  // 1. Fetch negotiation session state')

# 2. Add handleCopilotSubmit
handle_copilot = """
  const handleCopilotSubmit = (e: any) => {
    e.preventDefault();
    if(!copilotCommand.trim()) return;
    
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const userMsg = { sender: 'Farmer', text: copilotCommand, time: now };
    
    setCopilotMessages(prev => [...prev, userMsg]);
    
    // Simulate AI response and override logic
    setTimeout(() => {
      const lower = copilotCommand.toLowerCase();
      let aiResponse = 'Understood. Instruction applied.';
      
      if (lower.includes('below') || lower.includes('minimum') || lower.includes('floor')) {
        const match = copilotCommand.match(/\\d+/);
        if (match) {
          const val = Number(match[0]);
          if (val < minAllowedFloor) {
            aiResponse = `⚠️ Override blocked. ₹${val} is below the listing's statutory minimum acceptable price of ₹${minAllowedFloor}.`;
          } else {
            aiResponse = `Understood. I'll update your negotiation floor to ₹${val}/q.`;
          }
        }
      } else if (lower.includes('counter')) {
         aiResponse = `Manual instruction applied. Negotiators are updating counter offers.`;
         // Show override on Buyer A for demo
         setLiveBuyers(prev => prev.map(b => b.id === 'Buyer A' ? { ...b, aiStatus: 'Farmer Override: ₹' + (copilotCommand.match(/\\d+/)?.[0] || '2600') } : b));
      }
      
      setCopilotMessages(prev => [...prev, { sender: 'AI', text: aiResponse, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }]);
    }, 600);
    
    setCopilotCommand('');
  };
"""

content = content.replace('  if (isLoading) {', handle_copilot + '\n  if (isLoading) {')

# 3. Replace JSX UI from column 2 (Center) onwards
# Let's find "════ COLUMN 2" and replace everything down to the end of the div containing columns
# Actually we can replace from "      {/* ════ COLUMN 2: The Timeline / Chat Stream (Center ~50%) ════ */}"
# to "      {/* Floating RAG Modal */}"

replacement_jsx = """
      {/* ════ COLUMN 2: LIVE NEGOTIATIONS (Center ~50%) ════ */}
      <div className="w-full xl:w-2/4 flex flex-col gap-4">
        
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col overflow-hidden relative flex-1">
          <div className="p-3.5 border-b border-slate-100 bg-slate-50 flex justify-between items-center z-10 sticky top-0">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <MessageSquare size={17} className="text-emerald-600" /> LIVE NEGOTIATIONS
            </h3>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></span>
              <span className="text-[10px] font-bold text-slate-500 uppercase">WS Connected ✓</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-50/50 p-5 space-y-4">
            {liveBuyers.map((b, i) => (
              <div key={i} className={`bg-white border rounded-xl p-4 shadow-sm relative overflow-hidden ${b.aiStatus.includes('Override') ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200'}`}>
                
                {b.aiStatus.includes('Override') && (
                  <div className="absolute top-0 left-0 w-full h-1 bg-blue-500"></div>
                )}
                
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-bold text-slate-800 flex items-center gap-2">
                      ⭐ {b.id} — {b.match}% Match
                    </h4>
                    {b.aiStatus.includes('Override') && (
                      <span className="inline-block mt-1 text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded flex items-center gap-1 w-max">
                        <ShieldCheck size={12}/> FARMER OVERRIDE APPLIED
                      </span>
                    )}
                  </div>
                  <span className="font-black text-lg text-slate-800">₹{b.offer}</span>
                </div>
                
                <div className="bg-slate-50 rounded-lg p-3 text-xs space-y-2 border border-slate-100">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">AI Strategy:</span>
                    <span className="font-bold text-slate-700">{b.aiStatus}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Status:</span>
                    <span className={`font-bold text-${b.color}-600 flex items-center gap-1`}>
                      <span className={`w-2 h-2 rounded-full bg-${b.color}-500 animate-pulse`}></span> {b.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Fast Action / Best Deal Bar */}
        <div className="bg-emerald-900 rounded-2xl shadow-sm border border-emerald-800 p-4 text-white flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <p className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider mb-1">🏆 BEST DEAL SO FAR</p>
            <div className="flex items-center gap-4 text-sm">
              <span className="font-bold text-lg">Buyer A</span>
              <span className="bg-emerald-800 px-2 py-0.5 rounded font-bold">₹{liveBuyers[0].offer}/q</span>
              <span>{cropQty.toLocaleString()} Q</span>
              <span>{liveBuyers[0].match}% Match</span>
              <span className="font-bold text-emerald-300">Net ₹{(liveBuyers[0].offer * cropQty).toLocaleString()}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button className="px-4 py-2 bg-emerald-800 hover:bg-emerald-700 font-bold text-xs rounded-xl transition">View Analysis</button>
            <button onClick={() => {
                setAgreementData({...negState, price: liveBuyers[0].offer, farmer: user?.name, buyer: 'Buyer A'});
                setShowValidationModal(true);
            }} className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-emerald-950 font-black text-xs rounded-xl transition">Accept Deal</button>
          </div>
        </div>
      </div>
      
      {/* ════ COLUMN 3: Right Panel (AI / RAG / COPILOT ~25%) ════ */}
      <div className="w-full xl:w-1/4 flex flex-col gap-4 h-full">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 flex flex-col h-full overflow-hidden">
          
          <div className="flex bg-slate-50 border-b border-slate-100 p-1.5 gap-1">
            <button onClick={() => setRightTab('ai')} className={`flex-1 py-2 text-xs font-bold rounded-lg transition ${rightTab === 'ai' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}>🧠 AI</button>
            <button onClick={() => setRightTab('rag')} className={`flex-1 py-2 text-xs font-bold rounded-lg transition ${rightTab === 'rag' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}>📚 RAG</button>
            <button onClick={() => setRightTab('copilot')} className={`flex-1 py-2 text-xs font-bold rounded-lg transition ${rightTab === 'copilot' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}>💬 COPILOT</button>
          </div>

          <div className="p-5 flex-1 overflow-y-auto">
            {rightTab === 'ai' && (
              <div className="space-y-4">
                <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider mb-3">LangGraph Workflow</h4>
                <AgentWorkflowStepper activeAgent={activeAgent} />
                <div className="mt-6 p-4 bg-slate-50 rounded-xl border border-slate-100 text-xs">
                  <h5 className="font-bold text-slate-700 mb-2">Current State</h5>
                  <ul className="space-y-2 text-slate-600">
                    <li className="flex justify-between"><span>Agent:</span><span className="font-bold">Negotiator</span></li>
                    <li className="flex justify-between"><span>Phase:</span><span className="font-bold text-emerald-600">Parallel Bidding</span></li>
                    <li className="flex justify-between"><span>Strategy:</span><span className="font-bold">Maximize Yield</span></li>
                  </ul>
                </div>
              </div>
            )}
            
            {rightTab === 'rag' && (
              <div className="space-y-4">
                 <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider mb-3">Retrieved Context</h4>
                 <div className="space-y-3">
                   <div className="p-3 border border-slate-100 rounded-xl bg-blue-50/50">
                     <p className="text-xs font-bold text-slate-700 mb-1">Mandi Data Source</p>
                     <p className="text-[11px] text-slate-600">APMC daily arrivals for Soybean indicate a 5% drop, pushing short-term modal prices up.</p>
                     <span className="inline-block mt-2 text-[9px] font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded">98% Confidence</span>
                   </div>
                   <div className="p-3 border border-slate-100 rounded-xl bg-purple-50/50">
                     <p className="text-xs font-bold text-slate-700 mb-1">Crop Knowledge</p>
                     <p className="text-[11px] text-slate-600">Soybean Grade A moisture level required &lt; 10%. Your listing passes QA specs.</p>
                     <span className="inline-block mt-2 text-[9px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded">Source: ICAR</span>
                   </div>
                 </div>
                 <button onClick={() => setIsRagOpen(true)} className="w-full mt-2 py-2 border border-slate-200 text-slate-600 font-bold text-xs rounded-xl hover:bg-slate-50 transition">Expand Full Database</button>
              </div>
            )}

            {rightTab === 'copilot' && (
              <div className="flex flex-col h-full space-y-4">
                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                  {copilotMessages.map((msg, i) => (
                    <div key={i} className={`flex flex-col ${msg.sender === 'Farmer' ? 'items-end' : 'items-start'}`}>
                      <span className="text-[9px] font-bold text-slate-400 mb-1 px-1">{msg.sender} • {msg.time}</span>
                      <div className={`p-3 max-w-[90%] text-xs leading-relaxed rounded-xl ${msg.sender === 'Farmer' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-700 rounded-bl-none border border-slate-200'}`}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                </div>
                
                <form onSubmit={handleCopilotSubmit} className="mt-auto relative pt-2">
                  <input 
                    type="text" 
                    value={copilotCommand}
                    onChange={e => setCopilotCommand(e.target.value)}
                    placeholder="E.g. Set counter to 2600..." 
                    className="w-full bg-white border-2 border-slate-200 rounded-xl pl-4 pr-10 py-3 text-xs focus:outline-none focus:border-indigo-500 transition shadow-sm"
                  />
                  <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 mt-1 p-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition">
                    <Sparkles size={14} />
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
"""

# Replace the specific JSX block
start_idx = content.find('{/* ════ COLUMN 2: The Timeline / Chat Stream (Center ~50%) ════ */}')
end_idx = content.find('{/* Floating RAG Modal */}')

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + replacement_jsx + content[end_idx:]

with open('c:/PROJECT/FarmGenAI/frontend/src/pages/negotiation/NegotiationRoom.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Update complete")
