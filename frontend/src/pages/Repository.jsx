import React, { useState, useEffect } from 'react';
import { 
  FolderGit2, 
  FileCode, 
  GitCommit, 
  User, 
  Calendar, 
  Loader2, 
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import FileTree from '../components/FileTree';
import CodeViewer from '../components/CodeViewer';
import { api } from '../services/api';

export default function Repository({ repoPath }) {
  const [fileTree, setFileTree] = useState([]);
  const [selectedFile, setSelectedFile] = useState('auth.py');
  const [fileContent, setFileContent] = useState('');
  const [fileLanguage, setFileLanguage] = useState('python');
  const [isLoading, setIsLoading] = useState(true);
  const [blameInfo, setBlameInfo] = useState(null);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const res = await api.getFiles(repoPath);
      setFileTree(res.tree || []);

      // If we have files, load auth.py or first file
      loadFileContent('auth.py');
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadFileContent = async (path) => {
    setSelectedFile(path);
    try {
      const data = await api.getFile(path, repoPath);
      setFileContent(data.content || '');
      setFileLanguage(data.language || 'python');

      // Also get git blame for line 1
      try {
        const blame = await api.getGitBlame(path, 1, repoPath);
        setBlameInfo(blame);
      } catch {
        setBlameInfo(null);
      }
    } catch (err) {
      setFileContent(`# Error loading file: ${err.message}`);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [repoPath]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Repository Workspace Explorer
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              {repoPath || 'Active Workspace'}
            </p>
          </div>
        </div>

        <button
          onClick={loadFiles}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 hover:bg-slate-800 text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Tree</span>
        </button>
      </div>

      {/* Explorer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Col: File Tree */}
        <div className="lg:col-span-1 rounded-xl border border-white/10 bg-slate-900/90 p-4 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Files
            </span>
            <span className="text-[10px] font-mono text-slate-500">Tree view</span>
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span>Scanning project...</span>
            </div>
          ) : (
            <FileTree
              tree={fileTree}
              selectedFile={selectedFile}
              onSelectFile={loadFileContent}
            />
          )}
        </div>

        {/* Right 3 Cols: Monaco Editor + Blame Bar */}
        <div className="lg:col-span-3 space-y-4">
          <CodeViewer
            code={fileContent}
            language={fileLanguage}
            fileName={selectedFile}
            height="500px"
          />

          {/* Git Blame Context Footer */}
          {blameInfo && blameInfo.commit_hash && (
            <div className="p-3.5 rounded-xl bg-slate-900/90 border border-white/10 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-slate-300">
                <GitCommit className="w-4 h-4 text-indigo-400" />
                <span className="text-slate-400">Last touched by:</span>
                <span className="font-bold text-white font-sans">{blameInfo.author || 'Dev'}</span>
                <span className="px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/30 text-[10px]">
                  {blameInfo.commit_hash}
                </span>
              </div>
              <span className="text-slate-400 italic text-[11px] truncate max-w-md">
                "{blameInfo.commit_message || 'Update code'}"
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
