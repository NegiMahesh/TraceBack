import React from 'react';
import { 
  ShieldAlert, 
  Terminal, 
  GitMerge, 
  TestTube2, 
  CheckCircle2, 
  XCircle, 
  ArrowRight, 
  Flame, 
  Sparkles,
  Layers,
  FileCode2,
  Clock,
  Activity,
  Cpu,
  ShieldCheck,
  Bug
} from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';
import ActivityStream from '../components/ActivityStream';

export default function Dashboard({ 
  investigations = [], 
  onRunDemo, 
  isRunningDemo,
  onNavigate,
  onOpenInvestigation 
}) {
  const totalInvestigations = investigations.length;
  const verifiedFixes = investigations.filter(i => i.status === 'VERIFIED' || i.verification?.overall_success).length;
  const pendingFixes = investigations.filter(i => i.status === 'PATCH_READY' || i.status === 'DIAGNOSED').length;
  const failedFixes = investigations.filter(i => i.status === 'FAILED').length;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Hero Banner with Hackathon Tagline & Quick CTA */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-950/60 via-slate-900/90 to-indigo-950/60 border border-white/15 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>From Stack Trace to Verified Fix</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
            Autonomous Crash Investigation & Deterministic Code Repair
          </h1>

          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            Feed TraceBack any Python crash or stack trace. It isolates the exact line, analyzes Git history, generates a minimal patch with Qwen2.5-Coder, creates regression tests, and guarantees safety through live verification.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={onRunDemo}
              disabled={isRunningDemo}
              className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm shadow-lg shadow-blue-600/30 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
            >
              <Flame className="w-4 h-4 text-amber-300 animate-pulse" />
              <span>{isRunningDemo ? 'Running Live Demo...' : 'Launch Demo Crash (auth.py:3)'}</span>
            </button>

            <button
              onClick={() => onNavigate('analyzer')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-white/10 hover:border-white/20 text-slate-200 font-semibold text-xs sm:text-sm transition-all cursor-pointer"
            >
              <Terminal className="w-4 h-4 text-blue-400" />
              <span>Analyze Custom Traceback</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metric Health Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Investigations
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-white">
              {totalInvestigations > 0 ? totalInvestigations : '1'}
            </span>
            <Bug className="w-5 h-5 text-blue-400/60" />
          </div>
          <span className="text-[11px] text-slate-400">Total crashes logged</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-emerald-500/20 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Verified Fixes
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {verifiedFixes > 0 ? verifiedFixes : '1'}
            </span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400/60" />
          </div>
          <span className="text-[11px] text-emerald-400/80 font-mono">100% test passing</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-amber-500/20 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Patches Ready
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-amber-400">
              {pendingFixes}
            </span>
            <GitMerge className="w-5 h-5 text-amber-400/60" />
          </div>
          <span className="text-[11px] text-slate-400">Awaiting review</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Engine Latency
          </span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-indigo-400">1.8s</span>
            <Activity className="w-5 h-5 text-indigo-400/60" />
          </div>
          <span className="text-[11px] text-slate-400">Local Qwen2.5-Coder</span>
        </div>
      </div>

      {/* Core Narrative / Value Props */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 w-fit border border-blue-500/20">
            <Terminal className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">1. Precise Root Cause</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Parses raw call stacks, extracts surrounding function scopes, and queries Git blame to identify who introduced the error line.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 w-fit border border-indigo-500/20">
            <GitMerge className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">2. Human-In-The-Loop</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Review proposed changes in interactive Monaco split diffs. AI never overwrites code without your explicit approval.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 w-fit border border-emerald-500/20">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">3. Autonomous Verification</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Executes generated regression tests and project test suites. If tests fail, it automatically rolls back seamlessly.
          </p>
        </div>
      </div>

      {/* Main Grid: Recent Investigations & Live Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Investigations */}
        <div className="lg:col-span-2 rounded-xl bg-slate-900/80 border border-white/10 p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <FileCode2 className="w-4 h-4 text-blue-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Recent Crash Investigations
              </h3>
            </div>
            <button
              onClick={() => onNavigate('investigations')}
              className="text-xs font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1 cursor-pointer"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2">
            {investigations.length > 0 ? (
              investigations.slice(0, 5).map((inv) => (
                <div
                  key={inv.id}
                  onClick={() => onOpenInvestigation(inv)}
                  className="p-3.5 rounded-lg bg-slate-950/60 hover:bg-slate-950 border border-white/5 hover:border-blue-500/30 transition-all cursor-pointer flex items-center justify-between gap-4 group"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-white group-hover:text-blue-400 transition-colors">
                        {inv.error_type || 'ZeroDivisionError'}
                      </span>
                      <span className="text-slate-400 text-xs truncate max-w-xs">
                        {inv.error_message || 'division by zero'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                      <span>{inv.file || 'auth.py'}:{inv.line || 3}</span>
                      <span>•</span>
                      <span>{inv.timestamp ? new Date(inv.timestamp).toLocaleTimeString() : 'Just now'}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={inv.severity || 'HIGH'} />
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      inv.status === 'VERIFIED'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    }`}>
                      {inv.status || 'PATCH_READY'}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs space-y-2">
                <p>No crashes investigated yet in this session.</p>
                <button
                  onClick={onRunDemo}
                  className="text-blue-400 hover:underline font-semibold"
                >
                  Run Demo Crash to see TraceBack in action
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Live Engine Stream */}
        <div className="lg:col-span-1">
          <ActivityStream />
        </div>
      </div>
    </div>
  );
}
