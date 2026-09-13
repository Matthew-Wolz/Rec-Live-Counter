import os
import sys
import time
from flask import Flask, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

CACHE_TTL_SECONDS = 120  # collapse concurrent viewer bursts onto one Sheets read

try:
    from .sheets import fetch_sheet_data, process_hourly_breakdown
    sheets_available = True
except Exception as e:
    print(f"Warning: Could not import sheets module: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sheets_available = False
    fetch_sheet_data = None
    process_hourly_breakdown = None

# Simple in-process cache (helps warm Vercel instances; not shared across isolates)
_cache = {
    'data': None,
    'expires_at': 0.0,
}


def _resolve_static_dir():
    """Prefer public/ (Vercel static) then frontend/ (legacy local path)."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(current_dir, '..', '..'))
    candidates = [
        os.path.join(project_root, 'public'),
        os.path.join(project_root, 'frontend'),
        os.path.join(os.getcwd(), 'public'),
        os.path.join(os.getcwd(), 'frontend'),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return os.path.normpath(os.path.abspath(path))
    fallback = os.path.normpath(os.path.join(project_root, 'public'))
    print(f"Warning: Static directory may not exist: {fallback}", file=sys.stderr)
    return fallback


def create_app(test_config=None):
    """Create and configure the Flask application."""
    static_dir = _resolve_static_dir()
    app = Flask(__name__, static_folder=static_dir, static_url_path='')
    CORS(app)

    if test_config is None:
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        sheet_range = os.getenv('SHEET_RANGE', 'A:Q')

        app.config.from_mapping(
            SPREADSHEET_ID=spreadsheet_id,
            SHEET_RANGE=sheet_range,
            CACHE_TTL_SECONDS=int(os.getenv('CACHE_TTL_SECONDS', str(CACHE_TTL_SECONDS))),
        )

        if not spreadsheet_id:
            print("Warning: SPREADSHEET_ID environment variable not set", file=sys.stderr)
    else:
        app.config.update(test_config)

    def _cached_breakdown():
        now = time.time()
        ttl = app.config.get('CACHE_TTL_SECONDS', CACHE_TTL_SECONDS)
        if _cache['data'] is not None and now < _cache['expires_at']:
            return _cache['data'], True

        spreadsheet_id = app.config.get('SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError('SPREADSHEET_ID environment variable not set')

        sheet_range = app.config.get('SHEET_RANGE', 'A:Q')
        latest_row = fetch_sheet_data(spreadsheet_id, sheet_range)
        data = process_hourly_breakdown(latest_row)
        _cache['data'] = data
        _cache['expires_at'] = now + ttl
        return data, False

    @app.route('/api/hourly_breakdown')
    def hourly_breakdown():
        """Return latest area headcounts (cached briefly to reduce Sheets/CPU load)."""
        if not sheets_available or not fetch_sheet_data or not process_hourly_breakdown:
            return jsonify({
                'error': 'Sheets module not available',
                'status': 'error'
            }), 500

        try:
            data, from_cache = _cached_breakdown()
            resp = make_response(jsonify(data))
            ttl = app.config.get('CACHE_TTL_SECONDS', CACHE_TTL_SECONDS)
            resp.headers['Cache-Control'] = f'public, s-maxage={ttl}, max-age=30'
            resp.headers['X-Cache'] = 'HIT' if from_cache else 'MISS'
            return resp
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Error in hourly_breakdown: {error_msg}", file=sys.stderr)
            print(error_trace, file=sys.stderr)
            return jsonify({
                'error': error_msg,
                'status': 'error',
                'type': type(e).__name__
            }), 500

    @app.route('/')
    def index():
        try:
            return app.send_static_file('index.html')
        except Exception as e:
            return f"Error serving index.html: {str(e)}", 500

    @app.route('/<path:path>')
    def serve_static(path):
        if path.startswith('api/'):
            return "Not found", 404

        try:
            if path.startswith('styles/') or path.startswith('scripts/'):
                return app.send_static_file(path)
            try:
                return app.send_static_file(path)
            except Exception:
                return "File not found", 404
        except Exception as e:
            return f"Error serving file: {str(e)}", 500

    return app
