#!/bin/bash
# Quick start script - Run this after setup.sh

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Desktop Screen Analyzer - Quick Start ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first:"
    echo "   ./setup.sh"
    exit 1
fi

# Check if .env exists and has API key
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Run setup.sh first:"
    echo "   ./setup.sh"
    exit 1
fi

if grep -q "sk-your-api-key-here" .env; then
    echo "❌ OpenAI API key not configured!"
    echo "   Edit .env and add your API key:"
    echo "   nano .env"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo -e "${GREEN}✅ Environment ready${NC}"
echo ""
echo "Choose how to run:"
echo ""
echo "1. Single analysis (recommended for macOS - no sudo needed)"
echo "   python3 main.py --once"
echo ""
echo "2. Interactive mode (requires sudo on macOS)"
echo "   sudo ./venv/bin/python3 main.py"
echo ""
echo "3. Analysis + Data Viewer (shows results automatically)"
echo "   python3 main.py --once && python3 main.py --viewer"
echo ""
read -p "Enter choice (1, 2, or 3): " choice

case $choice in
    1)
        echo ""
        echo "Running single analysis..."
        python3 main.py --once
        ;;
    2)
        echo ""
        echo -e "${YELLOW}⚠️  Interactive mode requires sudo on macOS${NC}"
        echo "Press F9 to analyze screen, ESC to exit"
        sudo ./venv/bin/python3 main.py
        ;;
    3)
        echo ""
        echo "Running analysis with data viewer..."
        python3 main.py --once
        
        echo ""
        echo -e "${GREEN}📊 Launching data viewer...${NC}"
        python3 main.py --viewer &
        VIEWER_PID=$!
        
        # Wait a moment for the server to start
        sleep 2
        
        echo ""
        echo -e "${GREEN}📈 Analysis Results:${NC}"
        echo "=========================================="
        
        # Get and display the stats
        if command -v jq &> /dev/null; then
            curl -s "http://localhost:5000/api/stats" | jq .total_cycles
        else
            curl -s "http://localhost:5000/api/stats" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Total Cycles: {data.get(\"total_cycles\", \"N/A\")}')
except:
    print('Could not parse API response')
"
        fi
        
        echo ""
        echo -e "${YELLOW}🌐 Data viewer running at: http://localhost:5000${NC}"
        echo "Press Ctrl+C to stop the viewer"
        
        # Wait for the viewer process
        wait $VIEWER_PID
        ;;
    *)
        echo "Invalid choice. Please run again and select 1, 2, or 3."
        exit 1
        ;;
esac
