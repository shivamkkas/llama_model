import React, { useState, useEffect, useRef } from 'react';
import { Send, Upload, FileText, Trash2, MessageSquare, Plus, Settings, Database, Search, X, Menu, ChevronLeft, ChevronRight } from 'lucide-react';

const API_BASE = 'http://192.168.1.17:8000';

export default function OllamaRAGUI() {
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('chat');
  const [model, setModel] = useState('llama3');
  const [models, setModels] = useState([]);
  const [useRAG, setUseRAG] = useState(false);
  const [stats, setStats] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadConversations();
    loadDocuments();
    loadStats();
    checkHealth();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/conversations`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadConversation = async (convId) => {
    try {
      const res = await fetch(`${API_BASE}/api/conversations/${convId}`);
      const data = await res.json();
      setCurrentConversation(data);
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat', model })
      });
      const data = await res.json();
      setCurrentConversation(data);
      setMessages([]);
      loadConversations();
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      let conversationId = currentConversation?.id;

      if (useRAG) {
        const res = await fetch(`${API_BASE}/api/rag/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: input,
            model,
            conversation_id: conversationId
          })
        });
        const data = await res.json();
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          sources: data.num_sources
        }]);
        
        if (data.conversation_id) {
          conversationId = data.conversation_id;
        }
      } else {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [...messages, userMessage],
            model,
            conversation_id: conversationId
          })
        });
        const data = await res.json();
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message.content
        }]);
        
        conversationId = data.conversation_id;
      }

      if (conversationId && !currentConversation) {
        loadConversation(conversationId);
      }
      
      loadConversations();
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: Failed to get response from server.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const uploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    setUploadProgress('Uploading...');
    
    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        setUploadProgress('Upload successful!');
        loadDocuments();
        loadStats();
        setTimeout(() => setUploadProgress(null), 2000);
      } else {
        const error = await res.json();
        setUploadProgress(`Error: ${error.detail}`);
        setTimeout(() => setUploadProgress(null), 3000);
      }
    } catch (error) {
      setUploadProgress('Upload failed');
      setTimeout(() => setUploadProgress(null), 3000);
    }
  };

  const deleteDocument = async (fileHash) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await fetch(`${API_BASE}/api/documents/${fileHash}`, {
        method: 'DELETE'
      });
      loadDocuments();
      loadStats();
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  const deleteConversation = async (convId) => {
    if (!confirm('Delete this conversation?')) return;
    
    try {
      await fetch(`${API_BASE}/api/conversations/${convId}`, {
        method: 'DELETE'
      });
      
      if (currentConversation?.id === convId) {
        setCurrentConversation(null);
        setMessages([]);
      }
      
      loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 bg-gray-800 border-r border-gray-700 flex flex-col overflow-hidden`}>
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Database className="w-5 h-5" />
            Ollama RAG
          </h1>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Tabs */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setView('chat')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${view === 'chat' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            <MessageSquare className="w-4 h-4 inline mr-2" />
            Chats
          </button>
          <button
            onClick={() => setView('documents')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${view === 'documents' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'}`}
          >
            <FileText className="w-4 h-4 inline mr-2" />
            Docs
          </button>
        </div>

        {/* Chat View */}
        {view === 'chat' && (
          <div className="flex-1 overflow-y-auto">
            <div className="p-3">
              <button
                onClick={createNewConversation}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Chat
              </button>
            </div>

            <div className="px-3 space-y-1">
              {conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors group ${currentConversation?.id === conv.id ? 'bg-gray-700' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm">{conv.title}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {conv.message_count} messages
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Documents View */}
        {view === 'documents' && (
          <div className="flex-1 overflow-y-auto">
            <div className="p-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Upload className="w-4 h-4" />
                Upload Document
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md"
                onChange={(e) => e.target.files?.[0] && uploadDocument(e.target.files[0])}
                className="hidden"
              />
              {uploadProgress && (
                <div className="mt-2 text-xs text-center text-gray-400">
                  {uploadProgress}
                </div>
              )}
            </div>

            <div className="px-3 space-y-2">
              {documents.map(doc => (
                <div
                  key={doc.file_hash}
                  className="bg-gray-700 p-3 rounded-lg"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{doc.filename}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        {doc.chunks} chunks • {(doc.file_size / 1024).toFixed(1)}KB
                      </div>
                    </div>
                    <button
                      onClick={() => deleteDocument(doc.file_hash)}
                      className="ml-2 text-gray-400 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats Footer */}
        {stats && (
          <div className="p-4 border-t border-gray-700 text-xs text-gray-400">
            <div className="space-y-1">
              <div>Conversations: {stats.total_conversations}</div>
              <div>Documents: {stats.unique_documents}</div>
              <div>Messages: {stats.total_messages}</div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)}>
                <Menu className="w-5 h-5" />
              </button>
            )}
            <h2 className="font-semibold">
              {currentConversation?.title || 'Select or create a conversation'}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useRAG}
                onChange={(e) => setUseRAG(e.target.checked)}
                className="rounded"
              />
              <span>RAG Mode</span>
            </label>

            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1 text-sm"
            >
              {models.map(m => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
              <option value="llama3">llama3</option>
            </select>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No messages yet</p>
              <p className="text-sm mt-2">Start a conversation or ask a question</p>
              {useRAG && documents.length === 0 && (
                <p className="text-sm mt-4 text-yellow-500">
                  Upload documents to use RAG mode
                </p>
              )}
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3xl px-4 py-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-100'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.sources > 0 && (
                    <div className="text-xs mt-2 opacity-75">
                      📚 {msg.sources} sources used
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-700 px-4 py-3 rounded-lg">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-700 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder={useRAG ? "Ask a question about your documents..." : "Type a message..."}
                className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-3 rounded-lg transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}