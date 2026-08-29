import React from 'react';
import { 
  AlertOctagon, 
  Binary, 
  MapPin, 
  GitCommit, 
  BrainCircuit, 
  GitMerge, 
  TestTube, 
  CheckCheck,
  CheckCircle2,
  Clock,
  Loader2
} from 'lucide-react';

const PIPELINE_STEPS = [
  { id: 'detected', label: 'Error Detected', icon: AlertOctagon },
  { id: 'parsed', label: 'Trace Parsed', icon: Binary },
  { id: 'located', label: 'Source Located', icon: MapPin },
  { id: 'git', label: 'Git History Analyzed', icon: GitCommit },
  { id: 'ai', label: 'AI Investigation', icon: BrainCircuit },
  { id: 'patch', label: 'Patch Generated', icon: GitMerge },
  { id: 'test', label: 'Test Generated', icon: TestTube },
  { id: 'verified', label: 'Fix Verified', icon: CheckCheck },
];

export default function InvestigationTimeline({ currentStep = 0, isComplete = false }) {
  return (
    <div className="w-full p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Autonomous Pipeline Stream
          </span>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Step {Math.min(currentStep + 1, PIPELINE_STEPS.length)} of {PIPELINE_STEPS.length}
        </span>
      </div>

      {/* Horizontal Flow Pipeline */}
      <div className="relative">
        {/* Track Line */}
        <div className="absolute top-1/2 left-4 right-4 h-0.5 -translate-y-1/2 bg-slate-800 z-0" />
        
        {/* Animated Progress Fill */}
        <div 
          className="absolute top-1/2 left-4 h-0.5 -translate-y-1/2 pipeline-flowing-gradient z-0 transition-all duration-500"
          style={{ width: `${Math.min(100, (currentStep / (PIPELINE_STEPS.length - 1)) * 95)}%` }}
        />

        <div className="relative z-10 grid grid-cols-4 md:grid-cols-8 gap-2">
          {PIPELINE_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isPassed = idx < currentStep || isComplete;
            const isCurrent = idx === currentStep && !isComplete;
            const isPending = idx > currentStep && !isComplete;

            let badgeStyle = 'bg-slate-900 border-slate-800 text-slate-500';
            if (isPassed) {
              badgeStyle = 'bg-emerald-950/80 border-emerald-500/50 text-emerald-400 shadow-sm shadow-emerald-500/20';
            } else if (isCurrent) {
              badgeStyle = 'bg-blue-950/90 border-blue-500 text-blue-400 shadow-glow-sm animate-pulse-glow';
            }

            return (
              <div key={step.id} className="flex flex-col items-center text-center group">
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all duration-300 ${badgeStyle}`}>
                  {isPassed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                </div>
                <span className={`mt-2 text-[10px] font-medium leading-tight line-clamp-1 transition-colors ${
                  isPassed ? 'text-emerald-300' : isCurrent ? 'text-blue-400 font-bold' : 'text-slate-500'
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
