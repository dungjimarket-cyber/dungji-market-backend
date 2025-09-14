#!/bin/bash

echo "Applying migration to rename amount to offered_price..."

# Check if Docker container is running
if docker ps | grep -q dungji-market-backend; then
    echo "Applying migration in Docker container..."
    docker exec dungji-market-backend python manage.py migrate used_phones 0018_rename_amount_to_offered_price
else
    echo "Docker container not running. Applying migration directly..."
    python manage.py migrate used_phones 0018_rename_amount_to_offered_price
fi

echo "Migration completed!"