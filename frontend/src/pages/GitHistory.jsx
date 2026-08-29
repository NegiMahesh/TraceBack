import React, { useState, useEffect } from 'react';
import { 
  History, 
  GitCommit, 
  GitBranch, 
  User, 
  Calendar, 
  FileCode, 
  Search,
  CheckCircle2,
  RefreshCw,
  GitMerge
} from 'lucide-react';
import { api } from '../services/api';

export default function GitHistory({ repoPath }) {
  const [commits, setCommits] = useState([]);
  const [gitStatus, setGitStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchGitData = async () => {
    setIsLoading(true);
    try {
      const status = await api.getGitStatus(repoPath);
      setGitStatus(status);

      const history = await api.getGitHistory(null, 25, repoPath);
      setCommits(history.commits || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGitData();
  }, [repoPath]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Git Intelligence & Commit Timeline
            </h1>
            <p className="text-xs text-slate-400">
              Correlate code crashes with authorship, recent commit logs, and repository delta states
            </p>
          </div>
        </div>

        <button
          onClick={fetchGitData}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 hover:bg-slate-800 text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Git Log</span>
        </button>
      </div>

      {/* Git Status Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Current Branch
          </span>
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-indigo-400" />
            <span className="text-lg font-bold font-mono text-white">
              {gitStatus?.branch || 'master'}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Working Tree State
          </span>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-sm font-bold text-slate-200">
              {gitStatus?.clean ? 'Clean (No uncommitted drift)' : `${gitStatus?.modified_files?.length || 0} modified files`}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
            Latest Hash
          </span>
          <div className="flex items-center gap-2">
            <GitCommit className="w-5 h-5 text-blue-400" />
            <span className="text-base font-bold font-mono text-blue-400">
              {gitStatus?.latest_commit?.hash || 'e67847f'}
            </span>
          </div>
        </div>
      </div>

      {/* Commit History Timeline */}
      <div className="rounded-xl border border-white/10 bg-slate-900/90 p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Recent Commit History
          </h3>
          <span className="text-[11px] font-mono text-slate-500">
            {commits.length} commits logged
          </span>
        </div>

        <div className="space-y-3">
          {commits.length > 0 ? (
            commits.map((commit, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-lg bg-slate-950/60 border border-white/5 flex flex-wrap items-center justify-between gap-3 hover:border-white/15 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                    <GitCommit className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-white block">
                      {commit.message}
                    </span>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                      <span>{commit.author}</span>
                      <span>•</span>
                      <span>{commit.date}</span>
                    </div>
                  </div>
                </div>

                <span className="font-mono text-xs text-indigo-300 font-bold px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30">
                  {commit.hash}
                </span>
              </div>
            ))
          ) : (
            <div className="py-8 text-center text-slate-500 text-xs font-sans">
              No commit history returned from repository.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
