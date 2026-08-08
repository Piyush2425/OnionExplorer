#!/bin/bash
# OnionExplorer — One-command startup script
# Starts both Python Backend and SvelteKit Frontend together

echo ""
echo "🧅 Starting OnionExplorer Threat Intelligence Console..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Install the package in editable mode if not already registered
pip install -e .

# Run the unified CLI server (launches Svelte dev server and Flask API together)
onion serve
