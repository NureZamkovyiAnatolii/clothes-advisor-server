#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt
echo "Installation completed."

read -p "Press any key to continue..."
