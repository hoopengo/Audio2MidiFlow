#!/bin/bash

# Audio2MidiFlow Setup Script
# This script sets up the development environment for both backend and frontend

set -e  # Exit on any error

echo "🎵 Audio2MidiFlow Setup Script"
echo "=================================="

# Check if Python is installed
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is not installed."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup Backend
echo ""
echo "📦 Setting up Backend..."
echo "------------------------"

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3.12 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Backend setup complete"

# Setup Frontend
echo ""
echo "🌐 Setting up Frontend..."
echo "------------------------"

cd ../frontend

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

echo "✅ Frontend setup complete"

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
echo "-----------------------------------"

cd ..

# Create directories for uploads, outputs, and data
mkdir -p backend/uploads
mkdir -p backend/outputs
mkdir -p backend/data

echo "✅ Directories created"

# Create environment files
echo ""
echo "⚙️ Creating environment files..."
echo "-----------------------------------"

# Backend environment file
if [ ! -f "backend/.env" ]; then
    cat > backend/.env << EOF
# Backend Configuration
DEBUG=true
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/audio2midi.db
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
MAX_FILE_SIZE=52428800
CORS_ORIGINS=["http://localhost:3000"]
EOF
    echo "✅ Created backend/.env"
fi

# Frontend environment file
if [ ! -f "frontend/.env.local" ]; then
    cat > frontend/.env.local << EOF
# Frontend Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
EOF
    echo "✅ Created frontend/.env.local"
fi

echo ""
echo "🎉 Setup Complete!"
echo "==================="
echo ""
echo "To start the development servers:"
echo ""
echo "1. Backend (Terminal 1):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.main"
echo ""
echo "2. Frontend (Terminal 2):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "Or use Docker:"
echo "   docker-compose up --build"
echo ""
echo "📖 Documentation: http://localhost:8000/docs (after starting backend)"
echo "🌐 Frontend: http://localhost:3000 (after starting frontend)"
echo ""
echo "🚀 Happy coding!"