#!/bin/bash

# Stop All Services Script (Gemini Version)

echo ""
echo "🛑 Stopping Voice RAG services..."
echo ""

# Stop Frontend
if lsof -ti:5173 >/dev/null 2>&1; then
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    echo "✅ Frontend stopped"
else
    echo "✅ Frontend not running"
fi

# Stop Backend
if lsof -ti:8000 >/dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo "✅ Backend stopped"
else
    echo "✅ Backend not running"
fi

# Cleanup
pkill -f "vite" 2>/dev/null

echo ""
echo "✅ All services stopped!"
echo "ℹ️  Using Gemini API (cloud-based) - no local AI server needed"
echo ""
