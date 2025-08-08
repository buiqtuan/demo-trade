#!/bin/bash

echo "Stopping all services..."

# Kill uvicorn processes more safely
pkill -f "uvicorn.*app.main:app"
pkill -f "uvicorn.*main:app"

# Alternative: kill by port if needed
# lsof -ti:8000 | xargs kill -9 2>/dev/null
# lsof -ti:8001 | xargs kill -9 2>/dev/null

echo "Services stopped."