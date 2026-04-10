/*
    FILE ROLE:
    dashboard.js handles leaderboard table interactions and Chart.js rendering for the dashboard page.

    FLOW OVERVIEW:
    1. app.py index() sends data to index.html.
    2. index.html stores chart input data in JSON script tags and data attributes.
    3. dashboard.js reads that data and initializes Chart.js on canvas elements.
    4. User interactions (sort, search, top filters, sliders) update table rows and chart datasets.
*/

document.addEventListener('DOMContentLoaded', function () {
    const ROW_VISIBILITY_ANIMATION_MS = 300;
    const SEARCH_DEBOUNCE_MS = 250;

    // Dashboard script only runs on the leaderboard page where this table exists.
    const rankingTable = document.getElementById('by-rank-table');
    if (!rankingTable) {
        return;
    }

    // Reads JSON that is rendered by Jinja into <script type="application/json"> tags.
    // Data flow: app.py -> render_template(index.html) -> script tag text -> dashboard.js.
    function parseJsonScript(scriptElementId, fallbackValue) {
        const scriptElement = document.getElementById(scriptElementId);
        if (!scriptElement) {
            return fallbackValue;
        }
        try {
            return JSON.parse(scriptElement.textContent || '');
        } catch (error) {
            return fallbackValue;
        }
    }

    // Section 1: DOM references and initial page data.
    const dashboardConfigElement = document.getElementById('dashboard-config');
    const trendDefaultLimitFromConfig = dashboardConfigElement ? Number(dashboardConfigElement.dataset.trendDefaultLimit || 5) : 5;
    const decisiveMatches = dashboardConfigElement ? Number(dashboardConfigElement.dataset.decisiveMatches || 0) : 0;
    const outcomeDraws = dashboardConfigElement ? Number(dashboardConfigElement.dataset.draws || 0) : 0;

    const rankingTableBody = rankingTable.querySelector('tbody');
    const sortControlButtons = rankingTable.querySelectorAll('.sort-btn');
    const allowedSortKeys = new Set(['rank', 'name', 'points', 'matches', 'ratio']);
    const rankingEmptyRow = rankingTableBody.querySelector('[data-empty-row="rank"]');
    const pointsTable = document.querySelector('#rankings .table-card:nth-of-type(2) table');
    const pointsTableBody = pointsTable ? pointsTable.querySelector('tbody') : null;
    const pointsEmptyRow = pointsTableBody ? pointsTableBody.querySelector('[data-empty-row="points"]') : null;
    const searchInput = document.getElementById('ranking-search');
    const clearSearchButton = document.getElementById('ranking-search-clear');
    const topFilterButtons = document.querySelectorAll('.top-filter-btn');
    let currentSort = { key: 'rank', type: 'number', order: 'asc' };
    let currentTopLimit = 'all';
    let searchDebounceTimerId = null;

    // Section 2: Event listeners.
    sortControlButtons.forEach(function (sortButton) {
        sortButton.addEventListener('click', function () {
            const key = sortButton.dataset.sortKey;
            const type = sortButton.dataset.sortType;
            if (!allowedSortKeys.has(key)) {
                return;
            }
            const nextOrder = (currentSort.key === key && currentSort.order === 'asc') ? 'desc' : 'asc';
            applySort(key, type, nextOrder);
        });
    });

    topFilterButtons.forEach(function (topFilterButton) {
        topFilterButton.addEventListener('click', function () {
            currentTopLimit = topFilterButton.dataset.top || 'all';
            setActiveTopFilterButton(topFilterButton);
            applySearchAndTopFilter();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            if (searchDebounceTimerId) {
                clearTimeout(searchDebounceTimerId);
            }
            searchDebounceTimerId = setTimeout(applySearchAndTopFilter, SEARCH_DEBOUNCE_MS);
        });
    }

    if (clearSearchButton && searchInput) {
        clearSearchButton.addEventListener('click', function () {
            searchInput.value = '';
            applySearchAndTopFilter();
            searchInput.focus();
        });
    }

    // Section 3: Helper functions.
    function getDataRows(tableBody) {
        return Array.from(tableBody.querySelectorAll('tr.data-row'));
    }

    function applyRowVisibility(tableRow, shouldShow) {
        if (shouldShow) {
            if (tableRow.classList.contains('row-gone')) {
                tableRow.classList.remove('row-gone');
                tableRow.classList.add('row-enter');
                requestAnimationFrame(function () {
                    tableRow.classList.remove('row-enter');
                });
            }
        } else if (!tableRow.classList.contains('row-gone')) {
            tableRow.classList.add('row-leave');
            setTimeout(function () {
                tableRow.classList.add('row-gone');
                tableRow.classList.remove('row-leave');
            }, ROW_VISIBILITY_ANIMATION_MS);
        }
    }

    function syncEmptyState(tableBody, emptyRowElement) {
        if (!emptyRowElement) {
            return;
        }
        const hasVisibleRow = getDataRows(tableBody).some(function (tableRow) {
            return !tableRow.classList.contains('row-gone');
        });
        emptyRowElement.style.display = hasVisibleRow ? 'none' : '';
    }

    function setActiveTopFilterButton(selectedButton) {
        topFilterButtons.forEach(function (button) {
            button.classList.remove('active');
        });
        selectedButton.classList.add('active');
    }

    function applySearchAndTopFilter() {
        const searchTerm = (searchInput && searchInput.value ? searchInput.value : '').toLowerCase().trim();
        const topLimit = currentTopLimit === 'all' ? Number.POSITIVE_INFINITY : Number(currentTopLimit);

        [
            { tableBody: rankingTableBody, emptyRow: rankingEmptyRow },
            { tableBody: pointsTableBody, emptyRow: pointsEmptyRow }
        ].forEach(function (tableTarget) {
            if (!tableTarget.tableBody) {
                return;
            }
            const rows = getDataRows(tableTarget.tableBody);
            let matchingRowsSeen = 0;

            rows.forEach(function (tableRow) {
                const rowNameText = (tableRow.dataset.name || tableRow.textContent || '').toLowerCase();
                const matchesSearch = !searchTerm || rowNameText.includes(searchTerm);
                const isWithinTopFilter = matchingRowsSeen < topLimit;
                const shouldShowRow = matchesSearch && isWithinTopFilter;

                if (matchesSearch) {
                    matchingRowsSeen += 1;
                }
                applyRowVisibility(tableRow, shouldShowRow);
            });

            syncEmptyState(tableTarget.tableBody, tableTarget.emptyRow);
        });
    }

    function sortRankTable(key, type, order) {
        const rows = getDataRows(rankingTableBody);
        rows.sort(function (a, b) {
            const aValRaw = a.dataset[key];
            const bValRaw = b.dataset[key];

            let aVal = aValRaw;
            let bVal = bValRaw;
            if (type === 'number') {
                aVal = Number(aValRaw);
                bVal = Number(bValRaw);
            } else {
                aVal = (aValRaw || '').toLowerCase().trim();
                bVal = (bValRaw || '').toLowerCase().trim();
            }

            if (aVal < bVal) {
                return order === 'asc' ? -1 : 1;
            }
            if (aVal > bVal) {
                return order === 'asc' ? 1 : -1;
            }

            return Number(a.dataset.rank) - Number(b.dataset.rank);
        });

        rows.forEach(function (row) {
            rankingTableBody.appendChild(row);
        });
    }

    function updateSortIndicators(activeKey, activeOrder) {
        sortControlButtons.forEach(function (sortButton) {
            const indicator = sortButton.querySelector('.sort-indicator');
            if (!indicator) {
                return;
            }

            if (sortButton.dataset.sortKey === activeKey) {
                indicator.textContent = activeOrder === 'asc' ? '▲' : '▼';
            } else {
                indicator.textContent = '↕';
            }
        });
    }

    function applySort(key, type, order) {
        sortRankTable(key, type, order);
        currentSort = { key: key, type: type, order: order };
        updateSortIndicators(key, order);
        applySearchAndTopFilter();
    }

    applySort('rank', 'number', 'asc');
    applySearchAndTopFilter();

    // Chart data preparation: read server-provided JSON payloads from the template.

    const topPlayersRange = document.getElementById('top-players-range');
    const topPlayersRangeValue = document.getElementById('top-players-range-value');
    const allTopPointLabels = parseJsonScript('dashboard-data-top-labels', []);
    const allTopPointValues = parseJsonScript('dashboard-data-top-values', []);

    const chartColors = ['#14b8a6', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7'];
    const trendLineColors = ['#0ea5e9', '#f97316', '#22c55e', '#e11d48', '#8b5cf6', '#14b8a6', '#f59e0b', '#84cc16', '#6366f1', '#06b6d4', '#ef4444', '#10b981'];

    function hexToRgba(hex, alpha) {
        const cleanHex = hex.replace('#', '');
        const value = parseInt(cleanHex, 16);
        const r = (value >> 16) & 255;
        const g = (value >> 8) & 255;
        const b = value & 255;
        return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
    }

    function getPaletteBarColors(count, opacity) {
        return Array.from({ length: count }, function (_, i) {
            return hexToRgba(chartColors[i % chartColors.length], opacity);
        });
    }

    function getTopNChartData(limit) {
        return {
            labels: allTopPointLabels.slice(0, limit),
            values: allTopPointValues.slice(0, limit)
        };
    }

    const initialTopData = getTopNChartData(5);

    // Chart initialization: points leaderboard (horizontal bar chart).
    const topPlayersChart = new Chart(document.getElementById('topPointsChart'), {
        type: 'bar',
        data: {
            labels: initialTopData.labels,
            datasets: [{
                label: 'Points',
                data: initialTopData.values,
                backgroundColor: getPaletteBarColors(initialTopData.values.length, 0.85),
                borderRadius: 8,
                barThickness: 16,
                maxBarThickness: 18
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 400,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#171717',
                    borderColor: 'rgba(20, 184, 166, 0.35)',
                    borderWidth: 1,
                    titleColor: '#e5e5e5',
                    bodyColor: '#e5e5e5',
                    padding: 10,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    ticks: { color: '#a1a1aa', font: { size: 11 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#a1a1aa', font: { size: 11 } }
                }
            }
        }
    });

    function updateTopPlayersChart(limit) {
        const nextData = getTopNChartData(limit);
        topPlayersChart.data.labels = nextData.labels;
        topPlayersChart.data.datasets[0].data = nextData.values;
        topPlayersChart.data.datasets[0].backgroundColor = getPaletteBarColors(nextData.values.length, 0.85);
        topPlayersChart.update();
    }

    if (topPlayersRange && topPlayersRangeValue) {
        topPlayersRange.addEventListener('input', function () {
            const limit = Number(topPlayersRange.value);
            topPlayersRangeValue.textContent = 'Top ' + limit;
            updateTopPlayersChart(limit);
        });
    }

    const trendLabels = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'];
    const allTrendPlayers = parseJsonScript('dashboard-data-trend-players', []);

    function clampRank(value, maxRank) {
        return Math.min(maxRank, Math.max(1, value));
    }

    function getSeededValue(name, playerIndex, weekIndex) {
        const input = name + '-' + playerIndex + '-' + weekIndex;
        let hash = 0;
        for (let i = 0; i < input.length; i += 1) {
            hash = ((hash << 5) - hash) + input.charCodeAt(i);
            hash |= 0;
        }
        return Math.abs(hash);
    }

    function getTrendStep(name, playerIndex, weekIndex) {
        const seeded = getSeededValue(name, playerIndex, weekIndex);
        const magnitude = (seeded % 3) + 1;
        const direction = ((seeded >> 3) % 2 === 0) ? 1 : -1;
        const bias = ((playerIndex + weekIndex) % 5 === 0) ? (playerIndex % 2 === 0 ? -1 : 1) : 0;
        let step = (direction * magnitude) + bias;
        step = Math.max(-3, Math.min(3, step));
        if (step === 0) {
            step = direction;
        }
        return step;
    }

    function buildSimulatedTrend(player, playerIndex, totalPlayers) {
        const points = Array(trendLabels.length).fill(player.rank);
        points[trendLabels.length - 1] = player.rank;

        let nextRank = player.rank;
        for (let i = trendLabels.length - 2; i >= 0; i -= 1) {
            const step = getTrendStep(player.name, playerIndex, i);
            let previousRank = clampRank(nextRank + step, totalPlayers);
            if (previousRank === nextRank) {
                previousRank = clampRank(nextRank + (step > 0 ? 1 : -1), totalPlayers);
            }
            points[i] = previousRank;
            nextRank = previousRank;
        }

        return points;
    }

    function getTrendDatasets(limit) {
        const visiblePlayers = allTrendPlayers.slice(0, limit);
        const maxRank = Math.max(allTrendPlayers.length, 1);

        return visiblePlayers.map(function (player, index) {
            const color = trendLineColors[index % trendLineColors.length];
            const isTopThree = index < 3;
            const baseOpacity = isTopThree ? 1 : 0.55;
            const baseBorderWidth = isTopThree ? 3 : 1.6;
            return {
                label: player.name,
                data: buildSimulatedTrend(player, index, maxRank),
                borderColor: hexToRgba(color, baseOpacity),
                backgroundColor: hexToRgba(color, baseOpacity),
                pointBackgroundColor: hexToRgba(color, baseOpacity),
                pointBorderColor: hexToRgba(color, baseOpacity),
                borderWidth: baseBorderWidth,
                pointRadius: isTopThree ? 2.4 : 1.6,
                pointHoverRadius: 4,
                tension: 0.3,
                fill: false,
                _baseColor: color,
                _baseOpacity: baseOpacity,
                _baseBorderWidth: baseBorderWidth
            };
        });
    }

    function setTrendLegendMode(limit) {
        const compactLegend = limit > 8;
        rankingTrendChart.options.plugins.legend.display = true;
        rankingTrendChart.options.plugins.legend.labels.font = {
            size: compactLegend ? 9 : 11
        };
        rankingTrendChart.options.plugins.legend.labels.boxWidth = compactLegend ? 16 : 28;
        rankingTrendChart.options.plugins.legend.labels.boxHeight = compactLegend ? 6 : 8;
        rankingTrendChart.options.plugins.legend.labels.padding = compactLegend ? 8 : 12;
    }

    function applyTrendFocus(activeIndex) {
        rankingTrendChart.data.datasets.forEach(function (dataset, index) {
            const color = dataset._baseColor || trendLineColors[index % trendLineColors.length];
            const baseOpacity = dataset._baseOpacity || (index < 3 ? 1 : 0.55);
            const baseWidth = dataset._baseBorderWidth || (index < 3 ? 3 : 1.6);
            const isActive = activeIndex === index;
            const dimOthers = activeIndex !== null && !isActive;

            const opacity = isActive ? 1 : (dimOthers ? 0.2 : baseOpacity);
            const width = isActive ? baseWidth + 2 : baseWidth;

            dataset.borderColor = hexToRgba(color, opacity);
            dataset.backgroundColor = hexToRgba(color, opacity);
            dataset.pointBackgroundColor = hexToRgba(color, opacity);
            dataset.pointBorderColor = hexToRgba(color, opacity);
            dataset.borderWidth = width;
        });
    }

    const rankingTrendRange = document.getElementById('ranking-trend-range');
    const rankingTrendRangeValue = document.getElementById('ranking-trend-range-value');
    const initialTrendLimit = Number(rankingTrendRange ? rankingTrendRange.value : trendDefaultLimitFromConfig);

    // Chart initialization: ranking trend over time for top players.
    const rankingTrendChart = new Chart(document.getElementById('rankingTrendChart'), {
        type: 'line',
        data: {
            labels: trendLabels,
            datasets: getTrendDatasets(initialTrendLimit)
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            onHover: function (event, activeElements, chart) {
                const activeIndex = activeElements.length ? activeElements[0].datasetIndex : null;
                applyTrendFocus(activeIndex);
                chart.update('none');
            },
            animation: {
                duration: 650,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e5e5e5',
                        usePointStyle: true,
                        pointStyle: 'line',
                        boxWidth: 28,
                        boxHeight: 8,
                        padding: 12,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#171717',
                    borderColor: 'rgba(20, 184, 166, 0.35)',
                    borderWidth: 1,
                    titleColor: '#e5e5e5',
                    bodyColor: '#e5e5e5',
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        title: function (items) {
                            return items[0] ? items[0].dataset.label : '';
                        },
                        label: function (context) {
                            return 'Rank: ' + context.parsed.y;
                        },
                        footer: function (items) {
                            return items[0] ? ('Period: ' + items[0].label) : '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    reverse: true,
                    beginAtZero: false,
                    grid: { color: 'rgba(255,255,255,0.06)' },
                    ticks: { color: '#a1a1aa', font: { size: 11 } },
                    title: {
                        display: true,
                        text: 'Rank (lower is better)'
                    }
                },
                x: {
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    ticks: { color: '#a1a1aa', font: { size: 11 } }
                }
            }
        }
    });

    function updateRankingTrendChart(limit) {
        rankingTrendChart.data.datasets = getTrendDatasets(limit);
        setTrendLegendMode(limit);
        applyTrendFocus(null);
        rankingTrendChart.update();
    }

    setTrendLegendMode(initialTrendLimit);
    applyTrendFocus(null);

    if (rankingTrendRange && rankingTrendRangeValue) {
        rankingTrendRange.addEventListener('input', function () {
            const limit = Number(rankingTrendRange.value);
            rankingTrendRangeValue.textContent = 'Top ' + limit;
            updateRankingTrendChart(limit);
        });
    }

    const winRatioLabels = ['Decisive Games', 'Draws'];
    const totalOutcomeMatches = decisiveMatches + outcomeDraws;

    // Chart initialization: overall decisive vs draw outcomes.
    new Chart(document.getElementById('winRatioChart'), {
        type: 'bar',
        data: {
            labels: winRatioLabels,
            datasets: [{
                data: [decisiveMatches, outcomeDraws],
                backgroundColor: getPaletteBarColors(winRatioLabels.length, 0.8),
                borderRadius: 8,
                barThickness: 22,
                maxBarThickness: 24
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 650,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#171717',
                    borderColor: 'rgba(20, 184, 166, 0.35)',
                    borderWidth: 1,
                    titleColor: '#e5e5e5',
                    bodyColor: '#e5e5e5',
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            const value = context.parsed.x;
                            const percent = totalOutcomeMatches > 0 ? Math.round((value * 100) / totalOutcomeMatches) : 0;
                            return context.label + ': ' + value + ' (' + percent + '% of ' + totalOutcomeMatches + ' matches)';
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.08)' },
                    ticks: { color: '#a1a1aa', font: { size: 11 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#a1a1aa', font: { size: 11 } }
                }
            }
        }
    });
});
