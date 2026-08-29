import React from 'react';
import { Activity, Terminal, ShieldCheck, Bug, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ActivityStream({ activities = [] }) {
  const defaultActivities = [
    { time: '21:34:08', type: 'crash', text: 'Crash detected in auth.py:3 (ZeroDivisionError)', status: 'danger' },
    { time: '21:34:09', type: 'parse', text: 'Stack trace parsed: 2 frames extracted', status: 'info' },
    { time: '21:34:10', type: 'source', text: 'auth.py:3 located and context built (15 lines)', status: 'info' },
    { time: '21:34:11', type: 'git', text: 'Git blame identified commit 7d31a2f (Mahesh Negi)', status: 'info' },
    { time: '21:34:13', type: 'ai', text: 'Qwen2.5-Coder generated root cause diagnosis & patch', status: 'success' },
    { time: '21:34:14', type: 'patch', text: 'Regression test generated and validated', status: 'success' },
  ];

  const list = activities.length > 0 ? activities : defaultActivities;

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900/80 p-4 shadow-xl space-y-3">
      <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Real-Time Engine Stream
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Active</span>
        </div>
      </div>

      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
        {list.map((item, idx) => {
          let dotColor = 'bg-blue-400';
          let textColor = 'text-slate-300';
          if (item.status === 'danger') {
            dotColor = 'bg-rose-400';
            textColor = 'text-rose-300';
          } else if (item.status === 'success') {
            dotColor = 'bg-emerald-400';
            textColor = 'text-emerald-300';
          }

          return (
            <div key={idx} className="flex items-start gap-2.5 text-xs font-mono py-1 border-b border-white/5 last:border-0">
              <span className="text-slate-500 shrink-0 text-[11px]">{item.time}</span>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${dotColor} mt-1 shrink-0`} />
                <span className={`text-[11px] ${textColor}`}>{item.text}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
