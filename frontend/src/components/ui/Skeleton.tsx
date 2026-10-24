import React from 'react';

function SkeletonBlock({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={`bg-slate-200 rounded-xl animate-pulse ${className}`} style={style} />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
      <SkeletonBlock className="w-12 h-12 rounded-xl flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <SkeletonBlock className="h-3 w-24" />
        <SkeletonBlock className="h-6 w-16" />
        <SkeletonBlock className="h-2.5 w-20" />
      </div>
    </div>
  );
}

export function TableRowSkeleton({ rows = 3 }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 py-3 border-b border-slate-100 last:border-0">
          <SkeletonBlock className="h-4 w-24" />
          <SkeletonBlock className="h-4 flex-1" />
          <SkeletonBlock className="h-4 w-16" />
          <SkeletonBlock className="h-6 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = 'h-64' }) {
  return (
    <div className={`bg-white rounded-2xl border border-slate-100 shadow-sm p-6 ${height}`}>
      <SkeletonBlock className="h-5 w-40 mb-6" />
      <div className="flex items-end gap-2 h-36 w-full">
        {[60, 80, 40, 90, 55, 70].map((h, i) => (
          <SkeletonBlock
            key={i}
            className="flex-1 rounded-t-lg"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export default SkeletonBlock;
