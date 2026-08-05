/**
 * OnionExplorer v2 — Dashboard Client Logic
 * Unified threat directory table with merged/deduplicated onion URLs.
 */

(function () {
    'use strict';

    // ═══ STATE ═══
    let rawData = {};         // { forums_groups: {}, markets: {}, telegram_links: {}, meta: {} }
    let statsData = {};
    let allForumsGroups = [];
    let allMarkets = [];
    let allTelegramLinks = [];
    let currentTab = 'all_sectors'; // 'all_sectors', 'forums_groups', 'markets', 'telegram_links'
    let currentFilter = 'all'; // 'all', 'has-online', 'all-offline'
    let currentSort = 'name-asc';
    let currentSourceFilter = 'all';
    let searchQuery = '';
    let wasScraping = false;

    // ═══ INIT ═══
    document.addEventListener('DOMContentLoaded', async () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
            const toggleBtn = document.getElementById('themeToggleBtn');
            if (toggleBtn) toggleBtn.textContent = '🌙 Dark UI';
        }
        
        bindEvents();
        await loadData();
        await loadScraperConfig();
        checkScraperStatus();
    });

    async function loadScraperConfig() {
        try {
            const resp = await fetch('/api/config');
            const data = await resp.json();
            const select = document.getElementById('intervalSelect');
            if (select && data.interval_minutes) {
                select.value = data.interval_minutes.toString();
            }
        } catch (err) {
            console.log('Failed to load config:', err);
        }
    }

    async function checkScraperStatus() {
        try {
            const resp = await fetch('/api/scraper/status');
            const meta = await resp.json();
            updateScrapeStatus(meta);
            
            const runScrapeBtn = document.getElementById('runScrapeBtn');
            const mainScrapeBtn = document.getElementById('mainScrapeBtn');

            if (meta.is_running) {
                wasScraping = true;
                if (runScrapeBtn) {
                    runScrapeBtn.disabled = true;
                    runScrapeBtn.textContent = '🔄 Scraper Running...';
                }
                if (mainScrapeBtn) {
                    mainScrapeBtn.disabled = true;
                    mainScrapeBtn.textContent = '🔄 Scraping All Sources...';
                }
                setTimeout(checkScraperStatus, 3000);
            } else {
                if (wasScraping) {
                    wasScraping = false;
                    await loadData();
                }
                if (runScrapeBtn) {
                    runScrapeBtn.disabled = false;
                    runScrapeBtn.textContent = '🔄 Scrape Now';
                }
                if (mainScrapeBtn) {
                    mainScrapeBtn.disabled = false;
                    mainScrapeBtn.textContent = '⚡ Scrape All Sources';
                }
            }
        } catch (err) {
            console.error('Error polling status:', err);
        }
    }

    async function loadData() {
        try {
            const [dataResp, statsResp] = await Promise.all([
                fetch('/api/data'),
                fetch('/api/stats')
            ]);

            rawData = await dataResp.json();
            statsData = await statsResp.json();

            // Convert dicts to arrays
            allForumsGroups = dictToArray(rawData.forums_groups || {});
            allMarkets = dictToArray(rawData.markets || {});
            allTelegramLinks = dictToArray(rawData.telegram_links || {});

            updateDynamicStats();
            updateTabCounts();
            updateScrapeStatus(rawData.meta || {});
            applyAndRender();

        } catch (err) {
            console.error('Failed to load data:', err);
            const tbody = document.getElementById('unifiedTableBody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="no-results-cell">
                            <div class="no-results">
                                <div class="icon">⚠️</div>
                                <p>Failed to load threat intelligence data. Is the server running?</p>
                            </div>
                        </td>
                    </tr>
                `;
            }
        }
    }

    function dictToArray(dict) {
        return Object.entries(dict).map(([key, e]) => ({
            key,
            name: e.name || key,
            sources: e.sources || [],
            urls: e.urls || [],
            stats: e.stats || {},
            online_count: e.online_count || 0,
            offline_count: e.offline_count || 0,
            total_urls: e.total_urls || 0
        }));
    }

    function autoSwitchTabForSource(src) {
        if (src === 'all') return;
        
        let targetTab = 'forums_groups';
        if (src.includes('markets.md')) {
            targetTab = 'markets';
        } else if (src.includes('telegram')) {
            targetTab = 'telegram_links';
        } else if (src === 'ransomfeed' || src === 'ransomware.live' || src === 'ransomlook') {
            targetTab = 'forums_groups';
        }
        
        if (currentTab !== targetTab && currentTab !== 'all_sectors') {
            currentTab = targetTab;
            // Update active state in tabs CSS class
            document.querySelectorAll('.tab').forEach(tab => {
                if (tab.dataset.tab === targetTab) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });
        }
    }

    // ═══ EVENTS ═══
    function bindEvents() {
        // Main Scrape All Button
        const mainScrapeBtn = document.getElementById('mainScrapeBtn');
        if (mainScrapeBtn) {
            mainScrapeBtn.addEventListener('click', async () => {
                try {
                    mainScrapeBtn.disabled = true;
                    mainScrapeBtn.textContent = '🔄 Scraping All Sources...';
                    const resp = await fetch('/api/scraper/run', { method: 'POST' });
                    const res = await resp.json();
                    if (res.status === 'started' || res.status === 'already_running') {
                        checkScraperStatus();
                    }
                } catch (err) {
                    console.error('Failed to trigger scrape:', err);
                    mainScrapeBtn.disabled = false;
                    mainScrapeBtn.textContent = '⚡ Scrape All Sources';
                }
            });
        }

        // Search
        const searchInput = document.getElementById('searchInput');
        let debounce;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounce);
            debounce = setTimeout(() => {
                searchQuery = e.target.value.toLowerCase().trim();
                applyAndRender();
            }, 200);
        });

        // Clear search button
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                searchInput.value = '';
                searchQuery = '';
                applyAndRender();
            });
        }

        // Tabs
        document.querySelectorAll('.tab[data-tab]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentTab = tab.dataset.tab;
                applyAndRender();
            });
        });

        // Filter chips
        document.querySelectorAll('.chip[data-filter]').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.chip[data-filter]').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentFilter = chip.dataset.filter;
                applyAndRender();
            });
        });

        // Sort Select
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                currentSort = e.target.value;
                applyAndRender();
            });
        }

        // Source Filter
        const sourceFilterSelect = document.getElementById('sourceFilterSelect');
        if (sourceFilterSelect) {
            sourceFilterSelect.addEventListener('change', (e) => {
                currentSourceFilter = e.target.value;
                autoSwitchTabForSource(currentSourceFilter);
                updateDynamicStats();
                applyAndRender();
            });
        }

        // Export CSV
        const exportCsvBtn = document.getElementById('exportCsvBtn');
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => {
                let statusParam = 'all';
                if (currentFilter === 'has-online') {
                    statusParam = 'online';
                } else if (currentFilter === 'all-offline') {
                    statusParam = 'offline';
                }
                window.location.href = `/api/export/csv?sector=${currentTab}&status=${statusParam}&source=${currentSourceFilter}`;
            });
        }

        // Export Markdown
        const exportMdBtn = document.getElementById('exportMdBtn');
        if (exportMdBtn) {
            exportMdBtn.addEventListener('click', () => {
                let statusParam = 'all';
                if (currentFilter === 'has-online') {
                    statusParam = 'online';
                } else if (currentFilter === 'all-offline') {
                    statusParam = 'offline';
                }
                window.location.href = `/api/export/markdown?sector=${currentTab}&status=${statusParam}&source=${currentSourceFilter}`;
            });
        }

        // Theme Toggle
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => {
                const isLight = document.body.classList.toggle('light-theme');
                localStorage.setItem('theme', isLight ? 'light' : 'dark');
                themeToggleBtn.textContent = isLight ? '🌙 Dark UI' : '☀️ Light UI';
            });
        }

        // Settings Dropdown Toggle
        const settingsBtn = document.getElementById('settingsBtn');
        const settingsDropdown = document.getElementById('settingsDropdown');
        if (settingsBtn && settingsDropdown) {
            settingsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                settingsDropdown.classList.toggle('active');
            });
            document.addEventListener('click', (e) => {
                if (!settingsDropdown.contains(e.target) && e.target !== settingsBtn) {
                    settingsDropdown.classList.remove('active');
                }
            });
        }

        // Scraper Interval Select
        const intervalSelect = document.getElementById('intervalSelect');
        if (intervalSelect) {
            intervalSelect.addEventListener('change', async (e) => {
                const val = parseInt(e.target.value, 10);
                try {
                    const resp = await fetch('/api/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ interval_minutes: val })
                    });
                    const res = await resp.json();
                    console.log('Scraper config updated:', res);
                } catch (err) {
                    console.error('Failed to save config:', err);
                }
            });
        }
    }

    // ═══ FILTER, SORT, RENDER ═══
    function applyAndRender() {
        let source;
        if (currentTab === 'forums_groups') {
            source = allForumsGroups;
        } else if (currentTab === 'markets') {
            source = allMarkets;
        } else if (currentTab === 'telegram_links') {
            source = allTelegramLinks;
        } else {
            source = [...allForumsGroups, ...allMarkets, ...allTelegramLinks];
        }

        // Filter
        let filtered = source.filter(e => {
            // Search (Search both Actor name and onion URL)
            if (searchQuery) {
                const haystack = (e.name + ' ' + e.key + ' ' + e.urls.map(u => u.url).join(' ')).toLowerCase();
                if (!haystack.includes(searchQuery)) return false;
            }
            // Status filter
            if (currentFilter === 'has-online') return e.online_count > 0;
            if (currentFilter === 'all-offline') return e.online_count === 0;
            return true;
        });

        // Source Filter
        if (currentSourceFilter !== 'all') {
            filtered = filtered.filter(e => e.sources.includes(currentSourceFilter));
        }

        // Sort
        const [sortKey, sortDir] = currentSort.split('-');
        filtered.sort((a, b) => {
            let va, vb;
            switch (sortKey) {
                case 'name':
                    va = a.name.toLowerCase();
                    vb = b.name.toLowerCase();
                    return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
                case 'urls':
                    va = a.total_urls; vb = b.total_urls;
                    return sortDir === 'desc' ? vb - va : va - vb;
                case 'online':
                    va = a.online_count; vb = b.online_count;
                    return sortDir === 'desc' ? vb - va : va - vb;
                case 'sources':
                    va = a.sources.length; vb = b.sources.length;
                    return sortDir === 'desc' ? vb - va : va - vb;
                default: return 0;
            }
        });

        // Calculate matching URLs/links
        let totalMatchingLinks = 0;
        filtered.forEach(e => {
            let urlsToCount = e.urls;
            if (currentSourceFilter !== 'all') {
                urlsToCount = e.urls.filter(u => u.source === currentSourceFilter);
            }
            // Deduplicate to count unique links matching search
            const uniqueUrls = new Set(urlsToCount.map(u => u.url.trim()));
            totalMatchingLinks += uniqueUrls.size;
        });

        // Update search summary banner
        const banner = document.getElementById('searchSummaryBanner');
        const bannerText = document.getElementById('searchSummaryText');
        if (banner && bannerText) {
            if (searchQuery) {
                banner.style.display = 'flex';
                bannerText.innerHTML = `Search results for "<strong>${esc(searchQuery)}</strong>": Found <strong>${filtered.length}</strong> matching entries and <strong>${totalMatchingLinks}</strong> unique threat links.`;
            } else {
                banner.style.display = 'none';
            }
        }

        renderEntityList(filtered);
    }

    // ═══ STATS ═══
    function updateDynamicStats() {
        const srcFilter = currentSourceFilter;
        
        let groupsList = allForumsGroups;
        let marketsList = allMarkets;
        let telegramList = allTelegramLinks;

        if (srcFilter !== 'all') {
            groupsList = allForumsGroups.filter(e => e.sources.includes(srcFilter));
            marketsList = allMarkets.filter(e => e.sources.includes(srcFilter));
            telegramList = allTelegramLinks.filter(e => e.sources.includes(srcFilter));
        }

        // Count totals
        const totalGroups = groupsList.length;
        const totalMarkets = marketsList.length;
        const totalTelegram = telegramList.length;

        let totalUrls = 0;
        let totalOnline = 0;
        let totalOffline = 0;

        const countUrlsForCollection = (list) => {
            const uniqueUrls = {};
            list.forEach(e => {
                let urlsToCount = e.urls;
                if (srcFilter !== 'all') {
                    urlsToCount = e.urls.filter(u => u.source === srcFilter);
                }
                urlsToCount.forEach(u => {
                    const urlStr = u.url.trim();
                    if (!uniqueUrls[urlStr]) {
                        uniqueUrls[urlStr] = u.status || 'Offline';
                    } else if (u.status === 'Online') {
                        uniqueUrls[urlStr] = 'Online';
                    }
                });
            });
            
            // Sum up
            Object.values(uniqueUrls).forEach(status => {
                totalUrls++;
                if (status === 'Online') {
                    totalOnline++;
                } else {
                    totalOffline++;
                }
            });
        };

        countUrlsForCollection(groupsList);
        countUrlsForCollection(marketsList);
        countUrlsForCollection(telegramList);

        // Update elements on page
        animateCounter('statGroups', totalGroups);
        animateCounter('statMarkets', totalMarkets);
        animateCounter('statTelegram', totalTelegram);
        animateCounter('statUrls', totalUrls);
        animateCounter('statOnline', totalOnline);
        animateCounter('statOffline', totalOffline);
    }

    function animateCounter(id, target) {
        const el = document.getElementById(id);
        if (!el) return;
        if (target === 0) { el.textContent = '0'; return; }
        const duration = 1000;
        const start = performance.now();
        function tick(now) {
            const p = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(target * eased).toLocaleString();
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    function updateTabCounts() {
        const totalCount = allForumsGroups.length + allMarkets.length + allTelegramLinks.length;
        if (document.getElementById('tabAllCount')) {
            document.getElementById('tabAllCount').textContent = totalCount;
        }
        document.getElementById('tabGroupsCount').textContent = allForumsGroups.length;
        document.getElementById('tabMarketsCount').textContent = allMarkets.length;
        document.getElementById('tabTelegramCount').textContent = allTelegramLinks.length;
    }

    function updateScrapeStatus(meta) {
        const dot = document.getElementById('scrapeStatusDot');
        const text = document.getElementById('scrapeStatusText');

        if (meta.is_scraping) {
            dot.classList.add('scraping');
            text.textContent = 'Scraping...';
        } else if (meta.last_scraped) {
            dot.classList.remove('scraping');
            text.textContent = 'Updated: ' + meta.last_scraped;
        } else {
            dot.classList.remove('scraping');
            const freshness = meta.source_freshness || {};
            const times = Object.values(freshness);
            if (times.length > 0) {
                text.textContent = 'Data loaded from files';
            } else {
                text.textContent = 'No data yet';
            }
        }
    }

    // ═══ ENTITY LIST ═══
    function renderEntityList(entities) {
        const tbody = document.getElementById('unifiedTableBody');
        if (!tbody) return;

        if (entities.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="no-results-cell">
                        <div class="no-results">
                            <div class="icon">🔍</div>
                            <p>No results match your search or filter.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = entities.map(e => renderEntityRow(e)).join('');
    }

    function formatSourceName(src) {
        if (src === 'ransomfeed') return 'RansomFeed Feed';
        if (src === 'ransomlook') return 'RansomLook Feed';
        if (src === 'ransomware.live') return 'Ransomware.live Feed';
        if (src === 'watchguard') return 'WatchGuard Tracker';
        if (src.startsWith('github:')) {
            return `GitHub: ${src.substring(7)}`;
        }
        return src;
    }

    function renderEntityRow(e) {
        const statusType = getStatus(e);
        const statusLabel = statusType === 'mixed' ? 'Mixed' : statusType === 'online' ? 'Online' : 'Offline';
        
        // Sector display label
        let sectorLabel = 'Group';
        let sectorClass = 'group';
        if (e.type === 'market' || e.sector === 'markets') {
            sectorLabel = '🏪 Market';
            sectorClass = 'market';
        } else if (e.type === 'telegram' || e.sector === 'telegram_links') {
            sectorLabel = '📢 Telegram';
            sectorClass = 'telegram';
        } else {
            sectorLabel = '👥 Group';
            sectorClass = 'group';
        }

        const sourceTags = e.sources.map(s => {
            let label = s;
            let cls = s;
            if (s === 'ransomware.live') {
                label = 'R.Live';
                cls = 'ransomware-live';
            } else if (s === 'ransomfeed') {
                label = 'RFeed';
                cls = 'ransomfeed';
            } else if (s === 'ransomlook') {
                label = 'RLook';
                cls = 'ransomlook';
            } else if (s === 'watchguard') {
                label = 'WatchGuard';
                cls = 'watchguard';
            } else if (s.startsWith('github:')) {
                label = s.substring(7);
                cls = 'github';
            }
            return `<span class="source-tag ${cls}">${esc(label)}</span>`;
        }).join('');

        // Apply filters to URLs to show counts
        let urlsToRender = e.urls;
        if (currentSourceFilter !== 'all') {
            urlsToRender = e.urls.filter(u => u.source === currentSourceFilter);
        }

        // Deduplicate URLs for the accordion view
        const mergedUrlsMap = {};
        urlsToRender.forEach(u => {
            const urlStr = u.url.trim();
            if (!mergedUrlsMap[urlStr]) {
                mergedUrlsMap[urlStr] = {
                    url: urlStr,
                    status: u.status || 'Offline',
                    sources: new Set(),
                    last_visit: u.last_visit || ''
                };
            }
            if (u.source) {
                mergedUrlsMap[urlStr].sources.add(u.source);
            }
            if (u.status === 'Online') {
                mergedUrlsMap[urlStr].status = 'Online';
            }
            if (u.last_visit && (!mergedUrlsMap[urlStr].last_visit || u.last_visit > mergedUrlsMap[urlStr].last_visit)) {
                mergedUrlsMap[urlStr].last_visit = u.last_visit;
            }
        });

        const mergedUrls = Object.values(mergedUrlsMap);
        const onlineCount = mergedUrls.filter(u => u.status === 'Online').length;
        const totalCount = mergedUrls.length;

        // Generate nested table HTML
        const nestedRowsHtml = mergedUrls.map(u => {
            const isOnline = u.status === 'Online';
            
            // Generate source badges for the individual URL
            const urlSourceBadges = Array.from(u.sources).map(s => {
                let label = s;
                let cls = s;
                if (s === 'ransomware.live') { label = 'R.Live'; cls = 'ransomware-live'; }
                else if (s === 'ransomfeed') { label = 'RFeed'; cls = 'ransomfeed'; }
                else if (s === 'ransomlook') { label = 'RLook'; cls = 'ransomlook'; }
                else if (s === 'watchguard') { label = 'WatchGuard'; cls = 'watchguard'; }
                else if (s.startsWith('github:')) { label = s.substring(7); cls = 'github'; }
                return `<span class="source-tag ${cls}">${esc(label)}</span>`;
            }).join(' ');

            return `
                <tr>
                    <td class="nested-url-cell">
                        <span class="url-dot ${isOnline ? 'online' : 'offline'}"></span>
                        <a href="${esc(u.url)}" target="_blank" class="nested-link">${esc(u.url)}</a>
                        <button class="copy-url-btn" onclick="copyToClipboard('${esc(u.url)}', this); event.stopPropagation();" title="Copy URL">📋</button>
                    </td>
                    <td>
                        <span class="status-indicator ${isOnline ? 'online' : 'offline'}">
                            <span class="status-pip ${isOnline ? 'online' : 'offline'}"></span>
                            ${isOnline ? 'Online' : 'Offline'}
                        </span>
                    </td>
                    <td><div class="source-tags">${urlSourceBadges}</div></td>
                    <td class="last-visit-cell">${esc(u.last_visit) || 'N/A'}</td>
                </tr>
            `;
        }).join('');

        const detailsRowHtml = `
            <tr class="details-row" id="details-${esc(e.key)}">
                <td colspan="6">
                    <div class="details-content">
                        <table class="nested-links-table">
                            <thead>
                                <tr>
                                    <th>Onion URL / Invite Link</th>
                                    <th>Status</th>
                                    <th>Discovered Sources</th>
                                    <th>Last Visited</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${nestedRowsHtml || '<tr><td colspan="4" class="no-urls-placeholder">No links matching the active filters.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </td>
            </tr>
        `;

        return `
            <tr class="entity-row" data-key="${esc(e.key)}" onclick="toggleTableRow('${esc(e.key)}')">
                <td class="arrow-cell"><span class="expand-arrow">▶</span></td>
                <td class="name-cell"><strong>${esc(e.name)}</strong></td>
                <td><span class="sector-badge ${sectorClass}">${sectorLabel}</span></td>
                <td>
                    <div class="status-indicator ${statusType}">
                        <span class="status-pip ${statusType}"></span>
                        ${statusLabel}
                    </div>
                </td>
                <td><div class="source-tags">${sourceTags}</div></td>
                <td>
                    <div class="links-counter-badge">
                        <span class="online-count">${onlineCount}</span> / <span class="total-count">${totalCount}</span> active
                    </div>
                </td>
            </tr>
            ${detailsRowHtml}
        `;
    }

    function getStatus(e) {
        if (e.total_urls === 0) return 'offline';
        if (e.online_count > 0 && e.offline_count > 0) return 'mixed';
        if (e.online_count > 0) return 'online';
        return 'offline';
    }

    // ═══ EXPAND/COLLAPSE ═══
    window.toggleTableRow = function(key) {
        const row = document.querySelector(`.entity-row[data-key="${key}"]`);
        const detailsRow = document.getElementById(`details-${key}`);
        if (row && detailsRow) {
            const isExpanded = row.classList.toggle('expanded');
            if (isExpanded) {
                detailsRow.classList.add('visible');
            } else {
                detailsRow.classList.remove('visible');
            }
        }
    };

    // ═══ COPY UTILS ═══
    window.copyToClipboard = function(text, btn) {
        navigator.clipboard.writeText(text).then(() => {
            const oldText = btn.textContent;
            btn.textContent = '✅';
            setTimeout(() => {
                btn.textContent = oldText;
            }, 1000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
        });
    };

    // ═══ UTILS ═══
    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }

})();
