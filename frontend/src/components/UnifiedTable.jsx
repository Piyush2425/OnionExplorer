import React, { useState } from 'react';
import axios from 'axios';
import { ChevronRight, ChevronDown, Copy, Check, Scan, Image } from 'lucide-react';

export default function UnifiedTable({ data, scanResults, API_BASE }) {
  const [expandedRow, setExpandedRow] = useState(null);
  const [copiedUrl, setCopiedUrl] = useState(null);
  const [scanModalPath, setScanModalPath] = useState(null);
  const [scanningUrl, setScanningUrl] = useState(null);

  const toggleRow = (key) => {
    setExpandedRow(expandedRow === key ? null : key);
  };

  const handleCopy = (e, url) => {
    e.stopPropagation();
    navigator.clipboard.writeText(url);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 1500);
  };

  const handleScan = async (e, url) => {
    e.stopPropagation();
    setScanningUrl(url);
    try {
      const resp = await axios.post(`${API_BASE}/scan`, { url });
      if (resp.data.success && resp.data.screenshot_path) {
        setScanModalPath(resp.data.screenshot_path);
      } else {
        alert('Scan failed: ' + (resp.data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Scan request failed. Is Tor proxy running?');
    } finally {
      setScanningUrl(null);
    }
  };

  if (data.length === 0) {
    return <div style={{ padding: '20px', textAlign: 'center', color: '#888' }}>No threats found.</div>;
  }

  return (
    <>
      <div className="table-container">
        <table className="unified-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}></th>
              <th>Threat Name</th>
              <th>Sector</th>
              <th>Status</th>
              <th>Sources</th>
              <th>Active Links</th>
            </tr>
          </thead>
          <tbody>
            {data.map((entity) => {
              const isExpanded = expandedRow === entity.key;
              const onlineCount = entity.online_count || 0;
              const totalCount = entity.total_urls || 0;
              const isTelegram = entity.type === 'telegram' || entity.sector === 'telegram_links';
              
              let sectorLabel = '👥 Group';
              let sectorClass = 'group';
              if (entity.type === 'market' || entity.sector === 'markets') {
                sectorLabel = '🏪 Market';
                sectorClass = 'market';
              } else if (isTelegram) {
                sectorLabel = '📢 Telegram';
                sectorClass = 'telegram';
              }

              let statusType = 'offline';
              if (onlineCount > 0 && onlineCount < totalCount) statusType = 'mixed';
              if (onlineCount > 0 && onlineCount === totalCount) statusType = 'online';
              if (totalCount === 0) statusType = 'offline';

              return (
                <React.Fragment key={entity.key}>
                  <tr className={`entity-row ${isExpanded ? 'expanded' : ''}`} onClick={() => toggleRow(entity.key)} style={{ cursor: 'pointer' }}>
                    <td className="arrow-cell">
                      {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </td>
                    <td className="name-cell"><strong>{entity.name}</strong></td>
                    <td><span className={`sector-badge ${sectorClass}`}>{sectorLabel}</span></td>
                    <td>
                      <div className={`status-indicator ${statusType}`}>
                        <span className={`status-pip ${statusType}`}></span>
                        {statusType.charAt(0).toUpperCase() + statusType.slice(1)}
                      </div>
                    </td>
                    <td>
                      <div className="source-tags">
                        {entity.sources && entity.sources.map(s => (
                          <span key={s} className="source-tag">{s.replace('github:', '')}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div className="links-counter-badge">
                        <span className="online-count">{onlineCount}</span> / <span className="total-count">{totalCount}</span> active
                      </div>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr className="details-row show" style={{ display: 'table-row' }}>
                      <td colSpan="6">
                        <div className="details-content">
                          <table className="nested-links-table">
                            <thead>
                              <tr>
                                <th>Onion URL / Invite Link</th>
                                <th>Status</th>
                                <th>Last Visited</th>
                                <th>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {entity.urls && entity.urls.map((u, i) => {
                                const isOnline = u.status === 'Online';
                                const scanData = scanResults[u.url];
                                
                                return (
                                  <tr key={i}>
                                    <td className="nested-url-cell">
                                      <span className={`url-dot ${isOnline ? 'online' : 'offline'}`}></span>
                                      <a href={u.url} target="_blank" rel="noreferrer" className="nested-link" onClick={e => e.stopPropagation()}>{u.url}</a>
                                    </td>
                                    <td>
                                      <span className={`status-indicator ${isOnline ? 'online' : 'offline'}`}>
                                        <span className={`status-pip ${isOnline ? 'online' : 'offline'}`}></span>
                                        {isOnline ? 'Online' : 'Offline'}
                                      </span>
                                    </td>
                                    <td className="last-visit-cell">{u.last_visit || 'N/A'}</td>
                                    <td>
                                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                        <button className="copy-url-btn" onClick={(e) => handleCopy(e, u.url)} title="Copy">
                                          {copiedUrl === u.url ? <Check size={14} /> : <Copy size={14} />}
                                        </button>
                                        
                                        {!isTelegram && isOnline && (
                                          <button 
                                            className="scan-url-btn" 
                                            onClick={(e) => handleScan(e, u.url)}
                                            disabled={scanningUrl === u.url}
                                          >
                                            {scanningUrl === u.url ? <div className="spinner"></div> : <Scan size={14} />} 
                                            {scanningUrl === u.url ? 'Scanning...' : 'Scan'}
                                          </button>
                                        )}

                                        {scanData && scanData.screenshot && (
                                          <button 
                                            className="scan-url-btn" 
                                            style={{ background: 'var(--accent-green-dim)', borderColor: 'var(--accent-green)', color: 'var(--accent-green)' }}
                                            onClick={(e) => { e.stopPropagation(); setScanModalPath(scanData.screenshot); }}
                                          >
                                            <Image size={14} /> View
                                          </button>
                                        )}
                                      </div>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {scanModalPath && (
        <div className="modal-overlay" style={{ display: 'flex' }}>
          <div className="modal-content">
            <div className="modal-header">
              <h3>Scan Result</h3>
              <button className="modal-close" onClick={() => setScanModalPath(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <img src={`http://127.0.0.1:5000${scanModalPath}`} alt="Screenshot" />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
