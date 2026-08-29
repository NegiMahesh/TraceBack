import React from 'react';
import { AlertCircle, AlertTriangle, Flame, Info } from 'lucide-react';

export default function SeverityBadge({ severity = 'MEDIUM' }) {
  const norm = (severity || 'MEDIUM').toUpperCase();

  const configs = {
    LOW: {
      color: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      icon: Info,
      label: 'LOW'
    },
    MEDIUM: {
      color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: AlertTriangle,
      label: 'MEDIUM'
    },
    HIGH: {
      color: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
      icon: AlertCircle,
      label: 'HIGH'
    },
    CRITICAL: {
      color: 'bg-red-600/20 text-red-400 border-red-500/50 shadow-glow-rose',
      icon: Flame,
      label: 'CRITICAL'
    },
  };

  const current = configs[norm] || configs.MEDIUM;
  const Icon = current.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold tracking-wider font-mono border ${current.color}`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{current.label}</span>
    </span>
  );
}
