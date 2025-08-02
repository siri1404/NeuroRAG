import { Document, RetrievedDocument } from '../types';
import axios from 'axios';

// Simulated FAISS-like vector operations
class VectorStore {
  private documents: Document[] = [];
  private index: Map<string, number[]> = new Map();
  private vectorServiceUrl = import.meta.env.VITE_VECTOR_SERVICE_URL || 'http://localhost:8001';

  constructor() {
    this.loadDocuments();
  }

  private async loadDocuments() {
    try {
      // Try to load documents from localStorage first
      const savedDocs = localStorage.getItem('neurorag_documents');
      if (savedDocs) {
        const docs = JSON.parse(savedDocs);
        this.documents = docs;
        docs.forEach((doc: Document) => {
          this.index.set(doc.id, this.generateEmbedding(doc.content));
        });
        return;
      }

      // If no saved documents, create empty state
      this.documents = [];
      console.log('No documents found. Please upload documents using the interface.');
    } catch (error) {
      console.error('Error loading documents:', error);
      this.documents = [];
    }
  }

  private generateEmbedding(text: string): number[] {
    // Simulate embedding generation (in reality, this would use a model like sentence-transformers)
    const embedding = new Array(384).fill(0).map(() => Math.random() - 0.5);
    return embedding;
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
    const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
    const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
    return dotProduct / (magnitudeA * magnitudeB);
  }

  async search(query: string, maxResults: number = 5, threshold: number = 0.7): Promise<RetrievedDocument[]> {
    try {
      // Try to use backend vector service first
      const response = await axios.post(`${this.vectorServiceUrl}/search`, {
        query,
        k: maxResults,
        threshold
      });

      return response.data.documents.map((doc: any) => ({
        document: {
          id: doc.id,
          title: doc.title,
          content: doc.content,
          metadata: doc.metadata
        },
        score: doc.score,
        relevanceReason: doc.relevance_reason
      }));
    } catch (error) {
      console.warn('Backend vector service unavailable, using local search:', error);
      return this.localSearch(query, maxResults, threshold);
    }
  }

  private async localSearch(query: string, maxResults: number, threshold: number): Promise<RetrievedDocument[]> {
    // Simulate vector search latency
    await new Promise(resolve => setTimeout(resolve, Math.random() * 30 + 10));

    const queryEmbedding = this.generateEmbedding(query);
    const results: RetrievedDocument[] = [];

    for (const doc of this.documents) {
      const docEmbedding = this.index.get(doc.id);
      if (!docEmbedding) continue;

      const score = this.cosineSimilarity(queryEmbedding, docEmbedding);
      if (score >= threshold) {
        results.push({
          document: doc,
          score,
          relevanceReason: this.generateRelevanceReason(query, doc, score)
        });
      }
    }

    return results
      .sort((a, b) => b.score - a.score)
      .slice(0, maxResults);
  }

  private generateRelevanceReason(query: string, doc: Document, score: number): string {
    const queryWords = query.toLowerCase().split(' ');
    const contentWords = doc.content.toLowerCase().split(' ');
    const commonWords = queryWords.filter(word => contentWords.includes(word));
    
    if (commonWords.length > 0) {
      return `Semantic similarity (${(score * 100).toFixed(1)}%) - matching: ${commonWords.slice(0, 3).join(', ')}`;
    }
    return `Semantic similarity (${(score * 100).toFixed(1)}%)`;
  }

  getDocuments(): Document[] {
    return this.documents;
  }

  addDocument(doc: Document): void {
    try {
      // Try to add to backend service first
      axios.post(`${this.vectorServiceUrl}/documents`, doc).catch(() => {
        console.warn('Failed to add document to backend service');
      });
    } catch (error) {
      console.warn('Backend service unavailable for document addition');
    }

    // Always add to local storage as backup
    this.documents.push(doc);
    this.index.set(doc.id, this.generateEmbedding(doc.content));
    
    try {
      localStorage.setItem('neurorag_documents', JSON.stringify(this.documents));
    } catch (error) {
      console.error('Error saving documents to localStorage:', error);
    }
  }

  removeDocument(id: string): void {
    try {
      // Try to remove from backend service first
      axios.delete(`${this.vectorServiceUrl}/documents/${id}`).catch(() => {
        console.warn('Failed to remove document from backend service');
      });
    } catch (error) {
      console.warn('Backend service unavailable for document removal');
    }

    // Always remove from local storage
    this.documents = this.documents.filter(doc => doc.id !== id);
    this.index.delete(id);
    
    try {
      localStorage.setItem('neurorag_documents', JSON.stringify(this.documents));
    } catch (error) {
      console.error('Error updating localStorage:', error);
    }
  }

  clearAllDocuments(): void {
    try {
      // Clear backend service documents (if available)
      this.documents.forEach(doc => {
        axios.delete(`${this.vectorServiceUrl}/documents/${doc.id}`).catch(() => {
          // Ignore errors for bulk deletion
        });
      });
    } catch (error) {
      console.warn('Backend service unavailable for bulk deletion');
    }

    // Always clear local storage
    this.documents = [];
    this.index.clear();
    
    try {
      localStorage.removeItem('neurorag_documents');
    } catch (error) {
      console.error('Error clearing localStorage:', error);
    }
  }
}

export const vectorStore = new VectorStore();