import React, { useState } from 'react';

import {
  ArrowLeft,
  Terminal,
  GitMerge,
  TestTube2,
  ShieldCheck,
  FileCode2,
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
  onShowToast,
}) {
  const [isApplying, setIsApplying] =
    useState(false);

  const [isRollingBack, setIsRollingBack] =
    useState(false);

  const [isRunningTest, setIsRunningTest] =
    useState(false);

  const [activeTab, setActiveTab] =
    useState('diff');

  if (!investigation) {
    return null;
  }

  const {
    id,
    error_type,
    error_message,
    file,
    line,
    patch,
    test_case,
    source_context,
    original_code,
    modified_code,
    preview_available,
    preview_error,
    verification,
    status,
  } = investigation;


  // ---------------------------------------------------------------
  // Timeline
  // ---------------------------------------------------------------

  let stepIndex = 4;

  if (patch) {
    stepIndex = 5;
  }

  if (test_case) {
    stepIndex = 6;
  }

  if (verification?.overall_success) {
    stepIndex = 7;
  }


  // ---------------------------------------------------------------
  // Approve + Verify
  // ---------------------------------------------------------------

  const handleApproveFix = async (
    customModified
  ) => {
    setIsApplying(true);

    try {
      onShowToast({
        type: 'info',
        title: 'Verifying Fix...',
        message:
          'Applying patch and executing multi-stage verification.',
      });

      const report =
        await api.verifyPatch(
          patch,
          file,
          investigation.repo_path || null,
          id
        );

      const updated = {
        ...investigation,

        verification:
          report,

        status:
          report.overall_success
            ? 'VERIFIED'
            : 'FAILED',
      };

      onUpdateInvestigation(
        updated
      );

      if (
        report.overall_success
      ) {
        onShowToast({
          type: 'success',
          title: 'Fix Verified!',
          message:
            'Patch applied, tests passed, and the repaired application runs successfully.',
        });
      } else {

        const failedStep =
          Array.isArray(
            report.steps
          )
            ? report.steps.find(
              (step) =>
                step.status ===
                'failed'
            )
            : null;

        onShowToast({
          type: 'error',
          title:
            failedStep
              ? `${failedStep.name} Failed`
              : 'Verification Failed',

          message:
            failedStep?.message ||
            report.verdict ||
            'Patch failed verification.',
        });
      }

    } catch (error) {

      onShowToast({
        type: 'error',
        title: 'Patch Error',
        message:
          error.message ||
          'Unexpected verification error.',
      });

    } finally {
      setIsApplying(false);
    }
  };


  // ---------------------------------------------------------------
  // Reject
  // ---------------------------------------------------------------

  const handleRejectFix = () => {

    const updated = {
      ...investigation,
      status: 'REJECTED',
    };

    onUpdateInvestigation(
      updated
    );

    onShowToast({
      type: 'info',
      title: 'Fix Rejected',
      message:
        'Proposed patch was rejected.',
    });
  };


  // ---------------------------------------------------------------
  // Rollback
  // ---------------------------------------------------------------

  const handleRollback = async () => {

    setIsRollingBack(true);

    try {

      const backupRef =
        investigation
          .verification
          ?.backup_ref || '';

      if (!backupRef) {
        throw new Error(
          'No backup reference is available.'
        );
      }

      const result =
        await api.rollbackPatch(
          id,
          backupRef,
          investigation.repo_path ||
          null
        );

      if (!result.success) {
        throw new Error(
          result.message ||
          'Rollback failed.'
        );
      }

      const updated = {
        ...investigation,
        status: 'ROLLED_BACK',
      };

      onUpdateInvestigation(
        updated
      );

      onShowToast({
        type: 'success',
        title: 'Rollback Complete',
        message:
          'Original source restored successfully.',
      });

    } catch (error) {

      onShowToast({
        type: 'error',
        title: 'Rollback Failed',
        message:
          error.message ||
          'Could not rollback the patch.',
      });

    } finally {

      setIsRollingBack(
        false
      );
    }
  };


  // ---------------------------------------------------------------
  // Run tests manually
  // ---------------------------------------------------------------

  const handleRunTests = async () => {

    setIsRunningTest(true);

    try {

      const result =
        await api.runTests(
          '',
          investigation.repo_path ||
          null
        );

      onShowToast({
        type:
          result.success
            ? 'success'
            : 'error',

        title:
          result.success
            ? 'Pytest Succeeded'
            : 'Pytest Failed',

        message:
          `${result.passed} passed, ` +
          `${result.failed} failed ` +
          `(${result.duration_ms}ms)`,
      });

    } catch (error) {

      onShowToast({
        type: 'error',
        title: 'Test Runner Error',
        message:
          error.message ||
          'Could not run tests.',
      });

    } finally {

      setIsRunningTest(
        false
      );
    }
  };


  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">

      {/* =========================================================
          HEADER
      ========================================================== */}

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

              <span className="font-mono text-xs text-blue-400 font-bold">
                INV-{id}
              </span>

              <span className="text-white font-bold text-base tracking-tight">
                {error_type}: {error_message}
              </span>

            </div>

            <p className="text-xs text-slate-400 font-mono">
              Target: {file}:{line}
            </p>

          </div>

        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider ${status === 'VERIFIED'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              : status === 'FAILED'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
            }`}
        >
          {status}
        </span>

      </div>


      {/* =========================================================
          TIMELINE
      ========================================================== */}

      <InvestigationTimeline
        investigation={investigation}
      />


      {/* =========================================================
          ROOT CAUSE
      ========================================================== */}

      <RootCauseCard
        investigation={investigation}
      />


      {/* =========================================================
          TABS
      ========================================================== */}

      <div className="space-y-4">

        <div className="flex items-center justify-between border-b border-white/10 pb-2">

          <div className="flex items-center gap-2">

            {[
              {
                id: 'diff',
                label:
                  'Proposed Patch & Diff',
                icon: GitMerge,
                badge:
                  patch
                    ? preview_available
                      ? 'Ready'
                      : 'Patch'
                    : null,
              },

              {
                id: 'source',
                label:
                  'Surrounding Source Code',
                icon: FileCode2,
              },

              {
                id: 'test',
                label:
                  'Regression Test Suite',
                icon: TestTube2,
                badge:
                  test_case
                    ? 'Generated'
                    : null,
              },
            ].map((tab) => {

              const Icon =
                tab.icon;

              const active =
                activeTab ===
                tab.id;

              return (
                <button
                  key={tab.id}
                  onClick={() =>
                    setActiveTab(
                      tab.id
                    )
                  }
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${active
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                >
                  <Icon className="w-3.5 h-3.5" />

                  <span>
                    {tab.label}
                  </span>

                  {tab.badge && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      {tab.badge}
                    </span>
                  )}

                </button>
              );
            })}

          </div>

        </div>


        {/* =======================================================
            DIFF
        ======================================================== */}

        {activeTab === 'diff' && (
          <div className="space-y-3">

            {preview_error && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-300">
                <strong>
                  Preview notice:
                </strong>{' '}
                {preview_error}
              </div>
            )}

            <DiffViewer
              originalCode={
                original_code ||
                source_context?.content ||
                ''
              }

              modifiedCode={
                modified_code ||
                ''
              }

              patch={
                patch || ''
              }

              fileName={
                file ||
                'source.py'
              }

              onApprove={
                handleApproveFix
              }

              onReject={
                handleRejectFix
              }

              isApplying={
                isApplying
              }

              isApproved={
                status ===
                'VERIFIED'
              }

              isRejected={
                status ===
                'REJECTED'
              }
            />

          </div>
        )}


        {/* =======================================================
            SOURCE
        ======================================================== */}

        {activeTab === 'source' && (
          <CodeViewer
            code={
              source_context?.content ||
              original_code ||
              '# Source unavailable'
            }

            language="python"

            errorLine={
              line
            }

            fileName={
              file ||
              'source.py'
            }

            height="380px"
          />
        )}


        {/* =======================================================
            TEST
        ======================================================== */}

        {activeTab === 'test' && (
          <TestPanel
            testCode={
              test_case ||
              ''
            }

            testResult={
              verification
                ?.generated_test_result
            }

            onRunTest={
              handleRunTests
            }

            isRunning={
              isRunningTest
            }
          />
        )}

      </div>


      {/* =========================================================
          VERIFICATION REPORT
      ========================================================== */}

      {verification && (
        <VerificationReport
          verification={
            verification
          }

          onRollback={
            handleRollback
          }

          isRollingBack={
            isRollingBack
          }
        />
      )}

    </div>
  );
}