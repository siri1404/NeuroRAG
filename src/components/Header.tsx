import React from 'react';
import { Brain, Shield, Zap, BarChart3, FileText } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'query', label: 'Query Interface', icon: Brain },
    { id: 'documents', label: 'Document Manager', icon: FileText },
    { id: 'metrics', label: 'Performance Metrics', icon: BarChart3 },
    { id: 'compliance', label: 'Compliance & Audit', icon: Shield },
    { id: 'system', label: 'System Status', icon: Zap }
  ];

  return (
    <header className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-900 text-white shadow-2xl">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Brain className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">NeuroRAG</h1>
              <p className="text-blue-200 text-sm">Document Analysis System</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 text-sm">
            <div className="flex items-center space-x-1 bg-green-600 px-3 py-1 rounded-full">
              <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></div>
              <span>Online</span>
            </div>
          </div>
        </div>
        
        <nav className="mt-6">
          <div className="flex space-x-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white shadow-lg'
                      : 'text-blue-200 hover:bg-blue-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      </div>
    </header>
  );
};