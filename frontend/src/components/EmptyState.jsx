import React from 'react';
import { MessageSquare, Database } from 'lucide-react';

const EmptyState = ({ activeTab }) => {
  const content = {
    chat: {
      icon: MessageSquare,
      title: 'Start a conversation',
      subtitle: 'Chat with your LLM model'
    },
    rag: {
      icon: Database,
      title: 'Start a conversation',
      subtitle: 'Ask questions about your uploaded documents'
    }
  };

  const { icon: Icon, title, subtitle } = content[activeTab] || content.chat;

  return (
    <div className="text-center py-12 text-slate-400">
      <Icon size={48} className="mx-auto mb-4 opacity-50" />
      <p className="text-lg mb-2">{title}</p>
      <p className="text-sm">{subtitle}</p>
    </div>
  );
};

export default EmptyState;