#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down dev servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${RED}✗ Backend stopped${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${RED}✗ Frontend stopped${NC}"
    fi
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}🚀 Starting College Counter Development Environment${NC}\n"

# Check if required directories exist
if [ ! -d "cc-backend/v1" ]; then
    echo -e "${RED}Error: cc-backend/v1 directory not found${NC}"
    exit 1
fi

if [ ! -d "cc-frontend/v1" ]; then
    echo -e "${RED}Error: cc-frontend/v1 directory not found${NC}"
    exit 1
fi

# Start Backend
echo -e "${YELLOW}📦 Starting Django Backend...${NC}"
cd cc-backend/v1
uv run python manage.py runserver 8000 > ../../backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 2

# Check if backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Backend running on http://localhost:8000 (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}✗ Backend failed to start. Check backend.log for details.${NC}"
    cat backend.log
    exit 1
fi

# Start Frontend
echo -e "${YELLOW}🎨 Starting Vite Frontend...${NC}"
cd cc-frontend/v1
npm run dev > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait a moment for frontend to start
sleep 2

# Check if frontend is running
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend running on http://localhost:5173 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ Frontend failed to start. Check frontend.log for details.${NC}"
    cat frontend.log
    cleanup
fi

echo -e "\n${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Development servers are running!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${YELLOW}Logs:${NC}     backend.log | frontend.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop all servers${NC}\n"

# Monitor processes and show combined logs
tail -f backend.log frontend.log 2>/dev/null &
TAIL_PID=$!

# Wait for processes
while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
    sleep 1
done

# If we get here, one of the processes died
echo -e "\n${RED}⚠️  One or more servers stopped unexpectedly${NC}"
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend is no longer running${NC}"
fi
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Frontend is no longer running${NC}"
fi

kill $TAIL_PID 2>/dev/null
cleanup
