import React from 'react';
import { X, Key, Cpu, Thermometer, Hash } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';

export default function SettingsPanel() {
  const { settingsOpen, toggleSettings, apiKey, setApiKey, username, setUsername, settings, updateSettings } = useAppStore();

  if (!settingsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/30" onClick={toggleSettings} />
      <div className="relative w-96 bg-white dark:bg-gray-900 shadow-2xl flex flex-col h-full z-10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Settings</h2>
          <button onClick={toggleSettings} className="btn-ghost p-1.5">
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* API Key */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Key size={14} />
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="input-field"
              placeholder="pageindex-secret-key"
            />
          </div>

          {/* Username */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Hash size={14} />
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field"
              placeholder="default"
            />
          </div>

          {/* LLM Provider */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Cpu size={14} />
              LLM Provider
            </label>
            <select
              value={settings.llmProvider}
              onChange={(e) => updateSettings({ llmProvider: e.target.value })}
              className="input-field"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai">OpenAI (GPT-4o)</option>
            </select>
          </div>

          {/* Temperature */}
          <div>
            <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <span className="flex items-center gap-2">
                <Thermometer size={14} />
                Temperature
              </span>
              <span className="text-brand-600 font-mono">{settings.temperature}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value) })}
              className="w-full accent-brand-600"
            />
          </div>

          {/* Max Tokens */}
          <div>
            <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <span>Max Tokens</span>
              <span className="text-brand-600 font-mono">{settings.maxTokens}</span>
            </label>
            <input
              type="range"
              min="512"
              max="8192"
              step="512"
              value={settings.maxTokens}
              onChange={(e) => updateSettings({ maxTokens: parseInt(e.target.value) })}
              className="w-full accent-brand-600"
            />
          </div>

          {/* Show RAG Panel */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Show RAG Explorer Panel
            </span>
            <button
              onClick={() => updateSettings({ showRAGPanel: !settings.showRAGPanel })}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                settings.showRAGPanel ? 'bg-brand-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <div
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                  settings.showRAGPanel ? 'translate-x-5' : ''
                }`}
              />
            </button>
          </div>

          {/* Quick Index */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Quick Index</span>
              <p className="text-xs text-gray-400">Skip LLM summaries during indexing (faster but less accurate)</p>
            </div>
            <button
              onClick={() => updateSettings({ quickIndex: !settings.quickIndex })}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                settings.quickIndex ? 'bg-brand-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <div
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                  settings.quickIndex ? 'translate-x-5' : ''
                }`}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
