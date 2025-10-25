import React from 'react';

const SettingsPanel = ({ 
  backendUrl, 
  setBackendUrl, 
  model, 
  setModel, 
  temperature, 
  setTemperature,
  topK,
  setTopK
}) => {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-slate-700/50">
          <h3 className="text-lg font-semibold mb-4">Backend Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Backend URL</label>
              <input
                type="text"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="http://localhost:8000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Model Name</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="llama3"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Temperature: {temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-slate-400 mt-1">
                Lower = focused, Higher = creative
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                RAG Top K: {topK}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-slate-400 mt-1">
                Number of document chunks to retrieve
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;