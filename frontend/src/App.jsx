import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import CommandPalette from './components/CommandPalette';
import Toast from './components/Toast';

import Dashboard from './pages/Dashboard';
import CrashAnalyzer from './pages/CrashAnalyzer';
import InvestigationView from './pages/InvestigationView';
import Investigations from './pages/Investigations';
import Patches from './pages/Patches';
import Repository from './pages/Repository';
import GitHistory from './pages/GitHistory';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

import { api } from './services/api';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [systemStatus, setSystemStatus] = useState(null);
  const [investigations, setInvestigations] = useState([]);
  const [activeInvestigation, setActiveInvestigation] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isRunningDemo, setIsRunningDemo] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [toasts, setToasts] = useState([]);

  // Toast notification helper
  const showToast = ({ type = 'info', title = '', message = '' }) => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const closeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Initial Load: Fetch system status & existing investigations
  const loadInitialData = async () => {
    try {
      const status = await api.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.warn('System status fetch warning:', err);
    }

    try {
      const invs = await api.getInvestigations();
      setInvestigations(invs || []);
    } catch (err) {
      console.warn('Investigations fetch warning:', err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // ── Start Investigation Workflow ────────────────────────────────────
  const handleStartInvestigation = async ({
    crashResult,
    tracebackText,
    repoPath
  }) => {
    setIsAnalyzing(true);
    showToast({
      type: 'info',
      title: 'Crash Captured',
      message: 'Parsing traceback & extracting source context for Qwen2.5-Coder analysis...'
    });

    try {
      const investigation = await api.analyze({
        crash_result: crashResult || null,
        traceback_text: tracebackText || '',
        repo_path: repoPath || systemStatus?.repo_path || 'demo_project',
        explanation_mode: 'developer'
      });

      setInvestigations((prev) => [investigation, ...prev]);
      setActiveInvestigation(investigation);
      setCurrentTab('investigation-view');

      showToast({
        type: 'success',
        title: 'Diagnosis Ready',
        message: `Root cause identified with ${Math.round(investigation.confidence || 90)}% confidence.`
      });
    } catch (err) {
      showToast({
        type: 'error',
        title: 'Investigation Error',
        message: err.message
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ── Launch Live Demo Crash ──────────────────────────────────────────
  const handleRunDemo = async () => {
    setIsRunningDemo(true);
    showToast({
      type: 'info',
      title: 'Demo Crash Initialized',
      message: 'Running buggy auth.py:3 module...'
    });

    try {
      const crashRes = await api.runDemo();
      
      if (crashRes.crashed) {
        showToast({
          type: 'info',
          title: 'ZeroDivisionError Captured',
          message: 'Extracting stack frames and querying Git blame...'
        });

        // Trigger AI analysis pipeline
        const inv = await api.analyze({
          crash_result: crashRes,
          repo_path: systemStatus?.repo_path || 'demo_project',
        });

        setInvestigations((prev) => [inv, ...prev]);
        setActiveInvestigation(inv);
        setCurrentTab('investigation-view');

        showToast({
          type: 'success',
          title: 'AI Investigation Complete',
          message: 'Patch & regression test generated. Ready for developer approval.'
        });
      }
    } catch (err) {
      showToast({
        type: 'error',
        title: 'Demo Execution Failed',
        message: err.message
      });
    } finally {
      setIsRunningDemo(false);
    }
  };

  const handleOpenInvestigation = (inv) => {
    setActiveInvestigation(inv);
    setCurrentTab('investigation-view');
  };

  const handleUpdateInvestigation = (updated) => {
    setActiveInvestigation(updated);
    setInvestigations((prev) =>
      prev.map((i) => (i.id === updated.id ? updated : i))
    );
  };

  const handleRunAllTests = async () => {
    showToast({
      type: 'info',
      title: 'Pytest Suite',
      message: 'Executing tests across the workspace...'
    });
    try {
      const res = await api.runTests();
      showToast({
        type: res.success ? 'success' : 'error',
        title: res.success ? 'Pytest Passed' : 'Pytest Failed',
        message: `${res.passed} passed, ${res.failed} failed (${res.duration_ms}ms)`
      });
    } catch (err) {
      showToast({ type: 'error', title: 'Test Execution Failed', message: err.message });
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <Header
        systemStatus={systemStatus}
        onRunDemo={handleRunDemo}
        isRunningDemo={isRunningDemo}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* Main Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          currentTab={currentTab === 'investigation-view' ? 'investigations' : currentTab}
          onSelectTab={(tabId) => {
            setCurrentTab(tabId);
            if (tabId !== 'investigation-view') {
              setActiveInvestigation(null);
            }
          }}
        />

        {/* Dynamic Page Content */}
        <main className="flex-1 overflow-y-auto bg-[#07090e]">
          {currentTab === 'dashboard' && (
            <Dashboard
              investigations={investigations}
              onRunDemo={handleRunDemo}
              isRunningDemo={isRunningDemo}
              onNavigate={setCurrentTab}
              onOpenInvestigation={handleOpenInvestigation}
            />
          )}

          {currentTab === 'analyzer' && (
            <CrashAnalyzer
              onStartInvestigation={handleStartInvestigation}
              isAnalyzing={isAnalyzing}
              repoPath={systemStatus?.repo_path}
            />
          )}

          {currentTab === 'investigation-view' && (
            <InvestigationView
              investigation={activeInvestigation}
              onBack={() => setCurrentTab('investigations')}
              onUpdateInvestigation={handleUpdateInvestigation}
              onShowToast={showToast}
            />
          )}

          {currentTab === 'investigations' && (
            <Investigations
              investigations={investigations}
              onOpenInvestigation={handleOpenInvestigation}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'patches' && (
            <Patches onShowToast={showToast} />
          )}

          {currentTab === 'repository' && (
            <Repository repoPath={systemStatus?.repo_path} />
          )}

          {currentTab === 'git-history' && (
            <GitHistory repoPath={systemStatus?.repo_path} />
          )}

          {currentTab === 'analytics' && (
            <Analytics investigations={investigations} />
          )}

          {currentTab === 'settings' && (
            <Settings
              systemStatus={systemStatus}
              onShowToast={showToast}
            />
          )}
        </main>
      </div>

      {/* Developer Command Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={(tab) => {
          setCurrentTab(tab);
          setIsCommandPaletteOpen(false);
        }}
        onRunDemo={handleRunDemo}
        onRunTests={handleRunAllTests}
      />

      {/* Global Toast Container */}
      <Toast toasts={toasts} onClose={closeToast} />
    </div>
  );
}
