#!/usr/bin/env bash
# scripts/dev/setup_bt_sdk.sh
# Battle-tested Bittensor SDK installation for Mac (M-series) & Linux
set -euo pipefail

echo "🚀 Setting up Bittensor SDK environment..."

# Detect Python version - prefer 3.10.x
if command -v python3.10 &> /dev/null; then
    PY=python3.10
elif command -v python3.11 &> /dev/null; then
    PY=python3.11
    echo "⚠️  Using Python 3.11 (3.10.14 preferred for best compatibility)"
else
    echo "❌ Python 3.10 or 3.11 not found. Please install Python 3.10.14"
    exit 1
fi

echo "📦 Using Python: $($PY --version)"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    $PY -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and install build tools
echo "📦 Upgrading pip and build tools..."
pip install -U pip wheel setuptools

# Step 1: Install grpc wheels first (prevents compile failures)
echo "🔧 Installing grpcio wheels..."
pip install "grpcio>=1.73.0" "grpcio-tools>=1.73.0"

# Step 2: Install all other dependencies
echo "📦 Installing project dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Bittensor SDK setup complete!"
echo ""
echo "🔧 To activate the environment:"
echo "   source .venv/bin/activate"
echo ""
echo "🧪 To test the installation:"
echo "   python -m scripts.data_sources.sdk_smoketest"
echo "" 