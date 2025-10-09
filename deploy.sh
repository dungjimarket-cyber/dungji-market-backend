#!/bin/bash

# Dungji Market Backend Deployment Script

echo "Starting Dungji Market Backend deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.production to .env and configure it with your production values."
    exit 1
fi

# Check required environment variables
required_vars=(
    "SECRET_KEY"
    "DJANGO_ALLOWED_HOSTS"
    "DB_NAME"
    "DB_USER"
    "DB_PASSWORD"
    "DB_HOST"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo "Error: ${var} not set in .env file!"
        exit 1
    fi
done

# Ensure DJANGO_ENV is set to production
if ! grep -q "^DJANGO_ENV=production" .env; then
    echo "Warning: DJANGO_ENV is not set to 'production' in .env file!"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Build and start containers
echo "Building and starting containers..."
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
echo "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Run migrations (fake used_electronics migrations first, then migrate other apps)
echo "🔄 Running database migrations..."
echo "🔧 Faking used_electronics migrations (already applied in DB)..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate used_electronics 0007 --fake || echo "0007 fake done"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate used_electronics 0008 --fake || echo "0008 fake done"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate used_electronics 0009 --fake || echo "0009 fake done"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate used_electronics 0010 --fake || echo "0010 fake done"

echo "Running migrations for other apps..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate admin
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate api
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate auth
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate authtoken
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate contenttypes
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate sessions
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate used_phones

# Collect static files
echo "Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# Show logs
echo "Deployment complete! Showing logs..."
docker-compose -f docker-compose.prod.yml logs --tail=50

echo ""
echo "To view logs in real-time, run:"
echo "docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To restart services, run:"
echo "docker-compose -f docker-compose.prod.yml restart"