from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-client-IP limiter with in-memory storage. Single-process (one uvicorn
# worker) is fine for this; a multi-worker deployment would point `storage_uri`
# at Redis so the counts are shared. Behind a reverse proxy, the proxy must set
# a trusted X-Forwarded-For and the app must be configured to honor it, or every
# request will appear to come from the proxy's IP.
limiter = Limiter(key_func=get_remote_address)
