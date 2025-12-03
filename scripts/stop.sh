#!/bin/bash

# Stop Quorum Development Services

echo "🛑 Stopping Quorum backend services..."

docker-compose -f docker/development/docker-compose.yml down

echo "✅ Backend services stopped!"
echo ""
echo "Note: If the frontend is running, stop it with Ctrl+C in that terminal"
