
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and create the Flask app
# Vercel will automatically handle WSGI conversion
try:
    from backend.app import create_app
    app = create_app()
except Exception as e:
    # If app creation fails, create a minimal error app
    from flask import Flask, jsonify
    import traceback
    
    error_app = Flask(__name__)
    
    @error_app.route('/')
    @error_app.route('/<path:path>')
    def error_handler(path='/'):
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Flask app initialization error: {error_msg}", file=sys.stderr)
        print(error_trace, file=sys.stderr)
        return jsonify({
            'error': 'Application initialization failed',
            'message': error_msg,
            'type': type(e).__name__
        }), 500
    
    app = error_app

