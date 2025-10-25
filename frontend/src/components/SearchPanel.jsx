import React from 'react';
import { Search, MessageSquare } from 'lucide-react';

const SearchResultCard = ({ message }) => {
  return (
    <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-start gap-3">
        <MessageSquare size={20} className="text-purple-400 mt-1" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs px-2 py-1 rounded ${
              message.role === 'user' ? 'bg-blue-500/20 text-blue-300' : 'bg-purple-500/20 text-purple-300'
            }`}>
              {message.role}
            </span>
            {message.context && (
              <span className="text-xs text-slate-400">{message.context}</span>
            )}
          </div>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  );
};

const SearchPanel = ({ searchQuery, setSearchQuery, messages, onSearch }) => {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && onSearch()}
            placeholder="Search messages semantically..."
            className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            onClick={onSearch}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors flex items-center gap-2"
          >
            <Search size={20} />
            Search
          </button>
        </div>

        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <SearchResultCard key={idx} message={msg} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchPanel;