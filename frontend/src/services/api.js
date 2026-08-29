/**
 * API Service for communicating with the TraceBack FastAPI backend.
 */

const API_BASE = '/api';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // System
  async getHealth() {
    return handleResponse(await fetch(`${API_BASE}/health`));
  },

  async getSystemStatus() {
    return handleResponse(await fetch(`${API_BASE}/system/status`));
  },

  // Crash
  async runCrash(filePath, args = [], cwd = null, timeout = 30) {
    return handleResponse(await fetch(`${API_BASE}/crash/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, args, cwd, timeout })
    }));
  },

  async analyzeTraceback(tracebackText, repoPath = null) {
    return handleResponse(await fetch(`${API_BASE}/crash/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ traceback_text: tracebackText, repo_path: repoPath })
    }));
  },

  async uploadLog(file) {
    const formData = new FormData();
    formData.append('file', file);
    return handleResponse(await fetch(`${API_BASE}/crash/upload`, {
      method: 'POST',
      body: formData,
    }));
  },

  // Full AI Analysis & Demo
  async analyze(params) {
    return handleResponse(await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    }));
  },

  async runDemo(repoPath = null) {
    return handleResponse(await fetch(`${API_BASE}/demo/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: repoPath })
    }));
  },

  async getInvestigations() {
    return handleResponse(await fetch(`${API_BASE}/investigations`));
  },

  async getInvestigation(id) {
    return handleResponse(await fetch(`${API_BASE}/investigations/${id}`));
  },

  // Patch
  async validatePatch(patch, targetFile, repoPath = null, investigationId = '') {
    return handleResponse(await fetch(`${API_BASE}/patch/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patch,
        target_file: targetFile,
        repo_path: repoPath,
        investigation_id: investigationId
      })
    }));
  },

  async applyPatch(patch, targetFile, repoPath = null, investigationId = '') {
    return handleResponse(await fetch(`${API_BASE}/patch/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patch,
        target_file: targetFile,
        repo_path: repoPath,
        investigation_id: investigationId
      })
    }));
  },

  async verifyPatch(patch, targetFile, repoPath = null, investigationId = '') {
    return handleResponse(await fetch(`${API_BASE}/patch/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patch,
        target_file: targetFile,
        repo_path: repoPath,
        investigation_id: investigationId
      })
    }));
  },

  async rollbackPatch(investigationId, backupRef, repoPath = null) {
    return handleResponse(await fetch(`${API_BASE}/patch/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        investigation_id: investigationId,
        backup_ref: backupRef,
        repo_path: repoPath
      })
    }));
  },

  async getPatchHistory() {
    return handleResponse(await fetch(`${API_BASE}/patch/history`));
  },

  // Tests
  async runTests(target = '', repoPath = null) {
    return handleResponse(await fetch(`${API_BASE}/tests/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, repo_path: repoPath })
    }));
  },

  // Repository & Git
  async getRepository(repoPath = null) {
    const query = repoPath ? `?repo_path=${encodeURIComponent(repoPath)}` : '';
    return handleResponse(await fetch(`${API_BASE}/repository${query}`));
  },

  async getFiles(repoPath = null) {
    const query = repoPath ? `?repo_path=${encodeURIComponent(repoPath)}` : '';
    return handleResponse(await fetch(`${API_BASE}/repository/files${query}`));
  },

  async getFile(filePath, repoPath = null) {
    const params = new URLSearchParams({ path: filePath });
    if (repoPath) params.append('repo_path', repoPath);
    return handleResponse(await fetch(`${API_BASE}/file?${params.toString()}`));
  },

  async getGitStatus(repoPath = null) {
    const query = repoPath ? `?repo_path=${encodeURIComponent(repoPath)}` : '';
    return handleResponse(await fetch(`${API_BASE}/git/status${query}`));
  },

  async getGitBlame(filePath, line, repoPath = null) {
    const params = new URLSearchParams({ file: filePath, line: String(line) });
    if (repoPath) params.append('repo_path', repoPath);
    return handleResponse(await fetch(`${API_BASE}/git/blame?${params.toString()}`));
  },

  async getGitHistory(filePath = null, count = 20, repoPath = null) {
    const params = new URLSearchParams({ count: String(count) });
    if (filePath) params.append('file', filePath);
    if (repoPath) params.append('repo_path', repoPath);
    return handleResponse(await fetch(`${API_BASE}/git/history?${params.toString()}`));
  },

  async getGitDiff(repoPath = null) {
    const query = repoPath ? `?repo_path=${encodeURIComponent(repoPath)}` : '';
    return handleResponse(await fetch(`${API_BASE}/git/diff${query}`));
  }
};
