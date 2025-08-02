import React, { useState, useEffect } from 'react';
import { Shield, FileText, AlertTriangle, CheckCircle, Eye, Download, Filter } from 'lucide-react';
import { ragService } from '../services/ragService';
import { AuditLog } from '../types';

export const ComplianceAudit: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [filter, setFilter] = useState<'all' | 'compliant' | 'flagged' | 'blocked'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const logs = ragService.getAuditLogs();
    setAuditLogs(logs);
  }, []);

  const filteredLogs = auditLogs.filter(log => {
    const matchesFilter = filter === 'all' || log.complianceStatus === filter;
    const matchesSearch = searchTerm === '' || 
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.userId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.details.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesFilter && matchesSearch;
  });

  const complianceStats = {
    total: auditLogs.length,
    compliant: auditLogs.filter(log => log.complianceStatus === 'compliant').length,
    flagged: auditLogs.filter(log => log.complianceStatus === 'flagged').length,
    blocked: auditLogs.filter(log => log.complianceStatus === 'blocked').length
  };

  const StatCard: React.FC<{
    title: string;
    value: number;
    total: number;
    color: string;
    icon: React.ReactNode;
  }> = ({ title, value, total, color, icon }) => (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          <p className="text-sm text-gray-500">
            {total > 0 ? ((value / total) * 100).toFixed(1) : 0}% of total
          </p>
        </div>
        <div className={`p-3 rounded-lg ${color.replace('text-', 'bg-').replace('-600', '-100')}`}>
          {icon}
        </div>
      </div>
    </div>
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'compliant':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'flagged':
        return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
      case 'blocked':
        return <Shield className="w-4 h-4 text-red-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant':
        return 'bg-green-100 text-green-800';
      case 'flagged':
        return 'bg-yellow-100 text-yellow-800';
      case 'blocked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Compliance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="Total Queries"
          value={complianceStats.total}
          total={complianceStats.total}
          color="text-blue-600"
          icon={<FileText className="w-6 h-6" />}
        />
        <StatCard
          title="Compliant"
          value={complianceStats.compliant}
          total={complianceStats.total}
          color="text-green-600"
          icon={<CheckCircle className="w-6 h-6" />}
        />
        <StatCard
          title="Flagged"
          value={complianceStats.flagged}
          total={complianceStats.total}
          color="text-yellow-600"
          icon={<AlertTriangle className="w-6 h-6" />}
        />
        <StatCard
          title="Blocked"
          value={complianceStats.blocked}
          total={complianceStats.total}
          color="text-red-600"
          icon={<Shield className="w-6 h-6" />}
        />
      </div>

      {/* Compliance Features */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Responsible AI Features</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <Shield className="w-8 h-8 text-blue-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-800">Data Privacy</h4>
            <p className="text-sm text-gray-600 mt-1">
              Automatic PII redaction and sanitization before LLM processing
            </p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <Eye className="w-8 h-8 text-green-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-800">Explainability</h4>
            <p className="text-sm text-gray-600 mt-1">
              LIME/SHAP integration for transparent AI decision making
            </p>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <FileText className="w-8 h-8 text-purple-600 mx-auto mb-2" />
            <h4 className="font-medium text-gray-800">Auditability</h4>
            <p className="text-sm text-gray-600 mt-1">
              Complete audit trails linking responses to source documents
            </p>
          </div>
        </div>
      </div>

      {/* Audit Log Filters */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800">Audit Logs</h3>
          <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            <Download className="w-4 h-4" />
            <span>Export Logs</span>
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="compliant">Compliant</option>
              <option value="flagged">Flagged</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-600">Timestamp</th>
                <th className="text-left py-3 px-4 font-medium text-gray-600">User</th>
                <th className="text-left py-3 px-4 font-medium text-gray-600">Action</th>
                <th className="text-left py-3 px-4 font-medium text-gray-600">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-600">Details</th>
                <th className="text-left py-3 px-4 font-medium text-gray-600">Data Accessed</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-800">{log.userId}</td>
                  <td className="py-3 px-4 text-sm text-gray-800">{log.action}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(log.complianceStatus)}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(log.complianceStatus)}`}>
                        {log.complianceStatus}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600 max-w-xs truncate">
                    {log.details}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {log.dataAccessed.length} documents
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredLogs.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No audit logs match the current filters.
          </div>
        )}
      </div>

      {/* Compliance Metrics */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Compliance Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-green-600">0</div>
            <div className="text-sm text-gray-600">Data Privacy Leaks</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">100%</div>
            <div className="text-sm text-gray-600">Audit Coverage</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">
              {complianceStats.total > 0 ? ((complianceStats.compliant / complianceStats.total) * 100).toFixed(1) : 0}%
            </div>
            <div className="text-sm text-gray-600">Compliance Rate</div>
          </div>
          <div className="text-center p-4 border border-gray-200 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">&lt;1s</div>
            <div className="text-sm text-gray-600">Explanation Generation</div>
          </div>
        </div>
      </div>
    </div>
  );
};