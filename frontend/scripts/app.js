// ---------- configuration ----------
const API_URL = '/api/hourly_breakdown';   // set to your endpoint when ready
const PROD_INTERVAL_MS = 15 * 60 * 1000;   // 15 minutes
const DEV_INTERVAL_MS  = 30 * 1000;        // 30 seconds for demo

// gym hours
const OPEN_HOUR  = 6;
const CLOSE_HOUR = 22;

// displaying order of places
const PLACES = [
  "Cubby Cove",
  "Weight Room",
  "Track",
  "Aerobics Room",
  "Main Gym",
  "Table Tennis",
  "Chairs in Balcony",
  "Vicore Equipment",
  "Multipurpose Gym",
];

// URL flags
const url = new URL(window.location.href);
let devMode   = url.searchParams.get('dev')  === '1';
let forceMock = url.searchParams.get('mock') === '1';

// ---- state (declare ONCE) ----
let nextTick = null;
let timer    = null;
let chart    = null;

// ---- dom helpers ----
const el = (id) => document.getElementById(id);
const statusDot  = el('statusDot');
const statusText = el('statusText');

// theme toggle button
el('toggleTheme').addEventListener('click', () => {
  document.documentElement.toggleAttribute('data-light');
  const light = document.documentElement.hasAttribute('data-light');
  if (light) {
    document.documentElement.style.setProperty('--bg', '#f6f7fb');
    document.documentElement.style.setProperty('--card', '#ffffff');
    document.documentElement.style.setProperty('--text', '#0f172a');
    document.documentElement.style.setProperty('--muted', '#5b6470');
  } else {
    document.documentElement.style.setProperty('--bg', '#0b0d10');
    document.documentElement.style.setProperty('--card', '#141820');
    document.documentElement.style.setProperty('--text', '#eef2f8');
    document.documentElement.style.setProperty('--muted', '#9aa4b2');
  }
});

/* ---------------- MOCK HOURLY BREAKDOWN ---------------- */
function mockHourlyBreakdown() {
  const now = new Date();
  const endHour = Math.min(CLOSE_HOUR - 1, now.getHours());
  const labels = [];
  for (let h = OPEN_HOUR; h <= endHour; h++) {
    labels.push(String(h).padStart(2, "0") + ":00");
  }

  const ranges = {
    "Cubby Cove": [2, 8],
    "Weight Room": [10, 40],
    "Track": [6, 25],
    "Aerobics Room": [0, 12],
    "Main Gym": [5, 30],
    "Table Tennis": [0, 10],
    "Chairs in Balcony": [0, 12],
    "Vicore Equipment": [0, 8],
    "Multipurpose Gym": [2, 20],
  };

  const seriesByPlace = {};
  for (const place of PLACES) {
    const [lo, hi] = ranges[place];
    seriesByPlace[place] = labels.map(() =>
      Math.floor(Math.random() * (hi - lo + 1)) + lo
    );
  }

  return {
    labels,
    places: PLACES.slice(),
    seriesByPlace,
    last_updated_utc: new Date().toISOString(),
  };
}

// Fetch from API (or fallback to mock)
async function fetchHourlyBreakdown() {
  if (forceMock) return mockHourlyBreakdown();
  try {
    const res = await fetch(API_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } catch (err) {
    console.warn('API unavailable — falling back to mock:', err);
    setWarning("API unavailable — showing mock data");
    return mockHourlyBreakdown();
  }
}

// status helpers
function setWarning(msg) {
  statusDot.style.background = 'var(--danger)';
  statusText.textContent = msg;
  statusText.classList.add('warning');
}
function setLive(msg) {
  statusDot.style.background = 'var(--success)';
  statusText.textContent = msg || 'Live';
  statusText.classList.remove('warning');
}

// distinct color per place
function colorFor(index, alpha = 1) {
  const hue = Math.round((index / PLACES.length) * 330);
  return `hsla(${hue} 70% 60% / ${alpha})`;
}

// draw/update stacked chart
function renderStacked(labels, places, seriesByPlace) {
  const ctx = document.getElementById('chart').getContext('2d');
  const datasets = places.map((place, i) => ({
    label: place,
    data: seriesByPlace[place] || labels.map(() => 0),
    borderWidth: 0,
    borderRadius: 6,
    backgroundColor: colorFor(i, 0.9),
    stack: 'by-hour',
  }));

  if (chart) {
    chart.data.labels = labels;
    chart.data.datasets = datasets;
    chart.update();
    return;
  }

  chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      animation: false,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: 'Hour' },
          stacked: true,
          ticks: { autoSkip: false, maxRotation: 0 },
          grid: { display: false },
        },
        y: {
          title: { display: true, text: 'People present' },
          beginAtZero: true,
          stacked: true,
          ticks: { precision: 0 },
        }
      },
      plugins: {
        legend: { display: true },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            title: (items) => `Hour: ${items[0].label}`,
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y ?? 0}`,
            footer: (items) => {
              const total = items.reduce((acc, it) => acc + (it.parsed.y ?? 0), 0);
              return `Total: ${total}`;
            }
          }
        }
      }
    }
  });
}

// countdown to next refresh
function startCountdown() {
  const interval = devMode ? DEV_INTERVAL_MS : PROD_INTERVAL_MS;
  nextTick = Date.now() + interval;
  updateCountdown();
  if (timer) clearInterval(timer);
  timer = setInterval(updateCountdown, 1000);
}
function updateCountdown() {
  if (!nextTick) return;
  const diff = Math.max(0, nextTick - Date.now());
  const s = Math.floor(diff / 1000);
  const m = Math.floor(s / 60);
  const rem = String(s % 60).padStart(2, '0');
  el('countdown').textContent = `Next refresh: ${m}:${rem}`;
  if (diff <= 0) refresh();
}

// main refresh
async function refresh() {
  const payload = await fetchHourlyBreakdown();
  renderStacked(payload.labels, payload.places, payload.seriesByPlace);
  const last = new Date(payload.last_updated_utc);
  el('lastUpdated').textContent = last.toLocaleString();
  el('tz').textContent = Intl.DateTimeFormat().resolvedOptions().timeZone;
  setLive('Live');
  startCountdown();
}

// controls
el('refreshBtn').addEventListener('click', () => refresh());
el('useMock').addEventListener('click', () => {
  forceMock = !forceMock;
  el('useMock').classList.toggle('primary', forceMock);
  refresh();
});
if (forceMock) el('useMock').classList.add('primary');

// boot
(async function init(){
  devMode && console.log('DEV mode: 30s refresh');
  await refresh();
  setInterval(refresh, devMode ? DEV_INTERVAL_MS : PROD_INTERVAL_MS);
})();
