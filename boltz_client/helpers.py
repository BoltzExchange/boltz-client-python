import httpx
from loguru import logger

def req_wrap(funcname, *args, **kwargs):
    try:
        func = getattr(httpx, funcname)
    except AttributeError:
        logger.error('req_wrap, request failed. httpx function not found "%s"' % funcname)
    else:
        res = func(*args, timeout=30, **kwargs)
        res.raise_for_status()
        return res.json() if kwargs["headers"]["Content-Type"] == "application/json" else res.text
