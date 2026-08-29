import React, { useState } from 'react';
import { 
  Folder, 
  FolderOpen, 
  FileCode, 
  FileText, 
  ChevronRight, 
  ChevronDown,
  File
} from 'lucide-react';

function TreeNode({ node, selectedFile, onSelectFile, depth = 0 }) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const isDir = node.type === 'directory';
  const isSelected = selectedFile === node.path;

  const handleClick = () => {
    if (isDir) {
      setIsOpen(!isOpen);
    } else {
      onSelectFile(node.path);
    }
  };

  return (
    <div className="select-none">
      <div
        onClick={handleClick}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        className={`flex items-center gap-2 py-1.5 px-2 rounded-lg text-xs font-mono cursor-pointer transition-colors ${
          isSelected
            ? 'bg-blue-600/20 text-blue-400 font-semibold border border-blue-500/30'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
        }`}
      >
        {isDir ? (
          <>
            {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
            {isOpen ? <FolderOpen className="w-3.5 h-3.5 text-indigo-400" /> : <Folder className="w-3.5 h-3.5 text-indigo-400" />}
          </>
        ) : (
          <>
            <span className="w-3.5" />
            <FileCode className="w-3.5 h-3.5 text-blue-400" />
          </>
        )}
        <span className="truncate">{node.name}</span>
      </div>

      {isDir && isOpen && node.children && (
        <div>
          {node.children.map((child, idx) => (
            <TreeNode
              key={idx}
              node={child}
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({ tree = [], selectedFile, onSelectFile }) {
  return (
    <div className="space-y-0.5 overflow-y-auto max-h-[600px] pr-1">
      {tree.map((node, idx) => (
        <TreeNode
          key={idx}
          node={node}
          selectedFile={selectedFile}
          onSelectFile={onSelectFile}
          depth={0}
        />
      ))}
    </div>
  );
}
