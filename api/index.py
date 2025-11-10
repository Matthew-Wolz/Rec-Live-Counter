"""
Vercel serverless function entry point for Flask application.
"""
import sys
import os
from io import BytesIO

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app import create_app

# Create Flask app instance
app = create_app()

def handler(request):
    """Handle requests in Vercel's serverless environment using WSGI."""
    # Get request details
    method = request.get('REQUEST_METHOD', 'GET')
    path = request.get('PATH_INFO', '/')
    query_string = request.get('QUERY_STRING', '')
    headers = {k: v for k, v in request.items() if k.startswith('HTTP_')}
    
    # Build WSGI environ dictionary
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': headers.get('HTTP_HOST', 'localhost').split(':')[0],
        'SERVER_PORT': headers.get('HTTP_HOST', 'localhost').split(':')[1] if ':' in headers.get('HTTP_HOST', '') else '80',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': headers.get('HTTP_X_FORWARDED_PROTO', 'https'),
        'wsgi.input': BytesIO(),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    
    # Add all HTTP headers to environ
    for key, value in headers.items():
        environ[key] = value
    
    # Response storage
    response_status = [200]
    response_headers_list = []
    
    def start_response(status, headers_list):
        response_status[0] = int(status.split()[0])
        response_headers_list[:] = headers_list
    
    # Call Flask app
    result = app(environ, start_response)
    
    # Collect response body
    body_parts = []
    for part in result:
        if isinstance(part, bytes):
            body_parts.append(part)
        else:
            body_parts.append(part.encode('utf-8'))
    
    body = b''.join(body_parts)
    
    # Convert headers to dict
    headers_dict = dict(response_headers_list)
    
    return {
        'statusCode': response_status[0],
        'headers': headers_dict,
        'body': body.decode('utf-8')
    }

