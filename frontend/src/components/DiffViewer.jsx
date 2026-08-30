import React, {
  useEffect,
  useState,
} from 'react';

import {
  DiffEditor,
} from '@monaco-editor/react';

import {
  GitMerge,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Columns,
  Rows,
  Loader2,
  Sparkles,
  AlertCircle,
  Code2,
} from 'lucide-react';


export default function DiffViewer({
  originalCode = '',
  modifiedCode = '',
  patch = '',
  fileName = 'source.py',
  onApprove,
  onReject,
  isApplying = false,
  isRejected = false,
  isApproved = false,
}) {

  const [
    inlineView,
    setInlineView,
  ] = useState(false);

  const [
    isEditing,
    setIsEditing,
  ] = useState(false);

  const [
    customModified,
    setCustomModified,
  ] = useState(
    modifiedCode || ''
  );


  useEffect(() => {

    setCustomModified(
      modifiedCode || ''
    );

  }, [
    modifiedCode,
  ]);


  // IMPORTANT:
  // Never use originalCode as modifiedCode.
  //
  // That was the main reason the UI was showing:
  //
  //     BEFORE == AFTER
  //
  // when a patch existed.

  const effectiveModified =
    isEditing
      ? customModified
      : modifiedCode;


  const hasOriginal =
    Boolean(
      originalCode
    );


  const hasModified =
    Boolean(
      effectiveModified
    );


  const hasActualChange =
    hasOriginal &&
    hasModified &&
    originalCode !==
      effectiveModified;


  const handleApprove =
    () => {

      if (
        typeof onApprove !==
        'function'
      ) {
        return;
      }

      onApprove(
        isEditing
          ? customModified
          : null
      );
    };


  return (
    <div className="rounded-xl overflow-hidden border border-white/10 bg-slate-950 shadow-2xl flex flex-col">

      {/* ========================================================
          HEADER
      ========================================================= */}

      <div className="px-4 py-3 bg-[#0b0f19] border-b border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs">

        <div className="flex items-center gap-2">

          <GitMerge className="w-4 h-4 text-emerald-400" />

          <span className="font-mono font-bold text-slate-200">
            {fileName}
          </span>

          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-mono">
            PROPOSED FIX
          </span>

        </div>


        <div className="flex items-center gap-2">

          {/* View toggle */}

          <button
            type="button"
            onClick={() =>
              setInlineView(
                (value) =>
                  !value
              )
            }
            className="flex items-center gap-1 px-2.5 py-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/10 transition-colors cursor-pointer"
          >
            {inlineView ? (
              <Columns className="w-3.5 h-3.5" />
            ) : (
              <Rows className="w-3.5 h-3.5" />
            )}

            <span>
              {inlineView
                ? 'Side-by-Side'
                : 'Inline'}
            </span>

          </button>


          {/* Edit */}

          {!isApproved &&
            !isRejected && (
              <button
                type="button"
                onClick={() =>
                  setIsEditing(
                    (value) =>
                      !value
                  )
                }
                disabled={
                  isApplying ||
                  !hasOriginal
                }
                className="flex items-center gap-1 px-2.5 py-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/10 transition-colors cursor-pointer disabled:opacity-50"
              >

                <Code2 className="w-3.5 h-3.5" />

                <span>
                  {isEditing
                    ? 'Finish Edit'
                    : 'Edit'}
                </span>

              </button>
            )}


          {/* Actions */}

          {!isApproved &&
            !isRejected && (
              <div className="flex items-center gap-2">

                <button
                  type="button"
                  onClick={
                    onReject
                  }
                  disabled={
                    isApplying
                  }
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-slate-300 hover:text-rose-300 bg-slate-900 hover:bg-rose-950/40 border border-white/10 hover:border-rose-500/30 transition-all text-xs font-semibold cursor-pointer active:scale-95 disabled:opacity-50"
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  Reject
                </button>


                <button
                  type="button"
                  onClick={
                    handleApprove
                  }
                  disabled={
                    isApplying ||
                    (
                      !patch &&
                      !hasActualChange
                    )
                  }
                  className="flex items-center gap-1.5 px-4 py-1 rounded-lg text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-md shadow-emerald-600/30 transition-all text-xs font-semibold cursor-pointer active:scale-95 disabled:opacity-50"
                >

                  {isApplying ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />

                      <span>
                        Applying & Verifying...
                      </span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-200" />

                      <span>
                        Approve & Verify Fix
                      </span>
                    </>
                  )}

                </button>

              </div>
            )}


          {/* Approved */}

          {isApproved && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-emerald-300 bg-emerald-950/80 border border-emerald-500/40 font-bold text-xs">

              <CheckCircle2 className="w-4 h-4 text-emerald-400" />

              Patch Approved

            </span>
          )}


          {/* Rejected */}

          {isRejected && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-rose-300 bg-rose-950/80 border border-rose-500/40 font-bold text-xs">

              <XCircle className="w-4 h-4 text-rose-400" />

              Patch Rejected

            </span>
          )}

        </div>

      </div>


      {/* ========================================================
          NO PREVIEW
      ========================================================= */}

      {!hasModified && (
        <div className="px-4 py-3 border-b border-amber-500/10 bg-amber-500/5 flex items-center gap-2 text-xs text-amber-300">

          <AlertCircle className="w-4 h-4 shrink-0" />

          <span>
            A modified source preview was not generated.
            The raw unified patch is shown below.
          </span>

        </div>
      )}


      {/* ========================================================
          EDITOR
      ========================================================= */}

      <div className="h-[420px] w-full">

        {isEditing ? (

          <textarea
            value={
              customModified
            }

            onChange={(
              event
            ) =>
              setCustomModified(
                event.target.value
              )
            }

            spellCheck={false}

            className="w-full h-full resize-none bg-slate-950 text-slate-200 p-4 font-mono text-sm outline-none border-0"

            aria-label="Edited proposed source"
          />

        ) : hasOriginal &&
          hasModified ? (

          <DiffEditor

            height="100%"

            language="python"

            original={
              originalCode
            }

            modified={
              effectiveModified
            }

            theme="vs-dark"

            options={{
              renderSideBySide:
                !inlineView,

              readOnly:
                true,

              fontSize:
                13,

              minimap: {
                enabled: false,
              },

              scrollBeyondLastLine:
                false,

              automaticLayout:
                true,

              diffCodeLens:
                true,

              renderOverviewRuler:
                true,

              renderIndicators:
                true,

              ignoreTrimWhitespace:
                false,

              fontFamily:
                "'JetBrains Mono', Consolas, monospace",
            }}
          />

        ) : (

          /* ======================================================
             RAW PATCH FALLBACK
          ======================================================= */

          <div className="p-4 font-mono text-xs overflow-auto h-full bg-slate-950 text-slate-300">

            {patch ? (

              <pre className="leading-6">

                {patch
                  .split('\n')
                  .map(
                    (
                      line,
                      index
                    ) => {

                      let className =
                        'text-slate-400';

                      if (
                        line.startsWith(
                          '+'
                        ) &&
                        !line.startsWith(
                          '+++'
                        )
                      ) {
                        className =
                          'text-emerald-400 bg-emerald-950/30';
                      }

                      else if (
                        line.startsWith(
                          '-'
                        ) &&
                        !line.startsWith(
                          '---'
                        )
                      ) {
                        className =
                          'text-rose-400 bg-rose-950/30';
                      }

                      else if (
                        line.startsWith(
                          '@@'
                        )
                      ) {
                        className =
                          'text-blue-400 font-bold';
                      }

                      return (
                        <div
                          key={
                            `${index}-${line}`
                          }
                          className={`px-2 py-0.5 ${className}`}
                        >
                          {line}
                        </div>
                      );
                    }
                  )}

              </pre>

            ) : (

              <div className="flex items-center justify-center h-full text-slate-500 italic">
                No patch generated yet.
              </div>

            )}

          </div>
        )}

      </div>


      {/* ========================================================
          CHANGE STATUS
      ========================================================= */}

      {hasOriginal &&
        hasModified && (
          <div className="px-4 py-2 border-t border-white/5 bg-slate-900/70 text-[11px]">

            {hasActualChange ? (

              <span className="text-emerald-400">
                ✓ Actual source changes detected
              </span>

            ) : (

              <span className="text-amber-400">
                ⚠ Before and After are identical
              </span>

            )}

          </div>
        )}


      {/* ========================================================
          FOOTER
      ========================================================= */}

      <div className="px-4 py-2 bg-slate-900/90 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">

        <div className="flex items-center gap-1.5">

          <Sparkles className="w-3.5 h-3.5 text-blue-400" />

          <span>
            Safety: Automatic Git backup created before patch application.
          </span>

        </div>

        <span className="font-mono text-slate-500">
          Autonomous Rollback Enabled
        </span>

      </div>

    </div>
  );
}