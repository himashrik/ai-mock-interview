from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# In-memory by default (fine for a single process). Set RATE_LIMIT_STORAGE_URI to a Redis URI
# (e.g. "redis://localhost:6379") in any deployment running more than one API worker/instance,
# so limits are enforced globally instead of separately per worker.
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.RATE_LIMIT_STORAGE_URI)
