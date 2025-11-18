# Rec Center Live Patron Counter

An informational overview of the Rec Center Live Patron Counter project. This document describes what the project is, the problem it solves, and how the data is surfaced to viewers.

Live deployment and embedding
--------------------------------

- Live demo: https://rec-live-counter.vercel.app
- Embedded on: https://recreation.truman.edu

What this project does
----------------------

This project reads occupancy logs (headcounts) and displays a live, area-by-area bar chart of patron presence in the Student Recreation Center at Truman State University. The visualization is updated frequently so viewers can see where people are in the building in near real time.

Why this was built — the problem it solves
-----------------------------------------

Historically, the campus published an "active times" histogram that showed aggregate entry counts across a full year. That chart reported total entries (often cumulative or averaged over a long period) and did not reflect who was actually inside the building on a given day, nor where in the facility people were congregating.

This project addresses that limitation by:
- Using per-sample headcounts (timestamped logs) instead of long-term entry aggregates
- Providing a breakdown by area (Main Gym, Weight Room, Track, etc.) so viewers can see distribution of patrons across spaces
- Updating on a regular cadence so the chart reflects current conditions rather than a historical average

Features (for viewers)
-----------------------

- Live area-by-area bar chart showing current headcounts
- Automatic periodic refresh so the published widget stays up-to-date
- Compact JSON API that powers the visualization and can be repurposed by other consumers

API (what the frontend consumes)
--------------------------------

The backend exposes a single JSON endpoint consumed by the frontend: `GET /api/hourly_breakdown`.

The response includes the area labels and a mapping of area → counts. Example shape (single-current-count mode):

```json
{
	"labels": ["Main Gym","Weight Room","Multipurpose Gym","Track","Aerobics Room","Table Tennis","Lobby"],
	"places": ["Main Gym","Weight Room","Multipurpose Gym","Track","Aerobics Room","Table Tennis","Lobby"],
	"seriesByPlace": {
		"Main Gym": [11],
		"Weight Room": [22],
		"Multipurpose Gym": [0],
		"Track": [2],
		"Aerobics Room": [1],
		"Table Tennis": [0],
		"Lobby": [3]
	},
	"last_updated_utc": "2025-11-03T20:04:46Z"
}
```

Notes:
- The `seriesByPlace` values are arrays; in the current display mode each array contains a single value (the current/latest count for that area).

Data grouping and customization
------------------------------

Area groupings are defined in `backend/app/sheets.py` in the `AREA_MAPPINGS` dictionary. By default, the repository aggregates several related columns into a single additive group named `Lobby` (Cubby Cove, Vicore Equipment, Bikes in Lobby).
