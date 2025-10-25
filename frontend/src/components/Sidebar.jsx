import React from 'react';
import { MessageSquare, Database, FileText, Search, Settings } from 'lucide-react';

const ConversationItem = ({ 
  conversation, 
  isActive, 
  isEditing, 
  editTitle,
  onLoad, 
  onEdit, 
  onDelete,
  setEditingConvId,
  setEditTitle
}) => {
  return (
    <div
      className={`group relative rounded-lg p-3 transition-all cursor-pointer ${
        isActive
          ? 'bg-purple-600/20 border border-purple-500/50'
          : 'hover:bg-slate-700/30'
      }`}
    >
      {isEditing ? (
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onBlur={() => onEdit(conversation.id, editTitle)}
          onKeyPress={(e) => e.key === 'Enter' && onEdit(conversation.id, editTitle)}
          className="w-full bg-slate-900/50 border border-slate-600 rounded px-2 py-1 text-sm"
          autoFocus
        />
      ) : (
        <div onClick={() => onLoad(conversation.id)}>
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium truncate flex-1">{conversation.title}</p>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
            <span>{new Date(conversation.updated_at).toLocaleDateString()}</span>
            <span>•</span>
            <span>{conversation.message_count} msgs</span>
          </div>
        </div>
      )}
    </div>
  );
};

const NavButton = ({ icon: Icon, label, active, onClick, badge }) => {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
        active 
          ? 'bg-purple-600 text-white' 
          : 'text-slate-300 hover:bg-slate-700/50'
      }`}
    >
      <Icon size={18} />
      <span className="text-sm">{label}</span>
      {badge > 0 && (
        <span className="ml-auto bg-purple-500 text-xs px-2 py-0.5 rounded-full">
          {badge}
        </span>
      )}
    </button>
  );
};

const StatRow = ({ label, value }) => (
  <div className="flex justify-between">
    <span>{label}:</span>
    <span className="text-white">{value}</span>
  </div>
);

const Sidebar = ({ 
  conversations, 
  currentConversation, 
  documents, 
  stats, 
  activeTab,
  editingConvId,
  editTitle,
  onNewConversation,
  onLoadConversation,
  onEditConversation,
  onDeleteConversation,
  onTabChange,
  onToggleSettings,
  showSettings,
  setEditingConvId,
  setEditTitle
}) => {
  return (
    <div className="w-72 bg-slate-800/50 backdrop-blur-xl border-r border-slate-700/50 flex flex-col">
      <div className="p-4 border-b border-slate-700/50">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Ollama RAG UI
        </h1>
        <p className="text-sm text-slate-400 mt-1">Vector-powered chat</p>
      </div>

      <div className="p-4">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors shadow-lg shadow-purple-500/50"
        >
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 space-y-2">
        <h3 className="text-xs uppercase text-slate-500 font-semibold mb-2">Recent Conversations</h3>
        {conversations.map(conv => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={currentConversation?.id === conv.id}
            isEditing={editingConvId === conv.id}
            editTitle={editTitle}
            onLoad={onLoadConversation}
            onEdit={onEditConversation}
            onDelete={onDeleteConversation}
            setEditingConvId={setEditingConvId}
            setEditTitle={setEditTitle}
          />
        ))}
      </div>

      <nav className="p-4 space-y-2 border-t border-slate-700/50">
        <NavButton
          icon={MessageSquare}
          label="Chat"
          active={activeTab === 'chat'}
          onClick={() => onTabChange('chat')}
        />
        <NavButton
          icon={Database}
          label="RAG Query"
          active={activeTab === 'rag'}
          onClick={() => onTabChange('rag')}
        />
        <NavButton
          icon={FileText}
          label="Documents"
          active={activeTab === 'documents'}
          onClick={() => onTabChange('documents')}
          badge={documents.length}
        />
        <NavButton
          icon={Search}
          label="Search"
          active={activeTab === 'search'}
          onClick={() => onTabChange('search')}
        />
        <NavButton
          icon={Settings}
          label="Settings"
          active={showSettings}
          onClick={onToggleSettings}
        />
      </nav>

      {stats && (
        <div className="p-4 border-t border-slate-700/50 text-xs text-slate-400 space-y-1">
          <StatRow label="Documents" value={stats.unique_documents} />
          <StatRow label="Chunks" value={stats.total_document_chunks} />
          <StatRow label="Messages" value={stats.total_messages} />
        </div>
      )}
    </div>
  );
};

export default Sidebar;