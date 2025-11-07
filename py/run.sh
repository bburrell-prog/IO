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
read -p "Enter choice (1 or 2): " choice

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
    *)
        echo "Invalid choice. Please run again and select 1 or 2."
        exit 1
        ;;
esac
