import os
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
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

def get_sheets_service():
    """Initialize Google Sheets API service."""
    import json
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    # For production (Vercel) - read from environment variable
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    if service_account_json:
        try:
            service_account_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
            return build('sheets', 'v4', credentials=credentials)
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid GOOGLE_SERVICE_ACCOUNT environment variable: {e}")
    
    # For local development with service account file
    if os.path.exists('service-account.json'):
        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json', scopes=SCOPES)
        return build('sheets', 'v4', credentials=credentials)
    
    # For local development with OAuth token
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
        return build('sheets', 'v4', credentials=credentials)
    
    raise FileNotFoundError("No credentials found. Please set up authentication.")

def fetch_sheet_data(spreadsheet_id: str, range_name: str = 'A:Q') -> pd.DataFrame:
    """Fetch data from Google Sheet and return as DataFrame."""
    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    values = result.get('values', [])
    if not values:
        raise ValueError('No data found in spreadsheet')
        
    print(f"\nReceived {len(values)} rows from Google Sheets")
    print(f"First row (headers): {values[0]}")
    
    # Convert to DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])
    
    # Convert Timestamp column
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Convert count columns to numeric
    count_columns = [col for col in df.columns if col not in ['Timestamp', 'Day']]
    for col in count_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def process_hourly_breakdown(df: pd.DataFrame) -> Dict:
    """Process DataFrame into hourly breakdown by area."""
    # Simply get the last row of data
    latest_row = df.iloc[-1]  # Get the very last row
    print(f"\nUsing data from: {latest_row['Timestamp']}")
    
    # Calculate and print raw totals for debugging
    total_people = 0
    print("\nRaw counts from latest row:")
    for area, columns in AREA_MAPPINGS.items():
        area_total = sum(latest_row[col] for col in columns if col in latest_row)
        print(f"{area}: {area_total} (columns: {columns})")
        total_people += area_total
    print(f"Total people (sum of all areas): {total_people}")
    
    # Create data structure with areas as labels
    areas = list(AREA_MAPPINGS.keys())
    data = {
        'labels': areas,
        'places': areas,
        'seriesByPlace': {area: [] for area in areas},
        'last_updated_utc': latest_row['Timestamp'].isoformat()
    }
    
    # Calculate totals for each area
    for area, columns in AREA_MAPPINGS.items():
        total = sum(latest_row[col] for col in columns if col in latest_row)
        data['seriesByPlace'][area] = [int(total)]
    
    print("\nProcessed data structure:")
    print(f"Labels (areas): {data['labels']}")
    print(f"Series by place: {data['seriesByPlace']}")
    
    return data

    # ORIGINAL CODE TO RESTORE LATER:
    # # Get current date's data
    # today = datetime.now(timezone.utc).date()
    # df = df[df['Timestamp'].dt.date == today]
    # 
    # if df.empty:
    #     return {
    #         'labels': [],
    #         'places': list(AREA_MAPPINGS.keys()),
    #         'seriesByPlace': {place: [] for place in AREA_MAPPINGS},
    #         'last_updated_utc': datetime.now(timezone.utc).isoformat()
    #     }
    # 
    # # Group by hour
    # df['hour'] = df['Timestamp'].dt.hour
    # hourly_groups = df.groupby('hour')
    
    # Generate hourly breakdown for each area
    labels = []
    series_by_place = {place: [] for place in AREA_MAPPINGS}
    
    for hour in range(6, 23):  # 6 AM to 10 PM
        if hour in hourly_groups.groups:
            hour_data = hourly_groups.get_group(hour)
            latest_record = hour_data.iloc[-1]  # Get most recent count for the hour
            
            # Sum up counts for each area based on mappings
            for area, columns in AREA_MAPPINGS.items():
                total = sum(latest_record[col] for col in columns if col in latest_record)
                series_by_place[area].append(int(total))
        else:
            # Fill missing hours with zeros
            for area in AREA_MAPPINGS:
                series_by_place[area].append(0)
        
        labels.append(f"{hour:02d}:00")
    
    return {
        'labels': labels,
        'places': list(AREA_MAPPINGS.keys()),
        'seriesByPlace': series_by_place,
        'last_updated_utc': df['Timestamp'].max().isoformat()
    }