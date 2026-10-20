import React, { useState } from 'react';
import { ToggleRight, ToggleLeft, Zap, ShieldAlert, BookOpen, Bot } from 'lucide-react';

const initialFlags = [
  { id: 'flag-1', group: 'Core Features', name: 'Enable AI Negotiation', description: 'Allows LangGraph to fully orchestrate deals.', enabled: true, icon: <Bot size={16}/> },
  { id: 'flag-2', group: 'Core Features', name: 'Enable Warehouse Module', description: 'Enable post-deal logistics execution for storage.', enabled: true, icon: <Zap size={16}/> },
  { id: 'flag-3', group: 'Core Features', name: 'Enable Transport Module', description: 'Enable post-deal logistics execution for transport.', enabled: true, icon: <Zap size={16}/> },
  
  { id: 'flag-4', group: 'AI Capabilities', name: 'Enable RAG Knowledge Base', description: 'Inject ChromaDB vector context into LangGraph.', enabled: true, icon: <BookOpen size={16}/> },
  { id: 'flag-5', group: 'AI Capabilities', name: 'Enable Reflection Agent', description: 'Allows AI to learn from failed negotiations.', enabled: true, icon: <BookOpen size={16}/> },
  { id: 'flag-6', group: 'AI Capabilities', name: 'Enable Reinforcement Learning', description: 'Activate PPO model for policy updates.', enabled: false, icon: <ShieldAlert size={16}/> },
  
  { id: 'flag-7', group: 'Experimental', name: 'Enable Voice Negotiation', description: 'Speech-to-text integration for farmers.', enabled: false, icon: <Zap size={16}/> },
  { id: 'flag-8', group: 'Experimental', name: 'Enable Image Upload (Quality Check)', description: 'Allow farmers to upload crop images for AI grading.', enabled: false, icon: <Zap size={16}/> },
];

export default function FeatureFlags() {
  const [flags, setFlags] = useState(initialFlags);

  const toggleFlag = (id) => {
    setFlags(flags.map(f => f.id === id ? { ...f, enabled: !f.enabled } : f));
  };

  const groupedFlags = flags.reduce<Record<string, typeof initialFlags>>((acc, flag) => {
    (acc[flag.group] = acc[flag.group] || []).push(flag);
    return acc;
  }, {});

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      <div>
        <h2 className="text-xl font-bold text-slate-800">Feature Flags</h2>
        <p className="text-sm text-slate-500 mt-1">Instantly enable or disable platform capabilities without deploying new code.</p>
      </div>

      <div className="space-y-8">
        {Object.entries(groupedFlags).map(([group, groupFlags]) => (
          <div key={group}>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 border-b pb-2">{group}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {groupFlags.map(flag => (
                <div key={flag.id} className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between hover:border-slate-300 transition">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg mt-0.5 ${flag.enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                      {flag.icon}
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-700">{flag.name}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">{flag.description}</p>
                    </div>
                  </div>
                  <button onClick={() => toggleFlag(flag.id)} className="transition">
                    {flag.enabled ? (
                      <ToggleRight size={36} className="text-emerald-500" />
                    ) : (
                      <ToggleLeft size={36} className="text-slate-300" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      
    </div>
  );
}
