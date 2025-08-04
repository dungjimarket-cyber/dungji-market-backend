#!/bin/bash
# Force cleanup script for stuck Docker containers

echo "🧹 Starting aggressive Docker cleanup..."

# Stop all containers
echo "Stopping all containers..."
sudo docker stop $(sudo docker ps -aq) 2>/dev/null || true

# Kill all docker-proxy processes
echo "Killing docker-proxy processes..."
sudo pkill -9 -f docker-proxy || true

# Kill processes using port 8000
echo "Killing processes on port 8000..."
sudo fuser -k 8000/tcp || true
sudo lsof -ti:8000 | xargs -r sudo kill -9 || true

# Stop Docker service
echo "Stopping Docker service..."
sudo systemctl stop docker
sudo systemctl stop docker.socket

# Remove Docker runtime files
echo "Cleaning Docker runtime files..."
sudo rm -rf /var/run/docker/*
sudo rm -rf /var/lib/docker/containers/580c0a899188*

# Start Docker service
echo "Starting Docker service..."
sudo systemctl start docker.socket
sudo systemctl start docker

# Wait for Docker to be ready
echo "Waiting for Docker to be ready..."
sleep 10

# Verify Docker is working
echo "Verifying Docker..."
sudo docker ps

# Clean up all containers and networks
echo "Final cleanup..."
sudo docker container prune -f
sudo docker network prune -f
sudo docker system prune -f

echo "✅ Cleanup complete!"
echo "You can now run the deployment again."