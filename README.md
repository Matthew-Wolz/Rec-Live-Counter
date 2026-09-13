# Rec Center Live Patron Counter

Live, area-by-area headcount chart for the Student Recreation Center at Truman State University. Built to replace a year-long “active times” entry histogram that did not show who was actually in the building, or where.

| | |
|---|---|
| **Live demo** | https://rec-live-counter.vercel.app |
| **Embedded on** | https://recreation.truman.edu (iframe) |
| **Repo** | https://github.com/Matthew-Wolz/Rec-Live-Counter |

---

## What it does

- Reads timestamped occupancy logs from a **Google Sheet**
- Exposes a small JSON API with the **latest** counts per area
- Renders a **Chart.js** bar chart for viewers (desktop and mobile)
- Refreshes about every **15 minutes** (America/Chicago clock marks)
- Shows a **closed / no recent updates** message outside open hours or when sheet data is stale

---

## Architecture

```
Google Sheet (headcount rows)
        │  service account (readonly)
        ▼
Flask API  GET /api/hourly_breakdown
        │  (Vercel Python function only)
        ▼
Static UI  public/  (HTML / CSS / JS + Chart.js CDN)
        │
        ▼
Browser / iframe on recreation.truman.edu
```

**Production (Vercel)**

- `vercel.json` builds **two** outputs: `@vercel/python` for `api/index.py`, and `@vercel/static` for `public/**`.
- Routes: `/api/*` → Flask; `/` and other paths → `public/` (HTML/CSS/JS on the CDN, not Python).
- API responses are cached in-process for ~**2 minutes** and send `Cache-Control` so concurrent viewers share one Sheets read.
- Do **not** use a Python-only `builds` config — that ships the API but 404s the entire UI. Do **not** drop the Python build — that 404s `/api/*` while the UI still loads.

**Local development**

- One Flask process serves both the UI (from `public/`, falling back to `frontend/`) and the API.

---

## Repository layout

```
rec-center-traffic-histogram/
├── api/index.py              # Vercel Python entry (exposes Flask `app`)
├── backend/app/
│   ├── __init__.py           # Flask factory, routes, API cache
│   └── sheets.py             # Sheets auth, latest-row parse, AREA_MAPPINGS
├── public/                   # UI served in production (and preferred locally)
│   ├── index.html
│   ├── scripts/app.js
│   └── styles/styles.css
├── frontend/                 # Keep in sync with public/ when editing the UI
├── vercel.json               # API rewrite + headers
├── requirements.txt
├── convert-service-account.ps1   # Helper to flatten JSON for Vercel env
├── .env                      # Local config (gitignored)
└── service-account.json      # Local Google creds (gitignored)
```

**Important:** `public/` and `frontend/` should stay identical for the UI. Production uses `public/`. After editing either copy, update the other (or copy `frontend/` → `public/` before deploy).

---

## Features (viewers)

- Area bar chart (Truman purple): Main Gym, Weight Room, Multipurpose Gym, Track, Aerobics Room, Table Tennis, Lobby
- **Desktop:** vertical bars. **Narrow / mobile (&lt; ~600px):** horizontal bars so labels stay readable
- **Embed mode:** compact layout, `overflow: hidden`, sized for iframes (reduces unwanted scrolling on the campus site)
- Clock in Central time **without** `CDT`/`CST` suffix
- Subtitle: updated every 15 minutes
- Outside open hours (or stale data): message instead of chart

---

## Open hours and closed / stale message

All times are **America/Chicago**.

| Days | Open |
|------|------|
| Monday–Thursday | 6:30 AM – 10:00 PM |
| Friday | 6:30 AM – 7:00 PM |
| Saturday–Sunday | 11:00 AM – 6:00 PM |

Behavior (implemented in `public/scripts/app.js` / `frontend/scripts/app.js`):

1. **Outside open hours** → show: *There have been no updates recently. Please check the hours to make sure the Student Recreation Center is open.* **Do not call the API** (saves Vercel CPU overnight/weekends).
2. **During open hours** → fetch the API. If `last_updated_utc` is older than **5 hours**, show the same message (covers holidays / missed logs).
3. Otherwise → show the chart.

Edit `OPEN_HOURS` and `STALE_MS` in `app.js` if hours or the stale threshold change.

---

## API

`GET /api/hourly_breakdown`

Uses the **latest row** of the sheet (not a full hourly history). Area totals come from `AREA_MAPPINGS` in `backend/app/sheets.py`.

Example:

```json
{
  "labels": ["Main Gym", "Weight Room", "Multipurpose Gym", "Track", "Aerobics Room", "Table Tennis", "Lobby"],
  "places": ["Main Gym", "Weight Room", "Multipurpose Gym", "Track", "Aerobics Room", "Table Tennis", "Lobby"],
  "seriesByPlace": {
    "Main Gym": [11],
    "Weight Room": [22],
    "Multipurpose Gym": [0],
    "Track": [2],
    "Aerobics Room": [1],
    "Table Tennis": [0],
    "Lobby": [3]
  },
  "last_updated_utc": "9/12/2026 17:25:50"
}
```

Notes:

- Each `seriesByPlace` value is a one-element array (current count).
- Response may include `X-Cache: HIT|MISS` from the short server cache.
- Endpoint name is historical (`hourly_breakdown`); behavior is latest snapshot.

### Area groupings

Default mappings in `backend/app/sheets.py`:

| Chart label | Sheet columns summed |
|-------------|----------------------|
| Main Gym | Main Gym |
| Weight Room | Weight Room, Treadmills, CV Stairmasters |
| Multipurpose Gym | MP Gym |
| Track | Track, CV Rowers, Bikes on Track, CV Ellipticals |
| Aerobics Room | Aerobics Room |
| Table Tennis | Table Tennis |
| Lobby | Cubby "Cove", Vicore Equipment, Bikes in Lobby |

---

## Local development

### Prerequisites

- Python 3.10+ recommended
- Google Cloud service account with **Sheets read-only** access to the spreadsheet
- Share the spreadsheet with the service account email

### Setup

```powershell
cd rec-center-traffic-histogram
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in the project root (never commit it):

```env
SPREADSHEET_ID=your_spreadsheet_id
SHEET_RANGE=A:Q
FLASK_APP=backend.app:create_app
```

Place `service-account.json` in the project root (gitignored).

### Run

```powershell
$env:FLASK_APP = "backend.app:create_app"
$env:FLASK_DEBUG = "1"
flask run
```

Open http://127.0.0.1:5000/  
API: http://127.0.0.1:5000/api/hourly_breakdown  

Optional: `CACHE_TTL_SECONDS` (default `120`) controls the in-process API cache TTL.

---

## Deploy (Vercel)

1. Repo is connected to Vercel (GitHub: `Matthew-Wolz/Rec-Live-Counter`).
2. **Push to `main`** → Vercel builds and deploys automatically.
3. No dashboard changes are required for normal UI/API code updates.

### Vercel environment variables

| Variable | Purpose |
|----------|---------|
| `SPREADSHEET_ID` | Google Sheet ID |
| `SHEET_RANGE` | Range to read (e.g. `A:Q`) |
| `GOOGLE_SERVICE_ACCOUNT` | Full service-account JSON as a **single-line** string |

To prepare the JSON string locally:

```powershell
.\convert-service-account.ps1
```

That writes `service-account-oneline.txt` (gitignored). Paste its contents into the Vercel env var. **Do not commit** that file or `service-account.json`.

---

## Secrets — do not commit

Gitignored (must stay out of the repo):

- `.env`
- `service-account.json`
- `service-account-oneline.txt`
- `token.json`
- `.venv/`

`requirements.txt` **is** committed (Vercel needs it).

---

## Where to edit (handoff map)

| Change | Files |
|--------|--------|
| Area / column groupings | `backend/app/sheets.py` (`AREA_MAPPINGS`) |
| Open hours, stale window, refresh, chart behavior | `public/scripts/app.js` **and** `frontend/scripts/app.js` |
| Layout, embed sizing, styles | `public/styles/styles.css` **and** `frontend/styles/styles.css` (+ HTML if needed) |
| API caching / Flask routes | `backend/app/__init__.py` |
| Sheets fetch / auth | `backend/app/sheets.py` |
| Vercel routing (API vs static) | `vercel.json`, `api/index.py` |

---

## Why it was built

Campus used to publish an “active times” histogram of aggregate entries over a long period. That did not reflect current occupancy or distribution by area. This project uses per-sample headcounts, breaks them down by space, and refreshes on a regular cadence so the public widget shows near-real-time conditions.
