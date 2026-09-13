const getApiUrl = () => {
  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:5000/api/hourly_breakdown';
  }
  return '/api/hourly_breakdown';
};

const API_URL = getApiUrl();
const STALE_MS = 5 * 60 * 60 * 1000; // 5 hours
const MOBILE_BREAKPOINT = 600;
const TZ = 'America/Chicago';

// Open hours in Central time: [dayOfWeek 0=Sun..6=Sat] -> { openMin, closeMin } from midnight
// Closed = outside these windows.
const OPEN_HOURS = {
  0: { openMin: 11 * 60, closeMin: 18 * 60 },           // Sunday 11:00–18:00
  1: { openMin: 6 * 60 + 30, closeMin: 22 * 60 },       // Monday 6:30–22:00
  2: { openMin: 6 * 60 + 30, closeMin: 22 * 60 },       // Tuesday
  3: { openMin: 6 * 60 + 30, closeMin: 22 * 60 },       // Wednesday
  4: { openMin: 6 * 60 + 30, closeMin: 22 * 60 },       // Thursday
  5: { openMin: 6 * 60 + 30, closeMin: 19 * 60 },       // Friday 6:30–19:00
  6: { openMin: 11 * 60, closeMin: 18 * 60 },           // Saturday 11:00–18:00
};

let chart = null;
let lastRefreshTime = 0;
let lastChartHorizontal = null;
let latestPayload = null;

const el = (id) => document.getElementById(id);

function applyEmbedClass() {
  const embedded = window.self !== window.top;
  document.documentElement.classList.toggle('is-embed', embedded);
}

function updateDateTime() {
  const now = new Date();
  const centralTimeStr = now.toLocaleString('en-US', {
    timeZone: TZ,
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit'
  });
  el('currentDateTime').textContent = centralTimeStr;
}

setInterval(updateDateTime, 1000);

function getCentralParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: TZ,
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).formatToParts(date);

  const map = {};
  for (const p of parts) {
    if (p.type !== 'literal') map[p.type] = p.value;
  }

  const weekdayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  let hour = Number(map.hour);
  if (hour === 24) hour = 0; // some environments use 24:00
  const minute = Number(map.minute);
  return {
    day: weekdayMap[map.weekday],
    minutes: hour * 60 + minute
  };
}

function isWithinOpenHours(date = new Date()) {
  const { day, minutes } = getCentralParts(date);
  const window = OPEN_HOURS[day];
  if (!window) return false;
  return minutes >= window.openMin && minutes < window.closeMin;
}

function isDataStale(lastUpdatedUtc) {
  if (!lastUpdatedUtc) return true;
  const updated = new Date(lastUpdatedUtc);
  if (Number.isNaN(updated.getTime())) return true;
  return Date.now() - updated.getTime() > STALE_MS;
}

function shouldShowClosedMessage(lastUpdatedUtc) {
  return !isWithinOpenHours() || isDataStale(lastUpdatedUtc);
}

const DEFAULT_STATUS_MESSAGE =
  'There have been no updates recently. Please check the hours to make sure the Student Recreation Center is open.';

function showStatusMessage(show, text = DEFAULT_STATUS_MESSAGE) {
  const msg = el('statusMessage');
  const wrap = el('chartWrap');
  if (show) {
    msg.textContent = text;
    msg.hidden = false;
    wrap.hidden = true;
    if (chart) {
      chart.destroy();
      chart = null;
      lastChartHorizontal = null;
    }
  } else {
    msg.hidden = true;
    wrap.hidden = false;
  }
}

async function fetchHourlyBreakdown() {
  const res = await fetch(API_URL, {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache'
    }
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return await res.json();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchHourlyBreakdownWithRetry() {
  try {
    return await fetchHourlyBreakdown();
  } catch (firstError) {
    console.warn('API fetch failed; retrying once in 2s...', firstError);
    await sleep(2000);
    return await fetchHourlyBreakdown();
  }
}

function handleError(error) {
  console.error('Error fetching data:', error);
}

function colorFor(alpha = 0.9) {
  return `rgba(69, 44, 99, ${alpha})`;
}

function useHorizontalChart() {
  return window.innerWidth < MOBILE_BREAKPOINT;
}

function buildChartOptions(horizontal) {
  const categoryAxis = {
    title: {
      display: !horizontal,
      text: 'Area',
      font: { size: horizontal ? 12 : 16, weight: 'bold' }
    },
    grid: { display: false },
    ticks: {
      autoSkip: false,
      maxRotation: 0,
      minRotation: 0,
      font: { size: horizontal ? 11 : 12 }
    }
  };

  const valueAxis = {
    title: {
      display: true,
      text: 'People Present',
      font: { size: horizontal ? 12 : 16, weight: 'bold' }
    },
    beginAtZero: true,
    grid: { color: 'rgba(0, 0, 0, 0.1)' },
    ticks: { precision: 0, font: { size: 12 } }
  };

  return {
    indexAxis: horizontal ? 'y' : 'x',
    responsive: true,
    animation: false,
    maintainAspectRatio: false,
    scales: horizontal
      ? { x: valueAxis, y: categoryAxis }
      : { x: categoryAxis, y: valueAxis },
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          title: (items) => items[0].label,
          label: (ctx) => {
            const value = horizontal ? ctx.parsed.x : ctx.parsed.y;
            return `People Present: ${value ?? 0}`;
          }
        }
      }
    }
  };
}

function renderChart(labels, seriesByPlace) {
  const horizontal = useHorizontalChart();
  const data = labels.map((label) => {
    const placeData = seriesByPlace[label] || [0];
    return placeData[0] || 0;
  });

  const dataset = {
    label: 'People Present',
    data,
    borderWidth: 0,
    borderRadius: 6,
    backgroundColor: colorFor(0.9)
  };

  const needsRecreate =
    !chart || lastChartHorizontal !== horizontal;

  if (needsRecreate) {
    if (chart) {
      chart.destroy();
      chart = null;
    }
    const ctx = el('chart').getContext('2d');
    chart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [dataset] },
      options: buildChartOptions(horizontal)
    });
    lastChartHorizontal = horizontal;
    return;
  }

  chart.data.labels = labels;
  chart.data.datasets = [dataset];
  chart.update('none');
}

async function refresh() {
  try {
    // Outside open hours: show message without calling the API (saves Vercel CPU)
    if (!isWithinOpenHours()) {
      latestPayload = null;
      showStatusMessage(true);
      lastRefreshTime = Date.now();
      console.info('Outside open hours — skipped API fetch');
      return;
    }

    const payload = await fetchHourlyBreakdownWithRetry();
    latestPayload = payload;

    if (isDataStale(payload.last_updated_utc)) {
      showStatusMessage(true);
      console.info('Showing stale-data message', {
        last_updated_utc: payload.last_updated_utc
      });
    } else {
      showStatusMessage(false);
      renderChart(payload.labels, payload.seriesByPlace);
    }

    lastRefreshTime = Date.now();
    console.log('Data refreshed successfully. Next refresh in 15 minutes.');
  } catch (error) {
    handleError(error);
    // Keep the last good chart on transient failures; only error if we never loaded
    if (latestPayload) {
      console.warn('API refresh failed; keeping last successful chart');
    } else {
      showStatusMessage(
        true,
        'Unable to load live occupancy data right now. Please try again shortly.'
      );
    }
    lastRefreshTime = Date.now();
  }
}

function getMillisecondsUntilNextRefresh() {
  const now = new Date();
  const centralTimeStr = now.toLocaleString('en-US', {
    timeZone: TZ,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  const [centralHour, centralMinute, centralSecond] = centralTimeStr.split(':').map(Number);
  const minutesToNext = 15 - (centralMinute % 15);

  if (minutesToNext === 15 && centralSecond < 2) {
    return 15 * 60 * 1000 - centralSecond * 1000 - now.getMilliseconds();
  }
  if (minutesToNext === 15) {
    const secondsRemaining = 60 - centralSecond;
    return 14 * 60 * 1000 + secondsRemaining * 1000 - now.getMilliseconds();
  }

  const minutesDelay = minutesToNext - 1;
  const secondsDelay = 60 - centralSecond;
  const msDelay = 1000 - now.getMilliseconds();
  return minutesDelay * 60 * 1000 + secondsDelay * 1000 + msDelay;
}

function scheduleNextRefresh() {
  if (window.refreshTimeout) {
    clearTimeout(window.refreshTimeout);
  }

  const delay = getMillisecondsUntilNextRefresh();
  const nextRefreshTime = new Date(Date.now() + delay);
  const nextRefreshTimeStr = nextRefreshTime.toLocaleString('en-US', {
    timeZone: TZ,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  console.log(`Next refresh scheduled for: ${nextRefreshTimeStr} Central Time`);

  window.refreshTimeout = setTimeout(async () => {
    await refresh();
    scheduleNextRefresh();
  }, delay);
}

function maybeRefreshOnVisible() {
  const now = new Date();
  const { minutes } = getCentralParts(now);
  const seconds = Number(
    new Intl.DateTimeFormat('en-US', {
      timeZone: TZ,
      second: '2-digit'
    }).format(now)
  );

  if (minutes % 15 === 0 && seconds < 5) {
    const timeSinceLastRefresh = now.getTime() - lastRefreshTime;
    if (timeSinceLastRefresh >= 14 * 60 * 1000) {
      refresh();
    }
  }
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) maybeRefreshOnVisible();
});

window.addEventListener('focus', () => {
  maybeRefreshOnVisible();
});

let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (!latestPayload || shouldShowClosedMessage(latestPayload.last_updated_utc)) return;
    if (useHorizontalChart() !== lastChartHorizontal) {
      renderChart(latestPayload.labels, latestPayload.seriesByPlace);
    }
  }, 150);
});

(async function init() {
  applyEmbedClass();
  updateDateTime();
  await refresh();
  scheduleNextRefresh();
})();
