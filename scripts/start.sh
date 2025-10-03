#!/bin/bash

# Crypto Signal System Startup Script

set -e

echo "🚀 Starting Crypto Signal System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN is required in .env file"
    exit 1
fi

echo "✅ Environment variables loaded"

# Create necessary directories
mkdir -p screenshots logs

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker detected, starting with Docker Compose..."
    
    # Start databases first
    echo "📊 Starting databases..."
    docker-compose up -d clickhouse redis postgres
    
    # Wait for databases to be ready
    echo "⏳ Waiting for databases to be ready..."
    sleep 30
    
    # Start main application
    echo "🤖 Starting crypto signal system..."
    docker-compose up -d crypto-signals
    
    # Show status
    echo "📋 Container status:"
    docker-compose ps
    
    # Show logs
    echo "📝 Recent logs:"
    docker-compose logs --tail=50 crypto-signals
    
    echo "✅ System started successfully!"
    echo "📊 Grafana dashboard: http://localhost:3000 (admin/admin123)"
    echo "📈 Prometheus metrics: http://localhost:9090"
    echo "🔍 ClickHouse: http://localhost:8123"
    
else
    echo "🐍 Docker not available, starting locally..."
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    required_version="3.11"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo "❌ Python 3.11+ is required. Current version: $python_version"
        exit 1
    fi
    
    # Install dependencies if needed
    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    
    # Install Playwright browsers
    echo "🎭 Installing Playwright browsers..."
    playwright install chromium
    
    # Start the application
    echo "🚀 Starting application..."
    python main.py
fi