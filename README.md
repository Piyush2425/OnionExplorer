# OnionExplorer — Dark Web Threat Intelligence Dashboard
Project Made By Piyush G 
OnionExplorer is an enterprise-grade dark web threat intelligence platform that dynamically aggregates, parses, and monitors ransomware groups, leaked forums, marketplaces, and Telegram darknet invite links. 

---

## 🚀 Key Features

* **Multi-Feed Cybersecurity Ingestion**: Concurrently crawls and processes multiple OSINT CTI feeds including RansomFeed.it, RansomLook.io, Ransomware.live, and custom threat intelligence feeds from GitHub.
* **Modern React (Vite) Frontend**: A production-ready single-page application (SPA) with a sleek, tailored dark-mode UI.
* **Playwright Tor Batch Scanner**: Uses a headless Firefox engine routed through a Tor SOCKS5 proxy (`127.0.0.1:9050`) to automatically validate Onion links and permanently store screenshots.
* **Multi-Feed Cybersecurity Ingestion**: Concurrently crawls and processes OSINT CTI feeds including RansomFeed.it, RansomLook.io, Ransomware.live, and custom threat intelligence feeds from GitHub.
* **Responsive Visual Counters**: Interactive top counters (Forums, Markets, Telegram, URLs, Online, Offline) that dynamically recalculate metrics based on selected source filters.
* **Enterprise Exporters**:
  - **CSV Export**: Sanitized against CSV injection attacks (`=`, `+`, `-`, `@` escapes).
  - **Markdown Export**: Generates table-formatted threat reports containing executive summaries.
* **Persistent JSON Database**: Permanently stores historical link statuses and screenshot validation data in `data/scan_results.json`.

---

## 📂 Project Structure

```
OnionExplorer/
├── data/                    # Persistent storage database & logs
│   ├── config.json          # Crawling source list config
│   ├── scan_results.json    # Tor validation and screenshot DB
│   └── logs/                # Rotating server logs
├── frontend/                # React (Vite) UI source code
│   ├── src/                 # React components and assets
│   └── dist/                # Production UI build (served by Flask)
├── monitors/                # Custom scraper & validation modules
│   ├── batch_scanner.py     # Playwright Firefox Tor scanner
│   ├── validator.py         # Single URL validation script
│   └── ...                  # CTI scrapers (github_feed, telegram_checker, etc.)
├── static/screenshots/      # Captured Tor screenshots
├── requirements.txt         # Python package dependencies
└── main.py                  # Flask Application entry point (API)
```

---

## 🛠️ How to Deploy & Run on Ubuntu Server

### ✅ One-Time Setup (Ubuntu / Debian)

> **IMPORTANT**: Ensure you have Tor installed and running as a background service listening on `127.0.0.1:9050` before starting the scanners!
> `sudo apt install tor && sudo systemctl enable --now tor`

#### Step 1 — Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git nodejs npm tor
```

#### Step 2 — Clone the Repository
```bash
git clone https://github.com/Piyush2425/OnionExplorer.git
cd OnionExplorer
```

#### Step 3 — Install Python Dependencies & Playwright
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install firefox
```

#### Step 4 — Build the React Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

---

### 🚀 Start the Server

Start the Flask API and frontend server:
```bash
source venv/bin/activate
flask --app main run --host=0.0.0.0 --port=5000
```

> **Dashboard is live at**: `http://YOUR_SERVER_IP:5000`

---

### 🛑 Stop the Server
Press `CTRL+C` in the terminal to stop the Flask server.

### 📄 View Logs
```bash
tail -f data/logs/gunicorn.log
```

