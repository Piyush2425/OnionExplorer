# OnionExplorer — Dark Web Threat Intelligence Dashboard

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
├── Dockerfile               # Multi-stage production container build
├── docker-compose.yml       # Production orchestration
├── wsgi.py                  # Gunicorn gate entrypoint
├── requirements.txt         # Package dependencies
└── main.py                  # Application entry point
```

---

## 🛠️ How to Run

### Method 1: Using Docker (Recommended for Production)

Bypass the need for setting up a local virtual environment by containerizing the dashboard:

1. **Build and spin up the container**:
   ```bash
   docker-compose up --build -d
   ```
2. **Access the application**: Open your browser at **http://localhost:5000/**.
3. **Shut down the container**:
   ```bash
   docker-compose down
   ```

### Method 2: Local Python Execution (For Development)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch the web application**:
   ```bash
   python main.py
   ```
3. **Open the browser**: Go to **http://localhost:5000/**.

---

## ⚙️ Configuration (.env)

Customize parameters by creating a `.env` file in the root directory:
```ini
PORT=5000
HOST=0.0.0.0
DB_TYPE=sqlite
SCRAPE_INTERVAL_MINUTES=1440
LOG_LEVEL=INFO
SECRET_KEY=change-in-production-environments
```
