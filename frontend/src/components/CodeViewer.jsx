import React, { useRef } from 'react';
import Editor from '@monaco-editor/react';
import { FileCode, AlertOctagon, Copy, Check } from 'lucide-react';

export default function CodeViewer({ 
  code = '', 
  language = 'python', 
  errorLine = null,
  fileName = 'source.py',
  height = '360px' 
}) {
  const [copied, setCopied] = React.useState(false);
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;

    if (errorLine && errorLine > 0) {
      // Reveal line in center
      editor.revealLineInCenter(errorLine);

      // Add line highlight decoration
      editor.deltaDecorations([], [
        {
          range: new monaco.Range(errorLine, 1, errorLine, 1),
          options: {
            isWholeLine: true,
            className: 'bg-rose-500/20 border-l-4 border-rose-500',
            glyphMarginClassName: 'text-rose-400 font-bold',
            hoverMessage: { value: '**TraceBack Detection:** Crash frame exception triggered on this line.' }
          }
        }
      ]);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl overflow-hidden border border-white/10 bg-slate-950 shadow-xl flex flex-col">
      {/* Editor Top Bar */}
      <div className="px-4 py-2.5 bg-[#0b0f19] border-b border-white/10 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-blue-400" />
          <span className="font-mono text-slate-200 font-semibold">{fileName}</span>
          {errorLine && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/15 text-rose-300 border border-rose-500/30">
              <AlertOctagon className="w-3 h-3" />
              Line {errorLine}
            </span>
          )}
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-slate-400 hover:text-white rounded bg-slate-800/60 hover:bg-slate-800 transition-colors cursor-pointer"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Monaco Container */}
      <div style={{ height }}>
        <Editor
          height="100%"
          language={language}
          value={code}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            renderLineHighlight: 'all',
            padding: { top: 12, bottom: 12 },
            fontFamily: "'JetBrains Mono', Consolas, monospace",
          }}
          onMount={handleEditorDidMount}
        />
      </div>
    </div>
  );
}
