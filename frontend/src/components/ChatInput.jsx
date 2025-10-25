import React from 'react';
import { Send } from 'lucide-react';

const ChatInput = ({ 
  input, 
  setInput, 
  loading, 
  activeTab, 
  documents,
  onSend 
}) => {
  return (
    <div className="border-t border-slate-700/50 bg-slate-800/30 backdrop-blur-xl p-4">
      <div className="max-w-4xl mx-auto flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !loading && onSend()}
          placeholder={
            activeTab === 'rag' 
              ? 'Ask a question about your documents...'
              : 'Type your message...'
          }
          className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
          disabled={loading}
        />
        <button
          onClick={onSend}
          disabled={loading || !input.trim()}
          className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-xl transition-colors shadow-lg shadow-purple-500/50 disabled:shadow-none flex items-center gap-2"
        >
          <Send size={20} />
          Send
        </button>
      </div>
      {activeTab === 'rag' && documents.length === 0 && (
        <p className="text-center text-sm text-yellow-400 mt-2">
          ⚠️ No documents uploaded. Upload documents in the Documents tab for better RAG responses.
        </p>
      )}
    </div>
  );
};

export default ChatInput;