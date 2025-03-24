#!/bin/bash
set -e

# Activate the virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Run the application
python app.py