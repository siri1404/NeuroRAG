#!/bin/bash

# Setup Script
# Automated setup for development and production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.9"
NODE_VERSION="18"
DOCKER_COMPOSE_VERSION="2.20.0"

# Functions
log_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        log_success "$1 is installed"
        return 0
    else
        log_warning "$1 is not installed"
        return 1
    fi
}

install_docker() {
    log_info "Installing Docker..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install --cask docker
        else
            log_error "Please install Docker Desktop manually from https://docker.com/products/docker-desktop"
            exit 1
        fi
    else
        log_error "Unsupported operating system"
        exit 1
    fi
    
    log_success "Docker installed successfully"
}

install_python() {
    log_info "Setting up Python environment..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev
        sudo apt-get install -y build-essential cmake pkg-config
        sudo apt-get install -y libblas-dev liblapack-dev libhiredis-dev
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install python@${PYTHON_VERSION} cmake pkg-config hiredis
        else
            log_error "Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    fi
    
    # Create virtual environment
    python${PYTHON_VERSION} -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    log_success "Python environment set up successfully"
}

install_node() {
    log_info "Installing Node.js..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Install Node.js via NodeSource
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
        sudo apt-get install -y nodejs
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install node@${NODE_VERSION}
        else
            log_error "Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    fi
    
    log_success "Node.js installed successfully"
}

install_dependencies() {
    log_info "Installing project dependencies..."
    
    # Python dependencies
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    pip install -r requirements.txt
    
    # Node.js dependencies
    npm install
    
    log_success "Dependencies installed successfully"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        log_info "Created .env file from template"
        log_warning "Please edit .env file with your configuration"
    fi
    
    # Create necessary directories
    mkdir -p data logs build
    
    log_success "Environment configuration complete"
}

build_cpp_service() {
    log_info "Building C++ vector service..."
    
    cd src/vector_service
    mkdir -p build
    cd build
    
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    
    cd ../../..
    log_success "C++ vector service built successfully"
}

setup_database() {
    log_info "Setting up database..."
    
    # Start database services
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    sleep 10
    
    # Run database migrations
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Initialize database schema (if using Alembic)
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
    fi
    
    log_success "Database setup complete"
}

run_tests() {
    log_info "Running tests to verify installation..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Run Python tests
    pytest src/tests/ -v --tb=short
    
    # Run C++ tests
    if [ -f "src/vector_service/build/vector_service_tests" ]; then
        cd src/vector_service/build
        ./vector_service_tests
        cd ../../..
    fi
    
    # Run frontend tests
    npm test -- --watchAll=false
    
    log_success "All tests passed"
}

main() {
    echo "Setup Script"
    echo "========================"
    echo ""
    
    # Parse command line arguments
    ENVIRONMENT="development"
    SKIP_TESTS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --production)
                ENVIRONMENT="production"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --production    Setup for production environment"
                echo "  --skip-tests    Skip running tests"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Setting up for ${ENVIRONMENT} environment"
    echo ""
    
    # Check existing installations
    log_info "Checking existing installations..."
    
    if ! check_command "docker"; then
        install_docker
    fi
    
    if ! check_command "python${PYTHON_VERSION}"; then
        install_python
    fi
    
    if ! check_command "node"; then
        install_node
    fi
    
    # Setup project
    setup_environment
    install_dependencies
    
    if [[ "$ENVIRONMENT" == "development" ]]; then
        build_cpp_service
        setup_database
        
        if [[ "$SKIP_TESTS" == false ]]; then
            run_tests
        fi
    fi
    
    echo ""
    log_success "Setup completed successfully!"
    echo ""
    
    if [[ "$ENVIRONMENT" == "development" ]]; then
        echo "Next steps:"
        echo "1. Edit .env file with your configuration"
        echo "2. Run 'make docker-dev' to start all services"
        echo "3. Access the application at http://localhost:5173"
        echo ""
        echo "Useful commands:"
        echo "  make help           - Show all available commands"
        echo "  make health-check   - Check system health"
        echo "  make logs           - View application logs"
    else
        echo "Production setup complete. Please refer to SETUP.md for deployment instructions."
    fi
}

# Run main function
main "$@"