import React from 'react';
import { Upload, FileText, BookOpen, Trash2 } from 'lucide-react';

const DocumentCard = ({ document, onDelete }) => {
  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-4 border border-slate-700/50 flex items-start justify-between">
      <div className="flex items-start gap-3 flex-1">
        <BookOpen className="text-purple-400 mt-1" size={20} />
        <div className="flex-1 min-w-0">
          <h4 className="font-medium truncate">{document.filename}</h4>
          <div className="flex gap-3 text-sm text-slate-400 mt-1">
            <span>{(document.file_size / 1024).toFixed(1)} KB</span>
            <span>•</span>
            <span>{document.chunks} chunks</span>
            <span>•</span>
            <span>{new Date(document.upload_date).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
      <button
        onClick={() => onDelete(document.file_hash)}
        className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
      >
        <Trash2 size={18} />
      </button>
    </div>
  );
};

const DocumentsPanel = ({ documents, fileInputRef, onUpload, onDelete }) => {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors shadow-lg shadow-purple-500/50"
          >
            <Upload size={20} />
            Upload Documents
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.md,.json"
            onChange={onUpload}
            className="hidden"
          />
          <p className="text-sm text-slate-400 mt-2">
            Supported formats: .txt, .md, .json • Auto-chunked and vectorized
          </p>
        </div>

        <div className="space-y-3">
          {documents.map(doc => (
            <DocumentCard key={doc.file_hash} document={doc} onDelete={onDelete} />
          ))}
          {documents.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <FileText size={48} className="mx-auto mb-4 opacity-50" />
              <p>No documents uploaded yet</p>
              <p className="text-sm">Upload documents to enable RAG queries</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentsPanel;