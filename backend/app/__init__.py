"""Flask application factory and configuration."""
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from .sheets import fetch_sheet_data, process_hourly_breakdown

load_dotenv()

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # Serve the frontend directory so users can open the UI at http://127.0.0.1:5000/
    # Handle both local development and serverless deployment paths
    try:
        # Try relative path first (for serverless)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.join(current_dir, '..', '..', 'frontend')
        frontend_dir = os.path.abspath(frontend_dir)
        
        # Verify the directory exists
        if not os.path.exists(frontend_dir):
            # Try alternative path
            frontend_dir = os.path.join(os.getcwd(), 'frontend')
            if not os.path.exists(frontend_dir):
                raise FileNotFoundError(f"Frontend directory not found. Tried: {frontend_dir}")
    except Exception as e:
        print(f"Warning: Could not resolve frontend directory: {e}", file=sys.stderr)
        # Fallback to a relative path
        frontend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
    
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    CORS(app)  # Enable CORS for all routes
    
    if test_config is None:
        app.config.from_mapping(
            SPREADSHEET_ID=os.getenv('SPREADSHEET_ID'),
            SHEET_RANGE=os.getenv('SHEET_RANGE', 'A:Q')
        )
    else:
        app.config.update(test_config)
    
    @app.route('/api/hourly_breakdown')
    def hourly_breakdown():
        """Return the hourly breakdown of people in each area."""
        try:
            df = fetch_sheet_data(
                app.config['SPREADSHEET_ID'],
                app.config['SHEET_RANGE']
            )
            data = process_hourly_breakdown(df)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'error': str(e),
                'status': 'error'
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