# OnionExplorer — Dark Web Threat Intelligence Dashboard
Project Made By Piyush G 
OnionExplorer is an enterprise-grade dark web threat intelligence platform that dynamically aggregates, parses, and monitors ransomware groups, leaked forums, marketplaces, and Telegram darknet invite links. 

---

## 🚀 Key Features

* **Multi-Feed Cybersecurity Ingestion**: Concurrently crawls and processes multiple OSINT CTI feeds including RansomFeed.it, RansomLook.io, Ransomware.live, and custom threat intelligence feeds from GitHub.
* **Lightweight Light & Dark Themes**: Sleek, modern cybersecurity dash layout equipped with HSL tailored cards, micro-animations, and a one-click Light/Dark UI theme toggle with localStorage persistence.
* **Responsive Visual Counters**: Six interactive top counters (Forums, Markets, Telegram, URLs, Online, Offline) that dynamically recalculate metrics based on selected source filters.
* **Auto-Tab Switching**: Intuitively redirects active dashboard tab selections (e.g. shifts to 💬 Telegram Links or 🛍️ Markets) when selecting a source filter to prevent empty dashboard states.
* **Enterprise Exporters**:
  - **CSV Export**: Sanitized against CSV injection attacks (`=`, `+`, `-`, `@` escapes) and embedded with generation metadata headers for corporate audits.
  - **Markdown Export**: Generates table-formatted threat reports containing executive summaries, matching entity counts, and corporate intelligence disclaimers.
* **Production-Grade Infrastructure**: Powered by APScheduler background task management, Rotating File Logging (keeps up to 5 historical log backups), and multi-threaded session connection pool mounts to prevent network throttling warnings.

---

## 📂 Project Structure

```
OnionExplorer/
├── data/                    # Persistent storage database & logs
│   ├── config.json          # Crawling source list config
│   ├── onion_explorer.db    # Relational SQLite database
│   └── logs/                # Rotating server logs
├── monitors/                # Custom scraper modules
│   ├── github_feed.py       # GitHub .md markdown feeds scraper
│   ├── ransomelive.py       # Ransomware.live scraper
│   ├── ransomelook.py       # RansomLook API scraper
│   ├── ransomfeed.py        # RansomFeed web scraper
│   └── telegram_checker.py  # Telegram invite links validator
├── onion_explorer/          # Local client database abstraction layer
├── static/                  # JavaScript & stylesheet assets
├── templates/               # Flask html templates
├── tests/                   # Unified test suite files
├── wsgi.py                  # Gunicorn gate entrypoint
├── requirements.txt         # Package dependencies
└── main.py                  # Application entry point
```

---

## 🛠️ How to Deploy & Run on Ubuntu Server

### ✅ One-Time Setup (Only required on first deployment)

#### Step 1 — Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git
```

#### Step 2 — Clone the Repository
```bash
git clone https://github.com/Piyush2425/OnionExplorer.git
cd OnionExplorer
```

#### Step 3 — Create Virtual Environment & Install Packages
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4 — Configure Environment
```bash
nano .env
```
Paste the following settings and save (`CTRL+O → Enter → CTRL+X`):
```ini
PORT=5000
HOST=0.0.0.0
DB_TYPE=sqlite
SCRAPE_INTERVAL_MINUTES=1440
LOG_LEVEL=INFO
SECRET_KEY=generate-a-secure-random-key-here
```

---

### 🚀 Start the Server (Every Time)

After completing the one-time setup above, simply run **this single command** to start the dashboard:

```bash
bash serve.sh
```

> **Dashboard is live at**: `http://localhost:5000` (or `http://YOUR_SERVER_IP:5000`)

---

### 🛑 Stop the Server
```bash
pkill gunicorn
```


---

## 🔒 Automated Tor Screenshot Verification & Manual UI Scanning

OnionExplorer is integrated with a secure headless browser verifier that crawls darkweb Onion sites, checks link statuses, and captures full-page screenshot previews to render directly on your dashboard.

### ⚙️ How It Works (Tor Proxy)
* The system checks if a local Tor SOCKS5 service is listening on port `9050`.
* If detected, all browser crawls are routed via Tor SOCKS5 proxy (`socks5://127.0.0.1:9050`) to load onion URLs securely.
* If Tor is not running, it falls back to direct routing (ideal for local testing of standard web feeds).
* **Security Filter**: Telegram links are completely skipped and labeled as `N/A (Telegram)` since they cannot be loaded via standard browser verification.

### 🔧 Installing Chrome & Tor on Ubuntu Server

To get automated screenshots running on your Ubuntu virtual machine, install Tor and headless Chrome:

```bash
# 1. Install Tor Service
sudo apt update
sudo apt install -y tor
sudo systemctl enable tor
sudo systemctl start tor

# 2. Verify Tor is listening on port 9050
ss -nltp | grep 9050

# 3. Install Headless Chrome Web Browser
sudo apt install -y wget curl unzip
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb

# 4. Install ChromeDriver dependencies (Optional)
sudo apt install -y libnss3 libgconf-2-4 libxi6
```

### 📟 How to Verify and Scan Links via UI

1. Open the dashboard table and click the **arrow `▶`** next to any threat actor to expand its Onion locations.
2. If no screenshot has been captured yet, the row shows a **`No Preview`** placeholder.
3. Click the **`🔄 Re-Check`** action button inside the target link row.
4. The button changes to **`🔄 Queued...`** and then **`⏳ Processing...`** as the background thread launches a browser, connects via Tor, and takes a full-resolution screenshot.
5. Once completed, the status dot updates automatically (e.g. `Up` or `Down`) and a **thumbnail image preview** replaces the placeholder.
6. **Click the thumbnail preview** to open a premium lightbox zoom window and view the screenshot in full resolution.

---

### 📄 View Logs
```bash
tail -f data/logs/gunicorn.log
```


