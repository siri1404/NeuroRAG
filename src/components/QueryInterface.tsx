import React, { useState } from 'react';
import { Search, Send, Clock, FileText, AlertCircle, CheckCircle, Lightbulb } from 'lucide-react';
import { ragService } from '../services/ragService';
import { vectorStore } from '../services/vectorStore';
import { RAGResponse } from '../types';
import toast from 'react-hot-toast';

export const QueryInterface: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [includeExplanation, setIncludeExplanation] = useState(true);
  const [documentsCount, setDocumentsCount] = useState(0);

  React.useEffect(() => {
    setDocumentsCount(vectorStore.getDocuments().length);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const result = await ragService.processQuery({
        query: query.trim(),
        maxResults: 5,
        threshold: 0.7,
        includeExplanation
      });
      setResponse(result);
      toast.success(`Query processed in ${result.metadata.latency}ms`);
    } catch (error) {
      toast.error('Failed to process query');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const sampleQueries = [
    "What information do you have about financial performance?",
    "Can you summarize the key points from the documents?",
    "What are the main topics covered in the uploaded documents?",
    "Please analyze the content and provide insights."
  ];

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Query Input */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center space-x-3 mb-4">
          <Search className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold text-gray-800">Query Interface</h2>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={documentsCount > 0 ? "Ask questions about your uploaded documents..." : "Please upload documents first to start querying..."}
              className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none h-24"
              disabled={loading || documentsCount === 0}
            />
            <button
              type="submit"
              disabled={loading || !query.trim() || documentsCount === 0}
              className="absolute bottom-3 right-3 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          <div className="flex items-center justify-between">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={includeExplanation}
                onChange={(e) => setIncludeExplanation(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                disabled={documentsCount === 0}
              />
              <span className="text-sm text-gray-600">Include AI explanation</span>
            </label>
            
            <div className="text-sm text-gray-500">
              {documentsCount > 0 ? `${documentsCount} documents indexed` : 'No documents uploaded'}
            </div>
          </div>
        </form>

        {/* Document Upload Status */}
        {documentsCount === 0 && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-800">No Documents</span>
            </div>
            <p className="text-sm text-yellow-700 mt-1">
              Upload documents to start querying.
            </p>
          </div>
        )}
        {documentsCount > 0 && (
          <div className="mt-6">
          <p className="text-sm text-gray-600 mb-3">Sample queries:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {sampleQueries.map((sample, index) => (
              <button
                key={index}
                onClick={() => setQuery(sample)}
                className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors"
                disabled={documentsCount === 0}
              >
                "{sample}"
              </button>
            ))}
          </div>
          </div>
        )}
      </div>

      {/* Response Display */}
      {response && (
        <div className="space-y-6">
          {/* Main Answer */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">AI Response</h3>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{response.metadata.latency}ms</span>
                </div>
                <div className="flex items-center space-x-1">
                  <FileText className="w-4 h-4" />
                  <span>{response.metadata.tokensUsed} tokens</span>
                </div>
              </div>
            </div>
            
            <div className="prose max-w-none">
              <p className="text-gray-700 leading-relaxed">{response.answer}</p>
            </div>

            {/* Compliance Flags */}
            {response.metadata.complianceFlags.length > 0 && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-yellow-600" />
                  <span className="text-sm font-medium text-yellow-800">Flags:</span>
                </div>
                <div className="mt-1 text-sm text-yellow-700">
                  {response.metadata.complianceFlags.join(', ')}
                </div>
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Sources</h3>
            <div className="space-y-4">
              {response.retrievedDocuments.map((doc, index) => (
                <div key={doc.document.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-800">{doc.document.title}</h4>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">
                        Score: {(doc.score * 100).toFixed(1)}%
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        doc.document.metadata.classification === 'public' 
                          ? 'bg-green-100 text-green-800'
                          : doc.document.metadata.classification === 'confidential'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {doc.document.metadata.classification}
                      </span>
                    </div>
                  </div>
                  <p className="text-gray-600 text-sm mb-2">{doc.document.content}</p>
                  <p className="text-xs text-gray-500">{doc.relevanceReason}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {doc.document.metadata.tags.map(tag => (
                      <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {response.explanation && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Lightbulb className="w-5 h-5 text-yellow-500" />
                <h3 className="text-lg font-semibold text-gray-800">Explanation</h3>
                <span className="text-sm text-gray-500">
                  Confidence: {(response.explanation.confidenceScore * 100).toFixed(1)}%
                </span>
              </div>
              
              <p className="text-gray-700 mb-4">{response.explanation.reasoning}</p>
              
              <div className="space-y-2">
                <h4 className="font-medium text-gray-800">Source Influence:</h4>
                {response.explanation.sourceInfluence.map(influence => (
                  <div key={influence.documentId} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="text-sm text-gray-700">{influence.reason}</span>
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${influence.influence * 100}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};