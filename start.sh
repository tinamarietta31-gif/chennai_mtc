#!/bin/bash

# AI-Powered Smart Public Transport Optimization System
# Startup Script

echo "🚌 Chennai MTC Smart Transport System"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9+${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed. Please install Node.js 18+${NC}"
    exit 1
fi

# Function to start backend
start_backend() {
    echo -e "${YELLOW}Starting Backend Server...${NC}"
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -r requirements.txt -q
    
    # Start server
    echo -e "${GREEN}Backend starting at http://localhost:8000${NC}"
    python app.py &
    BACKEND_PID=$!
    cd ..
}

# Function to start frontend
start_frontend() {
    echo -e "${YELLOW}Starting Frontend Server...${NC}"
    cd frontend
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi
    
    # Start React development server
    echo -e "${GREEN}Frontend starting at http://localhost:3000${NC}"
    npm start &
    FRONTEND_PID=$!
    cd ..
}

# Trap to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main execution
echo ""
echo "Starting services..."
echo ""

start_backend
sleep 3
start_frontend

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "📡 Backend API: http://localhost:8000"
echo "🌐 Frontend App: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
