import React, { useState } from 'react';
import { 
  FileSearch, 
  Search, 
  Filter, 
  ArrowRight, 
  FileCode2, 
  CheckCircle2, 
  XCircle, 
  Clock,
  Sparkles
} from 'lucide-react';
import SeverityBadge from '../components/SeverityBadge';

export default function Investigations({ 
  investigations = [], 
  onOpenInvestigation,
  onNavigate 
}) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filtered = investigations.filter((inv) => {
    const matchesSearch = 
      (inv.error_type || '').toLowerCase().includes(search.toLowerCase()) ||
      (inv.file || '').toLowerCase().includes(search.toLowerCase()) ||
      (inv.root_cause || '').toLowerCase().includes(search.toLowerCase());
    
    if (statusFilter === 'ALL') return matchesSearch;
    return matchesSearch && inv.status === statusFilter;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <FileSearch className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Investigation Registry
            </h1>
            <p className="text-xs text-slate-400">
              Complete archive of parsed crashes, AI diagnoses, and patch verification histories
            </p>
          </div>
        </div>

        {/* Search & Filter */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-white">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by error, file..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent border-0 focus:outline-none placeholder:text-slate-500 font-sans text-xs w-44"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-slate-300 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="VERIFIED">Verified</option>
            <option value="PATCH_READY">Patch Ready</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* Investigations Table */}
      <div className="rounded-xl border border-white/10 bg-slate-900/90 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#0b0f19] border-b border-white/10 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="py-3 px-4">ID</th>
              <th className="py-3 px-4">Exception Type</th>
              <th className="py-3 px-4">Location</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">AI Confidence</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono">
            {filtered.length > 0 ? (
              filtered.map((inv) => (
                <tr 
                  key={inv.id} 
                  onClick={() => onOpenInvestigation(inv)}
                  className="hover:bg-slate-800/50 transition-colors cursor-pointer group"
                >
                  <td className="py-3.5 px-4 font-bold text-blue-400">
                    INV-{inv.id}
                  </td>
                  <td className="py-3.5 px-4 font-bold text-white font-sans">
                    {inv.error_type || 'ZeroDivisionError'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">
                    {inv.file}:{inv.line}
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <SeverityBadge severity={inv.severity || 'HIGH'} />
                  </td>
                  <td className="py-3.5 px-4 text-indigo-300 font-bold">
                    {Math.round(inv.confidence || 90)}%
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      inv.status === 'VERIFIED'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : inv.status === 'FAILED'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    }`}>
                      {inv.status || 'PATCH_READY'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                    {inv.timestamp ? new Date(inv.timestamp).toLocaleTimeString() : 'Recent'}
                  </td>
                  <td className="py-3.5 px-4 text-right font-sans">
                    <button className="text-blue-400 group-hover:text-blue-300 font-semibold inline-flex items-center gap-1">
                      <span>Inspect</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-500 font-sans">
                  No investigations recorded yet. Run a crash in Crash Analyzer to record your first diagnostic trace.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
