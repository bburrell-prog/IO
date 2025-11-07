#!/bin/bash
# Setup script for Desktop Screen Analyzer on macOS

echo "=== Desktop Screen Analyzer Setup ==="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if Tesseract is installed
if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract OCR is not installed."
    echo "   Install it with: brew install tesseract"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Tesseract OCR found: $(tesseract --version | head -n 1)"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo ""
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create .env file
echo ""
if [ -f ".env" ]; then
    echo "✅ .env file already exists"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: You must edit .env and add your OpenAI API key!"
        echo "   Run: nano .env"
    else
        echo "❌ .env.example not found"
    fi
fi

# Create necessary directories
mkdir -p screenshots reports logs
echo "✅ Created necessary directories"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OpenAI API key:"
echo "   nano .env"
echo ""
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python3 main.py --once"
echo ""
echo "For interactive mode (requires sudo on macOS):"
echo "   sudo ./venv/bin/python3 main.py"
echo ""
echo "See README.md for more information."
