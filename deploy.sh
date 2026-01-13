#!/bin/bash

# Crypto Predict Monitor Deployment Script
# Supports staging and production deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="crypto-predict-monitor"
DOCKER_REGISTRY="your-registry.com"
VERSION=${VERSION:-$(git rev-parse --short HEAD)}
ENVIRONMENT=${1:-staging}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-deployment checks
pre_deploy_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi
    
    # Check if required environment variables are set
    local required_vars=("SECRET_KEY" "SUPABASE_URL" "SUPABASE_ANON_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check if git working directory is clean
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "Git working directory is not clean"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Pre-deployment checks passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Build main application
    docker build \
        -f Dockerfile.prod \
        -t "${DOCKER_REGISTRY}/${PROJECT_NAME}/app:${VERSION}" \
        -t "${DOCKER_REGISTRY}/${PROJECT_NAME}/app:latest" \
        .
    
    # Build dashboard
    docker build \
        -f Dockerfile.dashboard \
        -t "${DOCKER_REGISTRY}/${PROJECT_NAME}/dashboard:${VERSION}" \
        -t "${DOCKER_REGISTRY}/${PROJECT_NAME}/dashboard:latest" \
        --build-arg REACT_APP_API_URL="${API_URL:-http://localhost:8000}" \
        --build-arg REACT_APP_WS_URL="${WS_URL:-ws://localhost:8000}" \
        .
    
    log_success "Docker images built successfully"
}

# Push images to registry
push_images() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Pushing images to registry..."
        
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}/app:${VERSION}"
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}/app:latest"
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}/dashboard:${VERSION}"
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}/dashboard:latest"
        
        log_success "Images pushed to registry"
    else
        log_info "Skipping image push for staging environment"
    fi
}

# Deploy application
deploy_application() {
    log_info "Deploying to ${ENVIRONMENT} environment..."
    
    # Set environment-specific variables
    local compose_file="docker-compose.${ENVIRONMENT}.yml"
    if [[ ! -f "$compose_file" ]]; then
        compose_file="docker-compose.yml"
    fi
    
    # Export environment variables
    export VERSION ENVIRONMENT
    
    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose -f "$compose_file" down
    
    # Pull latest images (production only)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Pulling latest images..."
        docker-compose -f "$compose_file" pull
    fi
    
    # Start services
    log_info "Starting services..."
    docker-compose -f "$compose_file" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    wait_for_health
    
    log_success "Application deployed successfully"
}

# Wait for services to be healthy
wait_for_health() {
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts"
        
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_success "Main application is healthy"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Health check failed after $max_attempts attempts"
            exit 1
        fi
        
        sleep 10
        ((attempt++))
    done
}

# Run post-deployment tests
post_deploy_tests() {
    log_info "Running post-deployment tests..."
    
    # Test main endpoints
    local endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8000/api/pnl-card/health"
        "http://localhost:3000/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "$endpoint" > /dev/null 2>&1; then
            log_success "✓ $endpoint"
        else
            log_error "✗ $endpoint"
            exit 1
        fi
    done
    
    # Test database connection
    if docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        log_success "✓ Database connection"
    else
        log_error "✗ Database connection"
        exit 1
    fi
    
    # Test Redis connection
    if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
        log_success "✓ Redis connection"
    else
        log_error "✗ Redis connection"
        exit 1
    fi
    
    log_success "Post-deployment tests passed"
}

# Show deployment status
show_status() {
    log_info "Deployment status:"
    echo
    docker-compose ps
    echo
    
    log_info "Service URLs:"
    echo "  Main API:     http://localhost:8000"
    echo "  Dashboard:    http://localhost:3000"
    echo "  Grafana:      http://localhost:3001"
    echo "  Prometheus:   http://localhost:9090"
    echo
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker system prune -f
    log_success "Cleanup completed"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    local compose_file="docker-compose.${ENVIRONMENT}.yml"
    if [[ ! -f "$compose_file" ]]; then
        compose_file="docker-compose.yml"
    fi
    
    docker-compose -f "$compose_file" down
    # Here you would implement logic to deploy previous version
    log_warning "Rollback completed"
}

# Main deployment function
main() {
    log_info "Starting deployment to ${ENVIRONMENT} environment..."
    log_info "Version: $VERSION"
    
    # Check for help flag
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        echo "Usage: $0 [staging|production] [--rollback] [--cleanup]"
        echo
        echo "Options:"
        echo "  staging       Deploy to staging environment (default)"
        echo "  production    Deploy to production environment"
        echo "  --rollback    Rollback to previous version"
        echo "  --cleanup     Cleanup unused Docker resources"
        echo
        exit 0
    fi
    
    # Handle special flags
    if [[ "${2:-}" == "--rollback" ]]; then
        rollback
        exit 0
    fi
    
    if [[ "${2:-}" == "--cleanup" ]]; then
        cleanup
        exit 0
    fi
    
    # Run deployment pipeline
    pre_deploy_checks
    build_images
    push_images
    deploy_application
    post_deploy_tests
    show_status
    
    log_success "Deployment completed successfully! 🚀"
}

# Trap to handle interruptions
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"
