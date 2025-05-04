#!/bin/bash
set -e
source ./venv/bin/activate
pip install -r requirements.txt

# Clean previous builds
echo "Cleaning old builds..."
rm -rf dist build mcp_db.egg-info

# Ensure build and twine are installed
pip install --upgrade build twine

# Build the package
echo "Building the package..."
python -m build

# Check the package
echo "Checking the package with twine..."
twine check dist/*

# Upload to PyPI
echo "Uploading to PyPI..."
twine upload dist/*

echo "Done! If you see no errors above, your package is live on PyPI." 