#!/bin/bash

# Oneo CRM Full Development Environment Startup Script
# This script starts both backend and frontend in parallel

set -e  # Exit on any error

echo "🚀 Starting Oneo CRM Full Development Environment..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down development environment..."
    
    # Kill backend processes
    echo "🧹 Stopping backend processes..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    
    # Kill frontend processes  
    echo "🧹 Stopping frontend processes..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Development environment stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Make scripts executable
chmod +x "$SCRIPT_DIR/start-backend.sh"
chmod +x "$SCRIPT_DIR/start-frontend.sh"

echo "📱 Starting backend in background..."
"$SCRIPT_DIR/start-backend.sh" &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 5

echo "🌐 Starting frontend in background..."
"$SCRIPT_DIR/start-frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "🎉 Development environment is starting up!"
echo ""
echo "📡 Available endpoints:"
echo "   🔧 Backend API: http://localhost:8000/api/v1/docs/"
echo "   🌐 Frontend: http://localhost:3000"
echo "   🏢 Tenants: http://{tenant}.localhost:3000"
echo ""
echo "📋 Useful commands:"
echo "   • View backend logs: tail -f backend/logs/django.log"
echo "   • View processes: ps aux | grep -E '(python|node)'"
echo "   • Stop everything: Press Ctrl+C"
echo ""
echo "✨ Both servers are running! Press Ctrl+C to stop everything."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID