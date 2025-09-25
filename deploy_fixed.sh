#!/bin/bash

# Enhanced Dungji Market Backend Deployment Script with Docker Hub fixes

set -e  # Exit on any error

echo "🚀 Starting enhanced deployment process..."

# Function to retry Docker operations
retry_docker_operation() {
    local max_attempts=3
    local delay=10
    local attempt=1
    local command="$1"

    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Attempt $attempt/$max_attempts: $command"
        if eval "$command"; then
            echo "✅ Command succeeded on attempt $attempt"
            return 0
        else
            if [ $attempt -lt $max_attempts ]; then
                echo "❌ Command failed on attempt $attempt. Retrying in ${delay}s..."
                sleep $delay
                delay=$((delay * 2))  # Exponential backoff
            else
                echo "❌ Command failed after $max_attempts attempts"
                return 1
            fi
        fi
        attempt=$((attempt + 1))
    done
}

# Function to clean up Docker resources
cleanup_docker() {
    echo "🧹 Cleaning up Docker resources..."

    # Stop all containers using port 8000
    if lsof -i :8000 >/dev/null 2>&1; then
        echo "🛑 Stopping processes using port 8000..."
        lsof -ti:8000 | xargs -r kill -9 || true
        sleep 5
    fi

    # Stop all running containers
    if [ "$(docker ps -q)" ]; then
        echo "Stopping running containers..."
        docker stop $(docker ps -q) || true
    fi

    # Remove stopped containers
    echo "Removing stopped containers..."
    docker container prune -f || true

    # Remove unused images (but keep some cache)
    echo "Removing unused images..."
    docker image prune -f || true

    # Clean build cache if disk space is low
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 5000000 ]; then  # Less than 5GB
        echo "Low disk space detected. Cleaning build cache..."
        docker builder prune -f || true
    fi
}

# Function to fix Docker Hub authentication
fix_docker_auth() {
    echo "🔧 Attempting to fix Docker Hub authentication..."

    # Try to login to Docker Hub (will use default credentials or prompt)
    if ! docker info > /dev/null 2>&1; then
        echo "Docker daemon not responding properly"
        return 1
    fi

    # Clear any existing auth issues
    docker logout docker.io || true

    # Try to pull a small test image to check connectivity
    echo "Testing Docker Hub connectivity..."
    if ! retry_docker_operation "docker pull hello-world:latest"; then
        echo "❌ Cannot connect to Docker Hub. Trying alternative registry..."
        return 1
    fi

    echo "✅ Docker Hub connectivity verified"
    return 0
}

# Main deployment function
main() {
    cd ~/dungji-market-backend || {
        echo "❌ Cannot change to backend directory"
        exit 1
    }

    echo "📍 Working directory: $(pwd)"

    # Clean up first
    cleanup_docker

    # Fix Docker authentication
    if ! fix_docker_auth; then
        echo "⚠️  Docker Hub authentication issues detected"
        echo "Continuing with deployment using cached images if available..."
    fi

    # Check disk space
    echo "💾 Checking disk usage..."
    df -h /

    # Build and start with retries
    echo "🏗️  Building and starting containers..."

    # Set Docker Compose project name to avoid conflicts
    export COMPOSE_PROJECT_NAME="dungji-backend"

    # Try building with no cache first if authentication is working
    if retry_docker_operation "docker-compose up --build -d"; then
        echo "✅ Containers built and started successfully"
    else
        echo "❌ Build failed with --build. Trying without rebuild..."
        if retry_docker_operation "docker-compose up -d"; then
            echo "✅ Containers started with existing images"
        else
            echo "❌ Failed to start containers"
            echo "📋 Showing container status for debugging:"
            docker-compose ps || true
            docker-compose logs --tail=50 || true
            exit 1
        fi
    fi

    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 15

    # Check service status
    echo "🔍 Checking service status..."
    docker-compose ps

    # Run migrations with retry
    echo "📊 Running database migrations..."
    if ! retry_docker_operation "docker-compose exec -T web python manage.py migrate"; then
        echo "❌ Migration failed. Checking logs..."
        docker-compose logs web --tail=20
        # Don't exit - migrations might already be up to date
    fi

    # Collect static files
    echo "📦 Collecting static files..."
    retry_docker_operation "docker-compose exec -T web python manage.py collectstatic --noinput" || echo "⚠️  Static file collection failed but continuing..."

    # Final status check
    echo "🔍 Final status check..."
    docker-compose ps

    # Show recent logs
    echo "📜 Recent logs:"
    docker-compose logs --tail=30

    echo "🎉 Deployment process completed!"
    echo ""
    echo "📝 Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Restart:   docker-compose restart"
    echo "  Stop:      docker-compose down"
    echo "  Shell:     docker-compose exec web bash"
}

# Run main function
main "$@"