import React from 'react';
import { 
  LayoutDashboard, 
  Terminal, 
  FolderGit2, 
  FileSearch, 
  GitMerge, 
  TestTube2, 
  History, 
  BarChart3, 
  Settings,
  Sparkles
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'analyzer', label: 'Crash Analyzer', icon: Terminal, badge: 'Live' },
  { id: 'repository', label: 'Repository', icon: FolderGit2 },
  { id: 'investigations', label: 'Investigations', icon: FileSearch },
  { id: 'patches', label: 'Patches & Diff', icon: GitMerge },
  { id: 'tests', label: 'Test Suite', icon: TestTube2 },
  { id: 'git-history', label: 'Git Intelligence', icon: History },
  { id: 'analytics', label: 'Error Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ currentTab, onSelectTab }) {
  return (
    <aside className="w-64 border-r border-white/10 bg-[#090d16] flex flex-col justify-between p-4 select-none shrink-0">
      <div className="space-y-6">
        {/* Navigation Group */}
        <div>
          <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Navigation
          </p>
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                    isActive 
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10' 
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Bottom Product Philosophy Card */}
      <div className="p-3 rounded-xl bg-gradient-to-br from-slate-900/90 to-blue-950/40 border border-white/10 text-xs">
        <div className="flex items-center gap-2 text-blue-400 font-semibold mb-1">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Core Guarantee</span>
        </div>
        <p className="text-[11px] text-slate-300 leading-relaxed">
          AI proposes. Developer approves. TraceBack verifies.
        </p>
      </div>
    </aside>
  );
}
