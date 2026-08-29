import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ toasts = [], onClose }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isError = toast.type === 'error';

        return (
          <div
            key={toast.id}
            className={`p-3.5 rounded-xl border shadow-2xl backdrop-blur-md flex items-start justify-between gap-3 text-xs animate-in slide-in-from-bottom-5 duration-200 ${
              isSuccess
                ? 'bg-slate-900/95 border-emerald-500/40 text-emerald-300'
                : isError
                ? 'bg-slate-900/95 border-rose-500/40 text-rose-300'
                : 'bg-slate-900/95 border-blue-500/40 text-blue-300'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {isSuccess ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              ) : isError ? (
                <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
              ) : (
                <Info className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
              )}
              <div>
                {toast.title && <h4 className="font-bold text-white mb-0.5">{toast.title}</h4>}
                <p className="text-slate-300 text-[11px] leading-relaxed">{toast.message}</p>
              </div>
            </div>

            <button
              onClick={() => onClose(toast.id)}
              className="text-slate-500 hover:text-white p-0.5 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
