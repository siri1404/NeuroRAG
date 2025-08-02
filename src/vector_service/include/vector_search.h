/**
 * @file vector_search.h
 * @brief High-performance vector search engine for NeuroRAG
 * 
 * This header defines the VectorSearchEngine class which provides
 * ultra-low latency vector similarity search using FAISS with
 * SIMD optimizations and NUMA-aware memory management.
 */

#pragma once

#include <vector>
#include <string>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <atomic>
#include <thread>
#include <queue>
#include <condition_variable>

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFFlat.h>
#include <faiss/IndexHNSW.h>
#include <faiss/index_io.h>
#include <nlohmann/json.hpp>

namespace neurorag {

/**
 * @brief Search result structure
 */
struct SearchResult {
    std::vector<int64_t> indices;
    std::vector<float> scores;
    std::vector<std::string> metadata;
    double latency_ms;
    bool from_cache;
};

/**
 * @brief Search request structure
 */
struct SearchRequest {
    std::vector<float> query_vector;
    int k;
    float threshold;
    std::unordered_map<std::string, std::string> filters;
    std::string request_id;
};

/**
 * @brief Configuration for vector search engine
 */
struct VectorSearchConfig {
    std::string index_path;
    std::string metadata_path;
    int dimension;
    int num_threads;
    bool use_gpu;
    int gpu_device;
    bool enable_cache;
    std::string cache_redis_url;
    int cache_ttl_seconds;
    bool enable_numa;
    int numa_node;
    bool enable_prefetch;
    int prefetch_size;
    double similarity_threshold;
    int max_results;
};

/**
 * @brief High-performance vector search engine
 * 
 * This class implements a high-throughput, low-latency vector search
 * engine using FAISS with various optimizations:
 * - SIMD vectorization
 * - NUMA-aware memory allocation
 * - Lock-free queues for concurrent requests
 * - Intelligent caching with Redis
 * - Batch processing for improved throughput
 */
class VectorSearchEngine {
public:
    /**
     * @brief Constructor
     * @param config Configuration parameters
     */
    explicit VectorSearchEngine(const VectorSearchConfig& config);
    
    /**
     * @brief Destructor
     */
    ~VectorSearchEngine();
    
    /**
     * @brief Initialize the search engine
     * @return true if initialization successful, false otherwise
     */
    bool initialize();
    
    /**
     * @brief Shutdown the search engine
     */
    void shutdown();
    
    /**
     * @brief Search for similar vectors
     * @param request Search request
     * @return Search results
     */
    SearchResult search(const SearchRequest& request);
    
    /**
     * @brief Batch search for multiple queries
     * @param requests Vector of search requests
     * @return Vector of search results
     */
    std::vector<SearchResult> batch_search(const std::vector<SearchRequest>& requests);
    
    /**
     * @brief Add vectors to the index
     * @param vectors Vector data
     * @param metadata Associated metadata
     * @return true if successful, false otherwise
     */
    bool add_vectors(const std::vector<std::vector<float>>& vectors,
                    const std::vector<std::string>& metadata);
    
    /**
     * @brief Remove vectors from the index
     * @param indices Indices to remove
     * @return true if successful, false otherwise
     */
    bool remove_vectors(const std::vector<int64_t>& indices);
    
    /**
     * @brief Save index to disk
     * @param path File path to save to
     * @return true if successful, false otherwise
     */
    bool save_index(const std::string& path);
    
    /**
     * @brief Load index from disk
     * @param path File path to load from
     * @return true if successful, false otherwise
     */
    bool load_index(const std::string& path);
    
    /**
     * @brief Get index statistics
     * @return JSON object with statistics
     */
    nlohmann::json get_statistics() const;
    
    /**
     * @brief Get health status
     * @return true if healthy, false otherwise
     */
    bool is_healthy() const;
    
    /**
     * @brief Warm up the cache with popular queries
     * @param queries List of query vectors to cache
     */
    void warmup_cache(const std::vector<std::vector<float>>& queries);

private:
    // Configuration
    VectorSearchConfig config_;
    
    // FAISS index
    std::unique_ptr<faiss::Index> index_;
    std::mutex index_mutex_;
    
    // Metadata storage
    std::vector<std::string> metadata_;
    std::mutex metadata_mutex_;
    
    // Thread pool for concurrent processing
    std::vector<std::thread> worker_threads_;
    std::queue<std::function<void()>> task_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_condition_;
    std::atomic<bool> shutdown_requested_;
    
    // Performance metrics
    std::atomic<uint64_t> total_searches_;
    std::atomic<uint64_t> cache_hits_;
    std::atomic<uint64_t> cache_misses_;
    std::atomic<double> total_latency_ms_;
    
    // Cache management
    class CacheManager* cache_manager_;
    
    // NUMA optimization
    void setup_numa_affinity();
    
    // SIMD optimized distance computation
    float compute_l2_distance_simd(const float* a, const float* b, int dimension) const;
    float compute_cosine_similarity_simd(const float* a, const float* b, int dimension) const;
    
    // Batch processing
    void process_batch_requests();
    
    // Worker thread function
    void worker_thread_function();
    
    // Cache key generation
    std::string generate_cache_key(const SearchRequest& request) const;
    
    // Metadata filtering
    bool passes_filters(int64_t index, const std::unordered_map<std::string, std::string>& filters) const;
    
    // Index optimization
    void optimize_index();
    
    // Memory prefetching
    void prefetch_vectors(const std::vector<int64_t>& indices) const;
    
    // Load balancing across NUMA nodes
    int get_optimal_numa_node() const;
    
    // Performance monitoring
    void update_metrics(double latency_ms, bool cache_hit);
    
    // Index validation
    bool validate_index() const;
    
    // Memory management
    void* allocate_aligned_memory(size_t size, size_t alignment) const;
    void free_aligned_memory(void* ptr) const;
};

/**
 * @brief Vector search factory for creating optimized instances
 */
class VectorSearchFactory {
public:
    /**
     * @brief Create optimized vector search engine
     * @param config Configuration parameters
     * @return Unique pointer to search engine
     */
    static std::unique_ptr<VectorSearchEngine> create_engine(const VectorSearchConfig& config);
    
    /**
     * @brief Auto-detect optimal configuration
     * @return Optimized configuration
     */
    static VectorSearchConfig auto_configure();
    
    /**
     * @brief Benchmark different configurations
     * @param test_queries Test queries for benchmarking
     * @return Best configuration
     */
    static VectorSearchConfig benchmark_configurations(
        const std::vector<std::vector<float>>& test_queries
    );
};

/**
 * @brief RAII wrapper for NUMA memory allocation
 */
class NumaMemoryAllocator {
public:
    explicit NumaMemoryAllocator(int numa_node);
    ~NumaMemoryAllocator();
    
    void* allocate(size_t size);
    void deallocate(void* ptr);
    
private:
    int numa_node_;
    std::vector<void*> allocated_blocks_;
    std::mutex allocation_mutex_;
};

/**
 * @brief Lock-free queue for high-performance request processing
 */
template<typename T>
class LockFreeQueue {
public:
    LockFreeQueue();
    ~LockFreeQueue();
    
    bool enqueue(const T& item);
    bool dequeue(T& item);
    size_t size() const;
    bool empty() const;
    
private:
    struct Node {
        std::atomic<T*> data;
        std::atomic<Node*> next;
    };
    
    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    std::atomic<size_t> size_;
};

} // namespace neurorag