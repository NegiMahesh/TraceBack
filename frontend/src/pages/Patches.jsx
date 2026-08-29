import React, { useState, useEffect } from 'react';
import { 
  GitMerge, 
  CheckCircle2, 
  RotateCcw, 
  FileCode, 
  Clock, 
  ShieldCheck, 
  Sparkles,
  AlertTriangle,
  Loader2
} from 'lucide-react';
import { api } from '../services/api';

export default function Patches({ onShowToast }) {
  const [patches, setPatches] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [rollingBackId, setRollingBackId] = useState(null);

  const fetchPatches = async () => {
    setIsLoading(true);
    try {
      const data = await api.getPatchHistory();
      setPatches(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPatches();
  }, []);

  const handleRollback = async (record) => {
    setRollingBackId(record.id);
    try {
      const res = await api.rollbackPatch(record.investigation_id, record.backup_ref);
      if (res.success) {
        onShowToast({
          type: 'success',
          title: 'Rollback Complete',
          message: `Reverted ${record.file} cleanly.`
        });
        fetchPatches();
      } else {
        throw new Error(res.message);
      }
    } catch (err) {
      onShowToast({
        type: 'error',
        title: 'Rollback Failed',
        message: err.message
      });
    } finally {
      setRollingBackId(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <GitMerge className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Patch Registry & Safety Records
          </h1>
          <p className="text-xs text-slate-400">
            Immutable log of all generated code patches, safety checkpoints, and verified rollbacks
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/10 bg-slate-900/90 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#0b0f19] border-b border-white/10 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="py-3 px-4">Patch ID</th>
              <th className="py-3 px-4">Target File</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Backup Ref</th>
              <th className="py-3 px-4">Applied Date</th>
              <th className="py-3 px-4 text-right">Rollback Control</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono">
            {patches.length > 0 ? (
              patches.map((p) => {
                const isApplied = p.status === 'APPLIED';
                return (
                  <tr key={p.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-indigo-400">{p.id}</td>
                    <td className="py-3.5 px-4 text-white flex items-center gap-1.5">
                      <FileCode className="w-3.5 h-3.5 text-blue-400" />
                      <span>{p.file}</span>
                    </td>
                    <td className="py-3.5 px-4 font-sans">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isApplied 
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">{p.backup_ref || 'stash-01'}</td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">{p.applied_at || 'Just now'}</td>
                    <td className="py-3.5 px-4 text-right font-sans">
                      {isApplied && (
                        <button
                          onClick={() => handleRollback(p)}
                          disabled={rollingBackId === p.id}
                          className="px-2.5 py-1 rounded bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-semibold inline-flex items-center gap-1 cursor-pointer transition-all disabled:opacity-50"
                        >
                          {rollingBackId === p.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <RotateCcw className="w-3 h-3" />
                          )}
                          <span>Rollback</span>
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-500 font-sans">
                  No patches applied yet in this session.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
