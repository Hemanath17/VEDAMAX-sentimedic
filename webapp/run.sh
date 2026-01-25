#!/bin/bash

# Run V.E.D.A.M.A.X. Web Application

echo "🩺 Starting V.E.D.A.M.A.X. Web Application..."
echo ""

# Activate virtual environment if it exists
if [ -d "../medic_env" ]; then
    echo "Activating virtual environment..."
    source ../medic_env/bin/activate
fi

# Install webapp dependencies if needed
if [ ! -f ".deps_installed" ]; then
    echo "Installing webapp dependencies..."
    pip install -r requirements.txt
    touch .deps_installed
fi

# Run Streamlit app
echo "Launching Streamlit application..."
streamlit run app.py --server.port 8501 --server.address localhost

