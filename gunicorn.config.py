bind="0.0.0.0"

def pre_request(worker, req):
    # pretend the request came over https
    req.scheme = 'https'