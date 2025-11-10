"""Flask application factory and configuration."""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from .sheets import fetch_sheet_data, process_hourly_breakdown

load_dotenv()

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # Serve the frontend directory so users can open the UI at http://127.0.0.1:5000/
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
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
        return app.send_static_file('index.html')
    
    return app