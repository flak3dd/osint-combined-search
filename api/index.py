import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osint_web_app import app

# Vercel serverless handler using WSGI
from vercel_wsgi import handle

def handler(request):
    return handle(app, request)

# For local development
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)