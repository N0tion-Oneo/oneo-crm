#!/bin/bash

# Oneo CRM Frontend Startup Script
# This script starts the Next.js frontend development server

set -e  # Exit on any error

echo "🚀 Starting Oneo CRM Frontend..."

# Change to frontend directory
cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ package.json not found! Make sure you're in the frontend directory."
    exit 1
fi

# Kill any existing Next.js server on port 3000
echo "🧹 Cleaning up any existing Next.js processes..."
lsof -ti :3000 | xargs kill -9 2>/dev/null || true

# Check if backend is running
echo "🔍 Checking if backend is available..."
if ! curl -s http://localhost:8000/api/v1/docs/ > /dev/null 2>&1; then
    echo "⚠️  Backend is not running on http://localhost:8000"
    echo "💡 Please start the backend first using: ./start-backend.sh"
    echo "   or run both with: ./start-dev.sh"
    echo ""
    echo "🤔 Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start the Next.js development server
echo "🌟 Starting Next.js development server..."
echo "📡 Frontend will be available at:"
echo "   • Main: http://localhost:3000"
echo "   • Tenants: http://{tenant}.localhost:3000"
echo ""
echo "✨ Frontend is ready! Press Ctrl+C to stop."

npm run dev