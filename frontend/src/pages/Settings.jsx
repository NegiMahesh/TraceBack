import React, { useState } from 'react';
import { 
  Settings as SettingsIcon, 
  Cpu, 
  Server, 
  ShieldCheck, 
  Clock, 
  Save, 
  Check,
  RefreshCw,
  Sparkles
} from 'lucide-react';

export default function Settings({ systemStatus, onShowToast }) {
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [model, setModel] = useState(systemStatus?.model || 'qwen2.5-coder:3b');
  const [timeout, setTimeoutVal] = useState('120');
  const [temperature, setTemperature] = useState('0.1');
  const [saved, setSaved] = useState(false);

  const availableModels = systemStatus?.ollama?.models || ['qwen2.5-coder:3b', 'qwen3:1.7b'];

  const handleSave = (e) => {
    e.preventDefault();
    setSaved(true);
    onShowToast({
      type: 'success',
      title: 'Settings Saved',
      message: `Active model configured to ${model}`
    });
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <SettingsIcon className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            System & LLM Engine Settings
          </h1>
          <p className="text-xs text-slate-400">
            Configure local Ollama connectivity, inference parameters, and diagnostic timeouts
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Ollama Service Settings */}
        <div className="rounded-xl border border-white/10 bg-slate-900/90 p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Ollama LLM Backend
              </h3>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
              systemStatus?.ollama?.status === 'connected'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
            }`}>
              {systemStatus?.ollama?.status === 'connected' ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 block">Ollama Endpoint URL</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-white/10 font-mono text-white focus:outline-none focus:border-blue-500/50"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 block">Target Model</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-white/10 font-mono text-white focus:outline-none focus:border-blue-500/50"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 block">Temperature (Determinism)</label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-white/10 font-mono text-white focus:outline-none focus:border-blue-500/50"
              />
              <span className="text-[10px] text-slate-500">Recommended: 0.1 for deterministic patch diffs</span>
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 block">Request Timeout (Seconds)</label>
              <input
                type="number"
                value={timeout}
                onChange={(e) => setTimeoutVal(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-white/10 font-mono text-white focus:outline-none focus:border-blue-500/50"
              />
            </div>
          </div>
        </div>

        {/* Security & Safety Policies */}
        <div className="rounded-xl border border-white/10 bg-slate-900/90 p-5 shadow-xl space-y-3 text-xs">
          <div className="flex items-center gap-2 border-b border-white/10 pb-3">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Security Policy Enforcement
            </h3>
          </div>
          <div className="space-y-2 text-slate-300 text-[12px] leading-relaxed">
            <p>✓ <strong>Subprocess Array Execution:</strong> Shell string injections are strictly blocked.</p>
            <p>✓ <strong>Path Traversal Defense:</strong> All file reads & writes are constrained to verified project bounds.</p>
            <p>✓ <strong>Explicit Approval Gate:</strong> AI patches are never auto-committed without developer approval.</p>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md shadow-blue-600/30 transition-all cursor-pointer active:scale-95"
          >
            {saved ? <Check className="w-4 h-4 text-emerald-300" /> : <Save className="w-4 h-4" />}
            <span>{saved ? 'Saved Successfully' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
