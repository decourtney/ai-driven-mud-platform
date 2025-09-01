#!/bin/bash
# start.sh - Start both model service and API server for development

set -e  # Exit on error

echo "🚀 Starting D&D Game Services"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MODEL_SERVER_PORT=8001
API_SERVER_PORT=8000
LOAD_MODELS_AT_STARTUP=true

echo -e "${BLUE}Configuration:${NC}"
echo "  Model Service: http://localhost:$MODEL_SERVER_PORT"
echo "  API Server: http://localhost:$API_SERVER_PORT"
echo "  Load models at startup: $LOAD_MODELS_AT_STARTUP"
echo ""

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ ! -z "$MODEL_PID" ]; then
        kill $MODEL_PID 2>/dev/null || true
        echo "  ✓ Model service stopped"
    fi
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        echo "  ✓ API server stopped"
    fi
    exit 0
}

# Trap cleanup on script exit
trap cleanup EXIT INT TERM

# Start model service
echo -e "${BLUE}1. Starting Model Service...${NC}"
if [ "$LOAD_MODELS_AT_STARTUP" = true ]; then
    python -m backend.services.ai_models.model_server --host 0.0.0.0 --port $MODEL_SERVER_PORT --load-models &
else
    python -m backend.services.ai_models.model_server --host 0.0.0.0 --port $MODEL_SERVER_PORT &
fi
MODEL_PID=$!

# Wait up to 30 seconds for model service to start
echo "  Waiting for model service to start..."
MAX_WAIT=30
SLEEP_INTERVAL=1
WAITED=0

until curl -s http://localhost:$MODEL_SERVER_PORT/health > /dev/null; do
    sleep $SLEEP_INTERVAL
    WAITED=$((WAITED + SLEEP_INTERVAL))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo -e "${RED}❌ Model service failed to start within ${MAX_WAIT}s${NC}"
        kill $MODEL_PID
        exit 1
    fi
done

echo -e "${GREEN}✅ Model service is ready!${NC}"

# Start API server
echo -e "${BLUE}2. Starting API Server...${NC}"
export MODEL_SERVER_URL="http://localhost:$MODEL_SERVER_PORT"
export WAIT_FOR_MODELS="true"
export AUTO_LOAD_MODELS="false"  # Models already loaded by model service
export DEV_MODE="true"

python -m backend.services.api.main &
API_PID=$!

echo "  Waiting for API server to start..."
MAX_WAIT=30
SLEEP_INTERVAL=1
WAITED=0

until curl -s http://localhost:$API_SERVER_PORT/health > /dev/null; do
    sleep $SLEEP_INTERVAL
    WAITED=$((WAITED + SLEEP_INTERVAL))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo -e "${RED}❌ API server failed to start within ${MAX_WAIT}s${NC}"
        kill $API_PID
        exit 1
    fi
done

echo -e "${GREEN}✓ API server ready${NC}"

echo ""
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo ""
echo "Available endpoints:"
echo "  📊 API Health: http://localhost:$API_SERVER_PORT/health"
echo "  📚 API Docs: http://localhost:$API_SERVER_PORT/docs"
echo "  🤖 Model Health: http://localhost:$MODEL_SERVER_PORT/health"
echo "  🎮 Games List: http://localhost:$API_SERVER_PORT/games"
echo ""
echo -e "${YELLOW}Development endpoints:${NC}"
echo "  🔧 Model Status: http://localhost:$API_SERVER_PORT/dev/model-status"
echo "  ⚡ Load Models: curl -X POST http://localhost:$API_SERVER_PORT/dev/load-models"
echo "  🧪 Test Parse: http://localhost:$API_SERVER_PORT/dev/test-parse?text=attack%20goblin"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Keep script running
wait