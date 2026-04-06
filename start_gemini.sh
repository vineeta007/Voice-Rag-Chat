#!/bin/bash

# Multilingual Voice RAG System - Robust Startup Script
# Handles process cleanup, environment verification, and graceful shutdown

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🎓 Voice RAG System - Gemini + Qdrant Cloud          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Cleanup Function
cleanup() {
    echo ""
    echo "ℹ️  Stopping all services..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    echo "✅ Backend and Frontend stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# 2. Process Cleanup (Kill anything on ports 8000 and 5173)
echo "ℹ️  Cleaning up previous processes..."
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
lsof -ti:8000,5173 | xargs kill -9 2>/dev/null || true
echo "✅ Old processes cleared."

# 3. Environment Verification
echo "ℹ️  Verifying environment..."

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install it with 'brew install node'."
    exit 1
fi

# Check Python Venv
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment 'venv' not found!"
    exit 1
fi

echo "✅ Environment verified."

# 4. Start Backend
echo "ℹ️  Starting Backend API..."
mkdir -p logs
source venv/bin/activate
# Use PYTHONPATH=$PWD to ensure local modules are found
PYTHONPATH=$PWD python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend
echo -n "ℹ️  Waiting for backend to initialize"
MAX_RETRIES=20
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "\n✅ Backend started (PID: $BACKEND_PID)"
        BACKEND_READY=true
        break
    fi
    echo -n "."
    sleep 1
    COUNT=$((COUNT + 1))
done

if [ "$BACKEND_READY" != true ]; then
    echo -e "\n❌ Backend failed to start. Check logs/backend.log"
    tail -n 20 logs/backend.log
    exit 1
fi

# 5. Start Frontend
echo "ℹ️  Starting Frontend..."
cd frontend
# Fix for "bad interpreter" by using npx directly
npx vite --port 5173 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend
sleep 2
if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
else
    echo "❌ Frontend failed to start. Check logs/frontend.log"
    tail -n 20 logs/frontend.log
    exit 1
fi

echo ""
echo "🚀 SYSTEM READY!"
echo "--------------------------------------------------------------"
echo "🌐 Frontend: http://localhost:5173"
echo "📡 Backend:  http://localhost:8000"
echo "--------------------------------------------------------------"
echo "ℹ️  Press Ctrl+C to stop all services."
echo ""

# Keep script running to maintain PIDs
wait
