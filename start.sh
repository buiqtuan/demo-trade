#!/bin/bash

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Add shared_models to Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Start market data aggregator
echo "Starting Market Data Aggregator on port 8001..."
cd "$SCRIPT_DIR/market_data_aggregator" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
MARKET_DATA_PID=$!

# Wait a moment for market data to start
sleep 2

# Start backend
echo "Starting Backend on port 8000..."
cd "$SCRIPT_DIR/backend" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Services started successfully!"
echo "Market Data Aggregator: http://localhost:8001"
echo "Backend API: http://localhost:8000"
echo "Press Ctrl+C to stop all services."

# Function to cleanup processes
cleanup() {
    echo "Stopping services..."
    kill $MARKET_DATA_PID $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for background processes
wait