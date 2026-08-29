import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  RotateCcw, 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  Sparkles, 
  Terminal,
  Loader2,
  FileCheck2
} from 'lucide-react';

export default function VerificationReport({ 
  verification, 
  onRollback, 
  isRollingBack = false 
}) {
  if (!verification) return null;

  const {
    steps = [],
    overall_success = false,
    verdict = 'PENDING',
    generated_test_result,
    existing_test_result,
    rerun_result
  } = verification;

  const isVerified = overall_success && verdict === 'FIX VERIFIED';

  return (
    <div className={`p-5 rounded-xl border shadow-2xl space-y-4 transition-all duration-500 ${
      isVerified
        ? 'bg-gradient-to-br from-emerald-950/40 via-slate-900/90 to-slate-950 border-emerald-500/40 shadow-glow-emerald'
        : 'bg-gradient-to-br from-rose-950/40 via-slate-900/90 to-slate-950 border-rose-500/40 shadow-glow-rose'
    }`}>
      {/* Report Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-md ${
            isVerified 
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' 
              : 'bg-rose-500/20 text-rose-400 border-rose-500/40'
          }`}>
            {isVerified ? <ShieldCheck className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold tracking-tight text-white">
                TRACEBACK VERIFICATION REPORT
              </h3>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wider ${
                isVerified 
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              }`}>
                {verdict}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Deterministic multi-stage validation engine results
            </p>
          </div>
        </div>

        {/* Rollback button if failed */}
        {!isVerified && onRollback && (
          <button
            onClick={onRollback}
            disabled={isRollingBack}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md shadow-rose-600/25 transition-all cursor-pointer disabled:opacity-50 active:scale-95"
          >
            {isRollingBack ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Rolling Back...</span>
              </>
            ) : (
              <>
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Safe Auto-Rollback</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Verification Steps List */}
      <div className="space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
          Stage Execution Checks
        </span>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {steps.map((step, idx) => {
            const isPassed = step.status === 'passed';
            const isFailed = step.status === 'failed';
            const isRunning = step.status === 'running';

            return (
              <div
                key={idx}
                className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                  isPassed 
                    ? 'bg-slate-950/70 border-emerald-500/20' 
                    : isFailed 
                    ? 'bg-rose-950/30 border-rose-500/40' 
                    : 'bg-slate-950/40 border-white/5'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {isPassed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isFailed ? (
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  ) : isRunning ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin shrink-0" />
                  ) : (
                    <Clock className="w-4 h-4 text-slate-600 shrink-0" />
                  )}
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      {step.name}
                    </span>
                    {step.message && (
                      <span className={`text-[11px] font-mono ${isFailed ? 'text-rose-400' : 'text-slate-400'}`}>
                        {step.message}
                      </span>
                    )}
                  </div>
                </div>

                {step.duration_ms > 0 && (
                  <span className="text-[10px] font-mono text-slate-500">
                    {step.duration_ms}ms
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Verification Verdict Box */}
      <div className={`p-4 rounded-xl border text-center space-y-1.5 ${
        isVerified 
          ? 'bg-emerald-950/30 border-emerald-500/40' 
          : 'bg-rose-950/30 border-rose-500/40'
      }`}>
        <div className="flex items-center justify-center gap-2">
          {isVerified ? (
            <FileCheck2 className="w-5 h-5 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-400" />
          )}
          <span className={`text-sm font-bold uppercase tracking-wider font-mono ${
            isVerified ? 'text-emerald-300' : 'text-rose-300'
          }`}>
            {isVerified ? '✓ FIX VERIFIED — ALL TESTS PASSING' : '⚠ VERIFICATION FAILED — ROLLBACK AVAILABLE'}
          </span>
        </div>
        <p className="text-xs text-slate-300">
          {isVerified 
            ? 'The proposed patch resolved the original crash without causing regressions in existing test suites.'
            : 'The proposed patch failed one or more verification stages. No permanent changes were forced on your codebase.'}
        </p>
      </div>
    </div>
  );
}
