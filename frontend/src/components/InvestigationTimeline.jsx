import React from 'react';

import {
  AlertOctagon,
  Binary,
  MapPin,
  GitCommit,
  BrainCircuit,
  GitMerge,
  TestTube,
  CheckCheck,
  CheckCircle2,
  Clock3,
  XCircle,
  Loader2,
} from 'lucide-react';


const PIPELINE_STEPS = [
  {
    id: 'detected',
    label: 'Error Detected',
    icon: AlertOctagon,
  },
  {
    id: 'parsed',
    label: 'Trace Parsed',
    icon: Binary,
  },
  {
    id: 'located',
    label: 'Source Located',
    icon: MapPin,
  },
  {
    id: 'git',
    label: 'Git History Analyzed',
    icon: GitCommit,
  },
  {
    id: 'ai',
    label: 'AI Investigation',
    icon: BrainCircuit,
  },
  {
    id: 'patch',
    label: 'Patch Generated',
    icon: GitMerge,
  },
  {
    id: 'test',
    label: 'Test Generated',
    icon: TestTube,
  },
  {
    id: 'verified',
    label: 'Fix Verified',
    icon: CheckCheck,
  },
];


function getStepState(
  stepId,
  investigation,
) {
  if (!investigation) {
    return 'pending';
  }

  const {
    status,
    error_type,
    error_message,
    file,
    line,
    source_context,
    git_blame,
    patch,
    test_case,
    verification,
  } = investigation;


  switch (stepId) {

    // ---------------------------------------------------------------
    // STEP 1
    // ---------------------------------------------------------------

    case 'detected':

      return (
        error_type ||
        error_message
      )
        ? 'passed'
        : 'pending';


    // ---------------------------------------------------------------
    // STEP 2
    // ---------------------------------------------------------------

    case 'parsed':

      return (
        error_type &&
        typeof line === 'number' &&
        line > 0
      )
        ? 'passed'
        : 'pending';


    // ---------------------------------------------------------------
    // STEP 3
    // ---------------------------------------------------------------

    case 'located':

      return (
        file ||
        source_context?.file_path ||
        source_context?.content
      )
        ? 'passed'
        : 'pending';


    // ---------------------------------------------------------------
    // STEP 4
    // ---------------------------------------------------------------

    case 'git':

      // A Git repository may legitimately have no blame information.
      // If investigation happened and git_blame exists, mark passed.
      // Otherwise display as warning/pending rather than falsely claiming
      // success.

      if (git_blame) {
        return 'passed';
      }

      if (
        status === 'PATCH_READY' ||
        patch ||
        test_case ||
        verification
      ) {
        return 'warning';
      }

      return 'pending';


    // ---------------------------------------------------------------
    // STEP 5
    // ---------------------------------------------------------------

    case 'ai':

      if (
        status === 'PATCH_READY' ||
        status === 'DIAGNOSED' ||
        patch ||
        investigation.root_cause
      ) {
        return (
          investigation.root_cause
            ? 'passed'
            : 'warning'
        );
      }

      return 'pending';


    // ---------------------------------------------------------------
    // STEP 6
    // ---------------------------------------------------------------

    case 'patch':

      if (patch) {
        return 'passed';
      }

      if (
        status === 'DIAGNOSED'
      ) {
        return 'failed';
      }

      return 'pending';


    // ---------------------------------------------------------------
    // STEP 7
    // ---------------------------------------------------------------

    case 'test':

      if (test_case) {
        return 'passed';
      }

      if (
        patch &&
        !test_case
      ) {
        return 'warning';
      }

      return 'pending';


    // ---------------------------------------------------------------
    // STEP 8
    // ---------------------------------------------------------------

    case 'verified':

      if (
        verification?.overall_success === true ||
        status === 'VERIFIED'
      ) {
        return 'passed';
      }

      if (
        verification &&
        verification.overall_success === false
      ) {
        return 'failed';
      }

      return 'pending';


    default:
      return 'pending';
  }
}


function stateClasses(
  state,
) {

  switch (state) {

    case 'passed':
      return {
        circle:
          'bg-emerald-950/80 border-emerald-500/50 text-emerald-400 shadow-sm shadow-emerald-500/20',

        text:
          'text-emerald-300',

        icon:
          'text-emerald-400',
      };


    case 'failed':
      return {
        circle:
          'bg-rose-950/80 border-rose-500/50 text-rose-400 shadow-sm shadow-rose-500/20',

        text:
          'text-rose-300',

        icon:
          'text-rose-400',
      };


    case 'warning':
      return {
        circle:
          'bg-amber-950/80 border-amber-500/50 text-amber-400 shadow-sm shadow-amber-500/20',

        text:
          'text-amber-300',

        icon:
          'text-amber-400',
      };


    default:
      return {
        circle:
          'bg-slate-900 border-slate-800 text-slate-500',

        text:
          'text-slate-500',

        icon:
          'text-slate-500',
      };
  }
}


export default function InvestigationTimeline({
  investigation,
}) {

  const states =
    PIPELINE_STEPS.map(
      (step) => ({
        ...step,
        state: getStepState(
          step.id,
          investigation,
        ),
      }),
    );


  const passedCount =
    states.filter(
      (step) =>
        step.state === 'passed'
    ).length;


  const failedCount =
    states.filter(
      (step) =>
        step.state === 'failed'
    ).length;


  const warningCount =
    states.filter(
      (step) =>
        step.state === 'warning'
    ).length;


  const currentIndex =
    states.findIndex(
      (step) =>
        step.state === 'warning'
        ||
        step.state === 'pending'
    );


  const displayIndex =
    currentIndex === -1
      ? PIPELINE_STEPS.length
      : currentIndex + 1;


  return (
    <div className="w-full p-4 rounded-xl bg-slate-900/80 border border-white/10 shadow-lg">

      {/* ==========================================================
          HEADER
      =========================================================== */}

      <div className="flex items-center justify-between mb-3">

        <div className="flex items-center gap-2">

          <div
            className={`w-2 h-2 rounded-full ${
              failedCount > 0
                ? 'bg-rose-500'
                : warningCount > 0
                ? 'bg-amber-500'
                : 'bg-blue-500'
            } animate-pulse`}
          />

          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Autonomous Pipeline Stream
          </span>

        </div>


        <span className="text-[11px] font-mono text-slate-400">

          Step {displayIndex} of {PIPELINE_STEPS.length}

        </span>

      </div>


      {/* ==========================================================
          PIPELINE
      =========================================================== */}

      <div className="relative">

        {/* Base line */}

        <div className="absolute top-1/2 left-4 right-4 h-0.5 -translate-y-1/2 bg-slate-800 z-0" />


        {/* Progress line */}

        <div
          className="absolute top-1/2 left-4 h-0.5 -translate-y-1/2 pipeline-flowing-gradient z-0 transition-all duration-500"
          style={{
            width: `${
              Math.max(
                0,
                Math.min(
                  100,
                  (
                    passedCount /
                    (PIPELINE_STEPS.length - 1)
                  ) *
                  95
                )
              )
            }%`,
          }}
        />


        <div className="relative z-10 grid grid-cols-4 md:grid-cols-8 gap-2">

          {states.map(
            (
              step,
              idx,
            ) => {

              const Icon =
                step.icon;

              const styles =
                stateClasses(
                  step.state,
                );


              return (
                <div
                  key={step.id}
                  className="flex flex-col items-center text-center group"
                >

                  {/* Circle */}

                  <div
                    className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all duration-300 ${styles.circle}`}
                  >

                    {step.state ===
                      'passed' && (
                      <CheckCircle2
                        className={`w-4 h-4 ${styles.icon}`}
                      />
                    )}


                    {step.state ===
                      'failed' && (
                      <XCircle
                        className={`w-4 h-4 ${styles.icon}`}
                      />
                    )}


                    {step.state ===
                      'warning' && (
                      <Clock3
                        className={`w-4 h-4 ${styles.icon}`}
                      />
                    )}


                    {step.state ===
                      'pending' && (
                      <Icon
                        className={`w-3.5 h-3.5 ${styles.icon}`}
                      />
                    )}

                  </div>


                  {/* Label */}

                  <span
                    className={`mt-2 text-[10px] font-medium leading-tight line-clamp-1 transition-colors ${styles.text}`}
                  >
                    {step.label}
                  </span>


                  {/* State */}

                  <span className="mt-0.5 text-[8px] uppercase tracking-wider font-mono opacity-0 group-hover:opacity-100 transition-opacity">

                    {step.state}

                  </span>

                </div>
              );
            },
          )}

        </div>

      </div>


      {/* ==========================================================
          STATUS SUMMARY
      =========================================================== */}

      <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-[10px] font-mono">

        <span className="flex items-center gap-1.5 text-emerald-400">

          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />

          {passedCount} passed

        </span>


        {warningCount > 0 && (
          <span className="flex items-center gap-1.5 text-amber-400">

            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />

            {warningCount} warning

          </span>
        )}


        {failedCount > 0 && (
          <span className="flex items-center gap-1.5 text-rose-400">

            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />

            {failedCount} failed

          </span>
        )}

      </div>

    </div>
  );
}