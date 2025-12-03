#!/bin/bash

# Quorum Development Quick Start Script
# This script starts backend services in Docker and the frontend locally

set -e

echo "🚀 Starting Quorum Development Environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start backend services in Docker
echo "📦 Starting backend services (Docker)..."
docker-compose -f docker/development/docker-compose.yml up -d

echo ""
echo "⏳ Waiting for backend to be ready..."
sleep 3

# Check if backend is healthy
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    echo "   Waiting for backend..."
    sleep 2
done

echo "✅ Backend services are running!"
echo ""
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Redis:        localhost:6379"
echo ""
echo "🎨 Starting frontend (local)..."
echo ""

# Change to frontend directory and start dev server
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
    echo ""
fi

echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the frontend (backend will keep running)"
echo "To stop backend: docker-compose -f docker/development/docker-compose.yml down"
echo ""

# Start frontend dev server
npm run dev
