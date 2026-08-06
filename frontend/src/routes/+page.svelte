<script>
	import { onMount } from 'svelte';

	// ═══ STATE (Svelte 5 Runes) ═══
	let rawData = $state({ forums_groups: {}, markets: {}, telegram_links: {}, meta: {} });
	let currentTab = $state('all_sectors'); // 'all_sectors', 'forums_groups', 'markets', 'telegram_links'
	let currentFilter = $state('all');     // 'all', 'has-online', 'all-offline'
	let currentSort = $state('name-asc');
	let currentSourceFilter = $state('all');
	let searchQuery = $state('');

	let scraperState = $state({
		last_scrape: null,
		next_scrape: null,
		is_running: false,
		interval_minutes: 1440,
		last_error: null,
		scrape_count: 0
	});

	let recentLogs = $state([]);
	let expandedKeys = $state(new Set());
	let scanStatuses = $state({}); // { url: 'queued' | 'processing' }

	// Modals & Menu Popups
	let showSettingsDropdown = $state(false);
	let showScreenshotModal = $state(false);
	let modalImgSrc = $state('');
	let modalCaptionText = $state('');
	let isLightTheme = $state(false);

	let logsTerminal = $state(null);

	// ═══ DERIVED VALUES (Svelte 5 Runes) ═══
	let allForumsGroups = $derived(Object.values(rawData.forums_groups || {}));
	let allMarkets = $derived(Object.values(rawData.markets || {}));
	let allTelegramLinks = $derived(Object.values(rawData.telegram_links || {}));

	// Top Counters
	let countForumsGroups = $derived(allForumsGroups.length);
	let countMarkets = $derived(allMarkets.length);
	let countTelegram = $derived(allTelegramLinks.length);

	let countUrls = $derived(
		allForumsGroups.reduce((acc, e) => acc + (e.urls?.length || 0), 0) +
		allMarkets.reduce((acc, e) => acc + (e.urls?.length || 0), 0) +
		allTelegramLinks.reduce((acc, e) => acc + (e.urls?.length || 0), 0)
	);

	let countOnline = $derived(
		allForumsGroups.reduce((acc, e) => acc + (e.online_count || 0), 0) +
		allMarkets.reduce((acc, e) => acc + (e.online_count || 0), 0) +
		allTelegramLinks.reduce((acc, e) => acc + (e.online_count || 0), 0)
	);

	let countOffline = $derived(
		allForumsGroups.reduce((acc, e) => acc + (e.offline_count || 0), 0) +
		allMarkets.reduce((acc, e) => acc + (e.offline_count || 0), 0) +
		allTelegramLinks.reduce((acc, e) => acc + (e.offline_count || 0), 0)
	);

	// Dynamic checklist of discovered feed sources
	let discoveredSources = $derived(
		Array.from(new Set(
			[...allForumsGroups, ...allMarkets, ...allTelegramLinks].flatMap(e => e.sources || [])
		)).sort()
	);

	// Dynamic tab counts (filtered based on search/status/source options)
	let tabAllCount = $derived(
		allForumsGroups.length + allMarkets.length + allTelegramLinks.length
	);

	// Main Filtered Entity List
	let filteredEntities = $derived.by(() => {
		let list = [];
		if (currentTab === 'all_sectors') {
			list = [...allForumsGroups, ...allMarkets, ...allTelegramLinks];
		} else if (currentTab === 'forums_groups') {
			list = allForumsGroups;
		} else if (currentTab === 'markets') {
			list = allMarkets;
		} else if (currentTab === 'telegram_links') {
			list = allTelegramLinks;
		}

		// Apply Status Filter
		if (currentFilter === 'has-online') {
			list = list.filter(e => e.online_count > 0);
		} else if (currentFilter === 'all-offline') {
			list = list.filter(e => e.online_count === 0 && e.offline_count > 0);
		}

		// Apply Feed Source Filter
		if (currentSourceFilter !== 'all') {
			list = list.filter(e => e.sources && e.sources.includes(currentSourceFilter));
		}

		// Apply Search Query
		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase().trim();
			list = list.filter(e => {
				const matchesName = e.name.toLowerCase().includes(q);
				const matchesUrl = e.urls && e.urls.some(u => u.url.toLowerCase().includes(q));
				const matchesSource = e.sources && e.sources.some(s => s.toLowerCase().includes(q));
				return matchesName || matchesUrl || matchesSource;
			});
		}

		// Apply Sorting
		if (currentSort === 'name-asc') {
			list.sort((a, b) => a.name.localeCompare(b.name));
		} else if (currentSort === 'name-desc') {
			list.sort((a, b) => b.name.localeCompare(a.name));
		} else if (currentSort === 'urls-desc') {
			list.sort((a, b) => (b.urls?.length || 0) - (a.urls?.length || 0));
		} else if (currentSort === 'online-desc') {
			list.sort((a, b) => (b.online_count || 0) - (a.online_count || 0));
		}

		return list;
	});

	// ═══ API CALLS ═══
	async function loadData() {
		try {
			const res = await fetch('/api/data');
			if (res.ok) {
				rawData = await res.json();
			}
		} catch (err) {
			console.error('Failed to load API data:', err);
		}
	}

	async function loadScraperStatus() {
		try {
			const res = await fetch('/api/scraper/status');
			if (res.ok) {
				scraperState = await res.json();
			}
		} catch (err) {
			console.error('Failed to load scraper status:', err);
		}
	}

	async function fetchLogs() {
		try {
			const res = await fetch('/api/scraper/logs');
			if (res.ok) {
				recentLogs = await res.json();
			}
		} catch (err) {
			console.error('Failed to fetch logs:', err);
		}
	}

	async function triggerManualScrape() {
		try {
			scraperState.is_running = true;
			const res = await fetch('/api/scraper/run', { method: 'POST' });
			if (res.ok) {
				loadScraperStatus();
				fetchLogs();
			}
		} catch (err) {
			console.error('Failed to run manual scrape:', err);
		}
	}

	async function updateConfigInterval(event) {
		const val = parseInt(event.target.value);
		try {
			const res = await fetch('/api/config', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ interval_minutes: val })
			});
			if (res.ok) {
				const json = await res.json();
				scraperState.interval_minutes = json.interval_minutes;
				showSettingsDropdown = false;
			}
		} catch (err) {
			console.error('Failed to update interval:', err);
		}
	}

	async function triggerScan(entityKey, url) {
		scanStatuses[url] = 'queued';
		try {
			const resp = await fetch('/api/screenshot/check', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ entity_key: entityKey, url: url })
			});
			if (resp.ok) {
				const res = await resp.json();
				if (res.status === 'queued') {
					scanStatuses[url] = 'processing';
					
					let checkCount = 0;
					const checkInterval = setInterval(async () => {
						checkCount++;
						await loadData();
						
						// Fetch matching item to see if screenshot has populated
						const item = [...allForumsGroups, ...allMarkets, ...allTelegramLinks].find(x => x.key === entityKey);
						if (item) {
							const u = item.urls.find(link => link.url === url);
							if (u && (u.screenshot || checkCount >= 12)) {
								clearInterval(checkInterval);
								delete scanStatuses[url];
							}
						}
					}, 2500);
				} else {
					delete scanStatuses[url];
				}
			} else {
				delete scanStatuses[url];
			}
		} catch (err) {
			console.error('Error triggering link scan:', err);
			delete scanStatuses[url];
		}
	}

	// ═══ LOCAL EVENTS ═══
	function toggleRow(key) {
		if (expandedKeys.has(key)) {
			expandedKeys.delete(key);
		} else {
			expandedKeys.add(key);
		}
	}

	function openScreenshot(img, caption) {
		modalImgSrc = `/static/screenshots/${img}`;
		modalCaptionText = caption;
		showScreenshotModal = true;
	}

	function toggleTheme() {
		isLightTheme = !isLightTheme;
		if (isLightTheme) {
			document.body.classList.add('light-theme');
			localStorage.setItem('theme', 'light');
		} else {
			document.body.classList.remove('light-theme');
			localStorage.setItem('theme', 'dark');
		}
	}

	function copyToClipboard(text, event) {
		navigator.clipboard.writeText(text).then(() => {
			const originalText = event.target.textContent;
			event.target.textContent = '✅';
			setTimeout(() => {
				event.target.textContent = originalText;
			}, 1200);
		}).catch(err => {
			console.error('Could not copy URL:', err);
		});
	}

	// Dynamic tab counting
	function getTabCount(tabName) {
		if (tabName === 'all_sectors') {
			return allForumsGroups.length + allMarkets.length + allTelegramLinks.length;
		} else if (tabName === 'forums_groups') {
			return allForumsGroups.length;
		} else if (tabName === 'markets') {
			return allMarkets.length;
		} else if (tabName === 'telegram_links') {
			return allTelegramLinks.length;
		}
		return 0;
	}

	function getStatusClass(ent) {
		if (ent.total_urls === 0) return 'offline';
		if (ent.online_count > 0 && ent.offline_count > 0) return 'mixed';
		if (ent.online_count > 0) return 'online';
		return 'offline';
	}

	function getStatusLabel(ent) {
		if (ent.total_urls === 0) return 'Offline';
		if (ent.online_count > 0 && ent.offline_count > 0) return 'Mixed';
		if (ent.online_count > 0) return 'Online';
		return 'Offline';
	}

	// ═══ ONMOUNT POLLING ═══
	onMount(() => {
		loadData();
		loadScraperStatus();
		fetchLogs();

		// Set local theme state
		const savedTheme = localStorage.getItem('theme');
		if (savedTheme === 'light') {
			isLightTheme = true;
			document.body.classList.add('light-theme');
		}

		// Polling intervals
		const logsInterval = setInterval(fetchLogs, 2500);
		const statusInterval = setInterval(loadScraperStatus, 5000);

		return () => {
			clearInterval(logsInterval);
			clearInterval(statusInterval);
		};
	});

	// Auto scroll logs console
	$effect(() => {
		if (recentLogs && logsTerminal) {
			logsTerminal.scrollTop = logsTerminal.scrollHeight;
		}
	});
</script>

<div class="app-container">
	<!-- ═══ HEADER ═══ -->
	<header class="app-header">
		<div class="brand">
			<div class="brand-icon">🧅</div>
			<div class="brand-text">
				<h1>OnionExplorer</h1>
				<span class="tagline">Dark Web Threat Intelligence</span>
			</div>
		</div>
		<div class="header-right">
			<div class="search-box">
				<span class="search-icon">🔍</span>
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search groups, markets, URLs..."
					autocomplete="off"
				/>
			</div>
			<div class="scrape-status">
				<span class="status-dot {scraperState.is_running ? 'online animate-pulse' : 'offline'}"></span>
				<span>{scraperState.is_running ? 'Scraping feeds...' : 'Idle'}</span>
			</div>
			<button
				class="scrape-all-btn"
				onclick={triggerManualScrape}
				disabled={scraperState.is_running}
				title="Run manual scrape across all darkweb sources"
			>
				⚡ Scrape All Sources
			</button>
			<button class="theme-toggle-btn" onclick={toggleTheme}>
				{isLightTheme ? '🌙 Dark UI' : '☀️ Light UI'}
			</button>
			<div class="settings-menu-container">
				<button class="settings-btn" onclick={() => showSettingsDropdown = !showSettingsDropdown}>
					⚙️ Config
				</button>
				{#if showSettingsDropdown}
					<div class="settings-dropdown">
						<div class="settings-group">
							<label for="intervalSelect">Scrape Every:</label>
							<select id="intervalSelect" value={scraperState.interval_minutes} onchange={updateConfigInterval}>
								<option value="720">12 Hours</option>
								<option value="1440">24 Hours</option>
								<option value="2880">48 Hours</option>
							</select>
						</div>
						<button class="settings-action-btn" onclick={triggerManualScrape} disabled={scraperState.is_running}>
							🔄 Scrape Now
						</button>
					</div>
				{/if}
			</div>
		</div>
	</header>

	<!-- ═══ STATS ROW ═══ -->
	<section class="stats-row">
		<div class="stat-card cyan">
			<div class="stat-label">Forums/Groups</div>
			<div class="stat-value">{countForumsGroups}</div>
		</div>
		<div class="stat-card purple">
			<div class="stat-label">Markets</div>
			<div class="stat-value">{countMarkets}</div>
		</div>
		<div class="stat-card orange">
			<div class="stat-label">Telegram</div>
			<div class="stat-value">{countTelegram}</div>
		</div>
		<div class="stat-card yellow">
			<div class="stat-label">Total URLs</div>
			<div class="stat-value">{countUrls}</div>
		</div>
		<div class="stat-card green">
			<div class="stat-label">Online</div>
			<div class="stat-value">{countOnline}</div>
		</div>
		<div class="stat-card red">
			<div class="stat-label">Offline</div>
			<div class="stat-value">{countOffline}</div>
		</div>
	</section>

	<!-- ═══ TABS & EXPORTS ═══ -->
	<section class="controls-bar">
		<div class="tab-group">
			{#each ['all_sectors', 'forums_groups', 'markets', 'telegram_links'] as tabName}
				<button
					class="tab {currentTab === tabName ? 'active' : ''}"
					onclick={() => currentTab = tabName}
				>
					<span class="tab-icon">
						{#if tabName === 'all_sectors'}🌐{:else if tabName === 'forums_groups'}👥{:else if tabName === 'markets'}🏪{:else}📢{/if}
					</span>
					{tabName === 'all_sectors' ? 'All Sectors' : tabName === 'forums_groups' ? 'Forums & Groups' : tabName === 'markets' ? 'Markets' : 'Telegram Links'}
					<span class="tab-count">{getTabCount(tabName)}</span>
				</button>
			{/each}
		</div>
		<div class="export-group">
			<a
				href="/api/export/csv?sector={currentTab}&status={currentFilter}&source={currentSourceFilter}"
				class="export-btn csv"
			>
				📊 Export CSV
			</a>
			<a
				href="/api/export/markdown?sector={currentTab}&status={currentFilter}&source={currentSourceFilter}"
				class="export-btn md"
			>
				📝 Export Report
			</a>
		</div>
	</section>

	<!-- ═══ DASHBOARD CONTENT SPLIT ═══ -->
	<div class="dashboard-layout">
		<!-- ═══ SIDEBAR FILTERS ═══ -->
		<aside class="sidebar">
			<!-- Link Status Filters -->
			<div class="filter-section">
				<h3 class="filter-title">Link Status</h3>
				<div class="filter-group">
					<button
						class="btn-filter {currentFilter === 'all' ? 'active' : ''}"
						onclick={() => currentFilter = 'all'}
					>
						Show All
					</button>
					<button
						class="btn-filter {currentFilter === 'has-online' ? 'active' : ''}"
						onclick={() => currentFilter = 'has-online'}
					>
						Online Only
					</button>
					<button
						class="btn-filter {currentFilter === 'all-offline' ? 'active' : ''}"
						onclick={() => currentFilter = 'all-offline'}
					>
						Offline Only
					</button>
				</div>
			</div>

			<!-- Dynamic Feed Sources Checklist -->
			<div class="filter-section">
				<h3 class="filter-title">Aggregated Sources</h3>
				<div class="source-checkbox-list">
					<label class="source-checkbox-item">
						<input
							type="radio"
							name="sourceFilter"
							checked={currentSourceFilter === 'all'}
							onchange={() => currentSourceFilter = 'all'}
						/>
						<span class="checkbox-custom"></span>
						<span class="source-label">All Sources</span>
					</label>
					{#each discoveredSources as src}
						<label class="source-checkbox-item">
							<input
								type="radio"
								name="sourceFilter"
								checked={currentSourceFilter === src}
								onchange={() => currentSourceFilter = src}
							/>
							<span class="checkbox-custom"></span>
							<span class="source-label">
								{#if src === 'rlive'}Ransomware.Live{:else if src === 'rlook'}RansomLook{:else if src === 'rfeed'}RansomFeed{:else if src === 'watchguard'}WatchGuard{:else}{src.replace('github:', '')}{/if}
							</span>
						</label>
					{/each}
				</div>
			</div>

			<!-- Sorting Options -->
			<div class="filter-section">
				<h3 class="filter-title">Sort Settings</h3>
				<div class="filter-group vertical">
					<button
						class="btn-sort {currentSort === 'name-asc' ? 'active' : ''}"
						onclick={() => currentSort = 'name-asc'}
					>
						🔤 Name (A - Z)
					</button>
					<button
						class="btn-sort {currentSort === 'name-desc' ? 'active' : ''}"
						onclick={() => currentSort = 'name-desc'}
					>
						🔤 Name (Z - A)
					</button>
					<button
						class="btn-sort {currentSort === 'urls-desc' ? 'active' : ''}"
						onclick={() => currentSort = 'urls-desc'}
					>
						🔗 URL Count
					</button>
					<button
						class="btn-sort {currentSort === 'online-desc' ? 'active' : ''}"
						onclick={() => currentSort = 'online-desc'}
					>
						🟢 Active Links
					</button>
				</div>
			</div>
		</aside>

		<!-- ═══ DIRECTORY MAIN TABLE ═══ -->
		<main class="main-content">
			<div class="data-table-container">
				<table class="data-table">
					<thead>
						<tr>
							<th style="width: 40px;"></th>
							<th>Threat Actor / Entity</th>
							<th>Domain / Sector</th>
							<th>Overall Status</th>
							<th>Feeds</th>
							<th>Discovered Links</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredEntities as ent (ent.key)}
							<!-- Threat Actor Accordion Header -->
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
							<tr
								class="entity-row {expandedKeys.has(ent.key) ? 'expanded' : ''}"
								onclick={() => toggleRow(ent.key)}
							>
								<td class="arrow-cell">
									<span class="expand-arrow">{expandedKeys.has(ent.key) ? '▼' : '▶'}</span>
								</td>
								<td class="name-cell">
									<strong>{ent.name}</strong>
								</td>
								<td>
									<span class="sector-badge {ent.sector || 'forums_groups'}">
										{#if ent.sector === 'forums_groups'}Forum{:else if ent.sector === 'markets'}Market{:else}Telegram{/if}
									</span>
								</td>
								<td>
									<div class="status-indicator {getStatusClass(ent)}">
										<span class="status-pip {getStatusClass(ent)}"></span>
										{getStatusLabel(ent)}
									</div>
								</td>
								<td>
									<div class="source-tags">
										{#each ent.sources || [] as s}
											<span class="source-tag {s.startsWith('github:') ? 'github' : s}">
												{#if s === 'rlive'}R.live{:else if s === 'rlook'}R.look{:else if s === 'rfeed'}R.feed{:else if s === 'watchguard'}WatchGuard{:else}{s.replace('github:', '')}{/if}
											</span>
										{/each}
									</div>
								</td>
								<td>
									<div class="links-counter-badge">
										<span class="online-count">{ent.online_count || 0}</span> / 
										<span class="total-count">{ent.urls?.length || 0}</span> active
									</div>
								</td>
							</tr>

							<!-- Expanded URLs Subtable Details Sheet -->
							{#if expandedKeys.has(ent.key)}
								<tr class="details-row visible" id="details-{ent.key}">
									<td colspan="6">
										<div class="details-content">
											<table class="nested-links-table">
												<thead>
													<tr>
														<th>Onion URL / Invite Link</th>
														<th>Status</th>
														<th>Discovered Sources</th>
														<th>Last Visited</th>
														<th style="width: 120px;">Screen</th>
														<th style="width: 100px;">Actions</th>
													</tr>
												</thead>
												<tbody>
													{#each ent.urls as u}
														{@const isOnline = u.status === 'Online' || u.status === 'Up'}
														{@const isTelegram = u.url.includes('t.me') || u.url.includes('telegram.me') || ent.sector === 'telegram_links'}
														<tr>
															<td class="nested-url-cell">
																<span class="url-dot {isOnline ? 'online' : 'offline'}"></span>
																<a href={u.url} target="_blank" class="nested-link">{u.url}</a>
																<button
																	class="copy-url-btn"
																	onclick={(e) => copyToClipboard(u.url, e)}
																	title="Copy URL"
																>
																	📋
																</button>
															</td>
															<td>
																<span class="status-indicator {isOnline ? 'online' : 'offline'}">
																	<span class="status-pip {isOnline ? 'online' : 'offline'}"></span>
																	{isOnline ? 'Up' : 'Down'}
																</span>
															</td>
															<td>
																<div class="source-tags">
																	{#each u.sources || [] as s}
																		<span class="source-tag {s.startsWith('github:') ? 'github' : s}">
																			{#if s === 'rlive'}R.live{:else if s === 'rlook'}R.look{:else if s === 'rfeed'}R.feed{:else if s === 'watchguard'}WatchGuard{:else}{s.replace('github:', '')}{/if}
																		</span>
																	{/each}
																</div>
															</td>
															<td class="last-visit-cell">{u.last_visit || 'N/A'}</td>
															<td>
																{#if isTelegram}
																	<span class="text-muted" style="font-size: 0.75rem; opacity: 0.6;">N/A (Telegram)</span>
																{:else if u.screenshot}
																	<div
																		class="screenshot-thumb-container"
																		role="button"
																		tabindex="0"
																		onclick={() => openScreenshot(u.screenshot, `${ent.name}: ${u.url}`)}
																		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') openScreenshot(u.screenshot, `${ent.name}: ${u.url}`); }}
																	>
																		<img
																			src="/static/screenshots/{u.screenshot}"
																			class="screenshot-thumb"
																			alt="Preview"
																		/>
																	</div>
																{:else}
																	<div class="screenshot-thumb-container" style="cursor: default;">
																		<div class="screenshot-placeholder">No Preview</div>
																	</div>
																{/if}
															</td>
															<td>
																{#if isTelegram}
																	<span class="text-muted" style="font-size: 0.75rem; opacity: 0.6;">N/A</span>
																{:else}
																	<button
																		class="check-status-btn"
																		onclick={() => triggerScan(ent.key, u.url)}
																		disabled={scanStatuses[u.url] !== undefined}
																	>
																		{#if scanStatuses[u.url] === 'queued'}
																			🔄 Queued...
																		{:else if scanStatuses[u.url] === 'processing'}
																			⏳ Processing...
																		{:else}
																			⚡ Scan
																		{/if}
																	</button>
																{/if}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									</td>
								</tr>
							{/if}
						{:else}
							<tr>
								<td colspan="6" class="no-urls-placeholder" style="padding: 40px; text-align: center; color: var(--text-muted);">
									No threat directories or matching entries found.
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</main>
	</div>

	<!-- ═══ ROLLING LIVE SCRAPER LOG CONSOLE ═══ -->
	<section class="log-section">
		<div class="log-header">
			<h2>Live Scraper Log Console</h2>
			<span class="pulse-indicator">
				<span class="pulse-dot"></span> Streaming Realtime logs
			</span>
		</div>
		<div class="log-terminal" bind:this={logsTerminal}>
			{#each recentLogs as line}
				{@const isErr = line.includes('[ERROR]')}
				{@const isWarn = line.includes('[WARNING]') || line.includes('⚠️')}
				{@const isSuccess = line.includes('Successfully') || line.includes('finished') || line.includes('✨') || line.includes('📸')}
				<div class="log-line {isErr ? 'error' : isWarn ? 'warning' : isSuccess ? 'success' : 'info'}">
					{line}
				</div>
			{/each}
		</div>
	</section>
</div>

<!-- ═══ LIGHTBOX PREVIEW SCREENSHOT MODAL ═══ -->
{#if showScreenshotModal}
	<div
		class="modal"
		style="display: block;"
		role="button"
		tabindex="0"
		onclick={() => showScreenshotModal = false}
		onkeydown={(e) => { if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') showScreenshotModal = false; }}
	>
		<span
			class="modal-close"
			role="button"
			tabindex="0"
			onclick={() => showScreenshotModal = false}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') showScreenshotModal = false; }}
		>
			&times;
		</span>
		<img
			class="modal-content"
			src={modalImgSrc}
			alt="Full Capture Preview"
			role="presentation"
			onclick={(e) => e.stopPropagation()}
		/>
		<div id="modalCaption">{modalCaptionText}</div>
	</div>
{/if}
