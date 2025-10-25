import React from 'react';
import { Download, Trash2 } from 'lucide-react';

const Header = ({ activeTab, currentConversation, messages, onExport, onClear }) => {
  const titles = {
    chat: currentConversation?.title || 'New Chat',
    rag: 'RAG Query',
    documents: 'Document Management',
    search: 'Semantic Search'
  };

  const subtitles = {
    chat: 'Direct conversation with LLM',
    rag: 'Query with document context',
    documents: 'Manage your knowledge base',
    search: 'Search across all conversations'
  };

  return (
    <div className="bg-slate-800/30 backdrop-blur-xl border-b border-slate-700/50 px-6 py-4 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold">{titles[activeTab]}</h2>
        <p className="text-sm text-slate-400">{subtitles[activeTab]}</p>
      </div>
      <div className="flex gap-2">
        {(activeTab === 'chat' || activeTab === 'rag') && messages.length > 0 && (
          <>
            <button
              onClick={onExport}
              className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-600/50 transition-colors"
              title="Export chat"
            >
              <Download size={20} />
            </button>
            <button
              onClick={onClear}
              className="p-2 rounded-lg bg-slate-700/50 hover:bg-red-600/50 transition-colors"
              title="Clear view"
            >
              <Trash2 size={20} />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default Header;