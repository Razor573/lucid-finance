import time
from functools import wraps
from collections import defaultdict
from flask import request, abort, jsonify, current_app

# in-memory store: { endpoint: { ip: [timestamps] } }
# fine for single-process deployments since the GIL prevents dict write races
_rate_limit_records = defaultdict(lambda: defaultdict(list))

def rate_limit(limit=5, period=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_app.config.get('TESTING') and not current_app.config.get('TEST_RATE_LIMITING'):
                return f(*args, **kwargs)
                
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
            
            endpoint = request.endpoint or 'global'
            now = time.time()
            
            timestamps = _rate_limit_records[endpoint][ip]
            _rate_limit_records[endpoint][ip] = [t for t in timestamps if now - t < period]
            
            if len(_rate_limit_records[endpoint][ip]) >= limit:
                if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                    resp = jsonify({'error': 'Too many requests. Please try again later.'})
                    resp.status_code = 429
                    return resp
                abort(429, description="Too many requests. Please try again later.")
                
            _rate_limit_records[endpoint][ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def reset_rate_limits():
    _rate_limit_records.clear()
