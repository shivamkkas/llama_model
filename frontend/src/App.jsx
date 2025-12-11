import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Upload, FileText, Trash2, MessageSquare, Plus, Database, X, Menu, Loader2, Check, AlertCircle, Sparkles, Server, Activity, Settings, Search, Download, ExternalLink } from 'lucide-react';

const API_BASE = 'http://192.168.1.17:8010';

export default function MCPOllamaUI() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadStatus, setUploadStatus] = useState({ show: false, message: '', type: 'info' });
  const [healthStatus, setHealthStatus] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [userId] = useState('user-' + Math.random().toString(36).substr(2, 9));
  const [model, setModel] = useState('llama3');
  const [models, setModels] = useState(['llama3', 'llama2', 'mistral', 'codellama']);
  const [useRAG, setUseRAG] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const initializeApp = async () => {
      await Promise.all([
        checkHealth(),
        loadConversations(),
        loadDocuments()
      ]);
    };
    initializeApp();
  }, []);

  useEffect(() => {
    inputRef.current?.focus();
  }, [currentConversation]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setHealthStatus(data);
    } catch (error) {
      console.error('Health check failed:', error);
      showToast('Unable to connect to server', 'error');
    }
  };

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations/list?user_id=${userId}`);
      const data = await res.json();
      if (data.status === 'success') {
        setConversations(data.conversations || []);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents/list?user_id=${userId}`);
      const data = await res.json();
      if (data.status === 'success') {
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadConversation = useCallback(async (convId) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${convId}`);
      const data = await res.json();
      if (data.status === 'success') {
        setCurrentConversation({ id: convId, ...data.history });
        setMessages(data.history.messages || []);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }, []);

  const createNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
    setInput('');
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          conversation_id: currentConversation?.id,
          user_id: userId,
          context: {}
        })
      });

      const data = await res.json();
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        sources: data.sources_used || [],
        metadata: data.metadata || {}
      }]);

      if (data.conversation_id && !currentConversation) {
        setCurrentConversation({ id: data.conversation_id });
      }

      loadConversations();
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: Failed to get response from server.',
        error: true
      }]);
      showToast('Failed to send message', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'info') => {
    setUploadStatus({ show: true, message, type });
    setTimeout(() => setUploadStatus({ show: false, message: '', type: 'info' }), 3000);
  };

  const uploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    formData.append('filename', file.name);
    
    showToast('Uploading document...', 'info');
    
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target.result;
        
        const res = await fetch(`${API_BASE}/documents/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_content: content,
            filename: file.name,
            user_id: userId,
            metadata: {
              size: file.size,
              type: file.type,
              uploaded_at: new Date().toISOString()
            }
          })
        });
        
        const data = await res.json();
        if (data.status === 'success') {
          showToast('Document uploaded successfully!', 'success');
          loadDocuments();
        } else {
          showToast(`Error: ${data.detail || 'Upload failed'}`, 'error');
        }
      };
      reader.readAsText(file);
    } catch (error) {
      console.error('Upload failed:', error);
      showToast('Upload failed', 'error');
    }
  };

  const searchDocuments = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      const res = await fetch(`${API_BASE}/documents/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          user_id: userId,
          top_k: 5
        })
      });
      
      const data = await res.json();
      if (data.status === 'success') {
        setSearchResults(data.results || []);
        showToast(`Found ${data.results?.length || 0} results`, 'success');
      }
    } catch (error) {
      console.error('Search failed:', error);
      showToast('Search failed', 'error');
    }
  };

  const deleteDocument = async (docId) => {
    if (!confirm('Delete this document? This cannot be undone.')) return;
    
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        showToast('Document deleted', 'success');
        loadDocuments();
      }
    } catch (error) {
      console.error('Failed to delete document:', error);
      showToast('Failed to delete document', 'error');
    }
  };

  const deleteConversation = async (convId) => {
    if (!confirm('Delete this conversation?')) return;
    
    try {
      const res = await fetch(`${API_BASE}/conversations/${convId}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        if (currentConversation?.id === convId) {
          setCurrentConversation(null);
          setMessages([]);
        }
        showToast('Conversation deleted', 'success');
        loadConversations();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      showToast('Failed to delete conversation', 'error');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const HealthIndicator = ({ status }) => {
    if (!status) return null;
    
    return (
      <div className="grid grid-cols-3 gap-2 p-3 bg-gray-700/30 rounded-xl">
        <div className="text-center">
          <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${status.ollama_connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <div className="text-xs text-gray-400">Ollama</div>
        </div>
        <div className="text-center">
          <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${status.databases_connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <div className="text-xs text-gray-400">Database</div>
        </div>
        <div className="text-center">
          <div className={`w-2 h-2 rounded-full mx-auto mb-1 ${status.chroma_connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <div className="text-xs text-gray-400">Vector DB</div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 text-gray-100">
      {uploadStatus.show && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top">
          <div className={`px-6 py-3 rounded-xl shadow-2xl flex items-center gap-3 ${
            uploadStatus.type === 'success' ? 'bg-green-600' :
            uploadStatus.type === 'error' ? 'bg-red-600' :
            'bg-blue-600'
          }`}>
            {uploadStatus.type === 'success' && <Check className="w-5 h-5" />}
            {uploadStatus.type === 'error' && <AlertCircle className="w-5 h-5" />}
            {uploadStatus.type === 'info' && <Loader2 className="w-5 h-5 animate-spin" />}
            <span className="font-medium">{uploadStatus.message}</span>
          </div>
        </div>
      )}

      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 bg-gray-800/50 backdrop-blur-xl border-r border-gray-700/50 flex flex-col overflow-hidden`}>
        <div className="p-6 border-b border-gray-700/50">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2 rounded-xl">
                <Database className="w-6 h-6" />
              </div>
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                MCP Ollama
              </span>
            </h1>
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden hover:bg-gray-700 p-2 rounded-lg transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <HealthIndicator status={healthStatus} />
        </div>

        <div className="flex p-2 gap-2">
          {['chat', 'documents', 'search'].map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`flex-1 px-3 py-2 text-xs font-medium rounded-xl transition-all ${
                view === v
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
              }`}
            >
              {v === 'chat' && <MessageSquare className="w-3 h-3 inline mr-1" />}
              {v === 'documents' && <FileText className="w-3 h-3 inline mr-1" />}
              {v === 'search' && <Search className="w-3 h-3 inline mr-1" />}
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>

        {view === 'chat' && (
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <button
                onClick={createNewConversation}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg"
              >
                <Plus className="w-5 h-5" />
                New Chat
              </button>
            </div>

            <div className="px-4 space-y-2">
              {conversations.length === 0 ? (
                <div className="text-center text-gray-500 py-8 text-sm">
                  No conversations yet
                </div>
              ) : (
                conversations.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left px-4 py-3 rounded-xl transition-all group ${
                      currentConversation?.id === conv.id
                        ? 'bg-gray-700/50 shadow-lg'
                        : 'hover:bg-gray-700/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate font-medium">{conv.title || 'Conversation'}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConversation(conv.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {view === 'documents' && (
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 text-white px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg"
              >
                <Upload className="w-5 h-5" />
                Upload Document
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="*/*"
                onChange={(e) => e.target.files?.[0] && uploadDocument(e.target.files[0])}
                className="hidden"
              />
            </div>

            <div className="px-4 space-y-3">
              {documents.length === 0 ? (
                <div className="text-center text-gray-500 py-8 text-sm">
                  No documents uploaded
                </div>
              ) : (
                documents.map(doc => (
                  <div
                    key={doc.id}
                    className="bg-gray-700/30 hover:bg-gray-700/50 p-4 rounded-xl transition-all border border-gray-700/50 group"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-4 h-4 text-green-400 flex-shrink-0" />
                          <div className="font-medium truncate text-sm">{doc.filename}</div>
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(doc.uploaded_at).toLocaleDateString()}
                        </div>
                      </div>
                      <button
                        onClick={() => deleteDocument(doc.id)}
                        className="ml-2 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {view === 'search' && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchDocuments()}
                  placeholder="Search documents..."
                  className="flex-1 bg-gray-700/50 border border-gray-600/50 rounded-xl px-4 py-2 text-sm"
                />
                <button
                  onClick={searchDocuments}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all"
                >
                  <Search className="w-4 h-4" />
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-2">
                  {searchResults.map((result, idx) => (
                    <div key={idx} className="bg-gray-700/30 p-3 rounded-xl border border-gray-700/50">
                      <div className="text-sm font-medium mb-1">{result.filename}</div>
                      <div className="text-xs text-gray-400">{result.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-4 border-t border-gray-700/50 bg-gray-800/30">
          <div className="text-xs text-center text-gray-500">
            User: {userId.slice(0, 8)}...
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="bg-gray-800/50 backdrop-blur-xl border-b border-gray-700/50 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4 min-w-0">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="hover:bg-gray-700 p-2 rounded-lg transition-colors"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <h2 className="font-semibold truncate">
              {currentConversation?.id ? `Conversation ${currentConversation.id.slice(0, 8)}...` : 'New Conversation'}
            </h2>
          </div>

          <button
            onClick={checkHealth}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-all text-sm"
          >
            <Activity className="w-4 h-4" />
            Status
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 px-4">
              <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 p-8 rounded-3xl mb-6">
                <Sparkles className="w-20 h-20 text-blue-400" strokeWidth={1.5} />
              </div>
              <h3 className="text-2xl font-semibold text-gray-300 mb-2">Start a Conversation</h3>
              <p className="text-gray-500 text-center max-w-md">
                Ask anything or upload documents for RAG-powered responses
              </p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl px-6 py-4 rounded-2xl shadow-lg ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white'
                        : msg.error
                        ? 'bg-red-600/20 text-red-300 border border-red-600/30'
                        : 'bg-gray-700/50 text-gray-100 border border-gray-600/30'
                    }`}
                  >
                    <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="text-xs mt-3 pt-3 border-t border-white/10 flex items-center gap-2">
                        <FileText className="w-3 h-3" />
                        {msg.sources.length} source(s) used
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-700/50 px-6 py-4 rounded-2xl border border-gray-600/30">
                    <div className="flex gap-2 items-center">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                      <span className="text-sm text-gray-400">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-gray-700/50 p-6 bg-gray-800/30 backdrop-blur-xl">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type a message..."
                className="flex-1 bg-gray-700/50 border border-gray-600/50 rounded-2xl px-6 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 disabled:from-gray-600 disabled:to-gray-600 text-white px-8 py-4 rounded-2xl transition-all disabled:cursor-not-allowed shadow-lg"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}