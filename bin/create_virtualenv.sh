#!/bin/bash
# Machine Health & Diagnostics VirtualEnv bootstrap script
# Use this script to create a virtual environment which contains
# all the dependencies for the project

# Safety mechanism: 
# -e: Stop the script if any of the command fails in the script.
# -u: Stop the script if unset variables are accessed
# -o pipefail: Fail any of the command in a pipeline is failed.
set -euo pipefail

# Install location
VENV_LOCATION="venv-huba-pypy-2.6.1"

# Required Python version
REQD_PYTHON="pypy-2.6.1"

# Check if virtual env already exists
if [ -d ${VENV_LOCATION} ]; then
    echo "Virtual environment directory (${VENV_LOCATION}) already exists!"
    exit 1
fi

# Create a new virtual env directory
virtualenv --python=${REQD_PYTHON} ${VENV_LOCATION}

# Workaround venv's unbound ps1 bug
set +o nounset

# Install the required packages into virtual env
source ${VENV_LOCATION}/bin/activate
pip install -r requirements-pypy.txt
