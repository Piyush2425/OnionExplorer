import React, { useState } from 'react';
import axios from 'axios';
import { ChevronRight, ChevronDown, Copy, Check, Scan, Image, CheckSquare, Square } from 'lucide-react';

export default function UnifiedTable({ data, scanResults, verifiedLinks, setVerifiedLinks, API_BASE }) {
  const [expandedRow, setExpandedRow] = useState(null);
  const [copiedUrl, setCopiedUrl] = useState(null);
  const [activeModalData, setActiveModalData] = useState(null); // { screenshotPath, url }
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
        setActiveModalData({ screenshotPath: resp.data.screenshot_path, url });
      } else {
        alert('Scan failed: ' + (resp.data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Scan request failed. Is Tor proxy running?');
    } finally {
      setScanningUrl(null);
    }
  };

  const handleToggleVerify = async (url, currentVerified, currentComment) => {
    const newVerified = !currentVerified;
    try {
      const res = await axios.post(`${API_BASE}/verify_link`, {
        url,
        verified: newVerified,
        comment: currentComment || ''
      });
      if (res.data.success) {
        setVerifiedLinks(prev => ({
          ...prev,
          [url]: res.data.verified_info
        }));
      }
    } catch (err) {
      console.error('Failed to update verification:', err);
    }
  };

  const handleCommentChange = async (url, newComment, currentVerified) => {
    try {
      const res = await axios.post(`${API_BASE}/verify_link`, {
        url,
        verified: currentVerified || false,
        comment: newComment
      });
      if (res.data.success) {
        setVerifiedLinks(prev => ({
          ...prev,
          [url]: res.data.verified_info
        }));
      }
    } catch (err) {
      console.error('Failed to update comment:', err);
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
                                <th>Feed Status</th>
                                <th>Analyst Verification</th>
                                <th>Analyst Comment</th>
                                <th>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {entity.urls && entity.urls.map((u, i) => {
                                const isOnline = u.status === 'Online';
                                const scanData = scanResults[u.url];
                                const vData = verifiedLinks[u.url] || { verified: false, comment: '' };

                                return (
                                  <tr key={i} style={{ background: vData.verified ? 'rgba(16, 185, 129, 0.05)' : 'transparent' }}>
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
                                    <td>
                                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: vData.verified ? '#10b981' : '#aaa', fontWeight: vData.verified ? 'bold' : 'normal' }}>
                                        <input 
                                          type="checkbox" 
                                          checked={vData.verified} 
                                          onChange={() => handleToggleVerify(u.url, vData.verified, vData.comment)}
                                          style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                                        />
                                        {vData.verified ? 'Verified Working ✅' : 'Unverified'}
                                      </label>
                                    </td>
                                    <td>
                                      <input 
                                        type="text" 
                                        placeholder="e.g. Captcha / DDoS protection..." 
                                        value={vData.comment || ''}
                                        onChange={(e) => handleCommentChange(u.url, e.target.value, vData.verified)}
                                        style={{
                                          padding: '4px 8px',
                                          borderRadius: '4px',
                                          border: '1px solid #444',
                                          background: '#222',
                                          color: '#fff',
                                          width: '100%',
                                          fontSize: '0.8rem'
                                        }}
                                      />
                                    </td>
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
                                            onClick={(e) => { e.stopPropagation(); setActiveModalData({ screenshotPath: scanData.screenshot, url: u.url }); }}
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

      {activeModalData && (
        <div className="modal-overlay" style={{ display: 'flex' }}>
          <div className="modal-content" style={{ maxWidth: '1000px' }}>
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>Screenshot Validation</h3>
                <span style={{ fontSize: '0.8rem', color: '#888' }}>{activeModalData.url}</span>
              </div>
              <button className="modal-close" onClick={() => setActiveModalData(null)}>&times;</button>
            </div>
            
            {/* Analyst Controls inside Modal */}
            <div style={{ padding: '12px 20px', background: '#181818', borderBottom: '1px solid #333', display: 'flex', gap: '15px', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#10b981', fontWeight: 'bold' }}>
                <input 
                  type="checkbox" 
                  checked={(verifiedLinks[activeModalData.url] || {}).verified || false} 
                  onChange={() => {
                    const current = verifiedLinks[activeModalData.url] || { verified: false, comment: '' };
                    handleToggleVerify(activeModalData.url, current.verified, current.comment);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                Verified Working Link
              </label>

              <input 
                type="text" 
                placeholder="Add comment (e.g., Captcha required, DDoS protection)..." 
                value={(verifiedLinks[activeModalData.url] || {}).comment || ''}
                onChange={(e) => {
                  const current = verifiedLinks[activeModalData.url] || { verified: false, comment: '' };
                  handleCommentChange(activeModalData.url, e.target.value, current.verified);
                }}
                style={{
                  flexGrow: 1,
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #444',
                  background: '#222',
                  color: '#fff',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto', padding: '20px' }}>
              <img src={`http://127.0.0.1:5000${activeModalData.screenshotPath}`} alt="Screenshot" style={{ width: '100%', borderRadius: '8px' }} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
