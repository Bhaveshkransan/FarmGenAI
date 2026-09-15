import React from 'react';
import { Network, BrainCircuit, Search, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function AgentWorkflowStepper({ activeAgent }) {
  const steps = [
    { id: 'Planner', icon: <Network size={16} />, label: 'Planning' },
    { id: 'Market Intel', icon: <Search size={16} />, label: 'Intelligence' },
    { id: 'Negotiator', icon: <BrainCircuit size={16} />, label: 'Negotiation' },
    { id: 'Validator', icon: <ShieldCheck size={16} />, label: 'Validation' }
  ];

  // Helper to determine step status
  const getStepStatus = (stepId) => {
    if (!activeAgent) return 'pending';
    
    const activeIndex = steps.findIndex(s => activeAgent.includes(s.id));
    const currentIndex = steps.findIndex(s => s.id === stepId);
    
    if (activeIndex === -1) {
       // If agent not in list, assume completed or idle
       return 'completed'; 
    }
    
    if (currentIndex < activeIndex) return 'completed';
    if (currentIndex === activeIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="w-full bg-white rounded-xl mb-6">
      <div className="space-y-3">
        {steps.map((step, idx) => {
          const status = getStepStatus(step.id);
          
          return (
            <div key={idx} className="flex flex-col">
              <div className="flex justify-between items-center">
                <span className={`text-xs font-bold uppercase tracking-widest ${
                  status === 'completed' ? 'text-slate-800' :
                  status === 'active' ? 'text-emerald-600' :
                  'text-slate-400'
                }`}>
                  {step.label}
                </span>
                
                {status === 'completed' ? (
                  <CheckCircle2 size={16} className="text-emerald-500" />
                ) : status === 'active' ? (
                  <span className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> RUNNING
                  </span>
                ) : null}
              </div>

              {/* Show sub-steps if active */}
              {status === 'active' && step.id === 'Negotiator' && (
                <div className="mt-3 pl-2 border-l-2 border-emerald-100 space-y-2">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Current Execution</p>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle2 size={14} className="text-emerald-500" /> Listing analyzed
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle2 size={14} className="text-emerald-500" /> Market context retrieved
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle2 size={14} className="text-emerald-500" /> RAG context retrieved
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <CheckCircle2 size={14} className="text-emerald-500" /> Buyers matched
                  </div>
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse ml-0.5"></span> Negotiating with buyers
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <div className="w-3 h-3 rounded-full border border-slate-300 ml-0.5"></div> Deal evaluation
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <div className="w-3 h-3 rounded-full border border-slate-300 ml-0.5"></div> Final selection
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
