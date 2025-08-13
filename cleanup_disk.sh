#!/bin/bash

echo "🧹 Starting disk cleanup..."

# 1. Clean up Docker system
echo "📦 Cleaning Docker resources..."
sudo docker system prune -a -f --volumes
echo "✅ Docker cleanup complete"

# 2. Remove old Docker images
echo "🗑️ Removing unused Docker images..."
sudo docker image prune -a -f
echo "✅ Image cleanup complete"

# 3. Remove stopped containers
echo "🗑️ Removing stopped containers..."
sudo docker container prune -f
echo "✅ Container cleanup complete"

# 4. Remove unused volumes
echo "🗑️ Removing unused volumes..."
sudo docker volume prune -f
echo "✅ Volume cleanup complete"

# 5. Remove build cache
echo "🗑️ Removing Docker build cache..."
sudo docker builder prune -a -f
echo "✅ Build cache cleanup complete"

# 6. Check disk space after cleanup
echo "📊 Current disk usage:"
df -h

# 7. Show Docker disk usage
echo "📦 Docker disk usage:"
sudo docker system df

echo "✨ Cleanup complete!"