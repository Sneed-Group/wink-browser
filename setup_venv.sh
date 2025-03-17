#!/bin/bash
# Script to set up virtual environment and install dependencies

# Stop on any error
set -e

# Create the virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  echo "Virtual environment created."
else
  echo "Using existing virtual environment."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Run our test script to verify the network implementation
echo "Running test script..."
python test_network.py

echo "Done!"

# You can uncomment the line below to keep the environment active
# echo "Virtual environment is active. Use 'deactivate' when finished."

# Deactivate the virtual environment
deactivate

echo "Virtual environment deactivated. You can activate it again with 'source venv/bin/activate'" 