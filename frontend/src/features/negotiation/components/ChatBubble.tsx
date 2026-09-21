import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Check, X, ArrowRightLeft } from 'lucide-react';

export default function ChatBubble({ agent, price, message, reasoning, isFarmer, isSystem, isInteractive, onAction }) {
  const [showReasoning, setShowReasoning] = useState(false);

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-slate-100 border border-slate-200 text-slate-500 px-4 py-2 rounded-full text-xs font-medium max-w-[85%] text-center">
          {message}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${isFarmer ? 'items-end' : 'items-start'}`}>
      <span className="text-xs font-semibold text-slate-500 mb-1 mx-2">{agent}</span>
      <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${
        isFarmer ? 'bg-emerald-600 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
      }`}>
        <p className="text-sm mb-2">{message}</p>
        {price && (
          <div className={`inline-block px-3 py-1 mt-2 rounded-full text-xs font-bold ${
            isFarmer ? 'bg-emerald-700 text-emerald-100' : 'bg-slate-100 text-slate-600'
          }`}>
            Offer: ₹{price}/kg
          </div>
        )}

        {/* Explainable AI (XAI) Reasoning Toggle */}
        {reasoning && (
          <div className="mt-3">
            <button 
              onClick={() => setShowReasoning(!showReasoning)}
              className={`flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider ${isFarmer ? 'text-emerald-200 hover:text-white' : 'text-slate-400 hover:text-slate-600'}`}
            >
              {showReasoning ? <ChevronUp size={12}/> : <ChevronDown size={12}/>}
              AI Reasoning
            </button>
            
            {showReasoning && (
              <div className={`mt-2 p-3 rounded-lg text-xs border ${isFarmer ? 'bg-emerald-700/50 border-emerald-600 text-emerald-50' : 'bg-slate-50 border-slate-200 text-slate-600'}`}>
                <ul className="space-y-1 list-disc list-inside">
                  {reasoning.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Interactive Action Cards */}
        {isInteractive && onAction && (
          <div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-slate-200/20">
            <button onClick={() => onAction('accept', price)} className="flex items-center gap-1 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-xs font-bold rounded-lg transition">
              <Check size={14}/> Accept Deal
            </button>
            <button onClick={() => onAction('counter', price)} className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-bold rounded-lg transition">
              <ArrowRightLeft size={14}/> Counter
            </button>
            <button onClick={() => onAction('reject', price)} className="flex items-center gap-1 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-bold rounded-lg transition">
              <X size={14}/> Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
