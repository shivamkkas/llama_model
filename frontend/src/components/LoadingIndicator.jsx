import React from 'react';

const LoadingIndicator = () => (
  <div className="flex justify-start">
    <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl px-4 py-3">
      <div className="flex gap-2">
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
    </div>
  </div>
);

export default LoadingIndicator;