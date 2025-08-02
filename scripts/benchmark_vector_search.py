#!/usr/bin/env python3
"""
Vector Search Benchmarking Script for NeuroRAG
Tests performance of FAISS index with various configurations
"""

import os
import time
import json
import argparse
import statistics
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorSearchBenchmark:
    def __init__(self, index_path: str, config_path: str):
        """Initialize benchmark with FAISS index and configuration."""
        self.index_path = Path(index_path)
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load FAISS index
        self.index = faiss.read_index(str(self.index_path))
        logger.info(f"Loaded index with {self.index.ntotal} vectors")
        
        # Initialize embedding model
        self.model = SentenceTransformer(self.config['model_name'])
        
        # Benchmark results
        self.results = {}

    def generate_query_vectors(self, num_queries: int = 1000) -> np.ndarray:
        """Generate random query vectors for benchmarking."""
        logger.info(f"Generating {num_queries} random query vectors...")
        
        # Generate random queries that are similar to indexed vectors
        random_indices = np.random.randint(0, self.index.ntotal, num_queries)
        query_vectors = np.zeros((num_queries, self.config['dimension']), dtype=np.float32)
        
        for i, idx in enumerate(random_indices):
            # Get a vector from the index and add some noise
            base_vector = self.index.reconstruct(idx)
            noise = np.random.normal(0, 0.1, base_vector.shape).astype(np.float32)
            query_vectors[i] = base_vector + noise
            
        # Normalize vectors
        faiss.normalize_L2(query_vectors)
        return query_vectors

    def benchmark_latency(self, query_vectors: np.ndarray, k: int = 5, num_runs: int = 100) -> Dict:
        """Benchmark search latency."""
        logger.info(f"Benchmarking latency with {num_runs} runs, k={k}")
        
        latencies = []
        
        for i in range(num_runs):
            query_idx = i % len(query_vectors)
            query = query_vectors[query_idx:query_idx+1]
            
            start_time = time.perf_counter()
            scores, indices = self.index.search(query, k)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        results = {
            'mean_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'p95_latency_ms': np.percentile(latencies, 95),
            'p99_latency_ms': np.percentile(latencies, 99),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'std_latency_ms': statistics.stdev(latencies),
            'latencies': latencies
        }
        
        logger.info(f"Mean latency: {results['mean_latency_ms']:.2f}ms")
        logger.info(f"P95 latency: {results['p95_latency_ms']:.2f}ms")
        logger.info(f"P99 latency: {results['p99_latency_ms']:.2f}ms")
        
        return results

    def benchmark_throughput(self, query_vectors: np.ndarray, k: int = 5, duration_seconds: int = 30) -> Dict:
        """Benchmark search throughput."""
        logger.info(f"Benchmarking throughput for {duration_seconds} seconds")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        query_count = 0
        
        while time.time() < end_time:
            query_idx = query_count % len(query_vectors)
            query = query_vectors[query_idx:query_idx+1]
            
            self.index.search(query, k)
            query_count += 1
        
        actual_duration = time.time() - start_time
        throughput = query_count / actual_duration
        
        results = {
            'queries_per_second': throughput,
            'total_queries': query_count,
            'duration_seconds': actual_duration
        }
        
        logger.info(f"Throughput: {throughput:.2f} queries/second")
        
        return results

    def benchmark_concurrent_throughput(self, query_vectors: np.ndarray, k: int = 5, 
                                      num_threads: int = 8, duration_seconds: int = 30) -> Dict:
        """Benchmark concurrent search throughput."""
        logger.info(f"Benchmarking concurrent throughput with {num_threads} threads")
        
        def worker(worker_id: int, end_time: float) -> int:
            query_count = 0
            while time.time() < end_time:
                query_idx = (worker_id + query_count) % len(query_vectors)
                query = query_vectors[query_idx:query_idx+1]
                
                self.index.search(query, k)
                query_count += 1
            return query_count
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i, end_time) for i in range(num_threads)]
            thread_results = [future.result() for future in as_completed(futures)]
        
        actual_duration = time.time() - start_time
        total_queries = sum(thread_results)
        throughput = total_queries / actual_duration
        
        results = {
            'concurrent_queries_per_second': throughput,
            'total_queries': total_queries,
            'duration_seconds': actual_duration,
            'num_threads': num_threads,
            'per_thread_results': thread_results
        }
        
        logger.info(f"Concurrent throughput: {throughput:.2f} queries/second")
        
        return results

    def benchmark_accuracy(self, query_vectors: np.ndarray, k_values: List[int] = [1, 5, 10, 20]) -> Dict:
        """Benchmark search accuracy using ground truth from exhaustive search."""
        logger.info("Benchmarking search accuracy...")
        
        # Create ground truth index (exhaustive search)
        gt_index = faiss.IndexFlatIP(self.config['dimension'])
        
        # Copy vectors from main index to ground truth index
        all_vectors = np.zeros((self.index.ntotal, self.config['dimension']), dtype=np.float32)
        for i in range(self.index.ntotal):
            all_vectors[i] = self.index.reconstruct(i)
        gt_index.add(all_vectors)
        
        accuracy_results = {}
        
        for k in k_values:
            recalls = []
            
            for query in query_vectors[:100]:  # Test on subset for speed
                query = query.reshape(1, -1)
                
                # Get results from main index
                _, main_indices = self.index.search(query, k)
                
                # Get ground truth results
                _, gt_indices = gt_index.search(query, k)
                
                # Calculate recall@k
                main_set = set(main_indices[0])
                gt_set = set(gt_indices[0])
                recall = len(main_set.intersection(gt_set)) / len(gt_set)
                recalls.append(recall)
            
            accuracy_results[f'recall@{k}'] = {
                'mean': statistics.mean(recalls),
                'std': statistics.stdev(recalls) if len(recalls) > 1 else 0,
                'min': min(recalls),
                'max': max(recalls)
            }
            
            logger.info(f"Recall@{k}: {accuracy_results[f'recall@{k}']['mean']:.4f}")
        
        return accuracy_results

    def run_full_benchmark(self, output_dir: str):
        """Run complete benchmark suite."""
        logger.info("Starting full benchmark suite...")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate query vectors
        query_vectors = self.generate_query_vectors(1000)
        
        # Run benchmarks
        self.results['latency'] = self.benchmark_latency(query_vectors)
        self.results['throughput'] = self.benchmark_throughput(query_vectors)
        self.results['concurrent_throughput'] = self.benchmark_concurrent_throughput(query_vectors)
        self.results['accuracy'] = self.benchmark_accuracy(query_vectors)
        
        # Add system info
        self.results['system_info'] = {
            'index_type': self.config.get('index_type', 'unknown'),
            'num_vectors': self.index.ntotal,
            'dimension': self.config['dimension'],
            'model_name': self.config['model_name']
        }
        
        # Save results
        results_path = output_dir / 'benchmark_results.json'
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate plots
        self.generate_plots(output_dir)
        
        logger.info(f"Benchmark completed. Results saved to {output_dir}")

    def generate_plots(self, output_dir: Path):
        """Generate visualization plots."""
        plt.style.use('seaborn-v0_8')
        
        # Latency distribution plot
        plt.figure(figsize=(10, 6))
        plt.hist(self.results['latency']['latencies'], bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(self.results['latency']['mean_latency_ms'], color='red', linestyle='--', 
                   label=f"Mean: {self.results['latency']['mean_latency_ms']:.2f}ms")
        plt.axvline(self.results['latency']['p95_latency_ms'], color='orange', linestyle='--',
                   label=f"P95: {self.results['latency']['p95_latency_ms']:.2f}ms")
        plt.xlabel('Latency (ms)')
        plt.ylabel('Frequency')
        plt.title('Search Latency Distribution')
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / 'latency_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Accuracy plot
        if 'accuracy' in self.results:
            k_values = []
            recall_values = []
            
            for key, value in self.results['accuracy'].items():
                if key.startswith('recall@'):
                    k = int(key.split('@')[1])
                    k_values.append(k)
                    recall_values.append(value['mean'])
            
            plt.figure(figsize=(8, 6))
            plt.plot(k_values, recall_values, marker='o', linewidth=2, markersize=8)
            plt.xlabel('k (number of results)')
            plt.ylabel('Recall@k')
            plt.title('Search Accuracy vs k')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_dir / 'accuracy_vs_k.png', dpi=300, bbox_inches='tight')
            plt.close()

def main():
    parser = argparse.ArgumentParser(description="Benchmark FAISS vector search performance")
    parser.add_argument("--index", required=True, help="Path to FAISS index file")
    parser.add_argument("--config", required=True, help="Path to configuration JSON file")
    parser.add_argument("--output", required=True, help="Output directory for results")
    parser.add_argument("--duration", type=int, default=30, help="Duration for throughput tests (seconds)")
    parser.add_argument("--threads", type=int, default=8, help="Number of threads for concurrent tests")
    
    args = parser.parse_args()
    
    # Run benchmark
    benchmark = VectorSearchBenchmark(args.index, args.config)
    benchmark.run_full_benchmark(args.output)

if __name__ == "__main__":
    main()