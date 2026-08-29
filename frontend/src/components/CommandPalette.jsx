import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Terminal, 
  Play, 
  GitMerge, 
  FolderGit2, 
  FileSearch, 
  Settings, 
  RotateCcw,
  Sparkles,
  Command,
  X
} from 'lucide-react';

export default function CommandPalette({ 
  isOpen, 
  onClose, 
  onNavigate, 
  onRunDemo, 
  onRunTests 
}) {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(false); // Toggle
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    { id: 'demo', label: 'Run Demo Crash Scenario', icon: Play, shortcut: 'D', action: onRunDemo },
    { id: 'analyzer', label: 'Analyze Crash / Paste Traceback', icon: Terminal, action: () => onNavigate('analyzer') },
    { id: 'tests', label: 'Execute Pytest Suite', icon: Play, action: onRunTests },
    { id: 'patches', label: 'View Proposed Patches & Diffs', icon: GitMerge, action: () => onNavigate('patches') },
    { id: 'repo', label: 'Browse Repository Files', icon: FolderGit2, action: () => onNavigate('repository') },
    { id: 'history', label: 'View Investigation History', icon: FileSearch, action: () => onNavigate('investigations') },
    { id: 'settings', label: 'Open System Settings', icon: Settings, action: () => onNavigate('settings') },
  ];

  const filtered = actions.filter(a => 
    a.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-start justify-center pt-24 px-4">
      <div 
        className="w-full max-w-xl rounded-2xl bg-slate-900 border border-white/15 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/10 bg-slate-950/80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Type a command or search action..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="w-full bg-transparent border-0 text-sm text-white focus:outline-none placeholder:text-slate-500 font-sans"
          />
          <button 
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="p-2 max-h-72 overflow-y-auto space-y-1">
          {filtered.length > 0 ? (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    item.action?.();
                    onClose();
                  }}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-blue-600/20 hover:border-blue-500/30 border border-transparent transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-slate-800 group-hover:bg-blue-500/20 text-slate-400 group-hover:text-blue-400 transition-colors">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span>{item.label}</span>
                  </div>
                  {item.shortcut && (
                    <kbd className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400">
                      {item.shortcut}
                    </kbd>
                  )}
                </button>
              );
            })
          ) : (
            <div className="py-8 text-center text-xs text-slate-500">
              No matching commands found
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 bg-slate-950 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500">
          <span>Navigation: <kbd className="px-1 py-0.5 rounded bg-slate-800 text-[10px]">↑</kbd> <kbd className="px-1 py-0.5 rounded bg-slate-800 text-[10px]">↓</kbd></span>
          <span>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px]">ESC</kbd> to close</span>
        </div>
      </div>
    </div>
  );
}
