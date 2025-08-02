import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, Zap, Database, DollarSign, Activity, Server } from 'lucide-react';
import { ragService } from '../services/ragService';
import { SystemMetrics } from '../types';

export const MetricsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);

  useEffect(() => {
    const loadMetrics = () => {
      setMetrics(ragService.getMetrics());
    };

    loadMetrics();
    const interval = setInterval(loadMetrics, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const latencyData = [
    { name: 'P50', value: metrics.apiLatency.p50, target: 100 },
    { name: 'P95', value: metrics.apiLatency.p95, target: 150 },
    { name: 'P99', value: metrics.apiLatency.p99, target: 200 }
  ];

  const performanceData = [
    { name: 'Vector Search', latency: metrics.vectorSearchLatency, color: '#3B82F6' },
    { name: 'LLM Processing', latency: Math.random() * 80 + 40, color: '#10B981' },
    { name: 'Post Processing', latency: Math.random() * 20 + 10, color: '#F59E0B' }
  ];

  const throughputData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    requests: Math.floor(Math.random() * 50000 + 20000)
  }));

  const cacheData = [
    { name: 'Cache Hit', value: metrics.cacheHitRate * 100, color: '#10B981' },
    { name: 'Cache Miss', value: (1 - metrics.cacheHitRate) * 100, color: '#EF4444' }
  ];

  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ReactNode;
    trend?: 'up' | 'down' | 'stable';
    color: string;
  }> = ({ title, value, subtitle, icon, trend, color }) => (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${color.replace('text-', 'bg-').replace('-600', '-100')}`}>
          {icon}
        </div>
      </div>
      {trend && (
        <div className="mt-4 flex items-center">
          <TrendingUp className={`w-4 h-4 mr-1 ${
            trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-gray-500'
          }`} />
          <span className="text-sm text-gray-600">
            {trend === 'up' ? 'Improving' : trend === 'down' ? 'Declining' : 'Stable'}
          </span>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="API Latency (P99)"
          value={`${metrics.apiLatency.p99}ms`}
          subtitle="< 200ms SLA"
          icon={<Zap className="w-6 h-6" />}
          trend="up"
          color="text-blue-600"
        />
        <MetricCard
          title="Daily Throughput"
          value={`${(metrics.throughput / 1000000).toFixed(1)}M`}
          subtitle="API calls/day"
          icon={<Activity className="w-6 h-6" />}
          trend="up"
          color="text-green-600"
        />
        <MetricCard
          title="System Uptime"
          value={`${metrics.uptime}%`}
          subtitle="99.99% SLA"
          icon={<Server className="w-6 h-6" />}
          trend="stable"
          color="text-purple-600"
        />
        <MetricCard
          title="Cost Reduction"
          value={`${metrics.costReduction}%`}
          subtitle="via caching"
          icon={<DollarSign className="w-6 h-6" />}
          trend="up"
          color="text-orange-600"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latency Distribution */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">API Latency Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value) => [`${value}ms`, 'Latency']} />
              <Bar dataKey="value" fill="#3B82F6" />
              <Bar dataKey="target" fill="#E5E7EB" opacity={0.5} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Breakdown */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Performance Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={performanceData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={100} />
              <Tooltip formatter={(value) => [`${value}ms`, 'Latency']} />
              <Bar dataKey="latency" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Throughput Over Time */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">24-Hour Throughput</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={throughputData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip formatter={(value) => [`${value}`, 'Requests']} />
              <Line type="monotone" dataKey="requests" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cache Performance */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Cache Performance</h3>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={cacheData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={120}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {cacheData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value.toFixed(1)}%`, 'Percentage']} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center space-x-4 mt-4">
            {cacheData.map((entry, index) => (
              <div key={index} className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full`} style={{ backgroundColor: entry.color }}></div>
                <span className="text-sm text-gray-600">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">System Health Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Database className="w-8 h-8 text-green-600" />
            </div>
            <h4 className="font-medium text-gray-800">Vector Store</h4>
            <p className="text-sm text-green-600">Healthy</p>
            <p className="text-xs text-gray-500">FAISS index optimized</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Zap className="w-8 h-8 text-blue-600" />
            </div>
            <h4 className="font-medium text-gray-800">C++ Microservice</h4>
            <p className="text-sm text-blue-600">Optimal</p>
            <p className="text-xs text-gray-500">10K+ concurrent requests</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Activity className="w-8 h-8 text-purple-600" />
            </div>
            <h4 className="font-medium text-gray-800">LLM Pipeline</h4>
            <p className="text-sm text-purple-600">Active</p>
            <p className="text-xs text-gray-500">GPT-4 Turbo ready</p>
          </div>
        </div>
      </div>
    </div>
  );
};