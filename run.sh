#!/bin/bash

# Edison Startup Script
# This script starts the FastAPI application

echo "🔆 Starting Edison - ChatGPT Interface..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if requirements are installed
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Starting server on http://localhost:8000"
echo "📝 Press Ctrl+C to stop the server"
echo ""

# Start the application
python3 main.py
