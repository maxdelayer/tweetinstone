#!/bin/bash

# TODO
# Ensure pip is installed and venv is installed
#sudo apt install python3-pip

# Create a virtual environment to install dependencies
python3 -m venv .venv --prompt="tis"

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Download browsers & relevant OS dependencies
playwright install --with-deps

# Exit the virtual environment
deactivate