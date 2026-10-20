import React from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  Factory, 
  Warehouse, 
  TrendingUp, 
  Recycle, 
  Truck, 
  ArrowRight,
  ShieldCheck,
  Calendar,
  DollarSign
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface RecommendationCardProps {
  recommendation?: string | any;
  status?: string;
  crop?: string;
  quantity?: number;
  finalPrice?: number;
  onActionClick?: (actionType: string) => void;
}

export default function RecommendationCard({
  recommendation,
  status,
  crop = 'Soybean',
  quantity = 1000,
  finalPrice,
  onActionClick
}: RecommendationCardProps) {
  const navigate = useNavigate();

  if (!recommendation) return null;

  // Normalize recommendation string or object
  let messageText = '';
  let rawAction = '';
  if (typeof recommendation === 'string') {
    // Check if it's stringified JSON
    try {
      const parsed = JSON.parse(recommendation);
      messageText = parsed.message || parsed.recommendation || recommendation;
      rawAction = parsed.action || '';
    } catch {
      messageText = recommendation;
    }
  } else if (typeof recommendation === 'object') {
    messageText = recommendation.message || recommendation.recommendation || JSON.stringify(recommendation);
    rawAction = recommendation.action || '';
  }

  // Detect recommendation type
  const lowerMsg = (messageText + ' ' + (status || '') + ' ' + rawAction).toLowerCase();
  
  let type: 'DEAL' | 'PROCESSING' | 'STORAGE' | 'HOLD' | 'COMPOST' = 'DEAL';
  if (lowerMsg.includes('processing') || lowerMsg.includes('derivative') || lowerMsg.includes('crush') || lowerMsg.includes('puree')) {
    type = 'PROCESSING';
  } else if (lowerMsg.includes('storage') || lowerMsg.includes('warehouse') || lowerMsg.includes('cold store')) {
    type = 'STORAGE';
  } else if (lowerMsg.includes('hold') || lowerMsg.includes('rebound') || lowerMsg.includes('arrival surge')) {
    type = 'HOLD';
  } else if (lowerMsg.includes('compost') || lowerMsg.includes('bio-compost') || lowerMsg.includes('organic recovery')) {
    type = 'COMPOST';
  } else {
    type = 'DEAL';
  }

  // Configuration mapping based on deal type
  const config = {
    DEAL: {
      title: 'Direct Sale Recommended',
      badge: 'PROCEED TO DISPATCH',
      badgeBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      border: 'border-emerald-500/40 shadow-emerald-950/20',
      headerBg: 'bg-gradient-to-r from-emerald-950/80 via-slate-900 to-slate-900',
      icon: <CheckCircle2 className="text-emerald-400" size={20} />,
      primaryBtn: 'Confirm Dispatch & Book Transport',
      primaryBtnClass: 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/25',
      primaryAction: () => navigate('/transport')
    },
    PROCESSING: {
      title: 'Value-Add Processing Diversion',
      badge: 'PROCESSING FACILITY',
      badgeBg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      border: 'border-amber-500/40 shadow-amber-950/20',
      headerBg: 'bg-gradient-to-r from-amber-950/80 via-slate-900 to-slate-900',
      icon: <Factory className="text-amber-400" size={20} />,
      primaryBtn: 'Connect to Processing Mill',
      primaryBtnClass: 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/25',
      primaryAction: () => navigate('/processor')
    },
    STORAGE: {
      title: 'Warehouse Cold Storage Retention',
      badge: 'STORAGE OPTIMIZED',
      badgeBg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      border: 'border-cyan-500/40 shadow-cyan-950/20',
      headerBg: 'bg-gradient-to-r from-cyan-950/80 via-slate-900 to-slate-900',
      icon: <Warehouse className="text-cyan-400" size={20} />,
      primaryBtn: 'Reserve Cold Storage Facility',
      primaryBtnClass: 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-500/25',
      primaryAction: () => navigate('/storage')
    },
    HOLD: {
      title: 'Market Timing Hold Strategy',
      badge: 'HOLD INVENTORY',
      badgeBg: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      border: 'border-purple-500/40 shadow-purple-950/20',
      headerBg: 'bg-gradient-to-r from-purple-950/80 via-slate-900 to-slate-900',
      icon: <TrendingUp className="text-purple-400" size={20} />,
      primaryBtn: 'Set APMC Price Alert',
      primaryBtnClass: 'bg-purple-500 hover:bg-purple-400 text-white shadow-purple-500/25',
      primaryAction: () => onActionClick ? onActionClick('SET_ALERT') : null
    },
    COMPOST: {
      title: 'Organic Biomass Recovery',
      badge: 'BIO-COMPOST DIVERT',
      badgeBg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
      border: 'border-rose-500/40 shadow-rose-950/20',
      headerBg: 'bg-gradient-to-r from-rose-950/80 via-slate-900 to-slate-900',
      icon: <Recycle className="text-rose-400" size={20} />,
      primaryBtn: 'Initiate Soil Recovery Program',
      primaryBtnClass: 'bg-rose-500 hover:bg-rose-400 text-white shadow-rose-500/25',
      primaryAction: () => onActionClick ? onActionClick('INITIATE_COMPOST') : null
    }
  }[type];

  return (
    <div className={`rounded-2xl border ${config.border} ${config.headerBg} p-5 text-white shadow-lg transition-all animate-in fade-in duration-300`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/60 shrink-0">
            {config.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-400 flex items-center gap-1">
                <Sparkles size={12} className="text-purple-400" />
                LangGraph Recommendation Engine
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider border ${config.badgeBg}`}>
                {config.badge}
              </span>
            </div>
            <h3 className="text-base font-bold text-white mt-0.5">
              {config.title}
            </h3>
          </div>
        </div>

        {finalPrice && (
          <div className="bg-slate-800/80 border border-slate-700/70 px-3.5 py-1.5 rounded-xl text-right shrink-0">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Settled Rate</span>
            <span className="text-emerald-400 font-mono font-black text-base">₹{finalPrice}/kg</span>
          </div>
        )}
      </div>

      {/* Rationale Body */}
      <div className="p-3.5 bg-slate-950/50 rounded-xl border border-slate-800/80 mb-4">
        <p className="text-sm text-slate-200 leading-relaxed font-medium">
          {messageText}
        </p>
      </div>

      {/* Contextual Stats Pill Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-4 text-xs">
        <div className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center gap-2">
          <Calendar size={14} className="text-slate-400 shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block font-medium">Target Commodity</span>
            <span className="text-slate-200 font-bold">{crop} ({quantity.toLocaleString()} kg)</span>
          </div>
        </div>

        <div className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center gap-2">
          <ShieldCheck size={14} className="text-blue-400 shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block font-medium">Validation Status</span>
            <span className="text-slate-200 font-bold">APMC Rule Verified</span>
          </div>
        </div>

        <div className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-800 col-span-2 sm:col-span-1 flex items-center gap-2">
          <DollarSign size={14} className="text-emerald-400 shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block font-medium">Strategy Outcome</span>
            <span className="text-emerald-300 font-bold capitalize">{type.toLowerCase()}</span>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
        <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Optimized for minimum transaction friction & statutory compliance
        </span>
        <button
          type="button"
          onClick={() => {
            if (onActionClick) {
              onActionClick(type);
            } else {
              config.primaryAction();
            }
          }}
          className={`w-full sm:w-auto px-4 py-2.5 rounded-xl font-bold text-xs transition shadow flex items-center justify-center gap-2 cursor-pointer ${config.primaryBtnClass}`}
        >
          <span>{config.primaryBtn}</span>
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
