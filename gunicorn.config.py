import os

bind="0.0.0.0"

def pre_request(worker, req):
    # pretend the request came over https
    if os.environ.get("GUNICORN_REWRITE_HTTPS") == "1":
        req.scheme = 'https'
    