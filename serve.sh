#!/bin/bash
# OnionExplorer — One-command startup script

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       OnionExplorer — Starting...        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start Gunicorn production server (3 workers, background logging)
nohup gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:app > data/logs/gunicorn.log 2>&1 &

echo "✅ OnionExplorer is running!"
echo "📍 Dashboard URL : http://localhost:5000"
echo "📄 Server Logs   : tail -f data/logs/gunicorn.log"
echo "🛑 To Stop       : pkill gunicorn"
echo ""
