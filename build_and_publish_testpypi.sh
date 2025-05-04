#!/bin/bash
set -e

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

# Upload to TestPyPI
echo "Uploading to TestPyPI..."
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

echo "Done! If you see no errors above, your package is live on TestPyPI."
echo "To install from TestPyPI, use:"
echo "  pip install --index-url https://test.pypi.org/simple/ mcp-db"
echo "(You may need to use a separate TestPyPI account/credentials.)" 