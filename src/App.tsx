import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { Header } from './components/Header';
import { QueryInterface } from './components/QueryInterface';
import { DocumentManager } from './components/DocumentManager';
import { MetricsDashboard } from './components/MetricsDashboard';
import { ComplianceAudit } from './components/ComplianceAudit';
import { SystemStatus } from './components/SystemStatus';

function App() {
  const [activeTab, setActiveTab] = useState('query');

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'query':
        return <QueryInterface />;
      case 'documents':
        return <DocumentManager />;
      case 'metrics':
        return <MetricsDashboard />;
      case 'compliance':
        return <ComplianceAudit />;
      case 'system':
        return <SystemStatus />;
      default:
        return <QueryInterface />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="py-8">
        {renderActiveTab()}
      </main>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
    </div>
  );
}

export default App;