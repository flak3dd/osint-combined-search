#!/usr/bin/env python3
"""
OSINT Combined Search Web App v4 (OPTIMIZED)
Flask + Bootstrap 5 with performance optimizations, caching, and async operations
"""

import os
import json
import time
import hashlib
import requests
import re
from io import BytesIO
from flask import Flask, render_template_string, request, jsonify, send_file
from osint_combined_search import OSINTCombinedSearch

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "osint-change-me-in-prod")

# Configure cache headers
@app.after_request
def add_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Global searcher instance with caching
searcher = OSINTCombinedSearch()

# API key storage (in-memory for demo, in production use secure storage)
api_keys_storage = {
    "osint_industries": os.getenv("OSINT_INDUSTRIES_API_KEY"),
    "dehashed": os.getenv("DEHASHED_API_KEY"),
    "cypher_dynamics": os.getenv("CYPHER_DYNAMICS_API_KEY")
}

# Simple in-memory cache for search results
search_cache = {}
CACHE_TTL = 3600  # 1 hour cache

def get_cache_key(query: str, query_type: str, sources: list, filters: dict) -> str:
    """Generate a unique cache key for search parameters"""
    cache_data = {
        'query': query,
        'type': query_type,
        'sources': sorted(sources),
        'filters': filters
    }
    return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

def extract_passwords_by_url(results: dict, target_emails: list, target_url: str) -> dict:
    """Extract passwords for specific emails from a specific URL"""
    extracted = {
        'target_url': target_url,
        'target_emails': target_emails,
        'passwords': []
    }
    
    for source, data in results.get('results', {}).items():
        if data.get('status') != 'success':
            continue
            
        source_results = data.get('results', {})
        
        # Handle DeHashed format
        if source == 'dehashed' and 'entries' in source_results:
            for entry in source_results['entries']:
                email = entry.get('email', '').lower()
                password = entry.get('password') or entry.get('hashed_password')
                breach_url = entry.get('website') or entry.get('source') or entry.get('breach', '')
                
                # Check if email matches and URL matches
                if email in [e.lower() for e in target_emails]:
                    if target_url.lower() in breach_url.lower() or breach_url.lower() in target_url.lower():
                        extracted['passwords'].append({
                            'email': email,
                            'password': password,
                            'url': breach_url,
                            'source': source,
                            'additional_fields': {k: v for k, v in entry.items() 
                                               if k not in ['email', 'password', 'hashed_password', 'website', 'source', 'breach']}
                        })
        
        # Handle Cypher Dynamics format
        elif source == 'cypher_dynamics' and 'credentials' in source_results:
            for cred in source_results['credentials']:
                email = cred.get('email', '').lower()
                password = cred.get('password') or cred.get('cleartext_password')
                url = cred.get('url') or cred.get('website') or cred.get('domain', '')
                
                if email in [e.lower() for e in target_emails]:
                    if target_url.lower() in url.lower() or url.lower() in target_url.lower():
                        extracted['passwords'].append({
                            'email': email,
                            'password': password,
                            'url': url,
                            'source': source,
                            'additional_fields': {k: v for k, v in cred.items() 
                                               if k not in ['email', 'password', 'cleartext_password', 'url', 'website', 'domain']}
                        })
        
        # Handle OSINT Industries format
        elif source == 'osint_industries':
            # OSINT Industries has varied structure, search broadly
            results_str = json.dumps(source_results).lower()
            if any(email.lower() in results_str for email in target_emails):
                if target_url.lower() in results_str:
                    # Try to extract structured data
                    for key, value in source_results.items():
                        if isinstance(value, dict):
                            for subkey, subval in value.items():
                                if isinstance(subval, dict):
                                    email = subval.get('email', '').lower()
                                    password = subval.get('password') or subval.get('pass')
                                    url = subval.get('url') or subval.get('website') or subval.get('domain', '')
                                    
                                    if email in [e.lower() for e in target_emails]:
                                        if target_url.lower() in url.lower() or url.lower() in target_url.lower():
                                            extracted['passwords'].append({
                                                'email': email,
                                                'password': password,
                                                'url': url,
                                                'source': source,
                                                'additional_fields': subval
                                            })
    
    extracted['total_found'] = len(extracted['passwords'])
    return extracted

def extract_lines_from_urls(urls: list, keyword: str) -> dict:
    """Extract lines containing keyword from given URLs"""
    results = {
        'keyword': keyword,
        'urls': urls,
        'extracted_lines': [],
        'errors': []
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    keyword_lower = keyword.lower()
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Try to decode content
            try:
                content = response.text
            except UnicodeDecodeError:
                content = response.content.decode('utf-8', errors='ignore')
            
            # Split into lines and filter by keyword
            lines = content.split('\n')
            matching_lines = []
            
            for i, line in enumerate(lines, 1):
                if keyword_lower in line.lower():
                    # Clean up the line (remove extra whitespace)
                    clean_line = ' '.join(line.split())
                    if clean_line:  # Only add non-empty lines
                        matching_lines.append({
                            'line_number': i,
                            'content': clean_line,
                            'url': url
                        })
            
            if matching_lines:
                results['extracted_lines'].extend(matching_lines)
                
        except requests.exceptions.RequestException as e:
            results['errors'].append({
                'url': url,
                'error': str(e)
            })
        except Exception as e:
            results['errors'].append({
                'url': url,
                'error': f"Unexpected error: {str(e)}"
            })
    
    results['total_lines_found'] = len(results['extracted_lines'])
    results['total_urls_processed'] = len(urls)
    results['total_errors'] = len(results['errors'])
    
    return results

def get_cached_result(cache_key: str):
    """Get cached result if valid"""
    if cache_key in search_cache:
        cached = search_cache[cache_key]
        if time.time() - cached['timestamp'] < CACHE_TTL:
            return cached['data']
        else:
            del search_cache[cache_key]
    return None

def set_cached_result(cache_key: str, data: dict):
    """Cache search result with timestamp"""
    search_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    # Limit cache size
    if len(search_cache) > 100:
        oldest_key = min(search_cache.keys(), key=lambda k: search_cache[k]['timestamp'])
        del search_cache[oldest_key]

# Optimized HTML template with minified CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Search v4</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root{--bg:#0d1117;--fg:#c9d1d9;--blue:#58a6ff;--purple:#a371f7;--green:#3fb950;--red:#f85149;--orange:#d29922;--glass:rgba(22,27,34,.85);--grad:linear-gradient(135deg,#667eea,#764ba2)}
        *{box-sizing:border-box}
        body{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#0d1117 0%,#161b22 50%,#0d1117 100%);min-height:100vh;color:var(--fg)}
        .bg-particles{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:-1}
        .particle{position:absolute;width:4px;height:4px;background:rgba(88,166,255,.3);border-radius:50%;animation:float 15s infinite}
        @keyframes float{0%,100%{transform:translateY(100vh) rotate(0deg);opacity:0}10%,90%{opacity:1}100%{transform:translateY(-100vh) rotate(720deg);opacity:0}}
        .navbar{background:var(--glass)!important;backdrop-filter:blur(20px);border-bottom:1px solid rgba(88,166,255,.15);box-shadow:0 4px 30px rgba(0,0,0,.4)}
        .navbar-brand{background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;font-size:1.6rem}
        .cyber-panel{background:var(--glass);border:1px solid rgba(88,166,255,.15);border-radius:20px;backdrop-filter:blur(20px);box-shadow:0 8px 32px rgba(0,0,0,.4);transition:all .4s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden}
        .cyber-panel:hover{border-color:rgba(88,166,255,.4);box-shadow:0 12px 48px rgba(88,166,255,.15);transform:translateY(-2px)}
        .nav-tabs{border-bottom:2px solid rgba(88,166,255,.15);gap:8px}
        .nav-tabs .nav-link{color:var(--fg);border:none;border-radius:12px 12px 0 0;padding:14px 28px;font-weight:600;transition:all .3s;background:transparent;position:relative}
        .nav-tabs .nav-link::after{content:'';position:absolute;bottom:-2px;left:50%;width:0;height:3px;background:var(--blue);transition:all .3s;transform:translateX(-50%);border-radius:3px 3px 0 0;box-shadow:0 0 10px rgba(88,166,255,.5)}
        .nav-tabs .nav-link.active{background:linear-gradient(135deg,rgba(88,166,255,.15),rgba(163,113,247,.15));color:var(--blue);font-weight:700}
        .nav-tabs .nav-link.active::after{width:60%}
        .form-control,.form-select{background:rgba(13,17,23,.9);border:1px solid rgba(88,166,255,.25);color:var(--fg);border-radius:12px;transition:all .3s}
        .form-control:focus,.form-select:focus{background:rgba(13,17,23,.95);border-color:var(--blue);box-shadow:0 0 0 4px rgba(88,166,255,.15);color:white;transform:scale(1.01)}
        .btn-primary{background:var(--grad);border:none;border-radius:12px;font-weight:700;padding:14px 28px;transition:all .3s;box-shadow:0 4px 20px rgba(102,126,234,.4)}
        .btn-primary:hover{transform:translateY(-3px);box-shadow:0 8px 30px rgba(102,126,234,.5)}
        .risk-badge{padding:8px 20px;border-radius:30px;font-weight:700;font-size:.9rem;text-transform:uppercase;display:inline-flex;align-items:center;gap:8px}
        .risk-high{background:linear-gradient(135deg,rgba(248,81,73,.2),rgba(248,81,73,.1));border:2px solid rgba(248,81,73,.5);color:var(--red);box-shadow:0 0 20px rgba(248,81,73,.3);animation:pulse-red 2s infinite}
        .risk-medium{background:linear-gradient(135deg,rgba(210,153,34,.2),rgba(210,153,34,.1));border:2px solid rgba(210,153,34,.5);color:var(--orange);box-shadow:0 0 20px rgba(210,153,34,.3)}
        .risk-low{background:linear-gradient(135deg,rgba(63,185,80,.2),rgba(63,185,80,.1));border:2px solid rgba(63,185,80,.5);color:var(--green);box-shadow:0 0 20px rgba(63,185,80,.3)}
        @keyframes pulse-red{0%,100%{box-shadow:0 0 20px rgba(248,81,73,.3)}50%{box-shadow:0 0 40px rgba(248,81,73,.5)}}
        .stat-card{background:linear-gradient(135deg,rgba(88,166,255,.08),rgba(163,113,247,.08));border:1px solid rgba(88,166,255,.2);border-radius:16px;padding:24px;transition:all .4s}
        .stat-card:hover{transform:translateY(-8px) scale(1.02);box-shadow:0 16px 40px rgba(88,166,255,.2);border-color:rgba(88,166,255,.4)}
        .stat-value{font-size:2.5rem;font-weight:800;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .stat-label{color:rgba(201,209,217,.7);font-size:.85rem;font-weight:600;text-transform:uppercase;letter-spacing:1px}
        .status-dot{width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:10px;animation:status-pulse 2s infinite}
        .status-success{background:var(--green);box-shadow:0 0 15px rgba(63,185,80,.6)}
        .status-error{background:var(--red);box-shadow:0 0 15px rgba(248,81,73,.6)}
        @keyframes status-pulse{0%,100%{opacity:1}50%{opacity:.5}}
        .loading-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(13,17,23,.95);backdrop-filter:blur(10px);display:flex;flex-direction:column;justify-content:center;align-items:center;z-index:9999;opacity:0;visibility:hidden;transition:all .3s}
        .loading-overlay.active{opacity:1;visibility:visible}
        .loading-spinner{width:80px;height:80px;border:4px solid rgba(88,166,255,.2);border-top-color:var(--blue);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:24px}
        @keyframes spin{to{transform:rotate(360deg)}}
        .progress{height:8px;background:rgba(88,166,255,.1);border-radius:10px;width:300px}
        .progress-bar{background:var(--grad);transition:width .5s;box-shadow:0 0 10px rgba(88,166,255,.5)}
        pre{background:rgba(13,17,23,.95);border:1px solid rgba(88,166,255,.2);border-radius:12px;color:#8b949e;font-size:.85rem;padding:1.25rem;overflow-x:auto;position:relative}
        pre::before{content:'JSON';position:absolute;top:8px;right:12px;font-size:.7rem;color:rgba(88,166,255,.5);font-weight:600}
        code{font-family:'Fira Code',monospace}
        .toast-container{position:fixed;top:80px;right:20px;z-index:9998}
        .toast{background:var(--glass);backdrop-filter:blur(20px);border:1px solid rgba(88,166,255,.3);border-radius:12px;color:var(--fg)}
        .history-item{padding:12px 16px;border-radius:10px;background:rgba(88,166,255,.05);border:1px solid rgba(88,166,255,.15);cursor:pointer;transition:all .3s;display:flex;justify-content:space-between;align-items:center}
        .history-item:hover{background:rgba(88,166,255,.15);border-color:rgba(88,166,255,.3);transform:translateX(5px)}
        .history-query{font-weight:600;color:var(--blue)}
        .history-time{font-size:.75rem;color:rgba(201,209,217,.5)}
        .source-checkbox{display:flex;align-items:center;padding:10px 12px;border-radius:8px;background:rgba(88,166,255,.05);border:1px solid rgba(88,166,255,.15);margin-bottom:8px;cursor:pointer;transition:all .3s}
        .source-checkbox:hover{background:rgba(88,166,255,.15);border-color:rgba(88,166,255,.3)}
        .source-checkbox input{margin-right:10px;accent-color:var(--blue)}
        .empty-state{padding:60px 20px;text-align:center}
        .empty-icon{font-size:5rem;margin-bottom:24px;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:float-icon 3s ease-in-out infinite}
        @keyframes float-icon{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
        .table thead th{background:rgba(88,166,255,.1);border-bottom:2px solid rgba(88,166,255,.3);color:var(--blue);font-weight:700;text-transform:uppercase;font-size:.8rem;letter-spacing:.5px}
        .table tbody tr{border-bottom:1px solid rgba(88,166,255,.1);transition:all .3s}
        .table tbody tr:hover{background:rgba(88,166,255,.08)}
        ::-webkit-scrollbar{width:10px;height:10px}
        ::-webkit-scrollbar-track{background:rgba(13,17,23,.5);border-radius:10px}
        ::-webkit-scrollbar-thumb{background:linear-gradient(135deg,rgba(88,166,255,.3),rgba(163,113,247,.3));border-radius:10px;border:2px solid rgba(13,17,23,.5)}
        .fade-in{animation:fadeIn .6s ease}
        @keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        .slide-up{animation:slideUp .6s ease}
        @keyframes slideUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
        @media(max-width:992px){.stat-value{font-size:2rem}}
        @media(max-width:768px){.navbar-brand{font-size:1.2rem}.stat-value{font-size:1.5rem}}
    </style>
</head>
<body>
<div class="bg-particles" id="particles"></div>
<div class="loading-overlay" id="loadingOverlay">
<div class="loading-spinner"></div>
<div class="text-info fw-bold mb-2">Searching OSINT Sources...</div>
<div class="progress"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:0%" id="progressBar"></div></div>
</div>
<div class="toast-container" id="toastContainer"></div>
<nav class="navbar navbar-dark sticky-top">
<div class="container-fluid d-flex justify-content-between align-items-center">
<span class="navbar-brand"><i class="bi bi-shield-lock-fill text-info me-2"></i>OSINT Search v4</span>
<div class="d-flex gap-2">
<button class="btn btn-outline-info btn-sm" onclick="clearHistory()"><i class="bi bi-trash"></i></button>
<div class="dropdown">
<button class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown"><i class="bi bi-gear"></i></button>
<ul class="dropdown-menu dropdown-menu-dark">
<li><a class="dropdown-item" href="#" onclick="exportHistory()">Export History</a></li>
<li><a class="dropdown-item" href="#" onclick="showShortcuts()">Shortcuts</a></li>
</ul>
</div>
</div>
</div>
</nav>
<div class="container-fluid py-4">
<div class="row">
<div class="col-lg-3">
<div class="cyber-panel p-4 mb-4 slide-up">
<h5 class="mb-4"><i class="bi bi-search text-info me-2"></i>New Search</h5>
<form id="searchForm" method="post" action="/">
<div class="mb-3">
<label class="form-label fw-semibold">Query</label>
<div class="input-group">
<span class="input-group-text bg-transparent border-secondary"><i class="bi bi-crosshair text-info"></i></span>
<input type="text" class="form-control" name="query" id="queryInput" value="{{ query or '' }}" required placeholder="email, username, domain..." autocomplete="off">
</div>
</div>
<div class="row g-2 mb-3">
<div class="col-6">
<label class="form-label fw-semibold">Type</label>
<select class="form-select" name="type" id="queryType" onchange="toggleCascade()">
<option value="email" {{ 'selected' if query_type == 'email' else '' }}>Email</option>
<option value="username" {{ 'selected' if query_type == 'username' else '' }}>Username</option>
<option value="domain" {{ 'selected' if query_type == 'domain' else '' }}>Domain</option>
<option value="ip" {{ 'selected' if query_type == 'ip' else '' }}>IP Address</option>
<option value="password" {{ 'selected' if query_type == 'password' else '' }}>Password</option>
</select>
</div>
<div class="col-6">
<label class="form-label fw-semibold">Sources</label>
<div id="sourceCheckboxes">
<label class="source-checkbox"><input type="checkbox" name="sources" value="osint_industries" checked><span class="small">OSINT Industries</span></label>
<label class="source-checkbox"><input type="checkbox" name="sources" value="dehashed" checked><span class="small">DeHashed</span></label>
<label class="source-checkbox"><input type="checkbox" name="sources" value="cypher_dynamics" checked><span class="small">Cypher Dynamics</span></label>
</div>
</div>
</div>
<div class="mb-3">
<div class="form-check form-switch p-3 rounded" style="background:rgba(88,166,255,.1);border:1px solid rgba(88,166,255,.2)">
<input class="form-check-input" type="checkbox" name="cascade" id="cascadeCheck" {{ 'checked' if cascade else '' }}>
<label class="form-check-label fw-semibold" for="cascadeCheck">
<i class="bi bi-diagram-3 text-info me-2"></i><span class="text-info">Cascade</span>
<span class="badge bg-info ms-2">Domain</span>
</label>
<div class="small text-muted mt-1">Extract & search emails from domain</div>
</div>
</div>
<details class="mb-3">
<summary class="text-muted small fw-semibold cursor-pointer"><i class="bi bi-sliders me-1"></i>Filters</summary>
<div class="row g-2 mt-3 p-3 rounded" style="background:rgba(13,17,23,.5)">
<div class="col-6"><input type="number" class="form-control form-control-sm" name="min_count" placeholder="Min count" value="{{ filters.min_count or '' }}"></div>
<div class="col-6"><input type="number" class="form-control form-control-sm" name="min_password_len" placeholder="Min pwd len" value="{{ filters.min_password_len or '' }}"></div>
<div class="col-12"><input type="text" class="form-control form-control-sm" name="regex" placeholder="Regex filter" value="{{ filters.regex or '' }}"></div>
<div class="col-12 mt-3 pt-3 border-top border-secondary">
<div class="d-flex justify-content-between align-items-center mb-2">
<div class="fw-semibold text-info"><i class="bi bi-key-fill me-1"></i>Password Extraction</div>
<div class="form-check form-switch">
<input class="form-check-input" type="checkbox" name="enable_password_extract" id="passwordExtractToggle" {{ 'checked' if filters.enable_password_extract else '' }}>
<label class="form-check-label small text-muted" for="passwordExtractToggle">Enable</label>
</div>
</div>
<div id="passwordExtractFields" style="{{ 'display:none' if not filters.enable_password_extract else '' }}">
<div class="col-12 mb-2">
<textarea class="form-control form-control-sm" name="target_emails" rows="2" placeholder="target emails (one per line)">{{ filters.target_emails or '' }}</textarea>
<div class="small text-muted">Emails to extract passwords for</div>
</div>
<div class="col-12">
<input type="text" class="form-control form-control-sm" name="target_url" placeholder="target URL/domain (z)" value="{{ filters.target_url or '' }}">
<div class="small text-muted">Only extract passwords from this URL/domain</div>
</div>
</div>
</div>
<div class="col-12 mt-3 pt-3 border-top border-secondary">
<div class="d-flex justify-content-between align-items-center mb-2">
<div class="fw-semibold text-warning"><i class="bi bi-link-45deg me-1"></i>URL Keyword Extraction</div>
<div class="form-check form-switch">
<input class="form-check-input" type="checkbox" name="enable_url_extract" id="urlExtractToggle" {{ 'checked' if filters.enable_url_extract else '' }}>
<label class="form-check-label small text-muted" for="urlExtractToggle">Enable</label>
</div>
</div>
<div id="urlExtractFields" style="{{ 'display:none' if not filters.enable_url_extract else '' }}">
<div class="col-12 mb-2">
<textarea class="form-control form-control-sm" name="extract_urls" rows="2" placeholder="URLs to extract from (one per line)">{{ filters.extract_urls or '' }}</textarea>
<div class="small text-muted">URLs to fetch and extract content from</div>
</div>
<div class="col-12">
<input type="text" class="form-control form-control-sm" name="extract_keyword" placeholder="keyword to search for (y)" value="{{ filters.extract_keyword or '' }}">
<div class="small text-muted">Extract lines containing this keyword</div>
</div>
</div>
</div>
</div>
</details>
<button type="submit" class="btn btn-primary w-100 py-3" id="searchBtn"><i class="bi bi-rocket-takeoff me-2"></i>Search <span class="badge bg-light text-dark ms-2">⌘↵</span></button>
</form>
</div>
<div class="cyber-panel p-4 slide-up" style="animation-delay:.1s">
<h6 class="mb-3 fw-semibold"><i class="bi bi-lightning-charge text-warning me-2"></i>Stats</h6>
<div class="row g-2">
<div class="col-6"><div class="stat-card text-center p-3"><div class="stat-value" id="totalSearches">0</div><div class="stat-label">Searches</div></div></div>
<div class="col-6"><div class="stat-card text-center p-3"><div class="stat-value" id="threatsFound">0</div><div class="stat-label">Threats</div></div></div>
</div>
</div>
<div class="cyber-panel p-4 slide-up" style="animation-delay:.2s">
<div class="d-flex justify-content-between align-items-center mb-3">
<h6 class="mb-0 fw-semibold"><i class="bi bi-clock-history text-info me-2"></i>History</h6>
<button class="btn btn-sm btn-outline-secondary" onclick="clearHistory()"><i class="bi bi-x-lg"></i></button>
</div>
<div id="historyList" class="d-flex flex-column gap-2"><div class="text-center text-muted small py-3">No recent searches</div></div>
</div>
<div class="cyber-panel p-3 small text-muted mt-4">
<strong class="text-info"><i class="bi bi-lightbulb me-1"></i>Tips:</strong><br>• Set API keys in .env<br>• Cascade only for domains<br>• ⌘+Enter to quick search<br>• Data stays local
</div>
</div>
<div class="col-lg-9">
{% if results %}
<div class="cyber-panel p-4 mb-4 fade-in">
<div class="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-3">
<div>
<h4 class="mb-1">Results: <span class="text-info">{{ results.query }}</span></h4>
<div class="d-flex align-items-center gap-3 text-muted small">
<span><i class="bi bi-clock me-1"></i>{{ results.execution_time_seconds }}s</span>
{% if results.cascade_search %}<span class="badge bg-info"><i class="bi bi-diagram-3 me-1"></i>Cascade</span>{% endif %}
</div>
</div>
<div class="d-flex gap-2">
<button class="btn btn-outline-info btn-sm" onclick="downloadJSON()"><i class="bi bi-filetype-json"></i></button>
<button class="btn btn-outline-success btn-sm" onclick="downloadMarkdown()"><i class="bi bi-file-earmark-text"></i></button>
<button class="btn btn-outline-secondary btn-sm" onclick="copyJSON()"><i class="bi bi-clipboard"></i></button>
</div>
</div>
<div class="mb-4">
{% set risk = results.summary.risk_score if results.summary else 'UNKNOWN' %}
{% if risk == 'HIGH' %}<span class="risk-badge risk-high"><i class="bi bi-exclamation-triangle-fill"></i>HIGH RISK</span>
{% elif risk == 'MEDIUM' %}<span class="risk-badge risk-medium"><i class="bi bi-exclamation-circle-fill"></i>MEDIUM RISK</span>
{% elif risk == 'LOW' %}<span class="risk-badge risk-low"><i class="bi bi-check-circle-fill"></i>LOW RISK</span>
{% else %}<span class="risk-badge" style="background:rgba(108,117,125,.2);border-color:rgba(108,117,125,.5);color:#6c757d"><i class="bi bi-question-circle-fill"></i>UNKNOWN</span>{% endif %}
</div>
<ul class="nav nav-tabs mb-4" id="resultTabs">
<li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#summary"><i class="bi bi-clipboard-data me-1"></i>Summary</button></li>
<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#sources"><i class="bi bi-hdd-stack me-1"></i>Sources</button></li>
{% if results.cascade_search %}<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#emails"><i class="bi bi-envelope me-1"></i>Emails ({{ results.emails_searched }})</button></li>{% endif %}
{% if results.password_extraction %}<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#passwords"><i class="bi bi-key-fill me-1"></i>Passwords ({{ results.password_extraction.total_found }})</button></li>{% endif %}
{% if results.url_extraction %}<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#url_extract"><i class="bi bi-link-45deg me-1"></i>URL Extract ({{ results.url_extraction.total_lines_found }})</button></li>{% endif %}
<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#raw"><i class="bi bi-code-square me-1"></i>Raw</button></li>
</ul>
<div class="tab-content">
<div class="tab-pane fade show active" id="summary">
<div class="row g-3 mb-4">
<div class="col-md-4"><div class="stat-card text-center"><div class="stat-value">{{ results.summary.sources_searched|length }}</div><div class="stat-label">Sources</div></div></div>
<div class="col-md-4"><div class="stat-card text-center"><div class="stat-value">{{ results.summary.total_sources_with_results }}</div><div class="stat-label">With Data</div></div></div>
<div class="col-md-4"><div class="stat-card text-center"><div class="stat-value">{{ results.execution_time_seconds }}s</div><div class="stat-label">Time</div></div></div>
</div>
{% if results.summary.key_findings %}
<h6 class="fw-semibold mb-3"><i class="bi bi-key-fill text-warning me-2"></i>Findings</h6>
<ul class="list-group list-group-flush mb-4">
{% for finding in results.summary.key_findings %}
<li class="list-group-item bg-transparent border-secondary text-light"><i class="bi bi-check-circle-fill text-success me-3 fs-5"></i>{{ finding }}</li>
{% endfor %}
</ul>
{% endif %}
{% if results.summary.recommendations %}
<h6 class="fw-semibold mb-3"><i class="bi bi-lightbulb-fill text-info me-2"></i>Recommendations</h6>
<ol class="list-group list-group-numbered list-group-flush">
{% for rec in results.summary.recommendations %}
<li class="list-group-item bg-transparent border-secondary text-light">{{ rec }}</li>
{% endfor %}
</ol>
{% endif %}
{% if results.cascade_search %}
<h6 class="fw-semibold mb-3 mt-4"><i class="bi bi-diagram-3 text-info me-2"></i>Cascade</h6>
<div class="row g-3">
<div class="col-md-3"><div class="stat-card text-center p-3"><div class="stat-value">{{ results.emails_found }}</div><div class="stat-label">Emails</div></div></div>
<div class="col-md-3"><div class="stat-card text-center p-3"><div class="stat-value">{{ results.emails_searched }}</div><div class="stat-label">Searched</div></div></div>
<div class="col-md-3"><div class="stat-card text-center p-3"><div class="stat-value text-success">{{ results.summary.email_searches_successful }}</div><div class="stat-label">Success</div></div></div>
<div class="col-md-3"><div class="stat-card text-center p-3"><div class="stat-value text-danger">{{ results.summary.email_searches_failed }}</div><div class="stat-label">Failed</div></div></div>
</div>
<div class="row g-3 mt-2">
<div class="col-md-4"><div class="stat-card text-center p-3"><div class="stat-value risk-high">{{ results.summary.total_risk_high }}</div><div class="stat-label">High</div></div></div>
<div class="col-md-4"><div class="stat-card text-center p-3"><div class="stat-value risk-medium">{{ results.summary.total_risk_medium }}</div><div class="stat-label">Medium</div></div></div>
<div class="col-md-4"><div class="stat-card text-center p-3"><div class="stat-value risk-low">{{ results.summary.total_risk_low }}</div><div class="stat-label">Low</div></div></div>
</div>
{% endif %}
</div>
<div class="tab-pane fade" id="sources">
{% for source,data in results.results.items() %}
<div class="cyber-panel p-3 mb-3">
<div class="d-flex justify-content-between align-items-center mb-3">
<h6 class="fw-bold mb-0 text-uppercase text-info"><i class="bi bi-database me-2"></i>{{ source.replace('_',' ') }}</h6>
{% if data.status == 'success' %}<span class="badge bg-success"><span class="status-dot status-success"></span>Success</span>
{% else %}<span class="badge bg-danger"><span class="status-dot status-error"></span>Failed</span>{% endif %}
</div>
{% if data.error %}<div class="alert alert-danger py-2"><i class="bi bi-exclamation-triangle me-2"></i>{{ data.error }}</div>{% endif %}
{% if data.results %}<pre class="mb-0"><code>{{ data.results|tojson(indent=2) }}</code></pre>{% endif %}
</div>
{% endfor %}
</div>
{% if results.cascade_search %}
<div class="tab-pane fade" id="emails">
<div class="table-responsive">
<table class="table table-dark table-hover">
<thead><tr><th>Email</th><th>Risk</th><th>Sources</th><th>Status</th></tr></thead>
<tbody>
{% for email,er in results.email_results.items() %}
<tr>
<td><code>{{ email }}</code></td>
<td>
{% set erisk = er.summary.risk_score if er.summary else 'UNKNOWN' %}
{% if erisk == 'HIGH' %}<span class="badge bg-danger">HIGH</span>
{% elif erisk == 'MEDIUM' %}<span class="badge bg-warning text-dark">MEDIUM</span>
{% elif erisk == 'LOW' %}<span class="badge bg-success">LOW</span>
{% else %}<span class="badge bg-secondary">UNKNOWN</span>{% endif %}
</td>
<td>{{ er.summary.total_sources_with_results if er.summary else 0 }}</td>
<td>{% if er.status == 'success' or not er.status %}<span class="status-dot status-success"></span>OK{% else %}<span class="status-dot status-error"></span>Error{% endif %}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% endif %}
{% if results.password_extraction %}
<div class="tab-pane fade" id="passwords">
<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>Extracted passwords for {{ results.password_extraction.target_emails|length }} emails from URL: <strong>{{ results.password_extraction.target_url }}</strong></div>
{% if results.password_extraction.passwords %}
<div class="table-responsive">
<table class="table table-dark table-hover">
<thead><tr><th>Email</th><th>Password</th><th>URL</th><th>Source</th></tr></thead>
<tbody>
{% for pwd in results.password_extraction.passwords %}
<tr>
<td><code>{{ pwd.email }}</code></td>
<td><code class="text-warning">{{ pwd.password }}</code></td>
<td>{{ pwd.url }}</td>
<td><span class="badge bg-secondary">{{ pwd.source }}</span></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% else %}
<div class="text-center py-5 text-muted">
<i class="bi bi-search fs-1 mb-3"></i>
<p>No passwords found matching the criteria</p>
</div>
{% endif %}
</div>
{% endif %}
{% if results.url_extraction %}
<div class="tab-pane fade" id="url_extract">
<div class="alert alert-warning"><i class="bi bi-link-45deg me-2"></i>Extracted lines containing "<strong>{{ results.url_extraction.keyword }}</strong>" from {{ results.url_extraction.total_urls_processed }} URLs</div>
{% if results.url_extraction.errors %}
<div class="alert alert-danger">
<strong>Errors ({{ results.url_extraction.total_errors }}):</strong>
<ul class="mb-0 mt-2">
{% for error in results.url_extraction.errors %}
<li>{{ error.url }}: {{ error.error }}</li>
{% endfor %}
</ul>
</div>
{% endif %}
{% if results.url_extraction.extracted_lines %}
<div class="table-responsive">
<table class="table table-dark table-hover">
<thead><tr><th>Line #</th><th>Content</th><th>Source URL</th></tr></thead>
<tbody>
{% for line in results.url_extraction.extracted_lines %}
<tr>
<td><span class="badge bg-secondary">{{ line.line_number }}</span></td>
<td><code class="text-info">{{ line.content }}</code></td>
<td><small class="text-muted">{{ line.url }}</small></td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% else %}
<div class="text-center py-5 text-muted">
<i class="bi bi-search fs-1 mb-3"></i>
<p>No lines found containing the keyword</p>
</div>
{% endif %}
</div>
{% endif %}
<div class="tab-pane fade" id="raw"><pre><code id="rawJson">{{ results|tojson(indent=2) }}</code></pre></div>
</div>
</div>
{% else %}
<div class="cyber-panel p-5 fade-in">
<div class="empty-state">
<div class="empty-icon"><i class="bi bi-shield-lock"></i></div>
<h3 class="mb-3 fw-bold">Ready for OSINT Search</h3>
<p class="text-muted mb-4">Enter a query to begin cross-platform intelligence gathering.</p>
<div class="row justify-content-center g-4">
<div class="col-md-4"><div class="cyber-panel p-4 text-center"><i class="bi bi-envelope text-info fs-2 mb-3"></i><div class="fw-semibold">Email</div><div class="small text-muted">user@example.com</div></div></div>
<div class="col-md-4"><div class="cyber-panel p-4 text-center"><i class="bi bi-person text-info fs-2 mb-3"></i><div class="fw-semibold">Username</div><div class="small text-muted">john_doe</div></div></div>
<div class="col-md-4"><div class="cyber-panel p-4 text-center"><i class="bi bi-globe text-info fs-2 mb-3"></i><div class="fw-semibold">Domain</div><div class="small text-muted">example.com</div></div></div>
</div>
</div>
</div>
{% endif %}
{% if error %}<div class="alert alert-danger mt-4"><i class="bi bi-exclamation-triangle-fill me-2"></i>{{ error }}</div>{% endif %}
</div>
</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
(function(){const p=document.getElementById('particles');for(let i=0;i<15;i++){const d=document.createElement('div');d.className='particle';d.style.left=Math.random()*100+'%';d.style.animationDelay=Math.random()*15+'s';p.appendChild(d)}})();
function updateStats(){const t=parseInt(localStorage.getItem('osint_total')||'0'),h=parseInt(localStorage.getItem('osint_threats')||'0');document.getElementById('totalSearches').textContent=t;document.getElementById('threatsFound').textContent=h}
updateStats();
{% if results %}
(function(){let t=parseInt(localStorage.getItem('osint_total')||'0')+1;localStorage.setItem('osint_total',t);const r='{{ results.summary.risk_score if results.summary else "UNKNOWN" }}';if(r==='HIGH'||r==='MEDIUM'){let h=parseInt(localStorage.getItem('osint_threats')||'0')+1;localStorage.setItem('osint_threats',h)}updateStats();saveHistory('{{ results.query }}','{{ query_type }}',r)})();
{% endif %}
function saveHistory(q,t,r){let h=JSON.parse(localStorage.getItem('osint_hist')||'[]');h.unshift({query:q,type:t,risk:r,time:new Date().toISOString()});h=h.slice(0,10);localStorage.setItem('osint_hist',JSON.stringify(h));renderHist()}
function renderHist(){const h=JSON.parse(localStorage.getItem('osint_hist')||'[]');const c=document.getElementById('historyList');if(!h.length){c.innerHTML='<div class="text-center text-muted small py-3">No recent searches</div>';return}c.innerHTML=h.map(i=>{const tm=new Date(i.time).toLocaleTimeString();const rc=i.risk==='HIGH'?'danger':i.risk==='MEDIUM'?'warning':'success';return`<div class="history-item" onclick="loadHist('${i.query}','${i.type}')"><div><div class="history-query">${i.query}</div><div class="history-time">${tm} • ${i.type}</div></div><span class="badge bg-${rc}">${i.risk}</span></div>`}).join('')}
renderHist();
function loadHist(q,t){document.getElementById('queryInput').value=q;document.getElementById('queryType').value=t;document.getElementById('searchForm').submit()}
function clearHistory(){localStorage.removeItem('osint_hist');renderHist();toast('History cleared')}
function exportHistory(){const h=localStorage.getItem('osint_hist');const b=new Blob([h],{type:'application/json'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='osint_history.json';a.click();URL.revokeObjectURL(u);toast('History exported')}
function toggleCascade(){const t=document.getElementById('queryType').value;const c=document.getElementById('cascadeCheck');if(t==='domain'){c.parentElement.style.opacity='1';c.disabled=false}else{c.checked=false;c.parentElement.style.opacity='.5';c.disabled=true}}
function toggleFilterFields(){const p=document.getElementById('passwordExtractToggle');const u=document.getElementById('urlExtractToggle');document.getElementById('passwordExtractFields').style.display=p.checked?'block':'none';document.getElementById('urlExtractFields').style.display=u.checked?'block':'none'}
toggleCascade();
document.getElementById('passwordExtractToggle').addEventListener('change',toggleFilterFields);
document.getElementById('urlExtractToggle').addEventListener('change',toggleFilterFields);
document.getElementById('searchForm').addEventListener('submit',function(e){document.getElementById('loadingOverlay').classList.add('active');let p=0;const i=setInterval(()=>{p+=Math.random()*30;if(p>90)p=90;document.getElementById('progressBar').style.width=p+'%'},500);this.dataset.interval=i});
function toast(m){const c=document.getElementById('toastContainer');const d=document.createElement('div');d.className='toast show';d.innerHTML=`<div class="toast-body d-flex align-items-center"><i class="bi bi-info-circle text-info me-2"></i>${m}</div>`;c.appendChild(d);setTimeout(()=>d.remove(),3000)}
function copyJSON(){const r=document.getElementById('rawJson').textContent;navigator.clipboard.writeText(r).then(()=>toast('Copied!'))}
function downloadJSON(){const r=document.getElementById('rawJson').textContent;const b=new Blob([r],{type:'application/json'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='osint_results.json';a.click();URL.revokeObjectURL(u);toast('Downloaded')}
function downloadMarkdown(){const r=document.getElementById('rawJson').textContent;fetch('/api/download/markdown',{method:'POST',headers:{'Content-Type':'application/json'},body:r}).then(r=>r.blob()).then(b=>{const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='osint_report.md';a.click();URL.revokeObjectURL(u);toast('Downloaded')}).catch(()=>toast('Failed'))}
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='Enter'){e.preventDefault();document.getElementById('searchForm').submit()}});
function showShortcuts(){toast('⌘+Enter: Quick Search')}
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    query = ""
    query_type = "email"
    cascade = False
    filters = {}
    results = None
    error = None
    use_cache = request.args.get("cache", "true").lower() == "true"

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        query_type = request.form.get("type", "email")
        cascade = request.form.get("cascade") == "on"
        sources = request.form.getlist("sources") or ["osint_industries", "dehashed", "cypher_dynamics"]

        filters = {}
        if request.form.get("min_count"):
            filters["min_count"] = int(request.form.get("min_count"))
        if request.form.get("min_password_len"):
            filters["min_password_len"] = int(request.form.get("min_password_len"))
        if request.form.get("regex"):
            filters["regex"] = request.form.get("regex")
        
        # Targeted password extraction filters
        enable_password_extract = request.form.get("enable_password_extract") == "on"
        target_emails = request.form.get("target_emails", "").strip()
        target_url = request.form.get("target_url", "").strip()
        
        filters["enable_password_extract"] = enable_password_extract
        if enable_password_extract:
            if target_emails:
                filters["target_emails"] = [e.strip() for e in target_emails.split('\n') if e.strip()]
            if target_url:
                filters["target_url"] = target_url
        
        # URL keyword extraction filters
        enable_url_extract = request.form.get("enable_url_extract") == "on"
        extract_urls = request.form.get("extract_urls", "").strip()
        extract_keyword = request.form.get("extract_keyword", "").strip()
        
        filters["enable_url_extract"] = enable_url_extract
        if enable_url_extract:
            if extract_urls:
                filters["extract_urls"] = [u.strip() for u in extract_urls.split('\n') if u.strip()]
            if extract_keyword:
                filters["extract_keyword"] = extract_keyword

        if not query:
            error = "Please enter a search query."
        else:
            try:
                # Check cache first
                cache_key = get_cache_key(query, query_type, sources, filters)
                cached = get_cached_result(cache_key) if use_cache else None
                
                if cached and not cascade:
                    results = cached
                    results["from_cache"] = True
                else:
                    if query_type == "domain" and cascade:
                        results = searcher.cascade_domain_to_emails(
                            domain=query,
                            filters=filters,
                            sources=sources
                        )
                    else:
                        results = searcher.run_search(
                            query=query,
                            query_type=query_type,
                            filters=filters,
                            sources=sources,
                            enable_rich_output=False
                        )
                    # Cache the result
                    if not cascade:
                        set_cached_result(cache_key, results)
                
                # Apply targeted password extraction if enabled and filters are provided
                if enable_password_extract and target_emails and target_url and results:
                    results["password_extraction"] = extract_passwords_by_url(
                        results, 
                        filters.get("target_emails", []), 
                        target_url
                    )
                
                # Apply URL keyword extraction if enabled and filters are provided
                if enable_url_extract and extract_urls and extract_keyword:
                    results["url_extraction"] = extract_lines_from_urls(
                        filters.get("extract_urls", []), 
                        extract_keyword
                    )
            except Exception as e:
                error = str(e)

    return render_template_string(
        HTML_TEMPLATE,
        query=query,
        query_type=query_type,
        cascade=cascade,
        filters=filters,
        results=results,
        error=error
    )


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True) or {}
    query = data.get("query", "").strip()
    query_type = data.get("type", "email")
    sources = data.get("sources", ["osint_industries", "dehashed", "cypher_dynamics"])
    filters = data.get("filters", {})
    cascade = data.get("cascade", False)
    use_cache = data.get("cache", True)

    if not query:
        return jsonify({"error": "Missing query"}), 400

    try:
        cache_key = get_cache_key(query, query_type, sources, filters)
        if use_cache and not cascade:
            cached = get_cached_result(cache_key)
            if cached:
                cached["from_cache"] = True
                return jsonify(cached)

        if query_type == "domain" and cascade:
            results = searcher.cascade_domain_to_emails(
                domain=query,
                filters=filters,
                sources=sources
            )
        else:
            results = searcher.run_search(
                query=query,
                query_type=query_type,
                filters=filters,
                sources=sources,
                enable_rich_output=False
            )
        
        if not cascade:
            set_cached_result(cache_key, results)
        
        # Apply targeted password extraction if enabled and filters are provided
        enable_password_extract = filters.get("enable_password_extract", False)
        target_emails = filters.get("target_emails", [])
        target_url = filters.get("target_url", "")
        if enable_password_extract and target_emails and target_url:
            results["password_extraction"] = extract_passwords_by_url(
                results, 
                target_emails, 
                target_url
            )
        
        # Apply URL keyword extraction if enabled and filters are provided
        enable_url_extract = filters.get("enable_url_extract", False)
        extract_urls = filters.get("extract_urls", [])
        extract_keyword = filters.get("extract_keyword", "")
        if enable_url_extract and extract_urls and extract_keyword:
            results["url_extraction"] = extract_lines_from_urls(
                extract_urls, 
                extract_keyword
            )
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def api_health():
    keys = searcher.api_keys
    return jsonify({
        "status": "ok",
        "version": "4.0",
        "cache_size": len(search_cache),
        "sources": {
            "osint_industries": bool(keys.get("osint_industries")),
            "dehashed": bool(keys.get("dehashed")),
            "cypher_dynamics": bool(keys.get("cypher_dynamics")),
        }
    })


@app.route("/api/cache/clear", methods=["POST"])
def api_clear_cache():
    search_cache.clear()
    return jsonify({"status": "cleared", "cache_size": 0})


@app.route("/api/cache/stats", methods=["GET"])
def api_cache_stats():
    return jsonify({
        "size": len(search_cache),
        "max_size": 100,
        "ttl_seconds": CACHE_TTL
    })


@app.route("/api/keys", methods=["GET"])
def api_get_keys():
    """Get current API keys (masked)"""
    return jsonify({
        "osint_industries": bool(api_keys_storage.get("osint_industries")),
        "dehashed": bool(api_keys_storage.get("dehashed")),
        "cypher_dynamics": bool(api_keys_storage.get("cypher_dynamics"))
    })


@app.route("/api/keys", methods=["POST"])
def api_set_keys():
    """Set API keys"""
    data = request.get_json(force=True) or {}
    
    if "osint_industries" in data:
        api_keys_storage["osint_industries"] = data["osint_industries"]
    if "dehashed" in data:
        api_keys_storage["dehashed"] = data["dehashed"]
    if "cypher_dynamics" in data:
        api_keys_storage["cypher_dynamics"] = data["cypher_dynamics"]
    
    # Update searcher with new keys
    searcher.api_keys = {
        "osint_industries": api_keys_storage.get("osint_industries"),
        "dehashed": api_keys_storage.get("dehashed"),
        "cypher_dynamics": api_keys_storage.get("cypher_dynamics")
    }
    
    return jsonify({
        "status": "success",
        "keys": {
            "osint_industries": bool(api_keys_storage.get("osint_industries")),
            "dehashed": bool(api_keys_storage.get("dehashed")),
            "cypher_dynamics": bool(api_keys_storage.get("cypher_dynamics"))
        }
    })


@app.route("/api/download/json", methods=["POST"])
def api_download_json():
    data = request.get_json(force=True) or {}
    if not data:
        return jsonify({"error": "No data provided"}), 400
    blob = BytesIO(json.dumps(data, indent=2).encode("utf-8"))
    return send_file(
        blob,
        mimetype="application/json",
        as_attachment=True,
        download_name="osint_results.json"
    )


@app.route("/api/download/markdown", methods=["POST"])
def api_download_markdown():
    data = request.get_json(force=True) or {}
    if not data:
        return jsonify({"error": "No data provided"}), 400

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        tmp_path = f.name

    try:
        searcher.generate_markdown_report(data, tmp_path)
        with open(tmp_path, "r") as f:
            content = f.read()
        blob = BytesIO(content.encode("utf-8"))
        return send_file(
            blob,
            mimetype="text/markdown",
            as_attachment=True,
            download_name="osint_report.md"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)