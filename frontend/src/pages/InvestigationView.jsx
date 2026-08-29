import React, { useState } from 'react';
import { 
  ArrowLeft, 
  Terminal, 
  GitMerge, 
  TestTube2, 
  ShieldCheck, 
  FileCode2, 
  Clock, 
  Sparkles,
  AlertOctagon,
  CheckCircle2,
  RefreshCw,
  Copy,
  Check
} from 'lucide-react';
import InvestigationTimeline from '../components/InvestigationTimeline';
import RootCauseCard from '../components/RootCauseCard';
import CodeViewer from '../components/CodeViewer';
import DiffViewer from '../components/DiffViewer';
import TestPanel from '../components/TestPanel';
import VerificationReport from '../components/VerificationReport';
import { api } from '../services/api';

export default function InvestigationView({ 
  investigation, 
  onBack, 
  onUpdateInvestigation,
  onShowToast 
}) {
  const [isApplying, setIsApplying] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [activeTab, setActiveTab] = useState('diff'); // 'diff' | 'source' | 'test'

  if (!investigation) return null;

  const {
    id,
    error_type,
    error_message,
    file,
    line,
    patch,
    test_case,
    source_context,
    verification,
    status
  } = investigation;

  // Determine timeline progress step
  let stepIndex = 4; // AI Investigation Complete
  if (patch) stepIndex = 5;
  if (test_case) stepIndex = 6;
  if (verification?.overall_success) stepIndex = 7;

  // ── Handler: Approve & Verify Fix ───────────────────────────────────
  const handleApproveFix = async (customModified) => {
    setIsApplying(true);
    try {
      onShowToast({
        type: 'info',
        title: 'Verifying Fix...',
        message: 'Applying patch and executing multi-stage test suite.'
      });

      // Call verification endpoint directly
      const report = await api.verifyPatch(
        patch,
        file,
        investigation.repo_path || null,
        id
      );

      const updated = {
        ...investigation,
        verification: report,
        status: report.overall_success ? 'VERIFIED' : 'FAILED'
      };

      onUpdateInvestigation(updated);

      if (report.overall_success) {
        onShowToast({
          type: 'success',
          title: 'Fix Verified!',
          message: 'Patch applied, regression test passed, and existing tests succeeded.'
        });
      } else {
        onShowToast({
          type: 'error',
          title: 'Verification Failed',
          message: 'Patch failed verification. Auto-rollback was triggered.'
        });
      }
    } catch (err) {
      onShowToast({
        type: 'error',
        title: 'Patch Error',
        message: err.message
      });
    } finally {
      setIsApplying(false);
    }
  };

  // ── Handler: Reject Fix ─────────────────────────────────────────────
  const handleRejectFix = () => {
    const updated = { ...investigation, status: 'REJECTED' };
    onUpdateInvestigation(updated);
    onShowToast({
      type: 'info',
      title: 'Fix Rejected',
      message: 'Proposed patch was rejected by developer.'
    });
  };

  // ── Handler: Safe Rollback ──────────────────────────────────────────
  const handleRollback = async () => {
    setIsRollingBack(true);
    try {
      const backupRef = investigation.verification?.backup_ref || '';
      const res = await api.rollbackPatch(id, backupRef, investigation.repo_path || null);
      if (res.success) {
        const updated = { ...investigation, status: 'ROLLED_BACK' };
        onUpdateInvestigation(updated);
        onShowToast({
          type: 'success',
          title: 'Rollback Complete',
          message: 'Files reverted to clean state without touching unrelated changes.'
        });
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
      setIsRollingBack(false);
    }
  };

  // ── Handler: Run Pytest Test Suite On Demand ─────────────────────────
  const handleRunTests = async () => {
    setIsRunningTest(true);
    try {
      const res = await api.runTests('', investigation.repo_path || null);
      onShowToast({
        type: res.success ? 'success' : 'error',
        title: res.success ? 'Pytest Succeeded' : 'Pytest Failed',
        message: `${res.passed} passed, ${res.failed} failed (${res.duration_ms}ms)`
      });
    } catch (err) {
      onShowToast({ type: 'error', title: 'Test Runner Error', message: err.message });
    } finally {
      setIsRunningTest(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Bar with Back & Meta */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-slate-900 border border-white/10 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-blue-400 font-bold">INV-{id}</span>
              <span className="text-white font-bold text-base tracking-tight">
                {error_type}: {error_message}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Target: {file}:{line}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider ${
            status === 'VERIFIED'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              : status === 'FAILED'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
          }`}>
            {status}
          </span>
        </div>
      </div>

      {/* Autonomous Investigation Timeline Stream */}
      <InvestigationTimeline
        currentStep={stepIndex}
        isComplete={status === 'VERIFIED'}
      />

      {/* Root Cause & Diagnosis Section */}
      <RootCauseCard investigation={investigation} />

      {/* Code / Patch / Test Navigation Tabs */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-2">
          <div className="flex items-center gap-2">
            {[
              { id: 'diff', label: 'Proposed Patch & Diff', icon: GitMerge, badge: patch ? 'Ready' : null },
              { id: 'source', label: 'Surrounding Source Code', icon: FileCode2 },
              { id: 'test', label: 'Regression Test Suite', icon: TestTube2, badge: test_case ? 'Generated' : null },
            ].map((t) => {
              const Icon = t.icon;
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{t.label}</span>
                  {t.badge && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      {t.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab 1: Monaco Diff Viewer */}
        {activeTab === 'diff' && (
          <DiffViewer
            originalCode={source_context?.content || ''}
            patch={patch || ''}
            fileName={file || 'auth.py'}
            onApprove={handleApproveFix}
            onReject={handleRejectFix}
            isApplying={isApplying}
            isApproved={status === 'VERIFIED'}
            isRejected={status === 'REJECTED'}
          />
        )}

        {/* Tab 2: Monaco Source Viewer */}
        {activeTab === 'source' && (
          <CodeViewer
            code={source_context?.content || '# Loading source code...'}
            language="python"
            errorLine={line}
            fileName={file || 'source.py'}
            height="380px"
          />
        )}

        {/* Tab 3: Test Panel */}
        {activeTab === 'test' && (
          <TestPanel
            testCode={test_case || ''}
            testResult={verification?.generated_test_result}
            onRunTest={handleRunTests}
            isRunning={isRunningTest}
          />
        )}
      </div>

      {/* Verification Report Section (If fix was approved or verified) */}
      {verification && (
        <VerificationReport
          verification={verification}
          onRollback={handleRollback}
          isRollingBack={isRollingBack}
        />
      )}
    </div>
  );
}
