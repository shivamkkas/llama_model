import React from 'react';

const Message = ({ message }) => {
  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          message.role === 'user'
            ? 'bg-purple-600 text-white'
            : 'bg-slate-800/50 backdrop-blur-xl border border-slate-700/50'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.context && (
          <p className="text-xs mt-2 opacity-70">{message.context}</p>
        )}
      </div>
    </div>
  );
};

export default Message;