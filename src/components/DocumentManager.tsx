import React, { useState, useRef } from 'react';
import { Upload, FileText, Trash2, Plus, AlertCircle, CheckCircle } from 'lucide-react';
import { vectorStore } from '../services/vectorStore';
import { Document } from '../types';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';

export const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>(vectorStore.getDocuments());
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    
    try {
      for (const file of Array.from(files)) {
        const content = await readFileContent(file);
        
        const document: Document = {
          id: uuidv4(),
          title: file.name,
          content: content,
          metadata: {
            source: file.name,
            timestamp: new Date().toISOString(),
            classification: 'confidential',
            tags: extractTags(content)
          }
        };

        vectorStore.addDocument(document);
      }

      setDocuments(vectorStore.getDocuments());
      toast.success(`Successfully uploaded ${files.length} document(s)`);
    } catch (error) {
      console.error('Error uploading files:', error);
      toast.error('Failed to upload documents');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        resolve(content);
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  const extractTags = (content: string): string[] => {
    const words = content.toLowerCase().match(/\b\w+\b/g) || [];
    const commonWords = ['financial', 'report', 'analysis', 'market', 'risk', 'compliance', 'revenue', 'profit'];
    return commonWords.filter(word => words.includes(word));
  };

  const handleDeleteDocument = (id: string) => {
    vectorStore.removeDocument(id);
    setDocuments(vectorStore.getDocuments());
    toast.success('Document deleted successfully');
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to delete all documents? This action cannot be undone.')) {
      vectorStore.clearAllDocuments();
      setDocuments([]);
      toast.success('All documents cleared');
    }
  };

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case 'public':
        return 'bg-green-100 text-green-800';
      case 'confidential':
        return 'bg-yellow-100 text-yellow-800';
      case 'restricted':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Upload className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-800">Document Management</h2>
          </div>
          
          {documents.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Clear All
            </button>
          )}
        </div>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.md,.json,.csv"
            onChange={handleFileUpload}
            className="hidden"
          />
          
          <div className="space-y-4">
            <div className="flex justify-center">
              <div className="p-4 bg-blue-100 rounded-full">
                <Upload className="w-8 h-8 text-blue-600" />
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-gray-800">Upload Files</h3>
              <p className="text-gray-600 mt-1">
                Upload text files, markdown, JSON, or CSV files
              </p>
            </div>
            
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {uploading ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Uploading...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <Plus className="w-4 h-4" />
                  <span>Choose Files</span>
                </div>
              )}
            </button>
            
            <p className="text-sm text-gray-500">
              Formats: .txt, .md, .json, .csv (Max 10MB)
            </p>
          </div>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            Uploaded Documents ({documents.length})
          </h3>
          
          {documents.length > 0 && (
            <div className="flex items-center space-x-2 text-sm text-green-600">
              <CheckCircle className="w-4 h-4" />
              <span>Ready</span>
            </div>
          )}
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-gray-100 rounded-full">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
            </div>
            <h4 className="text-lg font-medium text-gray-600 mb-2">No Documents</h4>
            <p className="text-gray-500">
              Upload documents to get started
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {documents.map((doc) => (
              <div key={doc.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <FileText className="w-5 h-5 text-gray-600" />
                      <h4 className="font-medium text-gray-800">{doc.title}</h4>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getClassificationColor(doc.metadata.classification)}`}>
                        {doc.metadata.classification}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {doc.content.substring(0, 200)}...
                    </p>
                    
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>Source: {doc.metadata.source}</span>
                      <span>
                        Uploaded: {new Date(doc.metadata.timestamp).toLocaleDateString()}
                      </span>
                      <span>Length: {doc.content.length} chars</span>
                    </div>
                    
                    {doc.metadata.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {doc.metadata.tags.map(tag => (
                          <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-800">Instructions</h4>
            <ul className="text-sm text-blue-700 mt-1 space-y-1">
              <li>• Upload text-based documents</li>
              <li>• Documents are processed and indexed for semantic search</li>
              <li>• Use Query Interface to ask questions</li>
              <li>• Configure OpenAI API key in .env for responses</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};