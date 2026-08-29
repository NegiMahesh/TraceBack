import React from 'react';
import { ShieldCheck, Sparkles } from 'lucide-react';

export default function ConfidenceMeter({ confidence = 0 }) {
  const score = Math.min(100, Math.max(0, Math.round(confidence)));
  
  let color = 'bg-blue-500';
  let textColor = 'text-blue-400';
  if (score >= 85) {
    color = 'bg-emerald-500';
    textColor = 'text-emerald-400';
  } else if (score >= 60) {
    color = 'bg-amber-500';
    textColor = 'text-amber-400';
  } else {
    color = 'bg-rose-500';
    textColor = 'text-rose-400';
  }

  return (
    <div className="flex flex-col gap-1 w-full max-w-[180px]">
      <div className="flex items-center justify-between text-xs font-mono">
        <span className="text-slate-400 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          AI Confidence
        </span>
        <span className={`font-bold ${textColor}`}>{score}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
