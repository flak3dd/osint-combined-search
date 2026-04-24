import os
import sys
import json
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Flask request for serverless
class MockRequest:
    def __init__(self, method, path, headers, body):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'wsgi.input': body.encode() if isinstance(body, str) else body
        }

def handler(request):
    """Vercel serverless handler"""
    try:
        # Parse the request
        method = request.get('method', 'GET')
        path = request.get('path', '/')
        headers = request.get('headers', {})
        body = request.get('body', '')
        
        # Import Flask app
        from osint_web_app import app
        
        # Use Flask's test client for serverless
        with app.test_client() as client:
            if method == 'GET':
                response = client.get(path, headers=headers)
            elif method == 'POST':
                response = client.post(path, data=body, headers=headers, content_type=headers.get('content-type', 'application/json'))
            else:
                response = client.open(path, method=method, data=body, headers=headers)
            
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': response.get_data(as_text=True)
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

# For local development
if __name__ == "__main__":
    from osint_web_app import app
    app.run(host='0.0.0.0', port=5000, debug=True)