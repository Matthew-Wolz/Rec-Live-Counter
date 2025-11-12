
const getApiUrl = () => {
  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:5000/api/hourly_breakdown';
  }
  // For deployed version, use relative URL (same origin)
  return '/api/hourly_breakdown';
};
const API_URL = getApiUrl();
const FIFTEEN_MINUTES = 15 * 60 * 1000;  // 15 minutes in milliseconds

// displaying order of places (matches backend groupings)
const PLACES = [
  "Main Gym",
  "Weight Room",
  "Multipurpose Gym",
  "Track",
  "Aerobics Room",
  "Cubby Cove",
  "Table Tennis",
  "Vicore Equipment",
  "Bikes in Lobby"
];

// ---- state (declare ONCE) ----
let chart = null;
let lastRefreshTime = 0;

// ---- dom helpers ----
const el = (id) => document.getElementById(id);

// Update date and time
function updateDateTime() {
  const now = new Date();
  const centralTimeStr = now.toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short'
  });
  el('currentDateTime').textContent = centralTimeStr;
}

// Update time every second
setInterval(updateDateTime, 1000);

// Fetch real data from API
async function fetchHourlyBreakdown() {
  try {
    const res = await fetch(API_URL, { 
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } catch (err) {
    console.error('API error:', err);
    throw err;
  }
}

// Error handling
function handleError(error) {
  console.error('Error fetching data:', error);
}

// Truman State University purple for all bars
function colorFor(index, alpha = 1) {
  return `rgba(69, 44, 99, ${alpha})`; // Truman State Purple
}

// draw/update stacked chart
function renderStacked(labels, places, seriesByPlace) {
  console.debug('renderStacked called at:', new Date().toLocaleString('en-US', { timeZone: 'America/Chicago' }));
  console.debug('Data:', seriesByPlace);

  // Create a single dataset with one value per area
  // Each area in seriesByPlace has an array with one value [count]
  const data = labels.map(label => {
    const placeData = seriesByPlace[label] || [0];
    return placeData[0] || 0; // Get the first (and only) value from the array
  });

  const dataset = {
    label: 'People Present',
    data: data,
    borderWidth: 0,
    borderRadius: 6,
    backgroundColor: colorFor(0, 0.9) // Truman State Purple for all bars
  };

  if (chart) {
    // Update existing chart
    chart.data.labels = labels;
    chart.data.datasets = [dataset];
    chart.update('none'); // 'none' mode = no animation
  } else {
    // Create new chart
    const ctx = document.getElementById('chart').getContext('2d');
    chart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [dataset] },
      options: {
        responsive: true,
        animation: false,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { 
              display: true, 
              text: 'Area', 
              font: { 
                size: 18,
                weight: 'bold'
              }
            },
            grid: { display: false },
            ticks: { 
              autoSkip: false, 
              maxRotation: 0,
              minRotation: 0,
              font: { size: 12 }
            }
          },
          y: {
            title: { 
              display: true, 
              text: 'People Present', 
              font: { 
                size: 18,
                weight: 'bold'
              }
            },
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: { 
              precision: 0,
              font: { size: 12 }
            }
          }
        },
        plugins: {
          legend: { display: false },  // Hide legend since we only have one series
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              title: (items) => items[0].label,
              label: (ctx) => `People Present: ${ctx.parsed.y ?? 0}`
            }
          }
        }
      }
    });
    console.debug('chart created');
  }
}

// main refresh
async function refresh() {
  try {
    const payload = await fetchHourlyBreakdown();
    console.info('refresh(): received payload at', new Date().toLocaleString('en-US', { timeZone: 'America/Chicago' }), {
      labels: payload.labels,
      places: payload.places,
      seriesByPlace: payload.seriesByPlace
    });
    renderStacked(payload.labels, payload.places, payload.seriesByPlace);
    lastRefreshTime = Date.now();
    console.log('Data refreshed successfully. Next refresh in 15 minutes.');
  } catch (error) {
    handleError(error);
    // Even on error, update lastRefreshTime to prevent rapid retries
    lastRefreshTime = Date.now();
  }
}

// Calculate milliseconds until next 15-minute mark in Central Time (:00, :15, :30, :45)
function getMillisecondsUntilNextRefresh() {
  const now = new Date();
  
  // Get current Central Time
  const centralTimeStr = now.toLocaleString('en-US', { 
    timeZone: 'America/Chicago',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  
  // Parse Central Time (format: HH:MM:SS)
  const [centralHour, centralMinute, centralSecond] = centralTimeStr.split(':').map(Number);
  
  // Calculate minutes until next 15-minute mark
  const minutesToNext = 15 - (centralMinute % 15);
  
  // Calculate total milliseconds until next mark
  // If we're at exactly :00, :15, :30, or :45 (within 2 seconds), go to the next one
  if (minutesToNext === 15 && centralSecond < 2) {
    // We're at a mark, schedule for the following mark (15 minutes later)
    return (15 * 60 * 1000) - (centralSecond * 1000) - now.getMilliseconds();
  } else if (minutesToNext === 15) {
    // We just passed a mark, go to next one
    const secondsRemaining = 60 - centralSecond;
    return (14 * 60 * 1000) + (secondsRemaining * 1000) - now.getMilliseconds();
  } else {
    // Calculate delay to next mark
    const minutesDelay = minutesToNext - 1;
    const secondsDelay = 60 - centralSecond;
    const msDelay = 1000 - now.getMilliseconds();
    return (minutesDelay * 60 * 1000) + (secondsDelay * 1000) + msDelay;
  }
}

// Schedule next refresh at the next 15-minute mark
function scheduleNextRefresh() {
  // Clear any existing timeout
  if (window.refreshTimeout) {
    clearTimeout(window.refreshTimeout);
  }
  
  const delay = getMillisecondsUntilNextRefresh();
  const nextRefreshTime = new Date(Date.now() + delay);
  
  // Format next refresh time in Central Time for display
  const nextRefreshTimeStr = nextRefreshTime.toLocaleString('en-US', { 
    timeZone: 'America/Chicago',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  
  console.log(`Next refresh scheduled for: ${nextRefreshTimeStr} Central Time`);
  
  window.refreshTimeout = setTimeout(async () => {
    const refreshTimeStr = new Date().toLocaleString('en-US', { 
      timeZone: 'America/Chicago',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    console.log(`Auto-refresh triggered at: ${refreshTimeStr} Central Time`);
    await refresh();
    scheduleNextRefresh(); // Schedule the next refresh
  }, delay);
}

// Handle page visibility changes (for iframe embedding)
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    // Page became visible - check if we're at or past a 15-minute mark
    const now = new Date();
    const centralTimeStr = now.toLocaleString('en-US', { timeZone: 'America/Chicago' });
    const centralTime = new Date(centralTimeStr);
    const minutes = centralTime.getMinutes();
    const seconds = centralTime.getSeconds();
    
    // Check if we're at a 15-minute mark (:00, :15, :30, :45)
    if ((minutes % 15 === 0) && seconds < 5) {
      const timeSinceLastRefresh = now.getTime() - lastRefreshTime;
      // Only refresh if it's been at least 14 minutes (to avoid duplicate refreshes)
      if (timeSinceLastRefresh >= (14 * 60 * 1000)) {
        console.log('Page became visible at 15-minute mark. Refreshing now...');
        refresh();
      }
    }
  }
});

// Also handle focus events as a backup (for iframe scenarios)
window.addEventListener('focus', () => {
  const now = new Date();
  const centralTimeStr = now.toLocaleString('en-US', { timeZone: 'America/Chicago' });
  const centralTime = new Date(centralTimeStr);
  const minutes = centralTime.getMinutes();
  const seconds = centralTime.getSeconds();
  
  // Check if we're at a 15-minute mark
  if ((minutes % 15 === 0) && seconds < 5) {
    const timeSinceLastRefresh = now.getTime() - lastRefreshTime;
    if (timeSinceLastRefresh >= (14 * 60 * 1000)) {
      console.log('Window gained focus at 15-minute mark. Refreshing now...');
      refresh();
    }
  }
});

// Initialize
(async function init(){
  updateDateTime();  // Set initial date/time
  await refresh();   // Initial refresh
  scheduleNextRefresh();  // Schedule next refresh at the next 15-minute mark
  
  // Update date/time display every second
  setInterval(updateDateTime, 1000);
})();
