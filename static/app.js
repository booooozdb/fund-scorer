/**
 * 基金投资评分系统 v2.0 - Frontend
 * Supports: Long-term scoring, Short-term scoring, Category batch scoring
 */

// ============================================================
// State
// ============================================================

let currentData = null;
let currentCode = null;
let investType = 'long';  // 'long' | 'short'
let pollTimer = null;
let pollFailures = 0;
let charts = {};
let abortController = null;

// DOM helpers
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    fundCodeInput: $('#fundCodeInput'),
    searchBtn: $('#searchBtn'),
    btnText: $('.btn-text'),
    btnLoading: $('.btn-loading'),
    typeToggle: $('#typeToggle'),
    dashboard: $('#dashboard'),
    emptyState: $('#emptyState'),
    categoryResults: $('#categoryResults'),
    errorBanner: $('#errorBanner'),
    errorMessage: $('#errorMessage'),
    warningBanner: $('#warningBanner'),
    warningMessage: $('#warningMessage'),
    loadingOverlay: $('#loadingOverlay'),
    loadingText: $('#loadingText'),
    marketBadge: $('#marketBadge'),
    marketStatusText: $('#marketStatusText'),
    scoreTypeTitle: $('#scoreTypeTitle'),
    gaugeValue: $('#gaugeValue'),
    gaugeLabel: $('#gaugeLabel'),
    gaugeDesc: $('#gaugeDesc'),
    gaugeNeedle: $('#gaugeNeedle'),
    gaugeSegments: $('#gaugeSegments'),
    fundNameTitle: $('#fundNameTitle'),
    factorList: $('#factorList'),
    totalScoreDisplay: $('#totalScoreDisplay'),
    positionCard: $('#positionCard'),
    positionAction: $('#positionAction'),
    positionMultiplier: $('#positionMultiplier'),
    positionDesc: $('#positionDesc'),
    profitProbability: $('#profitProbability'),
    probBar: $('#probBar'),
    probText: $('#probText'),
    infoCode: $('#infoCode'),
    infoNav: $('#infoNav'),
    infoEstNav: $('#infoEstNav'),
    infoChange: $('#infoChange'),
    infoNavDate: $('#infoNavDate'),
    infoMarketStatus: $('#infoMarketStatus'),
    chipRsi: $('#chipRsi'),
    chipVol: $('#chipVol'),
    chipRet5: $('#chipRet5'),
    chipRet20: $('#chipRet20'),
    categoryTitle: $('#categoryTitle'),
    categoryMeta: $('#categoryMeta'),
    categoryTableBody: $('#categoryTableBody'),
};

// ============================================================
// Invest Type Switch
// ============================================================

function switchType(type) {
    investType = type;
    // Update toggle UI
    $$('.type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });
    // If we have a current fund, re-query
    if (currentCode && /^\d{6}$/.test(currentCode)) {
        searchFund();
    }
}

// ============================================================
// Chart.js Defaults
// ============================================================

Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#6b7280';
Chart.defaults.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--color-hairline').trim() || '#e8e8e3';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0,0,0,0.8)';
Chart.defaults.plugins.tooltip.titleFont = { size: 12 };
Chart.defaults.plugins.tooltip.bodyFont = { size: 11 };

function makeChartOptions() {
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#6b7280';
    const gridColor = getComputedStyle(document.documentElement).getPropertyValue('--color-hairline').trim() || '#e8e8e3';
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: textColor, usePointStyle: true, pointStyleWidth: 8, padding: 16 } },
            tooltip: { bodyFont: { size: 12 } }
        },
        scales: {
            x: { grid: { color: gridColor, drawBorder: false }, ticks: { color: textColor, maxTicksLimit: 10, font: { size: 10 } } },
            y: { grid: { color: gridColor, drawBorder: false }, ticks: { color: textColor, font: { size: 10 } } }
        }
    };
}

// ============================================================
// SVG Gauge
// ============================================================

function buildGaugeSegments() {
    const svg = dom.gaugeSegments;
    const cx = 100, cy = 100, r = 70;
    const segments = [
        { start: 0.00, end: 0.20, color: '#ef4444' },
        { start: 0.20, end: 0.40, color: '#f97316' },
        { start: 0.40, end: 0.60, color: '#9ca3af' },
        { start: 0.60, end: 0.80, color: '#0891b2' },
        { start: 0.80, end: 1.00, color: '#16a34a' },
    ];
    let html = '';
    segments.forEach(seg => {
        const a1 = Math.PI + Math.PI * seg.start;
        const a2 = Math.PI + Math.PI * seg.end;
        const x1 = cx + r * Math.cos(a1), y1 = cy - r * Math.sin(a1);
        const x2 = cx + r * Math.cos(a2), y2 = cy - r * Math.sin(a2);
        const largeArc = (seg.end - seg.start) > 0.5 ? 1 : 0;
        html += `<path d="M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 0 ${x2} ${y2}" fill="none" stroke="${seg.color}" stroke-width="14" stroke-linecap="butt" opacity="0.7"/>`;
    });
    svg.innerHTML = html;
}

function setGauge(score) {
    const cx = 100, cy = 100, r = 58;
    const angle = Math.PI + Math.PI * (score / 100);
    dom.gaugeNeedle.setAttribute('x2', cx + r * Math.cos(angle));
    dom.gaugeNeedle.setAttribute('y2', cy - r * Math.sin(angle));
}

function getBandClass(score) {
    if (score <= 20) return 'band-sell-now';
    if (score <= 40) return 'band-sell-batch';
    if (score <= 60) return 'band-hold';
    if (score <= 80) return 'band-buy-batch';
    return 'band-buy-heavy';
}

function getBandBgClass(score) {
    if (score <= 20) return 'bg-sell-now';
    if (score <= 40) return 'bg-sell-batch';
    if (score <= 60) return 'bg-hold';
    if (score <= 80) return 'bg-buy-batch';
    return 'bg-buy-heavy';
}

// ============================================================
// Render Functions - Single Fund
// ============================================================

function renderAll(data) {
    currentData = data;
    renderGauge(data);
    renderFundInfo(data);
    renderPosition(data);
    renderFactors(data);
    renderCharts(data);
    updateMarketBadge(data);
    updateScoreTitle(data);
}

function updateScoreTitle(data) {
    const typeLabel = data.invest_type === 'short' ? '短期 · 目标+5%' : '长期 · 估值+趋势';
    dom.scoreTypeTitle.textContent = '综合评分 · ' + typeLabel;
}

function renderGauge(data) {
    const score = data.total_score;
    const rec = data.recommendation;
    const bandClass = getBandClass(score);
    const bandBgClass = getBandBgClass(score);

    dom.gaugeValue.textContent = score;
    dom.gaugeValue.className = 'gauge-value ' + bandClass;
    dom.gaugeLabel.textContent = rec.text;
    dom.gaugeLabel.className = 'gauge-label ' + bandClass + ' ' + bandBgClass;
    dom.gaugeDesc.textContent = rec.description;
    dom.totalScoreDisplay.textContent = score;
    dom.totalScoreDisplay.className = 'total-score ' + bandClass;
    setGauge(score);
}

function renderFundInfo(data) {
    dom.fundNameTitle.textContent = data.fund_name;
    dom.infoCode.textContent = data.fund_code;
    dom.infoNav.textContent = data.current_nav.toFixed(4);
    dom.infoEstNav.textContent = data.estimated_nav ? data.estimated_nav.toFixed(4) : '--';
    dom.infoNavDate.textContent = data.nav_date || '--';

    const change = data.estimated_change_pct;
    if (change !== null && change !== undefined) {
        dom.infoChange.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
        dom.infoChange.style.color = change >= 0 ? '#16a34a' : '#ef4444';
    } else {
        dom.infoChange.textContent = '--'; dom.infoChange.style.color = '';
    }

    dom.infoMarketStatus.textContent = data.market_status_label || '--';

    if (data.indicators) {
        dom.chipRsi.textContent = data.indicators.current_rsi != null ? data.indicators.current_rsi.toFixed(1) : '--';
        dom.chipVol.textContent = data.indicators.volatility_annualized != null ? data.indicators.volatility_annualized.toFixed(1) + '%' : '--';
    }

    const prices = data.chart_data?.prices || [];
    const n = prices.length;
    if (n >= 6) {
        const ret5 = ((prices[n-1] / prices[n-6] - 1) * 100);
        dom.chipRet5.textContent = (ret5 >= 0 ? '+' : '') + ret5.toFixed(2) + '%';
        dom.chipRet5.style.color = ret5 >= 0 ? '#16a34a' : '#ef4444';
    } else { dom.chipRet5.textContent = '--'; dom.chipRet5.style.color = ''; }
    if (n >= 21) {
        const ret20 = ((prices[n-1] / prices[n-21] - 1) * 100);
        dom.chipRet20.textContent = (ret20 >= 0 ? '+' : '') + ret20.toFixed(2) + '%';
        dom.chipRet20.style.color = ret20 >= 0 ? '#16a34a' : '#ef4444';
    } else { dom.chipRet20.textContent = '--'; dom.chipRet20.style.color = ''; }

    if (data.data_warning) showWarning(data.data_warning);
}

function renderPosition(data) {
    const pos = data.position;
    if (!pos) { dom.positionCard.style.display = 'none'; return; }
    dom.positionCard.style.display = '';

    const actionMap = {
        'buy_heavy': '🟢 大幅加仓',
        'buy_batch': '🔵 分批加仓',
        'hold': '⚪ 持有不动',
        'sell_batch': '🟠 分批卖出',
        'sell_now': '🔴 立即卖出',
    };
    const rec = data.recommendation;
    dom.positionAction.textContent = actionMap[rec.level] || rec.text;
    dom.positionAction.style.color = rec.color;
    dom.positionMultiplier.textContent = pos.multiplier > 0 ? pos.multiplier.toFixed(1) + 'x' : '--';
    dom.positionMultiplier.style.color = rec.color;
    dom.positionDesc.textContent = pos.description || '';

    // Short-term profit probability
    if (data.short_info) {
        dom.profitProbability.style.display = 'flex';
        const prob = data.short_info.profit_probability;
        dom.probBar.style.width = prob + '%';
        dom.probText.textContent = '1个月内达+5%概率: ' + prob + '%';
    } else {
        dom.profitProbability.style.display = 'none';
    }
}

function renderFactors(data) {
    const scores = data.scores;
    const keys = Object.keys(scores);

    let html = '';
    keys.forEach(key => {
        const f = scores[key];
        if (!f) return;
        const pct = Math.round(f.score);
        const bandClass = getBandClass(f.score);
        html += `
            <div class="factor-row" onclick="toggleFactorDetail('${key}')" style="cursor:pointer">
                <span class="factor-label">${f.label}<br><span class="factor-weight">${f.weight}%</span></span>
                <div class="factor-bar-wrapper"><div class="factor-bar ${bandClass}" style="width:${pct}%"></div></div>
                <span class="factor-score ${bandClass}">${pct}</span>
                <span class="factor-outof">/100</span>
            </div>
            <div class="factor-detail-row" id="detail-${key}">${f.description} · 得分 ${pct}/100 · 权重 ${f.weight}%</div>
        `;
    });
    dom.factorList.innerHTML = html;
}

function toggleFactorDetail(key) {
    const el = document.getElementById('detail-' + key);
    if (el) el.classList.toggle('show');
}

function renderCharts(data) {
    const cd = data.chart_data;
    if (!cd || !cd.dates || cd.dates.length === 0) return;
    const dates = cd.dates;
    const opts = makeChartOptions();

    // Price + MA Chart
    const priceCtx = document.getElementById('priceChart');
    if (charts.price) charts.price.destroy();
    const priceDatasets = [
        { label: '净值', data: cd.prices, borderColor: '#2a78d6', borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.1, fill: false },
    ];
    if (cd.ma20 && cd.ma20.some(v => v !== null)) {
        priceDatasets.push({ label: 'MA20', data: cd.ma20, borderColor: '#eb6834', borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false });
    }
    if (cd.ma60 && cd.ma60.some(v => v !== null)) {
        priceDatasets.push({ label: 'MA60', data: cd.ma60, borderColor: '#1baf7a', borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false, borderDash: [4, 3] });
    }
    charts.price = new Chart(priceCtx, { type: 'line', data: { labels: dates, datasets: priceDatasets }, options: opts });

    // MACD Chart
    const macdCtx = document.getElementById('macdChart');
    if (charts.macd) charts.macd.destroy();
    const macdDatasets = [
        { label: 'MACD', data: cd.macd_line, borderColor: '#2a78d6', borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false, order: 1 },
        { label: 'Signal', data: cd.signal_line, borderColor: '#eb6834', borderWidth: 1.5, pointRadius: 0, tension: 0.1, fill: false, order: 1 },
    ];
    if (cd.histogram && cd.histogram.some(v => v !== null)) {
        const histColors = cd.histogram.map(v => v !== null ? (v >= 0 ? '#e34948' : '#008300') : 'transparent');
        macdDatasets.push({ label: 'Histogram', data: cd.histogram, backgroundColor: histColors, borderColor: histColors, borderWidth: 0, type: 'bar', barPercentage: 0.6, order: 0 });
    }
    charts.macd = new Chart(macdCtx, { type: 'line', data: { labels: dates, datasets: macdDatasets }, options: opts });

    // RSI Chart
    const rsiCtx = document.getElementById('rsiChart');
    if (charts.rsi) charts.rsi.destroy();
    charts.rsi = new Chart(rsiCtx, {
        type: 'line',
        data: { labels: dates, datasets: [{ label: 'RSI(14)', data: cd.rsi_values || [], borderColor: '#2a78d6', borderWidth: 2, pointRadius: 0, pointHoverRadius: 3, tension: 0.1, fill: false }] },
        options: {
            ...opts,
            scales: { ...opts.scales, y: { ...opts.scales.y, min: 0, max: 100, ticks: { stepSize: 20 } } },
            plugins: { ...opts.plugins, legend: { display: false } }
        },
        plugins: [{
            id: 'rsiBands',
            beforeDraw(chart) {
                const ctx = chart.ctx;
                const { top, bottom, left, right } = chart.chartArea;
                const yScale = chart.scales.y;
                [70, 30].forEach(val => {
                    const y = yScale.getPixelForValue(val);
                    ctx.save();
                    ctx.setLineDash([5, 5]);
                    ctx.strokeStyle = val === 70 ? 'rgba(239,68,68,0.5)' : 'rgba(22,163,74,0.5)';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(left, y); ctx.lineTo(right, y);
                    ctx.stroke();
                    ctx.fillStyle = val === 70 ? 'rgba(239,68,68,0.7)' : 'rgba(22,163,74,0.7)';
                    ctx.font = '10px sans-serif';
                    ctx.fillText(val === 70 ? '超买 70' : '超卖 30', right - 50, y - 4);
                    ctx.restore();
                });
            }
        }]
    });
}

function updateMarketBadge(data) {
    const isOpen = data.market_status && (data.market_status.startsWith('trading'));
    dom.marketBadge.className = 'market-badge' + (isOpen ? '' : ' closed');
    dom.marketStatusText.textContent = isOpen ? ('实时 · ' + data.market_status_label) : data.market_status_label;
}

// ============================================================
// Render Category Results
// ============================================================

function renderCategoryResults(data) {
    dom.dashboard.style.display = 'none';
    dom.emptyState.style.display = 'none';
    dom.categoryResults.style.display = 'flex';
    dom.positionCard.style.display = 'none';

    const typeLabel = data.invest_type === 'short' ? '短期' : '长期';
    dom.categoryTitle.textContent = data.category + ' 基金评分排行';
    dom.categoryMeta.textContent = typeLabel + '投资 · ' + data.scored_funds + '/' + data.total_funds + ' 只基金 · 评分由高到低';

    let html = '';
    data.results.forEach((r, i) => {
        const rank = i + 1;
        let rankClass = '';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';

        const scoreColor = r.recommendation_color || '#6b7280';
        const posAction = r.position_action;
        const posMult = r.position_multiplier;
        let posText = '--';
        if (posAction === 'buy') posText = '买入 ' + posMult.toFixed(1) + 'x';
        else if (posAction === 'sell') posText = '卖出 ' + posMult.toFixed(1) + 'x';
        else if (posAction === 'hold') posText = '持有';

        html += `
            <tr>
                <td class="col-rank"><span class="rank-num ${rankClass}">${rank}</span></td>
                <td class="col-sector">${r.sector}</td>
                <td class="col-code">${r.code}</td>
                <td class="col-score"><span class="score-badge" style="background:${scoreColor}20;color:${scoreColor}">${r.total_score}</span></td>
                <td class="col-rec"><span class="rec-badge" style="background:${scoreColor}20;color:${scoreColor}">${r.recommendation_text}</span></td>
                <td class="col-pos"><span class="pos-badge">${posText}</span></td>
                <td class="col-recommend">${r.recommend}</td>
            </tr>
        `;
    });
    dom.categoryTableBody.innerHTML = html;
}

// ============================================================
// API Calls
// ============================================================

async function fetchScore(code, type) {
    if (abortController) abortController.abort();
    abortController = new AbortController();
    const resp = await fetch(`/api/score/${code}?type=${type}`, { signal: abortController.signal });
    if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `请求失败 (HTTP ${resp.status})`);
    }
    return await resp.json();
}

async function fetchCategory(catName, type) {
    if (abortController) abortController.abort();
    abortController = new AbortController();
    const resp = await fetch(`/api/category/${encodeURIComponent(catName)}?type=${type}`, { signal: abortController.signal });
    if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `请求失败 (HTTP ${resp.status})`);
    }
    return await resp.json();
}

// ============================================================
// Search Logic
// ============================================================

const CATEGORY_KEYWORDS = ['宽基', '策略', '行业', '板块', '指数', 'broad', 'strategy', 'sector'];

function isCategorySearch(input) {
    return CATEGORY_KEYWORDS.some(k => input === k);
}

function mapCategory(input) {
    const m = { '指数': '宽基', 'broad': '宽基', '板块': '行业', 'sector': '行业', 'strategy': '策略' };
    return m[input] || input;
}

async function searchFund() {
    const input = dom.fundCodeInput.value.trim();
    if (!input) { showError('请输入基金代码或分类关键词'); return; }

    setLoading(true);
    dismissError();
    dismissWarning();
    hideAllPanels();

    try {
        if (isCategorySearch(input)) {
            // Category batch search
            const catName = mapCategory(input);
            dom.loadingOverlay.style.display = 'flex';
            dom.loadingText.textContent = '正在计算「' + catName + '」分类所有基金评分...';
            const data = await fetchCategory(catName, investType);
            dom.loadingOverlay.style.display = 'none';
            currentCode = input;
            renderCategoryResults(data);
            window.location.hash = catName;
        } else if (/^\d{6}$/.test(input)) {
            // Single fund search
            const data = await fetchScore(input, investType);
            currentCode = input;
            dom.dashboard.style.display = 'flex';
            renderAll(data);
            setupPolling(data);
            window.location.hash = input;
        } else {
            showError('请输入正确的6位数字基金代码，或输入：宽基 / 策略 / 行业');
        }
    } catch (err) {
        if (err.name === 'AbortError') return;
        dom.loadingOverlay.style.display = 'none';
        showError(err.message);
    } finally {
        setLoading(false);
    }
}

function quickSearch(val) {
    dom.fundCodeInput.value = val;
    searchFund();
}

function hideAllPanels() {
    dom.dashboard.style.display = 'none';
    dom.emptyState.style.display = 'none';
    dom.categoryResults.style.display = 'none';
}

function setLoading(loading) {
    dom.searchBtn.disabled = loading;
    dom.btnText.style.display = loading ? 'none' : '';
    dom.btnLoading.style.display = loading ? 'flex' : '';
}

function showError(msg) {
    dom.errorMessage.textContent = msg;
    dom.errorBanner.style.display = 'flex';
}

function dismissError() { dom.errorBanner.style.display = 'none'; }

function showWarning(msg) {
    dom.warningMessage.textContent = msg;
    dom.warningBanner.style.display = 'flex';
}

function dismissWarning() { dom.warningBanner.style.display = 'none'; }

// ============================================================
// Polling
// ============================================================

function setupPolling(data) {
    stopPolling();
    const isOpen = data.market_status && data.market_status.startsWith('trading');
    if (!isOpen) return;
    pollFailures = 0;
    pollTimer = setInterval(async () => {
        if (!currentCode || !/^\d{6}$/.test(currentCode)) return;
        try {
            const newData = await fetchScore(currentCode, investType);
            pollFailures = 0;
            updateRealtimeData(newData);
        } catch (err) {
            pollFailures++;
            if (pollFailures >= 3) { stopPolling(); showWarning('数据更新已停止，请手动刷新'); }
        }
    }, 30000);
    document.addEventListener('visibilitychange', onVisibilityChange);
}

function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    document.removeEventListener('visibilitychange', onVisibilityChange);
}

function onVisibilityChange() {
    if (document.hidden) {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    } else {
        if (currentCode && /^\d{6}$/.test(currentCode)) {
            pollFailures = 0;
            fetchScore(currentCode, investType).then(data => {
                updateRealtimeData(data);
                setupPolling(data);
            }).catch(() => {});
        }
    }
}

function updateRealtimeData(data) {
    currentData = data;
    dom.infoEstNav.textContent = data.estimated_nav ? data.estimated_nav.toFixed(4) : '--';
    dom.infoNav.textContent = data.current_nav.toFixed(4);
    const change = data.estimated_change_pct;
    if (change !== null && change !== undefined) {
        dom.infoChange.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
        dom.infoChange.style.color = change >= 0 ? '#16a34a' : '#ef4444';
    }
    dom.infoMarketStatus.textContent = data.market_status_label || '--';
    updateMarketBadge(data);
}

// ============================================================
// Initialize
// ============================================================

function init() {
    buildGaugeSegments();
    setGauge(0);

    dom.fundCodeInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') searchFund();
    });

    dom.fundCodeInput.focus();

    // Check URL hash
    const hash = window.location.hash.replace('#', '');
    if (hash) {
        dom.fundCodeInput.value = hash;
        searchFund();
    }
}

document.addEventListener('DOMContentLoaded', init);
