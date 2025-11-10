"""
Vercel serverless function entry point for Flask application.
"""
import sys
import os
import json
from io import BytesIO
from urllib.parse import urlencode, urlparse

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from backend.app import create_app
    # Create Flask app instance (module-level for reuse)
    app = create_app()
except Exception as e:
    print(f"Error creating Flask app: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    app = None

def handler(request):
    """
    Handle requests in Vercel's serverless environment.
    Vercel Python runtime passes request as dict with keys like:
    - method (str)
    - url (str) 
    - headers (dict)
    - body (str, optional)
    - query (dict, optional)
    """
    if app is None:
        return {
            'statusCode': 500,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({'error': 'Flask app failed to initialize'})
        }
    
    try:
        # Handle both dict and object-style request
        if hasattr(request, 'method'):
            method = request.method
            url = getattr(request, 'url', '/')
            headers = getattr(request, 'headers', {})
            body = getattr(request, 'body', '')
            query = getattr(request, 'query', {})
        else:
            method = request.get('method', 'GET')
            url = request.get('url', request.get('path', '/'))
            headers = request.get('headers', {})
            body = request.get('body', '')
            query = request.get('query', {})
        
        # Parse URL to get path
        if url.startswith('http'):
            parsed = urlparse(url)
            path = parsed.path or '/'
            query_string = parsed.query
        else:
            # URL is just the path
            if '?' in url:
                path, query_string = url.split('?', 1)
            else:
                path = url
                query_string = urlencode(query) if query else ''
        
        # Get host and scheme from headers
        host = headers.get('host') or headers.get('x-forwarded-host') or 'localhost'
        scheme = headers.get('x-forwarded-proto') or headers.get('x-forwarded-proto') or 'https'
        
        # Prepare body
        if body and isinstance(body, str):
            body_bytes = body.encode('utf-8')
        elif body:
            body_bytes = body
        else:
            body_bytes = b''
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': method.upper(),
            'SCRIPT_NAME': '',
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body_bytes)),
            'SERVER_NAME': host.split(':')[0],
            'SERVER_PORT': host.split(':')[1] if ':' in host else ('443' if scheme == 'https' else '80'),
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': scheme,
            'wsgi.input': BytesIO(body_bytes),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add HTTP headers (convert to HTTP_* format)
        for key, value in headers.items():
            if key.lower() in ('content-type', 'content-length'):
                continue  # Already handled above
            env_key = 'HTTP_' + key.upper().replace('-', '_')
            environ[env_key] = value
        
        # Response storage
        status_code = [200]
        response_headers = []
        
        def start_response(status, headers_list, exc_info=None):
            status_code[0] = int(status.split()[0])
            response_headers[:] = headers_list
            if exc_info is not None:
                raise exc_info[1].with_traceback(exc_info[2])
        
        # Call Flask app
        response_iter = app(environ, start_response)
        
        # Collect response body
        response_body_parts = []
        try:
            for chunk in response_iter:
                if isinstance(chunk, bytes):
                    response_body_parts.append(chunk)
                else:
                    response_body_parts.append(chunk.encode('utf-8'))
        finally:
            if hasattr(response_iter, 'close'):
                response_iter.close()
        
        response_body = b''.join(response_body_parts)
        
        # Convert headers to dict
        headers_dict = {}
        for key, value in response_headers:
            key_lower = key.lower()
            if key_lower in headers_dict:
                # Handle multiple values
                if not isinstance(headers_dict[key_lower], list):
                    headers_dict[key_lower] = [headers_dict[key_lower]]
                headers_dict[key_lower].append(value)
            else:
                headers_dict[key_lower] = value
        
        # Convert header lists to strings (Vercel may need this)
        for key, value in headers_dict.items():
            if isinstance(value, list):
                headers_dict[key] = ', '.join(str(v) for v in value)
        
        return {
            'statusCode': status_code[0],
            'headers': headers_dict,
            'body': response_body.decode('utf-8', errors='replace')
        }
        
    except Exception as e:
        # Log the full error
        import traceback
        error_trace = traceback.format_exc()
        error_msg = str(e)
        print(f"Handler error: {error_msg}", file=sys.stderr)
        print(error_trace, file=sys.stderr)
        
        return {
            'statusCode': 500,
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': error_msg,
                'type': type(e).__name__
            })
        }

