#!/bin/bash

# NeuroRAG Cache Warmup Script
# Pre-loads frequently accessed vectors into Redis cache

set -e

# Configuration
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
VECTOR_SERVICE_URL=${VECTOR_SERVICE_URL:-http://localhost:8001}
WARMUP_QUERIES_FILE=${WARMUP_QUERIES_FILE:-config/warmup_queries.json}
BATCH_SIZE=${BATCH_SIZE:-100}
CONCURRENT_REQUESTS=${CONCURRENT_REQUESTS:-10}

echo "🔥 Starting NeuroRAG Cache Warmup"
echo "Redis: ${REDIS_HOST}:${REDIS_PORT}"
echo "Vector Service: ${VECTOR_SERVICE_URL}"
echo "Batch Size: ${BATCH_SIZE}"
echo "Concurrent Requests: ${CONCURRENT_REQUESTS}"

# Check if Redis is available
echo "📡 Checking Redis connection..."
if ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; then
    echo "❌ Redis is not available at ${REDIS_HOST}:${REDIS_PORT}"
    exit 1
fi
echo "✅ Redis connection successful"

# Check if Vector Service is available
echo "📡 Checking Vector Service connection..."
if ! curl -s "${VECTOR_SERVICE_URL}/health" > /dev/null; then
    echo "❌ Vector Service is not available at ${VECTOR_SERVICE_URL}"
    exit 1
fi
echo "✅ Vector Service connection successful"

# Function to warm up cache with a batch of queries
warmup_batch() {
    local batch_file=$1
    local batch_id=$2
    
    echo "🔄 Processing batch ${batch_id}..."
    
    # Send batch request to vector service
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d @"${batch_file}" \
        "${VECTOR_SERVICE_URL}/search/batch" > /dev/null
    
    echo "✅ Batch ${batch_id} completed"
}

# Create temporary directory for batch files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Check if warmup queries file exists
if [[ ! -f "$WARMUP_QUERIES_FILE" ]]; then
    echo "📝 Creating sample warmup queries..."
    cat > "$WARMUP_QUERIES_FILE" << EOF
{
  "queries": [
    "What was our revenue performance in Q3?",
    "Explain our risk management framework",
    "What are the current market conditions?",
    "What compliance guidelines should advisors follow?",
    "How did our technology sector investments perform?",
    "What are the key financial metrics for this quarter?",
    "Describe our portfolio diversification strategy",
    "What regulatory changes affect our operations?",
    "How do we assess credit risk?",
    "What are our operational risk controls?",
    "Explain our market risk exposure",
    "What is our current liquidity position?",
    "How do we handle data privacy compliance?",
    "What are our ESG investment criteria?",
    "Describe our client onboarding process"
  ]
}
EOF
fi

# Read queries from file
echo "📖 Reading warmup queries from ${WARMUP_QUERIES_FILE}..."
TOTAL_QUERIES=$(jq '.queries | length' "$WARMUP_QUERIES_FILE")
echo "📊 Total queries to process: ${TOTAL_QUERIES}"

# Split queries into batches
echo "📦 Creating batches of size ${BATCH_SIZE}..."
BATCH_COUNT=0

for ((i=0; i<$TOTAL_QUERIES; i+=$BATCH_SIZE)); do
    BATCH_COUNT=$((BATCH_COUNT + 1))
    BATCH_FILE="${TEMP_DIR}/batch_${BATCH_COUNT}.json"
    
    # Extract batch of queries
    jq --argjson start $i --argjson size $BATCH_SIZE \
        '{queries: .queries[$start:$start+$size]}' \
        "$WARMUP_QUERIES_FILE" > "$BATCH_FILE"
done

echo "📦 Created ${BATCH_COUNT} batches"

# Process batches concurrently
echo "🚀 Starting concurrent cache warmup..."
PIDS=()

for ((batch=1; batch<=BATCH_COUNT; batch++)); do
    # Limit concurrent processes
    while [[ ${#PIDS[@]} -ge $CONCURRENT_REQUESTS ]]; do
        for i in "${!PIDS[@]}"; do
            if ! kill -0 "${PIDS[$i]}" 2>/dev/null; then
                unset "PIDS[$i]"
            fi
        done
        PIDS=("${PIDS[@]}")  # Reindex array
        sleep 0.1
    done
    
    # Start batch processing in background
    warmup_batch "${TEMP_DIR}/batch_${batch}.json" "$batch" &
    PIDS+=($!)
done

# Wait for all background processes to complete
echo "⏳ Waiting for all batches to complete..."
for pid in "${PIDS[@]}"; do
    wait "$pid"
done

# Verify cache status
echo "📊 Checking cache statistics..."
CACHE_KEYS=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT dbsize)
CACHE_MEMORY=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')

echo "✅ Cache warmup completed successfully!"
echo "📈 Cache Statistics:"
echo "   - Total keys: ${CACHE_KEYS}"
echo "   - Memory usage: ${CACHE_MEMORY}"

# Optional: Precompute popular embeddings
if [[ "${PRECOMPUTE_EMBEDDINGS:-false}" == "true" ]]; then
    echo "🧠 Precomputing popular embeddings..."
    
    # Get most frequent query patterns
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"action": "precompute_popular"}' \
        "${VECTOR_SERVICE_URL}/admin/cache" > /dev/null
    
    echo "✅ Popular embeddings precomputed"
fi

# Set cache expiration policies
echo "⏰ Setting cache expiration policies..."
redis-cli -h $REDIS_HOST -p $REDIS_PORT config set maxmemory-policy allkeys-lru > /dev/null

# Log completion
echo "🎉 NeuroRAG Cache Warmup completed successfully!"
echo "🕐 Completed at: $(date)"
echo "📊 Final Statistics:"
echo "   - Processed queries: ${TOTAL_QUERIES}"
echo "   - Batch size: ${BATCH_SIZE}"
echo "   - Concurrent requests: ${CONCURRENT_REQUESTS}"
echo "   - Cache keys: ${CACHE_KEYS}"
echo "   - Memory usage: ${CACHE_MEMORY}"