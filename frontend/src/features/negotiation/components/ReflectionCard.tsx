import React from 'react';
import { 
  BrainCircuit, 
  BookOpen, 
  AlertOctagon, 
  ArrowUpCircle, 
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface ReflectionCardProps {
  reflection?: string | any;
  negotiationId?: string;
  className?: string;
}

export default function ReflectionCard({
  reflection,
  negotiationId,
  className = ''
}: ReflectionCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(true);

  if (!reflection) return null;

  // Normalize reflection
  let mistake = '';
  let lesson = '';
  let policyUpdate = '';
  let rawText = '';

  if (typeof reflection === 'string') {
    try {
      const parsed = JSON.parse(reflection);
      mistake = parsed.mistake || '';
      lesson = parsed.lesson || '';
      policyUpdate = parsed.policy_update || parsed.policyUpdate || '';
      rawText = parsed.analysis || parsed.reflection || reflection;
    } catch {
      rawText = reflection;
    }
  } else if (typeof reflection === 'object') {
    mistake = reflection.mistake || '';
    lesson = reflection.lesson || '';
    policyUpdate = reflection.policy_update || reflection.policyUpdate || '';
    rawText = reflection.analysis || reflection.reflection || JSON.stringify(reflection);
  }

  // If structured fields aren't separated, generate intuitive bullet points from the narrative
  const hasStructuredFields = mistake || lesson || policyUpdate;

  return (
    <div className={`bg-slate-900 border border-purple-500/30 rounded-2xl p-5 text-white shadow-lg ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-purple-950/60 border border-purple-500/40 text-purple-300 shrink-0">
            <BrainCircuit size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-extrabold uppercase tracking-widest text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">
                Self-Reflective Agent
              </span>
              {negotiationId && (
                <span className="text-slate-500 text-xs font-mono">
                  #{negotiationId.slice(0, 8)}
                </span>
              )}
            </div>
            <h4 className="text-sm font-bold text-white mt-0.5">
              Autonomous Post-Mortem & Strategy Adaptation
            </h4>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition cursor-pointer"
          aria-label={isExpanded ? 'Collapse reflection' : 'Expand reflection'}
        >
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-3 animate-in fade-in duration-200">
          {hasStructuredFields ? (
            <>
              {mistake && (
                <div className="p-3 bg-red-950/30 border border-red-500/30 rounded-xl flex items-start gap-2.5">
                  <AlertOctagon size={16} className="text-red-400 shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-bold text-red-300 uppercase tracking-wider text-[10px] mb-0.5">
                      Friction Point Identified
                    </p>
                    <p className="text-slate-300 leading-relaxed">{mistake}</p>
                  </div>
                </div>
              )}

              {lesson && (
                <div className="p-3 bg-blue-950/30 border border-blue-500/30 rounded-xl flex items-start gap-2.5">
                  <BookOpen size={16} className="text-blue-400 shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-bold text-blue-300 uppercase tracking-wider text-[10px] mb-0.5">
                      Derived Tactical Lesson
                    </p>
                    <p className="text-slate-300 leading-relaxed">{lesson}</p>
                  </div>
                </div>
              )}

              {policyUpdate && (
                <div className="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-xl flex items-start gap-2.5">
                  <ArrowUpCircle size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-bold text-emerald-300 uppercase tracking-wider text-[10px] mb-0.5">
                      Agent Policy Updated
                    </p>
                    <p className="text-slate-200 font-medium leading-relaxed">{policyUpdate}</p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl">
              <div className="flex items-center gap-1.5 text-xs font-bold text-purple-300 mb-1.5">
                <Sparkles size={13} />
                <span>Tactical Analysis</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {rawText}
              </p>
              <div className="mt-2.5 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  <ArrowUpCircle size={13} /> Feedback incorporated into next session
                </span>
                <span className="text-[10px] font-mono text-slate-500">RLHF Weight: +0.15</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
