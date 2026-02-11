#!/usr/bin/env bash
# Exit on error
set -e
set -x

echo "Python version:"
python --version

echo "Pip version:"
pip --version

echo "Content of requirements.txt:"
cat requirements.txt

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installing Playwright browsers..."
playwright install chromium

# Explicitly try installing openai if it's missing
if ! python -c "import openai" &> /dev/null; then
    echo "OpenAI not found after requirements install. Attempting explicit install..."
    pip install openai
fi

echo "Verifying installed packages..."
pip list

echo "Verifying openai import..."
python -c "import openai; print('openai imported successfully')"

echo "Skipping migrations during build to prevent Max Connection errors..."
# python migrate.py

echo "Build complete!"
