import React from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Cpu, 
  GitBranch, 
  Command, 
  Play, 
  Sparkles,
  Server,
  CheckCircle2,
  AlertTriangle,
  Flame
} from 'lucide-react';

export default function Header({ 
  systemStatus, 
  onRunDemo, 
  isRunningDemo,
  onOpenCommandPalette 
}) {
  const ollamaOnline = systemStatus?.ollama?.status === 'connected';
  const currentModel = systemStatus?.model || 'qwen2.5-coder:3b';
  const branchName = systemStatus?.repo?.branch || 'master';

  return (
    <header className="h-16 border-b border-white/10 bg-[#0b0f19]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 shadow-lg shadow-blue-500/20 text-white font-bold">
          <ShieldAlert className="w-5 h-5" />
          <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-[#0b0f19]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
              TraceBack
            </span>
            <span className="px-1.5 py-0.5 text-[10px] uppercase font-mono font-bold tracking-wider rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              PROD-READY
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            AI Crash Resolution & Autonomous Patch Engine
          </p>
        </div>
      </div>

      {/* Center Demo / Command Center Trigger */}
      <div className="flex items-center gap-3">
        <button
          onClick={onRunDemo}
          disabled={isRunningDemo}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md shadow-blue-600/25 transition-all duration-150 disabled:opacity-50 active:scale-95 cursor-pointer"
        >
          {isRunningDemo ? (
            <>
              <Activity className="w-3.5 h-3.5 animate-spin" />
              <span>Simulating Crash...</span>
            </>
          ) : (
            <>
              <Flame className="w-3.5 h-3.5 text-amber-300 animate-pulse" />
              <span>Run Demo Crash</span>
            </>
          )}
        </button>

        <button
          onClick={onOpenCommandPalette}
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-white/10 hover:border-white/20 text-slate-300 hover:text-white text-xs transition-all"
        >
          <Command className="w-3.5 h-3.5 text-slate-400" />
          <span>Command Center</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono border border-white/5">
            Ctrl + K
          </kbd>
        </button>
      </div>

      {/* Status Badges */}
      <div className="flex items-center gap-3 text-xs">
        {/* Ollama Status */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-900/90 border border-white/10">
          <div className={`w-2 h-2 rounded-full ${ollamaOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-300 font-mono text-[11px]">
              {ollamaOnline ? currentModel : 'Ollama Offline'}
            </span>
          </div>
        </div>

        {/* Git Branch */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/90 border border-white/10 text-slate-300">
          <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-mono text-[11px] text-slate-300">{branchName}</span>
        </div>
      </div>
    </header>
  );
}
