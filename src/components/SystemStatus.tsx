import React, { useState, useEffect } from 'react';
import { Server, Database, Cpu, Network, HardDrive, Activity, AlertCircle, CheckCircle } from 'lucide-react';

interface SystemComponent {
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  uptime: number;
  latency?: number;
  throughput?: number;
  details: string;
  icon: React.ReactNode;
}

export const SystemStatus: React.FC = () => {
  const [components, setComponents] = useState<SystemComponent[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    const updateStatus = () => {
      const newComponents: SystemComponent[] = [
        {
          name: 'C++ Vector Search Microservice',
          status: 'healthy',
          uptime: 99.99,
          latency: Math.random() * 20 + 30,
          throughput: Math.floor(Math.random() * 5000 + 8000),
          details: 'Lock-free queues, epoll I/O multiplexing active',
          icon: <Cpu className="w-5 h-5" />
        },
        {
          name: 'FAISS Vector Store',
          status: 'healthy',
          uptime: 99.98,
          details: 'SIMD-optimized, NUMA-aware CPU pinning enabled',
          icon: <Database className="w-5 h-5" />
        },
        {
          name: 'Redis Cache Layer',
          status: 'healthy',
          uptime: 99.95,
          details: 'Semantic proximity heuristics, 30% cost reduction',
          icon: <HardDrive className="w-5 h-5" />
        },
        {
          name: 'LangChain RAG Pipeline',
          status: 'healthy',
          uptime: 99.97,
          latency: Math.random() * 50 + 80,
          details: 'GPT-4 Turbo integration, prompt compression active',
          icon: <Network className="w-5 h-5" />
        },
        {
          name: 'Azure Kubernetes Service',
          status: 'healthy',
          uptime: 99.99,
          details: 'Horizontal Pod Autoscaling, warm pools maintained',
          icon: <Server className="w-5 h-5" />
        },
        {
          name: 'Compliance & Audit System',
          status: 'healthy',
          uptime: 100.0,
          details: 'LIME/SHAP explainability, full audit trails',
          icon: <Activity className="w-5 h-5" />
        }
      ];

      // Randomly introduce some warnings for demo
      if (Math.random() < 0.1) {
        newComponents[Math.floor(Math.random() * newComponents.length)].status = 'warning';
      }

      setComponents(newComponents);
      setLastUpdate(new Date());
    };

    updateStatus();
    const interval = setInterval(updateStatus, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-600" />;
      case 'critical':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600" />;
    }
  };

  const overallStatus = components.every(c => c.status === 'healthy') ? 'healthy' : 
                      components.some(c => c.status === 'critical') ? 'critical' : 'warning';

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Overall System Status */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${getStatusColor(overallStatus)}`}>
              {getStatusIcon(overallStatus)}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">System Status</h2>
              <p className="text-gray-600">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(overallStatus)}`}>
              {overallStatus === 'healthy' ? 'All Systems Operational' : 
               overallStatus === 'warning' ? 'Minor Issues Detected' : 'Critical Issues'}
            </div>
          </div>
        </div>
      </div>

      {/* Architecture Overview */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Architecture Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 border-2 border-blue-200 rounded-lg bg-blue-50">
            <h4 className="font-medium text-blue-800">Frontend Layer</h4>
            <p className="text-sm text-blue-600 mt-1">React + TypeScript UI</p>
          </div>
          <div className="p-4 border-2 border-green-200 rounded-lg bg-green-50">
            <h4 className="font-medium text-green-800">API Gateway</h4>
            <p className="text-sm text-green-600 mt-1">Azure API Gateway + Rate Limiting</p>
          </div>
          <div className="p-4 border-2 border-purple-200 rounded-lg bg-purple-50">
            <h4 className="font-medium text-purple-800">RAG Orchestration</h4>
            <p className="text-sm text-purple-600 mt-1">LangChain + GPT-4 Turbo</p>
          </div>
          <div className="p-4 border-2 border-orange-200 rounded-lg bg-orange-50">
            <h4 className="font-medium text-orange-800">Vector Search</h4>
            <p className="text-sm text-orange-600 mt-1">C++ Microservice + FAISS</p>
          </div>
          <div className="p-4 border-2 border-red-200 rounded-lg bg-red-50">
            <h4 className="font-medium text-red-800">Caching Layer</h4>
            <p className="text-sm text-red-600 mt-1">Redis + Semantic Heuristics</p>
          </div>
          <div className="p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
            <h4 className="font-medium text-gray-800">Infrastructure</h4>
            <p className="text-sm text-gray-600 mt-1">Azure Kubernetes Service</p>
          </div>
        </div>
      </div>

      {/* Component Status */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Component Status</h3>
        <div className="space-y-4">
          {components.map((component, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${getStatusColor(component.status)}`}>
                    {component.icon}
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-800">{component.name}</h4>
                    <p className="text-sm text-gray-600">{component.details}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center space-x-2 mb-1">
                    {getStatusIcon(component.status)}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(component.status)}`}>
                      {component.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    Uptime: {component.uptime}%
                  </div>
                </div>
              </div>
              
              {(component.latency || component.throughput) && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {component.latency && (
                      <div>
                        <span className="text-gray-600">Latency:</span>
                        <span className="ml-2 font-medium text-gray-800">{component.latency.toFixed(1)}ms</span>
                      </div>
                    )}
                    {component.throughput && (
                      <div>
                        <span className="text-gray-600">Throughput:</span>
                        <span className="ml-2 font-medium text-gray-800">{component.throughput.toLocaleString()} req/s</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Performance SLAs */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Performance SLAs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-green-600">&lt;200ms</div>
            <div className="text-sm text-gray-600">API Latency (P99)</div>
            <div className="text-xs text-green-600 mt-1">✓ Meeting SLA</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-green-600">&lt;50ms</div>
            <div className="text-sm text-gray-600">Vector Search</div>
            <div className="text-xs text-green-600 mt-1">✓ Meeting SLA</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-green-600">1M+</div>
            <div className="text-sm text-gray-600">Daily API Calls</div>
            <div className="text-xs text-green-600 mt-1">✓ Meeting SLA</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-green-600">99.99%</div>
            <div className="text-sm text-gray-600">Uptime</div>
            <div className="text-xs text-green-600 mt-1">✓ Meeting SLA</div>
          </div>
        </div>
      </div>
    </div>
  );
};