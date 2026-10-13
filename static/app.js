/**
 * SAMANEH RETENTION - PRINCIPAL ENTERPRISE SAAS INTERFACE LOGIC
 * Linear & Stripe Design System Implementation
 * Phase 1 Client-Server Architecture (Vanilla JS)
 */

// ---------------------------------------------------------------------------
// Helpers & Typography
// ---------------------------------------------------------------------------
const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

function toPersianDigits(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[0-9]/g, d => FA_DIGITS[d]);
}

function fmtInt(val) {
  if (val === null || val === undefined || isNaN(val)) return '۰';
  const n = Math.round(Number(val));
  const parts = Math.abs(n).toLocaleString('en-US');
  const sign = n < 0 ? '−' : '';
  return sign + toPersianDigits(parts);
}

function fmtToman(value) {
  const v = Number(value) || 0;
  if (v >= 1e9) {
    return { num: toPersianDigits((v / 1e9).toFixed(1)), unit: 'میلیارد تومان' };
  }
  if (v >= 1e6) {
    return { num: toPersianDigits(Math.round(v / 1e6).toLocaleString('en-US')), unit: 'میلیون تومان' };
  }
  return { num: fmtInt(v), unit: 'تومان' };
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `saas-toast ${type}`;
  toast.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px)';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function copyToClipboard(text, successMsg = 'متن با موفقیت کپی شد!') {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg);
    }).catch(() => {
      fallbackCopy(text, successMsg);
    });
  } else {
    fallbackCopy(text, successMsg);
  }
}

function fallbackCopy(text, successMsg) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  document.body.appendChild(textArea);
  textArea.select();
  try {
    document.execCommand('copy');
    showToast(successMsg);
  } catch (err) {
    console.warn('Copy failed:', err);
  }
  document.body.removeChild(textArea);
}

// ---------------------------------------------------------------------------
// Global Application State
// ---------------------------------------------------------------------------
const state = {
  insights: null,
  radarScanCount: 0,
  radarAutoRunning: true,
  radarCountdownInterval: null,
  radarCountdownSeconds: 6,
  radarElapsed: 0,
  radarDetailsOpen: new Set(),
  allCustomers: [],
  filteredCustomers: [],
  activeCustomer: null,
  registeredActions: new Set(),
  chartInstances: {},
};

// ---------------------------------------------------------------------------
// Linear-style Segmented Tab Switching
// ---------------------------------------------------------------------------
function initNavigation() {
  const tabBtns = document.querySelectorAll('.nav-tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-tab');

      // Update button active state
      tabBtns.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');

      // Update panels
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
      });
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }

      // Tab specific triggers
      if (targetId === 'tab-insights') {
        if (!state.insights) {
          loadInsights();
        }
      } else if (targetId === 'tab-radar') {
        fetchRadarCustomers();
        if (state.radarAutoRunning) {
          startRadarLoop();
        }
      } else if (targetId === 'tab-customers') {
        if (state.allCustomers.length === 0) {
          loadCustomers();
        }
      }
    });
  });
}

// ---------------------------------------------------------------------------
// SECTION 1: Business Intelligence & Strategic Analytics
// ---------------------------------------------------------------------------
async function loadInsights() {
  const container = document.getElementById('analyses-container');
  try {
    const res = await fetch('/api/insights');
    if (!res.ok) {
      throw new Error(`خطای دریافت (${res.status})`);
    }
    const data = await res.json();
    if (!data || !data.dataset) {
      throw new Error('داده‌های دریافتی نامعتبر است');
    }
    state.insights = data;

    renderInsightsKPIs();
    initSlider();
    renderAnalysesList(data.analyses || []);
    renderRoadmap(data.roadmap || []);
  } catch (err) {
    console.error('Failed to load /api/insights:', err);
    if (container) {
      container.innerHTML = `
        <div class="ui-card" style="padding: 24px; text-align: center; border-color: var(--risk-high-border); background: var(--risk-high-bg);">
          <h4 style="color: var(--risk-high); margin-bottom: 6px; font-weight: 700;">خطا در دریافت اطلاعات مرکز هوش تجاری</h4>
          <p style="color: var(--muted); font-size: 13px;">${err.message}</p>
          <button type="button" class="btn-subtle" style="margin-top: 14px;" onclick="loadInsights()">تلاش مجدد</button>
        </div>
      `;
    }
  }
}

function renderInsightsKPIs() {
  if (!state.insights || !state.insights.dataset) return;
  const d = state.insights.dataset;

  const churnRateElem = document.getElementById('kpi-churn-rate');
  if (churnRateElem) churnRateElem.textContent = `${toPersianDigits(d.churn_rate || 0)}٪`;

  const churnedElem = document.getElementById('kpi-churned-count');
  if (churnedElem) churnedElem.textContent = toPersianDigits(d.churned || 0);

  const retainedElem = document.getElementById('kpi-retained-count');
  if (retainedElem) retainedElem.textContent = `${fmtInt(d.retained || 0)} مشتری وفادار و ماندگار`;

  const monitoredElem = document.getElementById('kpi-total-monitored');
  if (monitoredElem) monitoredElem.textContent = `بر پایه پایش ${fmtInt(d.n || 0)} مشتری تاریخی`;

  const powerElem = document.getElementById('kpi-detection-power');
  if (powerElem) powerElem.textContent = `${toPersianDigits(d.detection_power || 0)}٪`;

  updateLossCalculation(10000);
}

function initSlider() {
  const slider = document.getElementById('total-customers-slider');
  const display = document.getElementById('slider-val-display');
  if (!slider || !display) return;

  slider.oninput = (e) => {
    const val = Number(e.target.value) || 10000;
    display.textContent = `${fmtInt(val)} نفر`;
    updateLossCalculation(val);
  };
}

function updateLossCalculation(totalCustomers) {
  if (!state.insights || !state.insights.dataset) return;
  const d = state.insights.dataset;
  const churnRate = (d.churn_rate || 16.84) / 100;
  const estimatedChurners = totalCustomers * churnRate;
  const assumedValuePerCustomer = 5000000; // 5 Million Toman
  const totalLoss = estimatedChurners * assumedValuePerCustomer;

  const { num, unit } = fmtToman(totalLoss);
  const lossValElem = document.getElementById('kpi-loss-value');
  const lossUnitElem = document.getElementById('kpi-loss-unit');

  if (lossValElem) lossValElem.textContent = num;
  if (lossUnitElem) lossUnitElem.textContent = unit;
}

function renderAnalysesList(analyses) {
  const container = document.getElementById('analyses-container');
  if (!container) return;

  if (!analyses || analyses.length === 0) {
    container.innerHTML = '<div class="saas-loader-box">هیچ تحلیلی برای نمایش وجود ندارد.</div>';
    return;
  }

  container.innerHTML = '';

  analyses.forEach((an, index) => {
    const card = document.createElement('div');
    card.className = 'ui-card analysis-deep-card';

    // Numbers HTML
    const nums = an.numbers || [];
    const numsHtml = nums.map(n => `
      <div class="metric-pill-box ${n.color || 'blue'}">
        <b>${toPersianDigits(n.value)}</b>
        <span>${n.label}</span>
      </div>
    `).join('');

    // Bullets HTML
    const bullets = an.bullets || [];
    const bulletsHtml = bullets.map(b => `<li>${b}</li>`).join('');

    card.innerHTML = `
      <div class="analysis-info-side">
        <div class="analysis-badge-row">
          <span class="stat-discovery-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
            کشف آماری
          </span>
          <span class="stat-kicker-title">${an.kicker || ''}</span>
        </div>

        <h3 class="analysis-headline">${an.title || ''}</h3>
        <div class="stat-tri-metrics">${numsHtml}</div>
        <ul class="analysis-bullet-list">${bulletsHtml}</ul>

        <div class="executive-takeaway-card">
          <b>پیام مدیریتی:</b> ${an.takeaway || ''}
        </div>
      </div>

      <div class="analysis-chart-side">
        <div class="chart-viewport-wrap" id="chart-wrap-${index}">
          <canvas id="chart-an-${index}"></canvas>
        </div>
      </div>
    `;

    container.appendChild(card);

    // Initialize Chart.js safely with slight delay for DOM painting
    setTimeout(() => {
      try {
        initAnalysisChart(an.chart_type, `chart-an-${index}`, `chart-wrap-${index}`);
      } catch (err) {
        console.warn(`Chart rendering error for ${an.chart_type}:`, err);
      }
    }, 60);
  });
}

function initAnalysisChart(type, canvasId, wrapId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (typeof Chart === 'undefined') {
    const wrap = document.getElementById(wrapId);
    if (wrap) {
      wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:12px;">کتابخانه گرافیکی لود نشد (نمایش آماری متن فعال است)</div>`;
    }
    return;
  }

  // Destroy previous instance
  if (state.chartInstances[canvasId]) {
    state.chartInstances[canvasId].destroy();
    delete state.chartInstances[canvasId];
  }

  const ctx = canvas.getContext('2d');
  const d = state.insights.dataset;
  const fontConfig = { family: 'Vazirmatn, Tahoma, sans-serif', size: 11 };
  const darkTooltip = {
    rtl: true,
    titleFont: { family: 'Vazirmatn, Tahoma, sans-serif', size: 12, weight: '700' },
    bodyFont: fontConfig,
    backgroundColor: '#003741',
    borderColor: '#006F83',
    borderWidth: 1,
    titleColor: '#99F2FF',
    bodyColor: '#FFFFFF',
    padding: 12,
    cornerRadius: 8,
    displayColors: false,
  };
  const darkGrid = { color: 'rgba(0, 55, 65, 0.08)', drawBorder: false };
  const tickColor = '#626264';

  try {
    let chartObj = null;

    if (type === 'complaint') {
      const compData = d.complain || { 'بدون شکایت': 10.9, 'دارای شکایت': 31.7 };
      chartObj = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['بدون شکایت', 'دارای شکایت'],
          datasets: [{
            data: [compData['بدون شکایت'], compData['دارای شکایت']],
            backgroundColor: ['#197A4B', '#CE0000'],
            borderRadius: 8,
            barThickness: 42,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...darkTooltip,
              callbacks: {
                label: (ctx) => `نرخ ریزش: ${toPersianDigits(ctx.raw)}٪`
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 42,
              ticks: { font: fontConfig, color: tickColor, callback: v => `${toPersianDigits(v)}٪` },
              grid: darkGrid
            },
            x: {
              ticks: { font: fontConfig, color: '#333333' },
              grid: { display: false }
            }
          }
        }
      });
    } else if (type === 'tenure') {
      const churnObj = d.tenure || {};
      const churn = Object.values(churnObj);
      const retention = churn.map(c => 100 - c);
      const labels = ['تا ۱ ماه', 'تا ۳ ماه', 'تا ۶ ماه', 'تا ۱۲ ماه', 'بیش از ۱۲ ماه'];

      chartObj = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'نرخ ماندگاری',
            data: retention,
            borderColor: '#00A3BF',
            borderWidth: 2.5,
            backgroundColor: 'rgba(0, 163, 191, 0.12)',
            fill: true,
            tension: 0.35,
            pointBackgroundColor: ['#CE0000', '#00A3BF', '#00A3BF', '#00A3BF', '#00A3BF'],
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: [7, 5, 5, 5, 5],
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...darkTooltip,
              callbacks: {
                label: (ctx) => `نرخ ماندگاری: ${toPersianDigits(ctx.raw ? ctx.raw.toFixed(1) : 0)}٪`
              }
            }
          },
          scales: {
            y: {
              min: 30,
              max: 100,
              ticks: { font: fontConfig, color: tickColor, callback: v => `${toPersianDigits(v)}٪` },
              grid: darkGrid
            },
            x: {
              ticks: { font: fontConfig, color: '#333333' },
              grid: { display: false }
            }
          }
        }
      });
    } else if (type === 'satisfaction') {
      const sc = state.insights.satisfaction_counts || {};
      const sat = d.satisfaction || {};
      const scores = [1, 2, 3, 4, 5];

      const loyal = scores.map(s => {
        const item = sc[s] || sc[String(s)];
        return item ? item.loyal : 0;
      });

      const churned = scores.map(s => {
        const item = sc[s] || sc[String(s)];
        return item ? item.churned : 0;
      });

      const rates = scores.map(s => {
        return sat[s] !== undefined ? sat[s] : (sat[String(s)] !== undefined ? sat[String(s)] : 0);
      });

      chartObj = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: scores.map(s => `امتیاز ${toPersianDigits(s)}`),
          datasets: [
            {
              type: 'line',
              label: 'نرخ ریزش',
              data: rates,
              borderColor: '#D97706',
              borderWidth: 2.8,
              tension: 0.3,
              yAxisID: 'y1',
              pointBackgroundColor: ['#D97706', '#D97706', '#D97706', '#D97706', '#CE0000'],
              pointBorderColor: '#FFFFFF',
              pointBorderWidth: 2,
              pointRadius: [5, 5, 5, 5, 8],
            },
            {
              type: 'bar',
              label: 'مشتریان وفادار',
              data: loyal,
              backgroundColor: '#00A3BF',
              borderRadius: 6,
              yAxisID: 'y',
            },
            {
              type: 'bar',
              label: 'مشتریان خارج‌شده',
              data: churned,
              backgroundColor: '#CE0000',
              borderRadius: 6,
              yAxisID: 'y',
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { font: fontConfig, color: '#333333', boxWidth: 12 }
            },
            tooltip: darkTooltip
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { font: fontConfig, color: tickColor, callback: v => toPersianDigits(v) },
              grid: darkGrid
            },
            y1: {
              position: 'right',
              min: 0,
              max: 30,
              ticks: { font: fontConfig, color: '#D97706', callback: v => `${toPersianDigits(v)}٪` },
              grid: { display: false }
            },
            x: {
              ticks: { font: fontConfig, color: '#333333' },
              grid: { display: false }
            }
          }
        }
      });
    } else if (type === 'category') {
      const catObj = d.category || {};
      const cats = Object.entries(catObj).sort((a, b) => b[1] - a[1]);
      const labels = cats.map(([k]) => {
        const names = {
          'Mobile Phone': 'موبایل و دیجیتال',
          'Fashion': 'مد و پوشاک',
          'Laptop & Accessory': 'لپ‌تاپ و تجهیزات',
          'Others': 'سایر محصولات',
          'Grocery': 'خواربار'
        };
        return names[k] || k;
      });
      const values = cats.map(([, v]) => v);
      const colors = ['#CE0000', '#D97706', '#00A3BF', '#006F83', '#197A4B'];

      chartObj = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: colors,
            borderRadius: 6,
            barThickness: 22,
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...darkTooltip,
              callbacks: { label: ctx => `نرخ ریزش: ${toPersianDigits(ctx.raw)}٪` }
            }
          },
          scales: {
            x: {
              beginAtZero: true,
              max: 35,
              ticks: { font: fontConfig, color: tickColor, callback: v => `${toPersianDigits(v)}٪` },
              grid: darkGrid
            },
            y: {
              ticks: { font: fontConfig, color: '#333333' },
              grid: { display: false }
            }
          }
        }
      });
    } else if (type === 'behaviour') {
      const distObj = d.distance || {};
      const distLabels = Object.keys(distObj);
      const distValues = Object.values(distObj);

      chartObj = new Chart(ctx, {
        type: 'line',
        data: {
          labels: distLabels.map(l => `${toPersianDigits(l)} کیلومتر`),
          datasets: [{
            label: 'ریزش بر اساس مسافت',
            data: distValues,
            borderColor: '#00A3BF',
            borderWidth: 2.5,
            backgroundColor: 'rgba(0, 163, 191, 0.12)',
            fill: true,
            tension: 0.25,
            pointBackgroundColor: ['#197A4B', '#D97706', '#CE0000'],
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...darkTooltip,
              callbacks: { label: ctx => `نرخ ریزش: ${toPersianDigits(ctx.raw)}٪` }
            }
          },
          scales: {
            y: {
              min: 10,
              max: 25,
              ticks: { font: fontConfig, color: tickColor, callback: v => `${toPersianDigits(v)}٪` },
              grid: darkGrid
            },
            x: {
              ticks: { font: fontConfig, color: '#333333' },
              grid: { display: false }
            }
          }
        }
      });
    }

    if (chartObj) {
      state.chartInstances[canvasId] = chartObj;
    }
  } catch (err) {
    console.error(`Error rendering chart ${type}:`, err);
  }
}

function renderRoadmap(roadmap) {
  const container = document.getElementById('roadmap-container');
  if (!container || !roadmap) return;
  container.innerHTML = '';

  roadmap.forEach(step => {
    const card = document.createElement('div');
    card.className = 'ui-card roadmap-step-card';

    const bullets = (step.bullets || []).map(b => `<li>${b}</li>`).join('');

    card.innerHTML = `
      <div>
        <span class="step-stage-tag">${step.stage || ''}</span>
        <h4 class="step-card-title">${step.title || ''}</h4>
        <ul class="step-bullets">${bullets}</ul>
      </div>
      <div class="step-target-metric">${step.target || ''}</div>
    `;

    container.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// SECTION 2: LIVE RADAR & RETENTION EXPERIMENT LAB
// ---------------------------------------------------------------------------
function initRadarAndLab() {
  // Toggle Auto Radar Switch
  const toggle = document.getElementById('auto-radar-toggle');
  if (toggle) {
    toggle.addEventListener('change', (e) => {
      state.radarAutoRunning = e.target.checked;
      const statusTag = document.getElementById('radar-status-tag');
      if (statusTag) {
        statusTag.textContent = state.radarAutoRunning
          ? `به‌روزرسانی خودکار | هر ${toPersianDigits(state.radarCountdownSeconds)} ثانیه`
          : 'پایش متوقف است';
      }
      if (state.radarAutoRunning) {
        startRadarLoop();
      } else {
        stopRadarLoop();
      }
    });
  }

  // Manual Scan Button
  const btnScan = document.getElementById('btn-manual-scan');
  if (btnScan) {
    btnScan.addEventListener('click', () => {
      fetchRadarCustomers();
      resetCountdown();
    });
  }

  // 3 Quick Scenario Chips
  const chipBtns = document.querySelectorAll('.chip-btn');
  chipBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-preset');
      applyLabPreset(preset);
    });
  });

  // Segmented Radios for Lab Form
  initSegmentedRadios();

  // Lab Form Submit
  const evalForm = document.getElementById('lab-eval-form');
  if (evalForm) {
    evalForm.addEventListener('submit', handleLabEvaluation);
  }

  // Initial Fetch & Start Loop
  fetchRadarCustomers();
  startRadarLoop();
}

function startRadarLoop() {
  stopRadarLoop();
  state.radarElapsed = 0;
  const progressFill = document.getElementById('radar-progress-bar');

  state.radarCountdownInterval = setInterval(() => {
    if (state.radarDetailsOpen.size > 0 || !state.radarAutoRunning) {
      return;
    }

    state.radarElapsed += 0.2;
    const pct = Math.min(100, (state.radarElapsed / state.radarCountdownSeconds) * 100);
    if (progressFill) progressFill.style.width = `${pct}%`;

    if (state.radarElapsed >= state.radarCountdownSeconds) {
      state.radarElapsed = 0;
      fetchRadarCustomers();
    }
  }, 200);
}

function stopRadarLoop() {
  if (state.radarCountdownInterval) {
    clearInterval(state.radarCountdownInterval);
    state.radarCountdownInterval = null;
  }
}

function resetCountdown() {
  state.radarElapsed = 0;
  const progressFill = document.getElementById('radar-progress-bar');
  if (progressFill) progressFill.style.width = '0%';
}

async function fetchRadarCustomers() {
  try {
    const res = await fetch('/api/radar');
    if (!res.ok) throw new Error('خطا در فراخوانی رادار');
    const customers = await res.json();
    state.radarScanCount++;

    const badge = document.getElementById('radar-scan-badge');
    if (badge) badge.textContent = `پایش شماره ${toPersianDigits(state.radarScanCount)}`;

    renderRadarCards(customers);
  } catch (err) {
    console.error('Error fetching radar customers:', err);
  }
}

function renderRadarCards(customers) {
  const container = document.getElementById('radar-cards-container');
  if (!container || !customers) return;
  container.innerHTML = '';

  customers.forEach(cust => {
    const card = document.createElement('div');
    card.className = `ui-card radar-customer-card card-${cust.tone}`;

    const riskVal = Math.round(cust.risk || 0);
    const tenureTxt = cust.tenure !== null && cust.tenure !== undefined
      ? `${toPersianDigits(Math.round(cust.tenure))} ماه`
      : 'ثبت نشده';

    const isStable = cust.tone === 'green';
    
    // Status Pill (with blinking pulse dot for critical)
    let pillHtml = '';
    if (cust.tone === 'red') {
      pillHtml = `<span class="pill pill-danger"><span class="pulse-dot"></span>بحرانی · ${toPersianDigits(riskVal)}٪</span>`;
    } else if (cust.tone === 'amber') {
      pillHtml = `<span class="pill pill-warning"><span class="status-dot"></span>هشدار · ${toPersianDigits(riskVal)}٪</span>`;
    } else {
      pillHtml = `<span class="pill pill-success">🟢 پایدار</span>`;
    }

    const riskBarHtml = isStable
      ? `<div class="saas-risk-bar green"><span style="width:100%"></span></div>`
      : `<div class="saas-risk-bar ${cust.tone}"><span style="width:${Math.max(4, riskVal)}%"></span></div>`;

    const causeHtml = isStable
      ? `<div class="cause-callout-box green">🟢 وضعیت مشتری پایدار است .</div>`
      : `<div class="cause-callout-box ${cust.tone}"><b>علت اصلی ریسک:</b> ${cust.main_cause || ''}</div>`;

    const fullInfo = cust.full_info || [];
    const miniCells = fullInfo.map(info => `
      <div class="grid-cell">
        <span>${info.label}</span>
        <b>${toPersianDigits(info.value)}</b>
      </div>
    `).join('');

    card.innerHTML = `
      <div class="radar-card-top">
        <div class="avatar-info-cluster">
          <div class="circle-avatar avatar-${cust.tone}">${cust.tone === 'red' ? 'بحرانی' : (cust.tone === 'amber' ? 'هشدار' : 'پایدار')}</div>
          <div class="customer-meta-titles">
            <b>شناسه کاربر: ${toPersianDigits(cust.id)}</b>
            <span>سابقه عضویت: ${tenureTxt}</span>
          </div>
        </div>
        ${pillHtml}
      </div>

      ${riskBarHtml}
      ${causeHtml}

      <button type="button" class="btn-drawer-toggle" data-id="${cust.id}">
        مشاهده اطلاعات کامل
      </button>

      <div class="radar-collapsible-drawer" id="drawer-${cust.id}">
        <div class="two-col-grid">${miniCells}</div>
      </div>
    `;

    container.appendChild(card);
  });

  // Attach drawer toggle listeners
  container.querySelectorAll('.btn-drawer-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const cid = Number(btn.getAttribute('data-id'));
      const drawer = document.getElementById(`drawer-${cid}`);
      if (!drawer) return;

      const isOpen = drawer.classList.contains('open');
      if (isOpen) {
        drawer.classList.remove('open');
        btn.textContent = 'مشاهده اطلاعات کامل';
        state.radarDetailsOpen.delete(cid);
      } else {
        drawer.classList.add('open');
        btn.textContent = 'بستن اطلاعات کامل';
        state.radarDetailsOpen.add(cid);
      }
    });
  });
}

function initSegmentedRadios() {
  document.querySelectorAll('.segmented-control').forEach(container => {
    const options = container.querySelectorAll('.seg-item');
    options.forEach(opt => {
      opt.addEventListener('click', () => {
        options.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        const input = opt.querySelector('input');
        if (input) input.checked = true;
      });
    });
  });
}

function applyLabPreset(presetNumber) {
  const p = Number(presetNumber);
  const tenureInput = document.getElementById('eval-tenure');
  const daysInput = document.getElementById('eval-days');
  const catInput = document.getElementById('eval-category');
  const ordersInput = document.getElementById('eval-orders');
  const tierInput = document.getElementById('eval-tier');

  if (p === 1) {
    if (tenureInput) tenureInput.value = 1;
    if (daysInput) daysInput.value = 3;
    if (catInput) catInput.value = 'Mobile Phone';
    if (ordersInput) ordersInput.value = 2;
    if (tierInput) tierInput.value = '1';
    setRadioOption('eval_complain', '1');
    setRadioOption('eval_sat', '3');
  } else if (p === 2) {
    if (tenureInput) tenureInput.value = 36;
    if (daysInput) daysInput.value = 12;
    if (catInput) catInput.value = 'Grocery';
    if (ordersInput) ordersInput.value = 4;
    if (tierInput) tierInput.value = '1';
    setRadioOption('eval_complain', '0');
    setRadioOption('eval_sat', '3');
  } else if (p === 3) {
    if (tenureInput) tenureInput.value = 1;
    if (daysInput) daysInput.value = 45;
    if (catInput) catInput.value = 'Fashion';
    if (ordersInput) ordersInput.value = 2;
    if (tierInput) tierInput.value = '3';
    setRadioOption('eval_complain', '0');
    setRadioOption('eval_sat', '3');
  }
}

function setRadioOption(name, val) {
  const radios = document.querySelectorAll(`input[name="${name}"]`);
  radios.forEach(r => {
    if (r.value === val) {
      r.checked = true;
      const label = r.closest('.seg-item');
      if (label && label.parentElement) {
        label.parentElement.querySelectorAll('.seg-item').forEach(l => l.classList.remove('active'));
        label.classList.add('active');
      }
    }
  });
}

async function handleLabEvaluation(e) {
  e.preventDefault();
  const submitBtn = document.getElementById('btn-submit-eval');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <div class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;border-top-color:#fff;"></div>
      <span>در حال استنتاج مدل هوش مصنوعی…</span>
    `;
  }

  const tenure = Number(document.getElementById('eval-tenure').value) || 0;
  const days = Number(document.getElementById('eval-days').value) || 0;
  const complain = Number(document.querySelector('input[name="eval_complain"]:checked')?.value || 0);
  const sat = Number(document.querySelector('input[name="eval_sat"]:checked')?.value || 3);
  const category = document.getElementById('eval-category').value || 'Mobile Phone';
  const orders = Number(document.getElementById('eval-orders').value) || 1;
  const tier = Number(document.getElementById('eval-tier').value) || 1;
  const store = document.getElementById('eval-store').value.trim() || 'کسب‌وکار شما';

  try {
    const res = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tenure: tenure,
        days_since_last_order: days,
        complain: complain,
        satisfaction_score: sat,
        category: category,
        order_count: orders,
        city_tier: tier,
        store_name: store,
      })
    });

    if (!res.ok) throw new Error('ارزیابی ناموفق بود');
    const result = await res.json();
    renderLabResult(result);
  } catch (err) {
    console.error('Lab evaluation error:', err);
    showToast('خطا در ارزیابی مدل: ' + err.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
        <span>ارزیابی هوشمند ریسک ریزش مشتری</span>
      `;
    }
  }
}

function renderLabResult(res) {
  const container = document.getElementById('eval-output-content');
  if (!container) return;

  const riskVal = Math.round(res.risk || 0);
  const isStable = res.scenario === 'do_not_disturb' || (res.nba && res.nba.playbook_id === 'do_not_disturb') || (res.risk < 35 && (!res.sms || !res.sms.code));

  if (isStable) {
    container.innerHTML = `
      <div class="risk-outcome-panel green">
        <div class="risk-outcome-head green">
          <span>🟢 وضعیت مشتری پایدار (${toPersianDigits(riskVal)}٪)</span>
          <span class="pill pill-success">🟢 پایدار</span>
        </div>
        <div class="saas-risk-bar green">
          <span style="width:100%"></span>
        </div>
        <div style="font-size:13px; color:var(--text-primary); margin-top:10px; line-height:1.9;">
          <b>اقدام بهینه پیشنهادی:</b> سکوت استراتژیک و عدم ارسال تبلیغات
        </div>
        <p style="margin-top:8px; color:var(--risk-low-text); font-size:12.5px; line-height:1.9;">
          🟢 وضعیت این مشتری کاملاً پایدار است. اقدام بهینه: <b>سکوت استراتژیک و عدم ارسال تبلیغات</b> (جلوگیری از ایجاد مزاحمت و حفظ سود).
        </p>
      </div>
    `;
    return;
  }

  const isRegistered = state.registeredActions.has(res.lab_id);
  const regBtnHtml = isRegistered
    ? `<button type="button" class="btn-primary-action" disabled style="background:#E2E8F0;color:#626264;box-shadow:none;">✓ اقدام پیشنهادی قبلاً ثبت شده است</button>`
    : `<button type="button" class="btn-primary-action" id="btn-reg-lab" data-id="${res.lab_id}">ثبت اقدام پیشنهادی در سامانه</button>`;

  const sms = res.sms || {};
  const smsMessage = sms.message || '';
  const smsCode = sms.code || '';
  const strategyDesc = res.strategy_desc || res.strategy || '';

  container.innerHTML = `
    <!-- Risk Box -->
    <div class="risk-outcome-panel ${res.tone}">
      <div class="risk-outcome-head ${res.tone}">
        <span>${toPersianDigits(riskVal)}٪ ریسک خروج</span>
        ${res.tone === 'red' ? '<span class="pill pill-danger"><span class="pulse-dot"></span>بحرانی</span>' : '<span class="pill pill-warning"><span class="status-dot"></span>هشدار</span>'}
      </div>
      <div class="saas-risk-bar ${res.tone}">
        <span style="width:${Math.max(4, riskVal)}%"></span>
      </div>
      <div style="font-size:12.5px; color:var(--text-primary); margin-top:8px;">
        <b>علت اصلی ریسک:</b> ${res.main_cause || ''}
      </div>
      <div style="font-size:12.5px; color:var(--text-primary); margin-top:5px;">
        <b>پیشنهاد مداخله:</b> ${res.scenario_label || res.intervention || ''}
      </div>
      ${strategyDesc ? `<div style="font-size:12px; color:var(--text-secondary); margin-top:4px; line-height:1.7;">${strategyDesc}</div>` : ''}
    </div>

    <!-- Golden Retention Value Card -->
    <div class="golden-value-card">
      <div class="golden-cap">ارزش تخمینی حفظ سالانه مشتری</div>
      <div class="golden-metric">${toPersianDigits(res.retention_value_formatted || '۰')} <small>تومان</small></div>
      <div class="golden-note">برآورد سالانه بر پایه سهم دسته خرید و شدت ریسک خروج</div>
    </div>

    <!-- Administrative SMS Proposal Box -->
    <div class="sms-proposal-box">
      <div class="sms-header-bar">
        <b>پیش‌نویس پیامک بازگشت مشتری</b>
        <span class="tier-ribbon ${sms.css || 'gold'}">${sms.tag || res.scenario_label || ''}</span>
      </div>
      ${smsCode ? `
      <div class="sms-code-strip">
        <span class="coupon-box ${sms.css || 'gold'}">کد تخفیف: <b>${smsCode}</b></span>
        ${sms.discount ? `<span style="font-size:12.5px; font-weight:700; color:var(--text-primary);">${toPersianDigits(sms.discount)}٪ تخفیف</span>` : ''}
      </div>` : ''}
      <div class="sms-text-area" id="lab-sms-text">${smsCode ? smsMessage.replace(smsCode, `<b style="direction:ltr;display:inline-block">${smsCode}</b>`) : smsMessage}</div>
      <div class="sms-action-footer">
        <button type="button" class="btn-copy-sms" id="btn-copy-lab-sms">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          کپی متن پیامک
        </button>
      </div>
    </div>

    <!-- Action Registration Button -->
    <div id="lab-reg-btn-wrap">${regBtnHtml}</div>
  `;

  // Attach Copy Listener
  const copyBtn = document.getElementById('btn-copy-lab-sms');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      copyToClipboard(smsMessage, 'متن پیامک دلجویی با موفقیت کپی شد! 📋');
    });
  }

  // Attach Action Button Listener
  const regBtn = document.getElementById('btn-reg-lab');
  if (regBtn) {
    regBtn.addEventListener('click', async () => {
      await registerAction(res.lab_id);
      regBtn.disabled = true;
      regBtn.textContent = '✓ اقدام پیشنهادی در سامانه ثبت شد';
      regBtn.style.background = '#E2E8F0';
      regBtn.style.color = '#626264';
      regBtn.style.boxShadow = 'none';
      showToast('سناریوی بازگشت برای مشتری در سامانه ثبت گردید ✅');
    });
  }
}

// ---------------------------------------------------------------------------
// SECTION 3: 200 CUSTOMERS STRIPE-LIKE DIRECTORY & 360 DOSSIER
// ---------------------------------------------------------------------------
async function loadCustomers() {
  const tbody = document.getElementById('customers-table-body');
  try {
    const res = await fetch('/api/customers');
    if (!res.ok) throw new Error('دریافت فهرست ناموفق بود');
    const list = await res.json();
    state.allCustomers = list || [];
    state.filteredCustomers = list || [];

    renderCustomersTable(state.filteredCustomers);
    initTableFilters();
  } catch (err) {
    console.error('Error loading customers:', err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--risk-high); padding:24px;">خطا در دریافت پرونده‌های مشتریان: ${err.message}</td></tr>`;
    }
  }
}

function initTableFilters() {
  const searchInput = document.getElementById('customer-search-input');
  const riskFilter = document.getElementById('customer-risk-filter');

  function applyFilters() {
    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const riskLevel = riskFilter ? riskFilter.value : 'all';

    const filtered = state.allCustomers.filter(c => {
      const matchQuery = !query || String(c.id).includes(query);
      const matchRisk = riskLevel === 'all' || c.tone === riskLevel;
      return matchQuery && matchRisk;
    });

    state.filteredCustomers = filtered;
    renderCustomersTable(filtered);

    const badge = document.getElementById('customers-count-badge');
    if (badge) {
      badge.textContent = `${toPersianDigits(filtered.length)} مشتری از ${toPersianDigits(state.allCustomers.length)} رکورد استریم`;
    }
  }

  if (searchInput) searchInput.oninput = applyFilters;
  if (riskFilter) riskFilter.onchange = applyFilters;
}

function getNbaBadgeConfig(nba, riskVal) {
  const pid = (nba && nba.playbook_id) || '';

  // ۱. مشتریان پایدار و سکوت استراتژیک (ریسک زیر 3535 درصد)
  if (riskVal < 35 || pid === 'do_not_disturb') {
    return {
      cssClass: 'badge-nba-dnd',
      icon: '🌿',
      label: 'سکوت استراتژیک',
      isStable: true
    };
  }

  // ۲. جبران تجربه نامطلوب و شکایت
  if (pid === 'trust_restoration') {
    return {
      cssClass: 'badge-nba-trust',
      icon: '🛡️',
      label: 'جبران تجربه نامطلوب',
      isStable: false
    };
  }

  // ۳. مشوق خرید بعدی (پرتگاه ماه اول)
  if (pid === 'streak_challenge') {
    return {
      cssClass: 'badge-nba-streak',
      icon: '⚡',
      label: 'مشوق خرید بعدی',
      isStable: false
    };
  }

  // ۴. ارتقا به مشتری ویژه (VIP باسابقه)
  if (pid === 'vip_elevation') {
    return {
      cssClass: 'badge-nba-vip',
      icon: '👑',
      label: 'ارتقا به مشتری ویژه',
      isStable: false
    };
  }

  // ۵. هدیه متناسب با خرید (فاصله زیاد یا شهرهای حاشیه‌ای)
  if (pid === 'smart_unbundling') {
    return {
      cssClass: 'badge-nba-gift',
      icon: '🎁',
      label: 'هدیه متناسب با خرید',
      isStable: false
    };
  }

  // ۶. مشوق بازگشت زمان‌دار (حالت پیش‌فرض برای ریسک بالای ۵۰ درصد)
  return {
    cssClass: 'badge-nba-amber',
    icon: '⏳',
    label: 'مشوق بازگشت زمان‌دار',
    isStable: false
  };
}
function renderCustomersTable(customers) {
  const tbody = document.getElementById('customers-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!customers || customers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:32px; color:var(--muted);">هیچ مشتری با این معیار جستجو یافت نشد.</td></tr>`;
    return;
  }

  customers.forEach(c => {
    const tr = document.createElement('tr');
    const riskVal = Math.round(c.risk || 0);

    // Stripe-Pattern Status Pills
    let pillHtml = '';
    if (riskVal >= 70) {
      pillHtml = `<span class="pill pill-danger"><span class="pulse-dot"></span>بحرانی · ${toPersianDigits(riskVal)}٪</span>`;
    } else if (riskVal >= 35) {
      pillHtml = `<span class="pill pill-warning"><span class="status-dot"></span>هشدار · ${toPersianDigits(riskVal)}٪</span>`;
    } else {
      pillHtml = `<span class="pill pill-success">🟢 پایدار · ${toPersianDigits(riskVal)}٪</span>`;
    }

    const tenureTxt = c.tenure !== null && c.tenure !== undefined ? `${toPersianDigits(Math.round(c.tenure))} ماه` : '—';
    const isReg = state.registeredActions.has(String(c.id));
    const actionStatus = isReg
      ? `<span class="badge-treatment-status active"><span class="pulse-dot-green"></span>تحت مداخله (In Treatment) ✅</span>`
      : `<span class="badge-treatment-status pending">در انتظار اقدام</span>`;

    const nba = c.nba || c.recommendation || {};
    const nbaCfg = getNbaBadgeConfig(nba, riskVal);

    tr.innerHTML = `
      <td><b>${toPersianDigits(c.id)}</b></td>
      <td>${tenureTxt}</td>
      <td>${c.category_fa || 'نامشخص'}</td>
      <td>${pillHtml}</td>
      <td>
        <span class="badge-nba ${nbaCfg.cssClass}">
          <span class="nba-badge-icon">${nbaCfg.icon}</span>
          <span class="nba-badge-title">${nbaCfg.label}</span>
        </span>
      </td>
      <td>${actionStatus}</td>
      <td style="text-align: left;">
        <button type="button" class="btn-pill-view btn-open-dossier" data-id="${c.id}">
          <span>مشاهده پرونده</span>
          
        </button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  // Attach dossier modal triggers
  tbody.querySelectorAll('.btn-open-dossier').forEach(btn => {
    btn.addEventListener('click', () => {
      const cid = Number(btn.getAttribute('data-id'));
      openDossierModal(cid);
    });
  });
}

function openDossierModal(customerId) {
  const customer = state.allCustomers.find(c => c.id === customerId);
  if (!customer) return;
  state.activeCustomer = customer;

  const modal = document.getElementById('dossier-modal');
  const titleElem = document.getElementById('modal-cust-title');
  const badgeElem = document.getElementById('modal-cust-badge');
  const cardsGrid = document.getElementById('modal-cards-grid');
  const riskArea = document.getElementById('modal-risk-area');
  const actionArea = document.getElementById('modal-action-area');

  const riskVal = Math.round(customer.risk || 0);
  const isStable = riskVal < 35;

  if (titleElem) titleElem.textContent = `اطلاعات مشتری ${toPersianDigits(customer.id)}`;
  
  if (badgeElem) {
    if (riskVal >= 70) {
      badgeElem.className = 'pill pill-danger';
      badgeElem.innerHTML = `<span class="pulse-dot"></span>بحرانی · ${toPersianDigits(riskVal)}٪`;
    } else if (riskVal >= 35) {
      badgeElem.className = 'pill pill-warning';
      badgeElem.innerHTML = `<span class="status-dot"></span>هشدار · ${toPersianDigits(riskVal)}٪`;
    } else {
      badgeElem.className = 'pill pill-success';
      badgeElem.innerHTML = `🟢 پایدار · ${toPersianDigits(riskVal)}٪`;
    }
  }

  // Right Column: Categorized 19 Variables into 3 Distinct Groups
  if (cardsGrid) {
    const modalCards = customer.modal_cards || [];
    const groups = [
      {
        id: 'identity',
        title: '۱. مشخصات هویتی و جغرافیایی',
        icon: '👤',
        items: modalCards.filter(m => m.group === 'identity')
      },
      {
        id: 'finance',
        title: '۲. تاریخچه تراکنش و مالی',
        icon: '💳',
        items: modalCards.filter(m => m.group === 'finance')
      },
      {
        id: 'app',
        title: '۳. رفتار در اپلیکیشن و تعامل',
        icon: '📱',
        items: modalCards.filter(m => m.group === 'app')
      }
    ];

    if (groups[0].items.length === 0 && modalCards.length > 0) {
      groups[0].items = modalCards.slice(0, 6);
      groups[1].items = modalCards.slice(6, 14);
      groups[2].items = modalCards.slice(14);
    }

    cardsGrid.innerHTML = groups.map(g => `
      <div class="m360-group-panel">
        <div class="m360-group-header">
          <span class="m360-group-title">
            <span class="m360-group-icon">${g.icon}</span>
            ${g.title}
          </span>
          <span class="m360-group-count">${toPersianDigits(g.items.length)} متغیر</span>
        </div>
        <div class="m360-group-grid">
          ${g.items.map(mc => `
            <div class="m360-data-card">
              <span class="m360-data-label">${mc.label}</span>
              <b class="m360-data-val">${toPersianDigits(mc.value)}</b>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  }

  const nba = customer.nba || customer.recommendation || {};
  const nbaCfg = getNbaBadgeConfig(nba, riskVal);
  const isReg = state.registeredActions.has(String(customer.id));

  if (riskArea) riskArea.innerHTML = '';

  // Left Column Content: Stable vs 3 Minimal Boxes
  if (actionArea) {
    if (isStable) {
      // Rule 1: Stable Customer -> short authoritative message only
      actionArea.innerHTML = `
        <div class="clean-stable-box">
          <div class="clean-stable-header">
            <span class="badge-nba badge-nba-dnd">🌿 سکوت استراتژیک</span>
            <span class="clean-stable-pill">ریسک: ${toPersianDigits(riskVal)}٪ (ایمن)</span>
          </div>
          <p class="clean-stable-msg">🟢 وضعیت این مشتری کاملاً پایدار است. اقدام بهینه: <b>سکوت استراتژیک و عدم ارسال تبلیغات</b> (جلوگیری از ایجاد مزاحمت و حفظ سود).</p>
        </div>
      `;
    } else {
      // Rule 2 & 3: High-Risk Customer -> 3 Minimal Boxes + Action Button
      // Box 1: Short Cause Title
      let causeTitle = nba.root_cause_short || '';
      if (!causeTitle && customer.drivers && customer.drivers.length > 0) {
        const d0 = customer.drivers[0];
        causeTitle = `${d0.title || d0.feature}: ${d0.detail || ''}`;
      }
      if (!causeTitle) {
        causeTitle = 'کاهش نرخ تعامل و افزایش ریسک خروج';
      }

      // Box 2: Bold Strategy Title + 1-line business explanation
      const stratDesc = nba.strategy_desc || nba.strategy || 'ارتقای فوری ۳۰ روزه به حساب VIP با ارسال کاملاً رایگان';

      // Box 3: Clean SMS (max 2 lines)
      const smsText = (nba.sms || '').trim();

      const btnHtml = isReg
        ? `<button type="button" class="btn-execute-clean in-treatment" disabled>
             <span>✓ تحت مداخله (In Treatment) ✅</span>
           </button>`
        : `<button type="button" class="btn-execute-clean" id="btn-modal-execute-nba" data-id="${customer.id}">
             <span>ثبت و اجرای راهبرد بازگشت</span>
           </button>`;

      actionArea.innerHTML = `
        <div class="clean-dossier-stack">
          <!-- ۱. علت اصلی ریسک -->
          <div class="clean-box clean-box-risk">
            <div class="clean-box-header">
              <span class="clean-box-title">⚠️ علت اصلی ریسک</span>
              <span class="clean-risk-pill ${customer.tone}">${toPersianDigits(riskVal)}٪ احتمال خروج</span>
            </div>
            <div class="clean-box-body">
              <b>${causeTitle}</b>
            </div>
          </div>

          <!-- ۲. راهبرد پیشنهادی -->
          <div class="clean-box clean-box-strategy">
            <div class="clean-box-header">
              <span class="clean-box-title">💡 راهبرد پیشنهادی</span>
              <span class="badge-nba ${nbaCfg.cssClass}">
                <span class="nba-badge-icon">${nbaCfg.icon}</span>
                <span>${nbaCfg.label}</span>
              </span>
            </div>
            <div class="clean-box-body">
              <p class="clean-strategy-text">${stratDesc}</p>
            </div>
          </div>

          <!-- ۳. متن پیامک / اعلان پیشنهادی -->
          <div class="clean-box clean-box-sms">
            <div class="clean-box-header">
              <span class="clean-box-title">📱 متن پیامک / اعلان پیشنهادی</span>
              <button type="button" class="btn-copy-clean-sms" id="btn-copy-modal-sms">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>کپی متن پیامک</span>
              </button>
            </div>
            <div class="clean-sms-text" id="modal-sms-text">${smsText}</div>
          </div>

          <!-- دکمه ثبت و اجرا -->
          <div class="clean-action-wrap">
            ${btnHtml}
          </div>
        </div>
      `;

      // Copy Button listener
      const copyBtn = document.getElementById('btn-copy-modal-sms');
      if (copyBtn) {
        copyBtn.addEventListener('click', () => {
          copyToClipboard(smsText, 'متن پیامک با موفقیت کپی شد! 📋');
        });
      }

      // Action CTA Button listener
      const executeBtn = document.getElementById('btn-modal-execute-nba');
      if (executeBtn) {
        executeBtn.addEventListener('click', async () => {
          executeBtn.disabled = true;
          executeBtn.innerHTML = `<span>در حال ثبت…</span>`;
          await registerAction(customer.id);
          customer.is_registered = true;
          executeBtn.className = 'btn-execute-clean in-treatment';
          executeBtn.innerHTML = `<span>✓ تحت مداخله (In Treatment) ✅</span>`;
          showToast(`راهبرد بازگشت برای مشتری ${toPersianDigits(customer.id)} با موفقیت ثبت شد ✅`, 'success');
          renderCustomersTable(state.filteredCustomers);
        });
      }
    }
  }

  if (modal) {
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }
}

function closeDossierModal() {
  const modal = document.getElementById('dossier-modal');
  if (modal) {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }
}
window.closeDossierModal = closeDossierModal;

function openIntegrationModal() {
  const modal = document.getElementById('integration-modal');
  if (modal) {
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }
}
window.openIntegrationModal = openIntegrationModal;

function closeIntegrationModal() {
  const modal = document.getElementById('integration-modal');
  if (modal) {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }
}
window.closeIntegrationModal = closeIntegrationModal;

function initModalEvents() {
  const modal = document.getElementById('dossier-modal');
  const closeBtn = document.getElementById('btn-close-modal');

  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeDossierModal();
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (!e.target.closest('.modal-surface-dialog')) {
        closeDossierModal();
      }
    });
  }

  // Integration Center Modal Handlers
  const integModal = document.getElementById('integration-modal');
  const openIntegBtn = document.getElementById('btn-open-integration-modal');
  const closeIntegBtn = document.getElementById('btn-close-integration-modal');

  if (openIntegBtn) {
    openIntegBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openIntegrationModal();
    });
  }

  if (closeIntegBtn) {
    closeIntegBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeIntegrationModal();
    });
  }

  if (integModal) {
    integModal.addEventListener('click', (e) => {
      if (!e.target.closest('.modal-surface-dialog')) {
        closeIntegrationModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDossierModal();
      closeIntegrationModal();
    }
  });
}

async function registerAction(targetId) {
  state.registeredActions.add(String(targetId));
  try {
    await fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_id: String(targetId) })
    });
  } catch (err) {
    console.error('Action registration error:', err);
  }
}

// ---------------------------------------------------------------------------
// Initialization on DOM Ready
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  try {
    initNavigation();
    initModalEvents();
    loadInsights();
    initRadarAndLab();
    loadCustomers();
  } catch (err) {
    console.error('Initialization error:', err);
  }
});
