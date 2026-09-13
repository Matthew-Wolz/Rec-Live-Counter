import os
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Area groupings for the histogram
AREA_MAPPINGS = {
    'Main Gym': ['Main Gym'],
    'Weight Room': ['Weight Room', 'Treadmills', 'CV Stairmasters'],
    'Multipurpose Gym': ['MP Gym'],
    'Track': ['Track', 'CV Rowers', 'Bikes on Track', 'CV Ellipticals'],
    'Aerobics Room': ['Aerobics Room'],
    'Table Tennis': ['Table Tennis'],
    'Lobby': ['Cubby "Cove"', 'Vicore Equipment', 'Bikes in Lobby']
}

_sheets_service = None


def get_sheets_service():
    """Initialize Google Sheets API service (cached for warm serverless instances)."""
    global _sheets_service
    if _sheets_service is not None:
        return _sheets_service

    import json
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    if service_account_json:
        try:
            service_account_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
            _sheets_service = build(
                'sheets', 'v4', credentials=credentials, cache_discovery=False)
            return _sheets_service
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid GOOGLE_SERVICE_ACCOUNT environment variable: {e}")

    if os.path.exists('service-account.json'):
        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json', scopes=SCOPES)
        _sheets_service = build(
            'sheets', 'v4', credentials=credentials, cache_discovery=False)
        return _sheets_service

    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
        _sheets_service = build(
            'sheets', 'v4', credentials=credentials, cache_discovery=False)
        return _sheets_service

    raise FileNotFoundError("No credentials found. Please set up authentication.")


def _to_number(value: Any) -> float:
    if value is None or value == '':
        return 0.0
    try:
        return float(str(value).replace(',', ''))
    except (TypeError, ValueError):
        return 0.0


def fetch_latest_row(spreadsheet_id: str, range_name: str = 'A:Q') -> Dict[str, Any]:
    """Fetch header + latest data row from Google Sheets without pandas."""
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        majorDimension='ROWS',
        valueRenderOption='UNFORMATTED_VALUE',
        dateTimeRenderOption='FORMATTED_STRING',
    ).execute()

    values: List[List[Any]] = result.get('values', [])
    if not values:
        raise ValueError('No data found in spreadsheet')

    headers = [str(h) for h in values[0]]
    data_rows = values[1:]
    if not data_rows:
        raise ValueError('Spreadsheet has headers but no data rows')

    latest = list(data_rows[-1])
    if len(latest) < len(headers):
        latest = latest + [''] * (len(headers) - len(latest))

    row = {headers[i]: latest[i] for i in range(len(headers))}
    print(f"Received {len(values)} rows from Google Sheets; using latest row")
    return row


def process_hourly_breakdown(latest_row: Dict[str, Any]) -> Dict:
    """Aggregate latest sheet row into area counts for the chart API."""
    timestamp = latest_row.get('Timestamp', '')
    if timestamp is None:
        timestamp = ''
    timestamp_str = str(timestamp)

    areas = list(AREA_MAPPINGS.keys())
    series_by_place = {}
    for area, columns in AREA_MAPPINGS.items():
        total = sum(_to_number(latest_row.get(col, 0)) for col in columns)
        series_by_place[area] = [int(total)]

    return {
        'labels': areas,
        'places': areas,
        'seriesByPlace': series_by_place,
        'last_updated_utc': timestamp_str,
    }


def fetch_sheet_data(spreadsheet_id: str, range_name: str = 'A:Q') -> Dict[str, Any]:
    """Backwards-compatible name used by the Flask app."""
    return fetch_latest_row(spreadsheet_id, range_name)
