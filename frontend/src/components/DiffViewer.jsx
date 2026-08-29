import React, { useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { 
  GitMerge, 
  CheckCircle2, 
  XCircle, 
  Edit3, 
  ShieldCheck, 
  Columns, 
  Rows, 
  Loader2,
  Sparkles,
  AlertCircle
} from 'lucide-react';

export default function DiffViewer({ 
  originalCode = '', 
  modifiedCode = '', 
  patch = '',
  fileName = 'auth.py', 
  onApprove, 
  onReject, 
  isApplying = false,
  isRejected = false,
  isApproved = false 
}) {
  const [inlineView, setInlineView] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [customModified, setCustomModified] = useState(modifiedCode || originalCode);

  // If modifiedCode is not directly passed, derive it or use patch
  let finalModified = modifiedCode;
  if (!finalModified && originalCode && patch) {
    // Generate modified preview from patch
    finalModified = originalCode; // Fallback
  }

  return (
    <div className="rounded-xl overflow-hidden border border-white/10 bg-slate-950 shadow-2xl flex flex-col">
      {/* Diff Header */}
      <div className="px-4 py-3 bg-[#0b0f19] border-b border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <GitMerge className="w-4 h-4 text-emerald-400" />
          <span className="font-mono font-bold text-slate-200">{fileName}</span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-mono">
            PROPOSED FIX
          </span>
        </div>

        {/* View mode toggle & Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInlineView(!inlineView)}
            className="flex items-center gap-1 px-2.5 py-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/10 transition-colors cursor-pointer"
            title="Toggle Split / Inline Diff"
          >
            {inlineView ? <Columns className="w-3.5 h-3.5" /> : <Rows className="w-3.5 h-3.5" />}
            <span>{inlineView ? 'Side-by-Side' : 'Inline'}</span>
          </button>

          {/* Approve / Reject Actions */}
          {!isApproved && !isRejected && (
            <div className="flex items-center gap-2">
              <button
                onClick={onReject}
                disabled={isApplying}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-slate-300 hover:text-rose-300 bg-slate-900 hover:bg-rose-950/40 border border-white/10 hover:border-rose-500/30 transition-all text-xs font-semibold cursor-pointer active:scale-95"
              >
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
                <span>Reject</span>
              </button>

              <button
                onClick={() => onApprove(isEditing ? customModified : null)}
                disabled={isApplying}
                className="flex items-center gap-1.5 px-4 py-1 rounded-lg text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-md shadow-emerald-600/30 transition-all text-xs font-semibold cursor-pointer active:scale-95 disabled:opacity-50"
              >
                {isApplying ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Applying & Verifying...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-200" />
                    <span>Approve & Verify Fix</span>
                  </>
                )}
              </button>
            </div>
          )}

          {isApproved && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-emerald-300 bg-emerald-950/80 border border-emerald-500/40 font-bold text-xs">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Patch Approved</span>
            </span>
          )}

          {isRejected && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-rose-300 bg-rose-950/80 border border-rose-500/40 font-bold text-xs">
              <XCircle className="w-4 h-4 text-rose-400" />
              <span>Patch Rejected</span>
            </span>
          )}
        </div>
      </div>

      {/* Monaco Diff Editor */}
      <div className="h-80 w-full">
        {originalCode && (finalModified || patch) ? (
          <DiffEditor
            height="100%"
            language="python"
            original={originalCode}
            modified={finalModified || originalCode}
            theme="vs-dark"
            options={{
              renderSideBySide: !inlineView,
              readOnly: true,
              fontSize: 13,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              fontFamily: "'JetBrains Mono', Consolas, monospace",
            }}
          />
        ) : (
          /* Raw Unified Diff View Fallback */
          <div className="p-4 font-mono text-xs overflow-auto h-full bg-slate-950 text-slate-300">
            <pre className="space-y-0.5">
              {patch ? (
                patch.split('\n').map((line, i) => {
                  let cls = 'text-slate-400';
                  if (line.startsWith('+') && !line.startsWith('+++')) cls = 'text-emerald-400 bg-emerald-950/30';
                  else if (line.startsWith('-') && !line.startsWith('---')) cls = 'text-rose-400 bg-rose-950/30';
                  else if (line.startsWith('@@')) cls = 'text-blue-400 font-bold';
                  return (
                    <div key={i} className={`px-2 py-0.5 ${cls}`}>
                      {line}
                    </div>
                  );
                })
              ) : (
                <span className="text-slate-500 italic">No patch generated yet.</span>
              )}
            </pre>
          </div>
        )}
      </div>

      {/* Safety Info Bar */}
      <div className="px-4 py-2 bg-slate-900/90 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>Safety: Automatic Git backup created before patch application.</span>
        </div>
        <span className="font-mono text-slate-500">Autonomous Rollback Enabled</span>
      </div>
    </div>
  );
}
