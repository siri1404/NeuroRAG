export interface Document {
  id: string;
  title: string;
  content: string;
  metadata: {
    source: string;
    timestamp: string;
    classification: 'public' | 'confidential' | 'restricted';
    tags: string[];
  };
  embedding?: number[];
}

export interface QueryRequest {
  query: string;
  maxResults?: number;
  threshold?: number;
  includeExplanation?: boolean;
}

export interface RetrievedDocument {
  document: Document;
  score: number;
  relevanceReason: string;
}

export interface RAGResponse {
  id: string;
  query: string;
  answer: string;
  retrievedDocuments: RetrievedDocument[];
  explanation?: {
    reasoning: string;
    confidenceScore: number;
    sourceInfluence: Array<{
      documentId: string;
      influence: number;
      reason: string;
    }>;
  };
  metadata: {
    latency: number;
    tokensUsed: number;
    timestamp: string;
    complianceFlags: string[];
  };
}

export interface SystemMetrics {
  apiLatency: {
    p50: number;
    p95: number;
    p99: number;
  };
  vectorSearchLatency: number;
  throughput: number;
  uptime: number;
  cacheHitRate: number;
  costReduction: number;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  queryId: string;
  userId: string;
  action: string;
  dataAccessed: string[];
  complianceStatus: 'compliant' | 'flagged' | 'blocked';
  details: string;
}