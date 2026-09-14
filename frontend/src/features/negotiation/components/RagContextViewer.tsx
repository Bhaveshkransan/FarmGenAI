import React, { useState, useEffect } from 'react';
import { Database, ExternalLink, X, Loader2, Search } from 'lucide-react';
import { api } from '@/services/api';
import { useQuery } from '@tanstack/react-query';

export default function RagContextViewer({ isOpen, onClose, query = 'market prices', crop = 'Onion' }) {
  const [activeCollection, setActiveCollection] = useState('market_prices');
  const [searchQuery, setSearchQuery] = useState(query);
  const [searchInput, setSearchInput] = useState(query);

  const { data: contexts, isLoading, isError } = useQuery({
    queryKey: ['rag-query', activeCollection, searchQuery, crop],
    queryFn: async () => {
      const res = await api.get(`/rag/query`, {
        params: {
          q: searchQuery || crop,
          collection: activeCollection,
          limit: 5,
          crop: crop
        }
      });
      return res.data?.data || [];
    },
    enabled: isOpen
  });

  if (!isOpen) return null;

  return (
    <div className="w-80 sm:w-96 border-l border-slate-200 bg-white h-full flex flex-col shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.05)]">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <h3 className="font-bold text-slate-700 flex items-center gap-2">
          <Database size={16} className="text-emerald-600" /> RAG Knowledge Base
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
          <X size={20} />
        </button>
      </div>
      
      <div className="p-4 border-b border-slate-100 bg-white space-y-3">
        <p className="text-xs text-slate-500">
          Explore the ChromaDB vectors that AI Agents use to ground their negotiation logic.
        </p>

        <div className="flex gap-2">
          <button 
            onClick={() => setActiveCollection('market_prices')}
            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full transition ${activeCollection === 'market_prices' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
          >
            Prices
          </button>
          <button 
            onClick={() => setActiveCollection('reflection_memory')}
            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full transition ${activeCollection === 'reflection_memory' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
          >
            Strategies
          </button>
          <button 
            onClick={() => setActiveCollection('crop_knowledge')}
            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full transition ${activeCollection === 'crop_knowledge' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
          >
            Knowledge
          </button>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); setSearchQuery(searchInput); }} className="relative flex items-center">
          <Search size={14} className="absolute left-2.5 text-slate-400" />
          <input 
            type="text" 
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search RAG memory..."
            className="w-full text-xs border border-slate-200 rounded-lg pl-8 pr-3 py-2 outline-none focus:border-emerald-500"
          />
        </form>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="text-center p-8 text-slate-400 flex flex-col items-center">
            <Loader2 size={24} className="animate-spin mb-2 text-emerald-500" />
            <span className="text-xs">Querying Vector DB...</span>
          </div>
        ) : isError ? (
          <div className="text-center p-8 text-red-400 text-xs">
            Failed to connect to RAG endpoint.
          </div>
        ) : !contexts || contexts.length === 0 ? (
          <div className="text-center p-8 text-slate-400 text-xs">
            No matching documents found in {activeCollection}.
          </div>
        ) : (
          contexts.map((ctx, idx) => (
            <div key={idx} className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                  {activeCollection}
                </span>
                <span className="text-[10px] font-medium text-slate-400">
                  {ctx.metadata?.id || `Doc ${idx + 1}`}
                </span>
              </div>
              <p className="text-slate-700 text-xs mb-3">{ctx.text || ctx.content}</p>
              <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-slate-200 pt-2">
                <span className="truncate max-w-[150px]">
                  {ctx.metadata?.source || ctx.metadata?.crop || 'Internal Source'}
                </span>
                {ctx.metadata?.url && (
                  <a href={ctx.metadata.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-500 hover:underline">
                    <ExternalLink size={12} /> Source
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
