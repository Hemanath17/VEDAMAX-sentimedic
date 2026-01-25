#!/bin/bash

# Setup script for SentiMedical-RAG development environment

set -e

echo "Setting up SentiMedical-RAG development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d "medic_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv medic_env
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source medic_env/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    echo "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/raw/pdfs
mkdir -p data/raw/docx
mkdir -p data/processed/chunks
mkdir -p data/embeddings
mkdir -p data/evaluation
mkdir -p models/embeddings
mkdir -p models/sentiment
mkdir -p models/ner
mkdir -p logs

# Copy .env.example to .env if .env doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        echo "Please edit .env and configure your API keys and settings."
    else
        echo "Warning: .env.example not found. Please create .env manually."
    fi
else
    echo ".env file already exists."
fi

# Download spaCy model (if needed)
echo "Downloading spaCy model..."
python -m spacy download en_core_web_sm || echo "Warning: Could not download spaCy model"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source medic_env/bin/activate"
echo "2. Edit .env file with your API keys and configuration"
echo "3. Start services: docker-compose up -d"
echo "4. Run the API: uvicorn src.api.main:app --reload"
echo ""

