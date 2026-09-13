import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _build_app():
    try:
        from backend.app import create_app
        return create_app()
    except Exception as e:
        from flask import Flask, jsonify
        import traceback

        error_app = Flask(__name__)
        init_error = e

        @error_app.route('/')
        @error_app.route('/<path:path>')
        def error_handler(path='/'):
            error_msg = str(init_error)
            error_trace = traceback.format_exc()
            print(f"Flask app initialization error: {error_msg}", file=sys.stderr)
            print(error_trace, file=sys.stderr)
            return jsonify({
                'error': 'Application initialization failed',
                'message': error_msg,
                'type': type(init_error).__name__
            }), 500

        return error_app


# Vercel requires a top-level WSGI/ASGI variable named app, application, or handler
app = _build_app()
