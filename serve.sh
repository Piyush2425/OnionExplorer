#!/bin/bash
# OnionExplorer — One-command startup script
# Starts both Python Backend and SvelteKit Frontend together

echo ""
echo "🧅 Starting OnionExplorer Threat Intelligence Console..."
echo ""

# Load NVM (Node Version Manager) if available
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    nvm use 20 --silent
fi

# Activate virtual environment
source venv/bin/activate

# Install the package in editable mode if not already registered
pip install -e .

# Run the unified CLI server (launches Svelte dev server and Flask API together)
onion serve
