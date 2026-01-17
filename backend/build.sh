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
pip install -v -r requirements.txt

# Explicitly try installing openai if it's missing
if ! python -c "import openai" &> /dev/null; then
    echo "OpenAI not found after requirements install. Attempting explicit install..."
    pip install openai
fi

echo "Verifying installed packages..."
pip list

echo "Verifying openai import..."
python -c "import openai; print('openai imported successfully')"

echo "Running database migrations..."
python migrate.py

echo "Build complete!"
