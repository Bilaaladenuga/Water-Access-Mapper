#!/bin/bash
# Water Access Mapper — Project Setup Script
# Run this script to set up the development environment.

set -e  # Exit on error

echo "🗺️  Water Access Mapper — Setup"
echo "================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+."
    exit 1
fi

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.10+."
    exit 1
fi

echo "✅ Node.js $(node --version)"
echo "✅ Python $(python --version 2>&1 || python3 --version 2>&1)"

# Setup frontend
echo ""
echo "Setting up frontend (apps/web)..."
cd apps/web
npm install
cd ../..

# Setup backend
echo ""
echo "Setting up backend (apps/api)..."
cd apps/api
python -m venv venv 2>/dev/null || python3 -m venv venv

# Activate venv and install dependencies
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

pip install -r requirements.txt
cd ../..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start development:"
echo "  Frontend:  cd apps/web && npm run dev"
echo "  Backend:   cd apps/api && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
