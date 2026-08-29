import React, { useState } from 'react';
import { 
  TestTube2, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Terminal, 
  Loader2, 
  Code2,
  Copy,
  Check
} from 'lucide-react';
import CodeViewer from './CodeViewer';

export default function TestPanel({ 
  testCode = '', 
  testResult = null, 
  onRunTest, 
  isRunning = false 
}) {
  const [activeTab, setActiveTab] = useState('code'); // code | output
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!testCode) return;
    navigator.clipboard.writeText(testCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasResult = !!testResult;
  const passed = testResult?.passed || 0;
  const failed = testResult?.failed || 0;
  const duration = testResult?.duration_ms || 0;
  const isSuccess = testResult?.success || false;

  return (
    <div className="rounded-xl overflow-hidden border border-white/10 bg-slate-900/90 shadow-xl flex flex-col space-y-3 p-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <TestTube2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Autonomous Regression Test
            </h3>
            <p className="text-[11px] text-slate-400">
              Proves whether the bug is reproduced and verifies patch stability
            </p>
          </div>
        </div>

        {/* Action button */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRunTest}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50 active:scale-95"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running Pytest...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Test Suite</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Test Execution Summary Cards (If Run) */}
      {hasResult && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className={`p-3 rounded-lg border flex items-center justify-between ${
            isSuccess 
              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300' 
              : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
          }`}>
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Status</span>
              <span className="text-xs font-bold font-mono">
                {isSuccess ? 'PASSED' : 'FAILED'}
              </span>
            </div>
            {isSuccess ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-rose-400" />}
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Passed</span>
              <span className="text-xs font-bold font-mono text-emerald-400">{passed}</span>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500/50" />
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Failed</span>
              <span className="text-xs font-bold font-mono text-rose-400">{failed}</span>
            </div>
            <XCircle className="w-4 h-4 text-rose-500/50" />
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-400 block">Duration</span>
              <span className="text-xs font-bold font-mono text-slate-200">{duration} ms</span>
            </div>
            <Clock className="w-4 h-4 text-slate-500" />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('code')}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${
              activeTab === 'code' 
                ? 'bg-slate-800 text-white font-bold' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Generated Test Code
          </button>
          {hasResult && (
            <button
              onClick={() => setActiveTab('output')}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                activeTab === 'output' 
                  ? 'bg-slate-800 text-white font-bold' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Pytest Stderr / Stdout
            </button>
          )}
        </div>

        {activeTab === 'code' && testCode && (
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800/50"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        )}
      </div>

      {/* Tab Content */}
      {activeTab === 'code' ? (
        <div className="h-56 rounded-lg overflow-hidden border border-white/5">
          <CodeViewer
            code={testCode || '# No regression test generated yet.'}
            language="python"
            fileName="test_regression.py"
            height="100%"
          />
        </div>
      ) : (
        <div className="h-56 p-3 rounded-lg bg-slate-950 border border-white/5 overflow-auto font-mono text-xs text-slate-300 space-y-1">
          {testResult?.stdout && (
            <pre className="text-slate-300 whitespace-pre-wrap">{testResult.stdout}</pre>
          )}
          {testResult?.stderr && (
            <pre className="text-rose-400 whitespace-pre-wrap">{testResult.stderr}</pre>
          )}
        </div>
      )}
    </div>
  );
}
