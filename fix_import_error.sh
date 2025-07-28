#\!/bin/bash

# Fix the import error in the Docker container
echo "Fixing import error in api/utils/__init__.py..."

# Check current import statement
echo "Current import:"
sudo docker exec d8 grep -n "from api.models_bid" /app/api/utils/__init__.py || echo "Pattern not found"

# Fix the import
sudo docker exec d8 sed -i 's/from api.models_bid import Bid/from api.models import Bid/g' /app/api/utils/__init__.py

# Verify the fix
echo -e "\nAfter fix:"
sudo docker exec d8 grep -n "from api.models import Bid" /app/api/utils/__init__.py

# Restart the container
echo -e "\nRestarting container..."
sudo docker restart d8

# Wait and check logs
echo -e "\nWaiting for container to start..."
sleep 5
echo -e "\nChecking logs:"
sudo docker logs --tail 20 d8
