#!/usr/bin/env bash

ANALYSIS_DIR="/pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis"
NEARLINE_DIR="/pscratch/sd/e/esabater/2x2_lifetime/arcube_nearline"

# load python on NERSC
module load python

VENV_DIR=".venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip

# Install required packages
if [[ -f "requirements.txt" ]]; then
    python -m pip install -r requirements.txt
else
    echo "Error: requirements.txt not found!"
    return 1
fi