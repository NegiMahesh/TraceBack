import React, { useState } from 'react';
import { 
  Terminal, 
  FileText, 
  UploadCloud, 
  FolderGit2, 
  Play, 
  Sparkles, 
  AlertOctagon, 
  Loader2, 
  CheckCircle2,
  FileCode,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';

export default function CrashAnalyzer({ 
  onStartInvestigation, 
  isAnalyzing = false,
  repoPath = ''
}) {
  const [activeTab, setActiveTab] = useState('run'); // 'run' | 'paste' | 'upload' | 'repo'
  
  // Option A: Run File
  const [runFile, setRunFile] = useState('auth.py');
  const [runArgs, setRunArgs] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [runOutput, setRunOutput] = useState(null);

  // Option B: Paste
  const [pastedTrace, setPastedTrace] = useState(`Traceback (most recent call last):
  File "auth.py", line 33, in <module>
    result = login_user({"username": "admin"})
  File "auth.py", line 12, in login_user
    risk_score = 100 / trust_level
ZeroDivisionError: division by zero`);

  // Option C: Upload
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // Option D: Repo
  const [customRepo, setCustomRepo] = useState(repoPath || '');

  // ── Option A Handler: Run Project ───────────────────────────────────
  const handleRunProject = async () => {
    setIsRunning(true);
    setRunOutput(null);
    try {
      const argsArray = runArgs.trim() ? runArgs.trim().split(/\s+/) : [];
      const res = await api.runCrash(runFile, argsArray, customRepo || null);
      setRunOutput(res);
      
      if (res.crashed && res.raw_traceback) {
        // Trigger investigation
        onStartInvestigation({
          crashResult: res,
          repoPath: customRepo || null,
          errorType: res.traceback?.error_type,
          file: res.traceback?.file
        });
      }
    } catch (err) {
      setRunOutput({
        crashed: true,
        stderr: err.message,
        stdout: '',
        exit_code: -1
      });
    } finally {
      setIsRunning(false);
    }
  };

  // ── Option B Handler: Paste Traceback ──────────────────────────────
  const handleAnalyzePasted = async () => {
    if (!pastedTrace.trim()) return;
    onStartInvestigation({
      tracebackText: pastedTrace,
      repoPath: customRepo || null
    });
  };

  // ── Option C Handler: Upload Log ───────────────────────────────────
  const handleUploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadFile(file);
    setIsUploading(true);
    try {
      const res = await api.uploadLog(file);
      if (res.parsed) {
        onStartInvestigation({
          tracebackText: res.parsed.raw,
          repoPath: customRepo || null
        });
      }
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Crash & Traceback Analyzer
            </h1>
            <p className="text-xs text-slate-400">
              Provide an execution entrypoint, stack trace, or log to initiate autonomous diagnosis
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/10 pb-3">
        {[
          { id: 'run', label: 'Option A — Run Python Project', icon: Play },
          { id: 'paste', label: 'Option B — Paste Traceback', icon: FileText },
          { id: 'upload', label: 'Option C — Upload Log File', icon: UploadCloud },
          { id: 'repo', label: 'Option D — Target Repository', icon: FolderGit2 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="rounded-xl border border-white/10 bg-slate-900/90 p-5 shadow-2xl space-y-4">
        {/* OPTION A: Run Project */}
        {activeTab === 'run' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2 space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Python Entry File
                </label>
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950 border border-white/10 text-xs font-mono">
                  <FileCode className="w-4 h-4 text-blue-400 shrink-0" />
                  <input
                    type="text"
                    value={runFile}
                    onChange={(e) => setRunFile(e.target.value)}
                    placeholder="e.g. auth.py or demo_project/auth.py"
                    className="w-full bg-transparent border-0 text-white focus:outline-none placeholder:text-slate-600"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">
                  Arguments (Optional)
                </label>
                <input
                  type="text"
                  value={runArgs}
                  onChange={(e) => setRunArgs(e.target.value)}
                  placeholder="--debug --port 8080"
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-white/10 text-xs font-mono text-white focus:outline-none placeholder:text-slate-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] text-slate-400">
                Executes via safe subprocess with execution time & exit code capture
              </span>
              <button
                onClick={handleRunProject}
                disabled={isRunning || isAnalyzing}
                className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md shadow-blue-600/30 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
              >
                {isRunning || isAnalyzing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing & Investigating...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Execute & Trace Crash</span>
                  </>
                )}
              </button>
            </div>

            {/* Run Output Console */}
            {runOutput && (
              <div className="mt-4 p-4 rounded-lg bg-slate-950 border border-white/10 space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-white/10 text-slate-400">
                  <span>Exit Code: <strong className={runOutput.crashed ? 'text-rose-400' : 'text-emerald-400'}>{runOutput.exit_code}</strong></span>
                  <span>Duration: {runOutput.duration_ms}ms</span>
                </div>
                {runOutput.stdout && (
                  <div>
                    <span className="text-slate-500 block text-[10px]">STDOUT:</span>
                    <pre className="text-slate-300 whitespace-pre-wrap">{runOutput.stdout}</pre>
                  </div>
                )}
                {runOutput.stderr && (
                  <div>
                    <span className="text-rose-400 block text-[10px]">STDERR / TRACEBACK:</span>
                    <pre className="text-rose-400 whitespace-pre-wrap">{runOutput.stderr}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* OPTION B: Paste Traceback */}
        {activeTab === 'paste' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Paste Python Stack Trace / Error Log
              </label>
              <textarea
                rows={10}
                value={pastedTrace}
                onChange={(e) => setPastedTrace(e.target.value)}
                placeholder="Traceback (most recent call last):&#10;  File 'app.py', line 12, in main&#10;ZeroDivisionError: division by zero"
                className="w-full p-4 rounded-lg bg-slate-950 border border-white/10 font-mono text-xs text-rose-300 focus:outline-none focus:border-blue-500/50 leading-relaxed"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] text-slate-400">
                Supports standard CPython tracebacks across all exception types
              </span>
              <button
                onClick={handleAnalyzePasted}
                disabled={isAnalyzing || !pastedTrace.trim()}
                className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-600/30 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing Stack Frames...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Analyze Traceback</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* OPTION C: Upload Log */}
        {activeTab === 'upload' && (
          <div className="space-y-4">
            <div className="border-2 border-dashed border-white/15 rounded-xl p-8 text-center space-y-3 bg-slate-950/40 hover:bg-slate-950/70 transition-colors">
              <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center border border-blue-500/20">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-bold text-white">Upload Error Log or Trace File</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Drag & drop or browse for .log, .txt, .trace, or .json
                </p>
              </div>
              <input
                type="file"
                accept=".log,.txt,.trace,.json"
                onChange={handleUploadFile}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer border border-white/10 transition-all"
              >
                Browse File
              </label>
            </div>
            {isUploading && (
              <div className="flex items-center justify-center gap-2 text-xs text-blue-400 font-mono">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Parsing uploaded log file...</span>
              </div>
            )}
          </div>
        )}

        {/* OPTION D: Target Repository */}
        {activeTab === 'repo' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 block">
                Local Repository / Directory Path
              </label>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950 border border-white/10 text-xs font-mono">
                <FolderGit2 className="w-4 h-4 text-indigo-400 shrink-0" />
                <input
                  type="text"
                  value={customRepo}
                  onChange={(e) => setCustomRepo(e.target.value)}
                  placeholder="e.g. demo_project or /path/to/repo"
                  className="w-full bg-transparent border-0 text-white focus:outline-none placeholder:text-slate-600"
                />
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              TraceBack will use this directory for source mapping, file context queries, and Git blame analysis.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
