# NeuroRAG Vector Search Service CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project(NeuroRAGVectorService VERSION 1.0.0)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O3 -march=native")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -g -O0 -DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -DNDEBUG")

# Find required packages
find_package(PkgConfig REQUIRED)

# OpenMP for parallel processing
find_package(OpenMP REQUIRED)
if(OpenMP_CXX_FOUND)
    target_link_libraries(vector_service PUBLIC OpenMP::OpenMP_CXX)
endif()

# FAISS
find_path(FAISS_INCLUDE_DIR faiss/IndexFlat.h)
find_library(FAISS_LIBRARY faiss)

if(NOT FAISS_INCLUDE_DIR OR NOT FAISS_LIBRARY)
    message(FATAL_ERROR "FAISS not found. Please install FAISS library.")
endif()

# Intel MKL (optional, for better performance)
find_package(MKL QUIET)
if(MKL_FOUND)
    add_definitions(-DUSE_MKL)
    include_directories(${MKL_INCLUDE_DIRS})
    set(MKL_LIBRARIES ${MKL_LIBRARIES})
else()
    # Fallback to BLAS/LAPACK
    find_package(BLAS REQUIRED)
    find_package(LAPACK REQUIRED)
    set(MKL_LIBRARIES ${BLAS_LIBRARIES} ${LAPACK_LIBRARIES})
endif()

# Redis C++ client (hiredis)
pkg_check_modules(HIREDIS REQUIRED hiredis)

# JSON library (nlohmann/json)
find_package(nlohmann_json REQUIRED)

# HTTP server library (httplib)
find_path(HTTPLIB_INCLUDE_DIR httplib.h)
if(NOT HTTPLIB_INCLUDE_DIR)
    message(FATAL_ERROR "httplib.h not found. Please install cpp-httplib.")
endif()

# Threading
find_package(Threads REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${FAISS_INCLUDE_DIR}
    ${HIREDIS_INCLUDE_DIRS}
    ${HTTPLIB_INCLUDE_DIR}
)

# Source files
set(SOURCES
    src/main.cpp
    src/vector_search.cpp
    src/cache_manager.cpp
    src/utils.cpp
    src/http_server.cpp
    src/metrics_collector.cpp
)

# Create executable
add_executable(vector_service ${SOURCES})

# Link libraries
target_link_libraries(vector_service
    ${FAISS_LIBRARY}
    ${MKL_LIBRARIES}
    ${HIREDIS_LIBRARIES}
    nlohmann_json::nlohmann_json
    Threads::Threads
    OpenMP::OpenMP_CXX
)

# Compiler-specific optimizations
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(vector_service PRIVATE
        -ftree-vectorize
        -ffast-math
        -funroll-loops
        -fprefetch-loop-arrays
    )
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(vector_service PRIVATE
        -fvectorize
        -ffast-math
        -funroll-loops
    )
endif()

# SIMD optimizations
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-mavx2" COMPILER_SUPPORTS_AVX2)
check_cxx_compiler_flag("-mfma" COMPILER_SUPPORTS_FMA)

if(COMPILER_SUPPORTS_AVX2)
    target_compile_options(vector_service PRIVATE -mavx2)
    add_definitions(-DUSE_AVX2)
endif()

if(COMPILER_SUPPORTS_FMA)
    target_compile_options(vector_service PRIVATE -mfma)
    add_definitions(-DUSE_FMA)
endif()

# NUMA support
find_library(NUMA_LIBRARY numa)
if(NUMA_LIBRARY)
    target_link_libraries(vector_service ${NUMA_LIBRARY})
    add_definitions(-DUSE_NUMA)
endif()

# Install targets
install(TARGETS vector_service
    RUNTIME DESTINATION bin
)

# Install configuration files
install(FILES
    ${CMAKE_CURRENT_SOURCE_DIR}/config/vector_service.conf
    DESTINATION etc/neurorag
)

# Testing
enable_testing()

# Google Test
find_package(GTest QUIET)
if(GTest_FOUND)
    add_executable(vector_service_tests
        tests/test_vector_search.cpp
        tests/test_cache_manager.cpp
        tests/test_utils.cpp
        src/vector_search.cpp
        src/cache_manager.cpp
        src/utils.cpp
    )
    
    target_link_libraries(vector_service_tests
        ${FAISS_LIBRARY}
        ${MKL_LIBRARIES}
        ${HIREDIS_LIBRARIES}
        nlohmann_json::nlohmann_json
        GTest::gtest_main
        Threads::Threads
    )
    
    add_test(NAME VectorServiceTests COMMAND vector_service_tests)
endif()

# Benchmarking
add_executable(vector_service_benchmark
    benchmarks/benchmark_search.cpp
    src/vector_search.cpp
    src/cache_manager.cpp
    src/utils.cpp
)

target_link_libraries(vector_service_benchmark
    ${FAISS_LIBRARY}
    ${MKL_LIBRARIES}
    ${HIREDIS_LIBRARIES}
    nlohmann_json::nlohmann_json
    Threads::Threads
)

# Documentation
find_package(Doxygen QUIET)
if(DOXYGEN_FOUND)
    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/docs/Doxyfile.in
                   ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile @ONLY)
    
    add_custom_target(docs
        ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMENT "Generating API documentation with Doxygen"
        VERBATIM
    )
endif()

# Package configuration
set(CPACK_PACKAGE_NAME "neurorag-vector-service")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "High-performance vector search service for NeuroRAG")
set(CPACK_PACKAGE_VENDOR "NeuroRAG Team")
set(CPACK_GENERATOR "DEB;RPM")

include(CPack)

# Print configuration summary
message(STATUS "")
message(STATUS "NeuroRAG Vector Service Configuration Summary:")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  FAISS: ${FAISS_LIBRARY}")
message(STATUS "  MKL: ${MKL_FOUND}")
message(STATUS "  AVX2: ${COMPILER_SUPPORTS_AVX2}")
message(STATUS "  FMA: ${COMPILER_SUPPORTS_FMA}")
message(STATUS "  NUMA: ${NUMA_LIBRARY}")
message(STATUS "  OpenMP: ${OpenMP_CXX_FOUND}")
message(STATUS "  Tests: ${GTest_FOUND}")
message(STATUS "")