/**
 * OnionExplorer v2 — Dashboard Client Logic
 * Groups/Markets tabs, entity cards with all URLs, search/filter/sort.
 * No charts.
 */

(function () {
    'use strict';

    // ═══ STATE ═══
    let rawData = {};         // { forums_groups: {}, markets: {}, telegram_links: {}, meta: {} }
    let statsData = {};
    let allForumsGroups = [];
    let allMarkets = [];
    let allTelegramLinks = [];
    let currentTab = 'forums_groups'; // 'forums_groups', 'markets', or 'telegram_links'
    let currentFilter = 'all'; // 'all', 'has-online', 'all-offline'
    let currentSort = 'name-asc';
    let currentSourceFilter = 'all';
    let searchQuery = '';

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
            if (meta.is_running) {
                if (runScrapeBtn) {
                    runScrapeBtn.disabled = true;
                    runScrapeBtn.textContent = '🔄 Scraper Running...';
                }
                setTimeout(checkScraperStatus, 3000);
            } else {
                if (runScrapeBtn) {
                    runScrapeBtn.disabled = false;
                    runScrapeBtn.textContent = '🔄 Scrape Now';
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
            document.getElementById('entityList').innerHTML =
                '<div class="no-results"><div class="icon">⚠️</div><p>Failed to load data. Is the server running?</p></div>';
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
        
        if (currentTab !== targetTab) {
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

        // Sort
        document.getElementById('sortSelect').addEventListener('change', (e) => {
            currentSort = e.target.value;
            applyAndRender();
        });

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

        // Trigger Scrape Button
        const runScrapeBtn = document.getElementById('runScrapeBtn');
        if (runScrapeBtn) {
            runScrapeBtn.addEventListener('click', async () => {
                runScrapeBtn.disabled = true;
                runScrapeBtn.textContent = '🔄 Scraper Running...';
                try {
                    const resp = await fetch('/api/scraper/run', { method: 'POST' });
                    const res = await resp.json();
                    if (res.status === 'started' || res.status === 'already_running') {
                        checkScraperStatus();
                    }
                } catch (err) {
                    console.error('Failed to trigger scrape:', err);
                    runScrapeBtn.disabled = false;
                    runScrapeBtn.textContent = '🔄 Scrape Now';
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
        } else {
            source = allTelegramLinks;
        }

        // Filter
        let filtered = source.filter(e => {
            // Search
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
            totalMatchingLinks += urlsToCount.length;
        });

        // Update search summary banner
        const banner = document.getElementById('searchSummaryBanner');
        const bannerText = document.getElementById('searchSummaryText');
        if (banner && bannerText) {
            if (searchQuery) {
                banner.style.display = 'flex';
                bannerText.innerHTML = `Search results for "<strong>${esc(searchQuery)}</strong>": Found <strong>${filtered.length}</strong> matching entries and <strong>${totalMatchingLinks}</strong> threat links.`;
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
            list.forEach(e => {
                let urlsToCount = e.urls;
                if (srcFilter !== 'all') {
                    urlsToCount = e.urls.filter(u => u.source === srcFilter);
                }
                urlsToCount.forEach(u => {
                    totalUrls++;
                    if (u.status === 'Online') {
                        totalOnline++;
                    } else {
                        totalOffline++;
                    }
                });
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
            // Check source freshness
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
        const container = document.getElementById('entityList');

        if (entities.length === 0) {
            container.innerHTML =
                '<div class="no-results"><div class="icon">🔍</div><p>No results match your search or filter.</p></div>';
            return;
        }

        container.innerHTML = entities.map(e => renderEntityCard(e)).join('');
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

    function renderEntityCard(e) {
        const statusType = getStatus(e);
        const statusLabel = statusType === 'mixed' ? 'Mixed' : statusType === 'online' ? 'Online' : 'Offline';
        
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

        // Filter URLs inside the card if a specific source filter is active
        let urlsToRender = e.urls;
        if (currentSourceFilter !== 'all') {
            urlsToRender = e.urls.filter(u => u.source === currentSourceFilter);
        }

        // Group URLs by source feed
        const groups = {};
        urlsToRender.forEach(u => {
            const src = u.source || 'Unknown';
            if (!groups[src]) groups[src] = [];
            groups[src].push(u);
        });

        // Generate visual HTML panel per source group
        const sourceSectionsHtml = Object.entries(groups).map(([srcName, urls]) => {
            const cleanSrcName = formatSourceName(srcName);
            const online = urls.filter(u => u.status === 'Online');
            const offline = urls.filter(u => u.status !== 'Online');

            const onlineRows = online.length > 0
                ? online.map(u => renderUrlRow(u)).join('')
                : '<div class="no-urls-placeholder">No active online links.</div>';

            const offlineRows = offline.length > 0
                ? offline.map(u => renderUrlRow(u)).join('')
                : '<div class="no-urls-placeholder">No inactive offline links.</div>';

            return `
                <div class="source-section">
                    <div class="source-section-title">📂 ${esc(cleanSrcName)}</div>
                    <div class="links-grid-container">
                        <div class="links-column online-column">
                            <div class="column-header online">🟢 Online Links (${online.length})</div>
                            <div class="url-list">
                                ${onlineRows}
                            </div>
                        </div>
                        <div class="links-column offline-column">
                            <div class="column-header offline">🔴 Offline Links (${offline.length})</div>
                            <div class="url-list">
                                ${offlineRows}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="entity-card" data-key="${esc(e.key)}">
                <div class="entity-card-header" onclick="toggleCard(this)">
                    <div class="entity-name-area">
                        <span class="expand-arrow">▶</span>
                        <span class="entity-name">${esc(e.name)}</span>
                        <div class="source-tags">${sourceTags}</div>
                    </div>
                    <div class="entity-meta">
                        <div class="meta-badge total"><span class="count">${e.total_urls}</span> links</div>
                        <div class="meta-badge online"><span class="count">${e.online_count}</span> up</div>
                        <div class="meta-badge offline"><span class="count">${e.offline_count}</span> down</div>
                        <div class="status-indicator ${statusType}">
                            <span class="status-pip ${statusType}"></span>
                            ${statusLabel}
                        </div>
                    </div>
                </div>
                <div class="entity-card-body">
                    ${sourceSectionsHtml || '<div class="no-urls-placeholder">No links match selected source filter.</div>'}
                </div>
            </div>
        `;
    }

    function renderUrlRow(u) {
        const isOnline = u.status === 'Online';
        return `
            <div class="url-row">
                <span class="url-dot ${isOnline ? 'online' : 'offline'}"></span>
                <span class="url-text">${esc(u.url)}</span>
            </div>
        `;
    }

    function getStatus(e) {
        if (e.total_urls === 0) return 'offline';
        if (e.online_count > 0 && e.offline_count > 0) return 'mixed';
        if (e.online_count > 0) return 'online';
        return 'offline';
    }

    // ═══ EXPAND/COLLAPSE ═══
    window.toggleCard = function (headerEl) {
        const card = headerEl.closest('.entity-card');
        if (card) card.classList.toggle('expanded');
    };

    // ═══ UTILS ═══
    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }

})();
