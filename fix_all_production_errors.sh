#!/bin/bash

echo "=== Production Fix Script ==="
echo "This script fixes all known production errors"
echo ""

# Fix 1: Replace created_at with start_time in views.py
echo "1. Fixing created_at -> start_time in views.py..."
sudo docker exec d8 sed -i "s/order_by('-created_at')/order_by('-start_time')/g" /app/api/views.py
sudo docker exec d8 sed -i "s/order_by('-current_participants', '-created_at')/order_by('-current_participants', '-start_time')/g" /app/api/views.py

# Fix 2: Fix import errors for models_bid
echo "2. Fixing import from models_bid -> models..."
sudo docker exec d8 sed -i "s/from api.models_bid import/from api.models import/g" /app/api/utils/__init__.py
sudo docker exec d8 sed -i "s/from \.\.models_bid import/from ..models import/g" /app/api/utils/__init__.py
sudo docker exec d8 sed -i "s/from \.models_bid import/from .models import/g" /app/api/serializers.py

# Verify fixes
echo ""
echo "=== Verifying Fixes ==="
echo "1. Checking views.py for start_time:"
sudo docker exec d8 grep -n "order_by.*start_time" /app/api/views.py | head -5

echo ""
echo "2. Checking imports in utils/__init__.py:"
sudo docker exec d8 grep -n "from.*models import Bid" /app/api/utils/__init__.py | head -5

echo ""
echo "3. Checking imports in serializers.py:"
sudo docker exec d8 grep -n "from.*models import Bid" /app/api/serializers.py | head -5

# Restart container
echo ""
echo "=== Restarting Container ==="
sudo docker restart d8

# Wait for container to start
echo "Waiting for container to start..."
sleep 10

# Check final status
echo ""
echo "=== Final Status Check ==="
echo "Container status:"
sudo docker ps | grep d8

echo ""
echo "Recent logs:"
sudo docker logs --tail 30 d8

echo ""
echo "=== Fix script completed ==="
echo "If errors persist, check the logs above."