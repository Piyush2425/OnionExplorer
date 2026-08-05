import React, { useEffect, useState } from 'react';
import axios from 'axios';
import UnifiedTable from './components/UnifiedTable';
import './index.css';

const API_BASE = 'http://127.0.0.1:5000/api';

function App() {
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [scanResults, setScanResults] = useState({});
  const [loading, setLoading] = useState(true);
  const [currentTab, setCurrentTab] = useState('all_sectors');
  const [searchQuery, setSearchQuery] = useState('');
  const [isBatchScanning, setIsBatchScanning] = useState(false);

  useEffect(() => {
    fetchData();
    fetchScanResults();
    const interval = setInterval(fetchScanResults, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [dataRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE}/data`),
        axios.get(`${API_BASE}/stats`)
      ]);
      setData(dataRes.data);
      setStats(statsRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const fetchScanResults = async () => {
    try {
      const res = await axios.get(`${API_BASE}/scan_results`);
      setScanResults(res.data);
    } catch (error) {
      console.error('Error fetching scan results:', error);
    }
  };

  const startBatchScan = async () => {
    if (!confirm('Start batch Tor scanning? This will take a while.')) return;
    setIsBatchScanning(true);
    try {
      await axios.post(`${API_BASE}/batch_scan`);
      alert('Batch scan started in the background!');
    } catch (err) {
      alert('Failed to start batch scan.');
    }
    setTimeout(() => setIsBatchScanning(false), 3000);
  };

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', color: '#fff' }}>
        <h2>Loading Threat Intelligence...</h2>
      </div>
    );
  }

  // Convert dicts to arrays
  const allForumsGroups = Object.entries(data.forums_groups || {}).map(([k, v]) => ({ key: k, ...v }));
  const allMarkets = Object.entries(data.markets || {}).map(([k, v]) => ({ key: k, ...v }));
  const allTelegramLinks = Object.entries(data.telegram_links || {}).map(([k, v]) => ({ key: k, ...v }));

  let displayData = [];
  if (currentTab === 'all_sectors') {
    displayData = [...allForumsGroups, ...allMarkets, ...allTelegramLinks];
  } else if (currentTab === 'forums_groups') {
    displayData = allForumsGroups;
  } else if (currentTab === 'markets') {
    displayData = allMarkets;
  } else if (currentTab === 'telegram_links') {
    displayData = allTelegramLinks;
  }

  if (searchQuery) {
    displayData = displayData.filter(d => 
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.urls.some(u => u.url.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }

  return (
    <div className="dark-theme" style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <header className="top-header">
        <div className="header-left">
          <h1>🧅 OnionExplorer V2</h1>
          <span className="version-badge">React Native</span>
        </div>
        <div className="header-right">
          <button className="scrape-btn" onClick={startBatchScan} disabled={isBatchScanning}>
            {isBatchScanning ? 'Starting...' : '🔄 Run Batch Tor Scan'}
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="stats-row">
          <div className="stat-card group">
            <div className="stat-title">Tracked Groups</div>
            <div className="stat-value">{allForumsGroups.length}</div>
          </div>
          <div className="stat-card market">
            <div className="stat-title">Tracked Markets</div>
            <div className="stat-value">{allMarkets.length}</div>
          </div>
          <div className="stat-card telegram">
            <div className="stat-title">Telegram Links</div>
            <div className="stat-value">{allTelegramLinks.length}</div>
          </div>
        </div>

        <div className="controls-bar">
          <input 
            type="text" 
            placeholder="Search threats, URLs, domains..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
            style={{ padding: '10px', width: '100%', maxWidth: '400px', borderRadius: '8px', border: '1px solid #333', background: '#1a1a1a', color: '#fff' }}
          />
        </div>

        <div className="tabs-container">
          <button className={`tab ${currentTab === 'all_sectors' ? 'active' : ''}`} onClick={() => setCurrentTab('all_sectors')}>All Sectors</button>
          <button className={`tab ${currentTab === 'forums_groups' ? 'active' : ''}`} onClick={() => setCurrentTab('forums_groups')}>Forums & Groups</button>
          <button className={`tab ${currentTab === 'markets' ? 'active' : ''}`} onClick={() => setCurrentTab('markets')}>Markets</button>
          <button className={`tab ${currentTab === 'telegram_links' ? 'active' : ''}`} onClick={() => setCurrentTab('telegram_links')}>Telegram Links</button>
        </div>

        <div className="table-card">
          <UnifiedTable data={displayData} scanResults={scanResults} API_BASE={API_BASE} />
        </div>
      </main>
    </div>
  );
}

export default App;
