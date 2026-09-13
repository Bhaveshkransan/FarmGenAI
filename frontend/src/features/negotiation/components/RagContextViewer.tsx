import React from 'react';
import { Database, Link, ExternalLink, X } from 'lucide-react';

export default function RagContextViewer({ isOpen, onClose }) {
  if (!isOpen) return null;

  // Mock data representing ChromaDB vector search retrievals
  const contexts = [
    {
      collection: 'agmarknet_prices',
      source: 'Maharashtra/Nashik/Onion',
      similarity: 0.94,
      content: 'Modal price for Grade A Onion in Nashik APMC is ₹2200/quintal (₹22/kg) as of 2026-08-07.',
      url: '#'
    },
    {
      collection: 'government_schemes',
      source: 'PM-AASHA Directive 2026',
      similarity: 0.88,
      content: 'Price Stabilization Fund (PSF) buffer procurement guidelines active for perishable produce in designated APMC zones.',
      url: '#'
    },
    {
      collection: 'weather_alerts',
      source: 'IMD Pune',
      similarity: 0.82,
      content: 'Heavy rainfall expected in Nashik region in 48 hours. Spoilage risk for harvested onion increases by 40%.',
      url: '#'
    }
  ];

  return (
    <div className="w-80 border-l border-slate-200 bg-white h-full flex flex-col shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)]">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <h3 className="font-bold text-slate-700 flex items-center gap-2">
          <Database size={16} className="text-emerald-600" /> RAG Knowledge Base
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
          <X size={20} />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <p className="text-xs text-slate-500 mb-2">
          The AI Agents are actively retrieving context from these ChromaDB vectors to ground their negotiation logic:
        </p>
        
        {contexts.map((ctx, idx) => (
          <div key={idx} className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                {ctx.collection}
              </span>
              <span className="text-[10px] font-medium text-slate-400">Score: {ctx.similarity}</span>
            </div>
            <p className="text-slate-700 text-xs mb-3">{ctx.content}</p>
            <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-slate-200 pt-2">
              <span className="truncate max-w-[150px]">{ctx.source}</span>
              <a href={ctx.url} className="flex items-center gap-1 text-blue-500 hover:underline">
                <ExternalLink size={12} /> Source
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
