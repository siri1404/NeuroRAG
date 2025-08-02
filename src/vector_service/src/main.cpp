/**
 * @file main.cpp
 * @brief Main entry point for NeuroRAG Vector Search Service
 * 
 * High-performance C++ microservice for vector similarity search
 * with sub-50ms latency and 10K+ concurrent request support.
 */

#include <iostream>
#include <string>
#include <memory>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>

#include <nlohmann/json.hpp>
#include "vector_search.h"
#include "cache_manager.h"
#include "http_server.h"
#include "metrics_collector.h"
#include "utils.h"

using json = nlohmann::json;
using namespace neurorag;

// Global variables for graceful shutdown
std::atomic<bool> shutdown_requested{false};
std::unique_ptr<VectorSearchEngine> search_engine;
std::unique_ptr<HttpServer> http_server;
std::unique_ptr<MetricsCollector> metrics_collector;

/**
 * @brief Signal handler for graceful shutdown
 */
void signal_handler(int signal) {
    std::cout << "\nReceived signal " << signal << ", initiating graceful shutdown..." << std::endl;
    shutdown_requested.store(true);
    
    if (http_server) {
        http_server->stop();
    }
    
    if (search_engine) {
        search_engine->shutdown();
    }
}

/**
 * @brief Load configuration from file and environment
 */
VectorSearchConfig load_configuration() {
    VectorSearchConfig config;
    
    // Default values
    config.index_path = "/data/faiss_index.bin";
    config.metadata_path = "/data/documents.json";
    config.dimension = 1536;
    config.num_threads = std::thread::hardware_concurrency();
    config.use_gpu = false;
    config.gpu_device = 0;
    config.enable_cache = true;
    config.cache_redis_url = "redis://localhost:6379";
    config.cache_ttl_seconds = 3600;
    config.enable_numa = true;
    config.numa_node = -1; // Auto-detect
    config.enable_prefetch = true;
    config.prefetch_size = 1000;
    config.similarity_threshold = 0.7;
    config.max_results = 100;
    
    // Override with environment variables
    if (const char* env_index_path = std::getenv("FAISS_INDEX_PATH")) {
        config.index_path = env_index_path;
    }
    
    if (const char* env_metadata_path = std::getenv("METADATA_PATH")) {
        config.metadata_path = env_metadata_path;
    }
    
    if (const char* env_dimension = std::getenv("VECTOR_DIMENSION")) {
        config.dimension = std::stoi(env_dimension);
    }
    
    if (const char* env_threads = std::getenv("NUM_WORKER_THREADS")) {
        config.num_threads = std::stoi(env_threads);
    }
    
    if (const char* env_redis_url = std::getenv("REDIS_URL")) {
        config.cache_redis_url = env_redis_url;
    }
    
    if (const char* env_use_gpu = std::getenv("USE_GPU")) {
        config.use_gpu = (std::string(env_use_gpu) == "true");
    }
    
    if (const char* env_gpu_device = std::getenv("GPU_DEVICE")) {
        config.gpu_device = std::stoi(env_gpu_device);
    }
    
    return config;
}

/**
 * @brief Initialize system optimizations
 */
void initialize_system_optimizations() {
    std::cout << "Initializing system optimizations..." << std::endl;
    
    // Set CPU affinity for main thread
    utils::set_cpu_affinity(0);
    
    // Set high priority for the process
    utils::set_process_priority(utils::Priority::HIGH);
    
    // Configure memory allocation
    utils::configure_memory_allocation();
    
    // Disable swap for better performance
    utils::disable_swap();
    
    // Configure network optimizations
    utils::configure_network_optimizations();
    
    std::cout << "System optimizations initialized" << std::endl;
}

/**
 * @brief Print system information
 */
void print_system_info() {
    auto system_info = utils::get_system_info();
    
    std::cout << "\n=== NeuroRAG Vector Search Service ===" << std::endl;
    std::cout << "Version: 1.0.0" << std::endl;
    std::cout << "Build: " << __DATE__ << " " << __TIME__ << std::endl;
    std::cout << "\n=== System Information ===" << std::endl;
    std::cout << "CPU Cores: " << system_info["cpu_cores"] << std::endl;
    std::cout << "Memory: " << system_info["total_memory_gb"] << " GB" << std::endl;
    std::cout << "NUMA Nodes: " << system_info["numa_nodes"] << std::endl;
    std::cout << "SIMD Support: " << system_info["simd_support"] << std::endl;
    std::cout << "Cache Line Size: " << system_info["cache_line_size"] << " bytes" << std::endl;
    std::cout << "======================================\n" << std::endl;
}

/**
 * @brief Health check thread function
 */
void health_check_thread() {
    while (!shutdown_requested.load()) {
        if (search_engine && !search_engine->is_healthy()) {
            std::cerr << "WARNING: Search engine health check failed!" << std::endl;
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(30));
    }
}

/**
 * @brief Metrics reporting thread function
 */
void metrics_reporting_thread() {
    while (!shutdown_requested.load()) {
        if (metrics_collector) {
            auto metrics = metrics_collector->get_metrics();
            
            // Log key metrics
            std::cout << "Metrics - "
                     << "RPS: " << metrics["requests_per_second"]
                     << ", Latency P99: " << metrics["latency_p99_ms"] << "ms"
                     << ", Cache Hit Rate: " << metrics["cache_hit_rate"] * 100 << "%"
                     << ", Memory Usage: " << metrics["memory_usage_mb"] << "MB"
                     << std::endl;
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(60));
    }
}

/**
 * @brief Main function
 */
int main(int argc, char* argv[]) {
    try {
        // Print system information
        print_system_info();
        
        // Initialize system optimizations
        initialize_system_optimizations();
        
        // Set up signal handlers
        std::signal(SIGINT, signal_handler);
        std::signal(SIGTERM, signal_handler);
        
        // Load configuration
        auto config = load_configuration();
        
        std::cout << "Configuration loaded:" << std::endl;
        std::cout << "  Index path: " << config.index_path << std::endl;
        std::cout << "  Metadata path: " << config.metadata_path << std::endl;
        std::cout << "  Dimension: " << config.dimension << std::endl;
        std::cout << "  Worker threads: " << config.num_threads << std::endl;
        std::cout << "  GPU enabled: " << (config.use_gpu ? "yes" : "no") << std::endl;
        std::cout << "  Cache enabled: " << (config.enable_cache ? "yes" : "no") << std::endl;
        std::cout << "  NUMA enabled: " << (config.enable_numa ? "yes" : "no") << std::endl;
        
        // Initialize metrics collector
        metrics_collector = std::make_unique<MetricsCollector>();
        
        // Initialize vector search engine
        std::cout << "\nInitializing vector search engine..." << std::endl;
        search_engine = std::make_unique<VectorSearchEngine>(config);
        
        if (!search_engine->initialize()) {
            std::cerr << "Failed to initialize vector search engine" << std::endl;
            return 1;
        }
        
        std::cout << "Vector search engine initialized successfully" << std::endl;
        
        // Print index statistics
        auto stats = search_engine->get_statistics();
        std::cout << "Index statistics:" << std::endl;
        std::cout << "  Total vectors: " << stats["total_vectors"] << std::endl;
        std::cout << "  Index type: " << stats["index_type"] << std::endl;
        std::cout << "  Memory usage: " << stats["memory_usage_mb"] << " MB" << std::endl;
        
        // Initialize HTTP server
        std::cout << "\nStarting HTTP server..." << std::endl;
        
        int port = std::stoi(std::getenv("VECTOR_SERVICE_PORT") ?: "8001");
        std::string host = std::getenv("VECTOR_SERVICE_HOST") ?: "0.0.0.0";
        
        http_server = std::make_unique<HttpServer>(host, port, search_engine.get(), metrics_collector.get());
        
        if (!http_server->start()) {
            std::cerr << "Failed to start HTTP server" << std::endl;
            return 1;
        }
        
        std::cout << "HTTP server started on " << host << ":" << port << std::endl;
        
        // Start background threads
        std::thread health_thread(health_check_thread);
        std::thread metrics_thread(metrics_reporting_thread);
        
        // Cache warmup if enabled
        if (config.enable_cache) {
            std::cout << "\nWarming up cache..." << std::endl;
            // Load popular queries from file or generate synthetic ones
            std::vector<std::vector<float>> warmup_queries;
            for (int i = 0; i < 100; ++i) {
                std::vector<float> query(config.dimension);
                for (int j = 0; j < config.dimension; ++j) {
                    query[j] = static_cast<float>(rand()) / RAND_MAX;
                }
                warmup_queries.push_back(query);
            }
            search_engine->warmup_cache(warmup_queries);
            std::cout << "Cache warmup completed" << std::endl;
        }
        
        std::cout << "\n🚀 NeuroRAG Vector Search Service is ready!" << std::endl;
        std::cout << "📊 Metrics endpoint: http://" << host << ":" << port << "/metrics" << std::endl;
        std::cout << "🏥 Health endpoint: http://" << host << ":" << port << "/health" << std::endl;
        std::cout << "🔍 Search endpoint: http://" << host << ":" << port << "/search" << std::endl;
        std::cout << "\nPress Ctrl+C to shutdown gracefully..." << std::endl;
        
        // Main event loop
        while (!shutdown_requested.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        std::cout << "\nShutting down..." << std::endl;
        
        // Stop background threads
        if (health_thread.joinable()) {
            health_thread.join();
        }
        if (metrics_thread.joinable()) {
            metrics_thread.join();
        }
        
        // Cleanup
        http_server.reset();
        search_engine.reset();
        metrics_collector.reset();
        
        std::cout << "Shutdown completed successfully" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown fatal error occurred" << std::endl;
        return 1;
    }
}