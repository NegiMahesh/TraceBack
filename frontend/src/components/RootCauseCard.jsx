import React, { useState } from 'react';
import { 
  AlertTriangle, 
  GitCommit, 
  User, 
  Calendar, 
  ShieldAlert, 
  Lightbulb, 
  FileCode2, 
  Check, 
  Copy, 
  HelpCircle,
  Cpu,
  Layers
} from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import ConfidenceMeter from './ConfidenceMeter';

export default function RootCauseCard({ investigation }) {
  const [explanationMode, setExplanationMode] = useState('developer'); // beginner | developer | expert
  const [copied, setCopied] = useState(false);

  if (!investigation) return null;

  const {
    error_type,
    error_message,
    file,
    line,
    function: funcName,
    severity,
    confidence,
    root_cause,
    explanation,
    fix_strategy,
    potential_risks = [],
    git_blame
  } = investigation;

  const handleCopy = () => {
    navigator.clipboard.writeText(`${error_type}: ${error_message}\nLocation: ${file}:${line}\nRoot Cause: ${root_cause}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Generate perspective based on mode
  let modeExplanation = explanation || root_cause;
  if (explanationMode === 'beginner') {
    modeExplanation = `Simple Explanation: The code tried to perform an invalid operation (${error_type || 'Error'}). In file ${file || 'the source file'} at line ${line}, the program encountered a situation it didn't expect, causing the application to stop immediately. TraceBack has identified a way to handle this safely.`;
  } else if (explanationMode === 'expert') {
    modeExplanation = `Deep Debugging Analysis: ${root_cause}\n\nExecution State & Invariants: During frame execution of function ${funcName || 'login_user'}, an unhandled ${error_type} was raised due to invalid runtime state. The call stack terminated at line ${line}. The suggested patch introduces boundary validation while maintaining idempotent state behavior.`;
  }

  return (
    <div className="p-5 rounded-xl bg-slate-900/90 border border-white/10 shadow-xl space-y-4">
      {/* Header with Title and Severity/Confidence */}
      <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-white/10">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              {error_type || 'Unknown Exception'}
            </span>
            <span className="text-sm font-semibold text-white">
              {error_message || 'Runtime crash detected'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-blue-300 font-medium">{file || 'unknown_file.py'}:{line || 1}</span>
            {funcName && (
              <>
                <span className="text-slate-600">in</span>
                <span className="text-slate-300">{funcName}()</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <SeverityBadge severity={severity} />
          <ConfidenceMeter confidence={confidence} />
        </div>
      </div>

      {/* Explanation Modes Switcher */}
      <div className="flex items-center justify-between gap-2 pt-1">
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-950 border border-white/5 text-xs">
          <span className="text-[11px] text-slate-500 px-2 font-medium">Mode:</span>
          {['beginner', 'developer', 'expert'].map((mode) => (
            <button
              key={mode}
              onClick={() => setExplanationMode(mode)}
              className={`px-2.5 py-1 rounded text-xs capitalize font-medium transition-all ${
                explanationMode === mode
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-400 hover:text-white rounded bg-slate-800/80 hover:bg-slate-800 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Diagnosis'}</span>
        </button>
      </div>

      {/* Root Cause Box */}
      <div className="p-4 rounded-lg bg-slate-950/70 border border-blue-500/20 text-xs leading-relaxed space-y-2">
        <div className="flex items-center gap-2 text-blue-400 font-semibold uppercase tracking-wider text-[11px]">
          <Lightbulb className="w-4 h-4" />
          <span>Root Cause Diagnosis</span>
        </div>
        <p className="text-slate-200 whitespace-pre-wrap font-sans text-xs sm:text-[13px] leading-relaxed">
          {modeExplanation}
        </p>
      </div>

      {/* Git Blame Attribution Card */}
      {git_blame && (git_blame.author || git_blame.commit_hash) && (
        <div className="p-3.5 rounded-lg bg-gradient-to-r from-slate-950 to-indigo-950/30 border border-indigo-500/20 flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <GitCommit className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium text-slate-400">Likely Introduced By:</span>
                <span className="font-semibold text-slate-200">{git_blame.author || 'Contributor'}</span>
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/30">
                  {git_blame.commit_hash || '7d31a2f'}
                </span>
              </div>
              <p className="text-slate-400 text-[11px] italic mt-0.5">
                "{git_blame.commit_message || 'Update authentication risk scoring'}"
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Fix Strategy & Potential Risks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {fix_strategy && (
          <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5 text-xs space-y-1">
            <span className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider block">
              Repair Strategy
            </span>
            <p className="text-slate-300 text-[12px]">{fix_strategy}</p>
          </div>
        )}

        {potential_risks && potential_risks.length > 0 && (
          <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5 text-xs space-y-1">
            <span className="text-amber-400 font-semibold text-[11px] uppercase tracking-wider block flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Safety & Risk Evaluation
            </span>
            <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5">
              {potential_risks.map((risk, i) => (
                <li key={i}>{risk}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
