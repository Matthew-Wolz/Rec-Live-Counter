"""Flask application factory and configuration."""
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Import sheets module with error handling
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

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # Serve the frontend directory so users can open the UI at http://127.0.0.1:5000/
    # Handle both local development and serverless deployment paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(current_dir, '..', '..', 'frontend')
    frontend_dir = os.path.normpath(os.path.abspath(frontend_dir))
    
    # Verify the directory exists, if not try alternative paths
    if not os.path.exists(frontend_dir):
        # Try from current working directory
        alt_frontend_dir = os.path.join(os.getcwd(), 'frontend')
        if os.path.exists(alt_frontend_dir):
            frontend_dir = alt_frontend_dir
        else:
            # Try relative to project root (for Vercel)
            project_root = os.path.dirname(os.path.dirname(current_dir))
            alt_frontend_dir = os.path.join(project_root, 'frontend')
            if os.path.exists(alt_frontend_dir):
                frontend_dir = alt_frontend_dir
            else:
                # Last resort: use the path anyway (might work in some environments)
                print(f"Warning: Frontend directory may not exist: {frontend_dir}", file=sys.stderr)
    
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    CORS(app)  # Enable CORS for all routes
    
    if test_config is None:
        # Get environment variables with defaults
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        sheet_range = os.getenv('SHEET_RANGE', 'A:Q')
        
        app.config.from_mapping(
            SPREADSHEET_ID=spreadsheet_id,
            SHEET_RANGE=sheet_range
        )
        
        # Log configuration (without sensitive data)
        if not spreadsheet_id:
            print("Warning: SPREADSHEET_ID environment variable not set", file=sys.stderr)
    else:
        app.config.update(test_config)
    
    @app.route('/api/hourly_breakdown')
    def hourly_breakdown():
        """Return the hourly breakdown of people in each area."""
        if not sheets_available or not fetch_sheet_data or not process_hourly_breakdown:
            return jsonify({
                'error': 'Sheets module not available',
                'status': 'error'
            }), 500
        
        try:
            spreadsheet_id = app.config.get('SPREADSHEET_ID')
            if not spreadsheet_id:
                return jsonify({
                    'error': 'SPREADSHEET_ID environment variable not set',
                    'status': 'error'
                }), 500
            
            sheet_range = app.config.get('SHEET_RANGE', 'A:Q')
            df = fetch_sheet_data(spreadsheet_id, sheet_range)
            data = process_hourly_breakdown(df)
            return jsonify(data)
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

    # Serve the single-page frontend (index.html) at the root
    @app.route('/')
    def index():
        try:
            return app.send_static_file('index.html')
        except Exception as e:
            return f"Error serving index.html: {str(e)}", 500
    
    # Serve static files (CSS, JS) - but not API routes
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files from frontend directory."""
        # Don't serve API routes as static files
        if path.startswith('api/'):
            return "Not found", 404
        
        try:
            # Serve files from styles and scripts directories
            if path.startswith('styles/') or path.startswith('scripts/'):
                return app.send_static_file(path)
            # Try to serve other files (like favicon)
            try:
                return app.send_static_file(path)
            except:
                return "File not found", 404
        except Exception as e:
            return f"Error serving file: {str(e)}", 500
    
    return app