#!/usr/bin/env bash
set -euo pipefail

echo "Starting OCR-VLM services..."

# Start FastAPI in the background
echo "Launching FastAPI server on port 8000..."
uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info &
UVICORN_PID=$!

# Cleanup function
cleanup() {
    echo "Shutting down services..."
    kill "${UVICORN_PID}" 2>/dev/null || true
    wait "${UVICORN_PID}" 2>/dev/null || true
    echo "Shutdown complete."
}

trap cleanup EXIT INT TERM

# Wait for API to be ready
echo "Waiting for API server to start..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "API server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "API server failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start Streamlit
echo "Launching Streamlit UI on port 8501..."
exec streamlit run main.py --server.port=8501 --server.address=0.0.0.0

