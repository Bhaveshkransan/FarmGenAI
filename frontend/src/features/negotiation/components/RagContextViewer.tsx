import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { Database, X, Loader2, Search, ShieldCheck, Tag, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '@/services/api';
import { useQuery } from '@tanstack/react-query';

interface RagContextViewerProps {
  isOpen: boolean;
  onClose: () => void;
  query?: string;
  crop?: string;
  role?: string;
}

export default function RagContextViewer({ 
  isOpen, 
  onClose, 
  query = 'market prices', 
  crop = 'Onion',
  role = 'buyer'
}: RagContextViewerProps) {
  const isBuyerRole = role === 'buyer' || role === 'trader' || role === 'user';
  
  // Buyer Domain Tabs
  const [buyerDomain, setBuyerDomain] = useState<string>('all');
  // Legacy farmer collection
  const [activeCollection, setActiveCollection] = useState<string>('market_prices');
  
  const [searchQuery, setSearchQuery] = useState(query);
  const [searchInput, setSearchInput] = useState(query);

  // Buyer-specific RAG Query
  const { data: buyerData, isLoading: isBuyerLoading, isError: isBuyerError } = useQuery({
    queryKey: ['rag-buyer-query', searchQuery, crop],
    queryFn: async () => {
      const res = await api.get('/rag/buyer-query', {
        params: {
          q: searchQuery || crop,
          crop: crop,
          limit: 3
        }
      });
      return res.data?.data || null;
    },
    enabled: isOpen && isBuyerRole
  });

  // Farmer-specific RAG Query
  const { data: farmerData, isLoading: isFarmerLoading, isError: isFarmerError } = useQuery({
    queryKey: ['rag-farmer-query', activeCollection, searchQuery, crop],
    queryFn: async () => {
      const res = await api.get('/rag/query', {
        params: {
          q: searchQuery || crop,
          collection: activeCollection,
          limit: 5,
          crop: crop
        }
      });
      const returnedData = res.data?.data;
      return Array.isArray(returnedData) ? returnedData : [];
    },
    enabled: isOpen && !isBuyerRole
  });

  if (!isOpen) return null;

  // Compile buyer documents based on domain filter
  const getFilteredBuyerDocs = () => {
    if (!buyerData) return [];
    const domainMap: Record<string, { title: string; docs: any[]; badgeColor: string }> = {
      buyer_profile: {
        title: 'Buyer Profile & Preferences',
        docs: buyerData.buyer_profile || [],
        badgeColor: 'bg-blue-100 text-blue-700 border-blue-200',
      },
      procurement_knowledge: {
        title: 'Commercial Procurement Knowledge',
        docs: buyerData.procurement_knowledge || [],
        badgeColor: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      },
      crop_quality_knowledge: {
        title: 'Crop Quality & Grading Specs',
        docs: buyerData.crop_quality_knowledge || [],
        badgeColor: 'bg-amber-100 text-amber-700 border-amber-200',
      },
      government_rules: {
        title: 'Government Regulations & APMC Acts',
        docs: buyerData.government_rules || [],
        badgeColor: 'bg-purple-100 text-purple-700 border-purple-200',
      },
      negotiation_memory: {
        title: 'Buyer Historical Negotiation Memory',
        docs: buyerData.negotiation_memory || [],
        badgeColor: 'bg-indigo-100 text-indigo-700 border-indigo-200',
      },
      relevant_shared_knowledge: {
        title: 'Shared Agricultural Reference Knowledge',
        docs: buyerData.relevant_shared_knowledge || buyerData.shared_knowledge || [],
        badgeColor: 'bg-teal-100 text-teal-700 border-teal-200',
      },
    };

    if (buyerDomain !== 'all') {
      const target = domainMap[buyerDomain];
      return target ? [{ domainKey: buyerDomain, ...target }] : [];
    }

    return Object.entries(domainMap)
      .filter(([_, val]) => val.docs && val.docs.length > 0)
      .map(([key, val]) => ({ domainKey: key, ...val }));
  };

  const filteredBuyerSections = isBuyerRole ? getFilteredBuyerDocs() : [];
  const totalBuyerDocs = filteredBuyerSections.reduce((acc, sec) => acc + (sec.docs?.length || 0), 0);

  return typeof document !== 'undefined' ? createPortal(
    <div className="relative z-[9999]">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose}></div>
      <div className="fixed inset-y-0 right-0 w-80 sm:w-[440px] border-l border-slate-200 bg-white h-full flex flex-col shadow-2xl transform transition-transform">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Database size={16} className="text-emerald-600" />
              {isBuyerRole ? 'Buyer RAG Knowledge Base' : 'RAG Knowledge Base'}
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {isBuyerRole 
                ? 'Isolated Buyer Grounding & Metadata Retrieval' 
                : 'ChromaDB Vector Retrieval Engine'}
            </p>
          </div>
          <button 
            onClick={onClose} 
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-200 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Security / Isolation Banner for Buyer */}
        {isBuyerRole && (
          <div className="bg-emerald-50/70 border-b border-emerald-100 px-4 py-2 flex items-center justify-between text-[11px] text-emerald-800">
            <div className="flex items-center gap-1.5 font-medium">
              <ShieldCheck size={14} className="text-emerald-600" />
              <span>Farmer-Private Data: <strong className="text-emerald-900 font-semibold">Blocked & Isolated</strong></span>
            </div>
            <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">
              Buyer Safe
            </span>
          </div>
        )}

        {/* Controls */}
        <div className="p-4 border-b border-slate-100 bg-white space-y-3">
          {/* Domain Filter Pills */}
          {isBuyerRole ? (
            <div className="flex flex-wrap gap-1.5">
              {[
                { id: 'all', label: 'All Domains' },
                { id: 'buyer_profile', label: 'Profile' },
                { id: 'procurement_knowledge', label: 'Procurement' },
                { id: 'crop_quality_knowledge', label: 'Quality' },
                { id: 'government_rules', label: 'Rules' },
                { id: 'negotiation_memory', label: 'Memory' },
                { id: 'relevant_shared_knowledge', label: 'Shared' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setBuyerDomain(tab.id)}
                  className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full transition border ${
                    buyerDomain === tab.id
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                      : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          ) : (
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
          )}

          {/* Search bar */}
          <form onSubmit={(e) => { e.preventDefault(); setSearchQuery(searchInput); }} className="relative flex items-center">
            <Search size={14} className="absolute left-2.5 text-slate-400" />
            <input 
              type="text" 
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={`Search ${crop} RAG context...`}
              className="w-full text-xs border border-slate-200 rounded-lg pl-8 pr-3 py-2 outline-none focus:border-emerald-500 bg-slate-50 focus:bg-white"
            />
          </form>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Buyer View */}
          {isBuyerRole ? (
            isBuyerLoading ? (
              <div className="text-center p-8 text-slate-400 flex flex-col items-center">
                <Loader2 size={24} className="animate-spin mb-2 text-emerald-500" />
                <span className="text-xs">Querying Isolated Buyer RAG Collections...</span>
              </div>
            ) : isBuyerError ? (
              <div className="text-center p-8 text-red-500 text-xs bg-red-50 rounded-lg border border-red-200">
                Failed to connect to Buyer RAG endpoint.
              </div>
            ) : totalBuyerDocs === 0 ? (
              <div className="text-center p-8 text-slate-400 text-xs bg-slate-50 rounded-lg border border-slate-100">
                No matching buyer context found for query "{searchQuery || crop}".
              </div>
            ) : (
              <div className="space-y-4">
                {filteredBuyerSections.map((sec) => (
                  <div key={sec.domainKey} className="bg-slate-50 border border-slate-200 rounded-lg p-3 shadow-sm">
                    <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200">
                      <h4 className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                        <Tag size={12} className="text-emerald-600" />
                        {sec.title}
                      </h4>
                      <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${sec.badgeColor}`}>
                        {sec.docs.length} Items
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {sec.docs.map((doc: any, idx: number) => {
                        const meta = doc.metadata || {};
                        const source = meta.source || doc.source || 'Verified Knowledge Base';
                        const stakeholder = meta.stakeholder || 'buyer';
                        const docCrop = meta.crop || crop;

                        return (
                          <div key={idx} className="bg-white p-3 rounded-lg border border-slate-200/80 shadow-xs space-y-1.5">
                            <p className="text-slate-700 text-xs leading-relaxed font-normal">
                              {doc.text || doc.content || JSON.stringify(doc)}
                            </p>
                            
                            {/* Provenance Metadata Badges */}
                            <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
                              <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono text-[9px]">
                                {source}
                              </span>
                              <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium text-[9px]">
                                Stakeholder: {stakeholder}
                              </span>
                              {docCrop && (
                                <span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded font-medium text-[9px]">
                                  Crop: {docCrop}
                                </span>
                              )}
                              {meta.quality_grade && (
                                <span className="bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-medium text-[9px]">
                                  Grade {meta.quality_grade}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

                {/* Query Provenance Footer */}
                <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg p-3 text-xs">
                  <h5 className="font-bold text-emerald-900 text-[11px] uppercase tracking-wider mb-1.5 flex items-center gap-1">
                    <CheckCircle2 size={12} className="text-emerald-600" /> Provenance Grounds:
                  </h5>
                  <ul className="text-emerald-800 text-[11px] space-y-1 list-disc pl-4">
                    <li>Target Crop: <span className="font-semibold">{crop}</span></li>
                    <li>Jurisdiction: <span className="font-semibold">Maharashtra APMC Mandis</span></li>
                    <li>Query Filter: <span className="font-semibold">"{searchQuery}"</span></li>
                    <li>Policy Isolation: <span className="font-semibold text-emerald-700">Strict Buyer/Shared Access</span></li>
                  </ul>
                </div>
              </div>
            )
          ) : (
            /* Farmer View (Untouched original behavior) */
            isFarmerLoading ? (
              <div className="text-center p-8 text-slate-400 flex flex-col items-center">
                <Loader2 size={24} className="animate-spin mb-2 text-emerald-500" />
                <span className="text-xs">Querying Vector DB...</span>
              </div>
            ) : isFarmerError ? (
              <div className="text-center p-8 text-red-400 text-xs">
                Failed to connect to RAG endpoint.
              </div>
            ) : !farmerData || farmerData.length === 0 ? (
              <div className="text-center p-8 text-slate-400 text-xs">
                No matching documents found in {activeCollection}.
              </div>
            ) : (
              <>
                {activeCollection === 'market_prices' && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm mb-4 shadow-sm">
                    <h4 className="font-bold text-slate-700 uppercase text-[10px] tracking-wider mb-2 text-emerald-600">Market Information</h4>
                    <div className="flex justify-between items-center text-[10px] text-slate-500 mb-3 pb-2 border-b border-slate-200">
                      <span>Source: Mandi API & Historical Datasets</span>
                      <span>Updated: Live</span>
                    </div>
                    <div className="space-y-4">
                      {farmerData.map((ctx: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded border border-slate-100 shadow-sm">
                          <p className="text-slate-800 text-xs font-semibold mb-1 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            {ctx.metadata?.crop || crop} Price Context
                          </p>
                          <p className="text-slate-600 text-xs leading-relaxed">{ctx.text || ctx.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeCollection === 'reflection_memory' && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm mb-4 shadow-sm">
                    <h4 className="font-bold text-slate-700 uppercase text-[10px] tracking-wider mb-2 text-blue-600">Negotiation Strategies</h4>
                    <div className="space-y-4">
                      {farmerData.map((ctx: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded border border-slate-100 shadow-sm">
                          <p className="text-slate-800 text-xs font-semibold mb-1 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                            Strategy Insight
                          </p>
                          <p className="text-slate-600 text-xs leading-relaxed">{ctx.text || ctx.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeCollection === 'crop_knowledge' && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm mb-4 shadow-sm">
                    <h4 className="font-bold text-slate-700 uppercase text-[10px] tracking-wider mb-2 text-purple-600">Crop Knowledge</h4>
                    <div className="space-y-4">
                      {farmerData.map((ctx: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded border border-slate-100 shadow-sm">
                          <p className="text-slate-800 text-xs font-semibold mb-1 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
                            {ctx.metadata?.variety || 'Quality'} Requirements
                          </p>
                          <p className="text-slate-600 text-xs leading-relaxed">{ctx.text || ctx.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )
          )}
        </div>
      </div>
    </div>,
    document.body
  ) : null;
}
