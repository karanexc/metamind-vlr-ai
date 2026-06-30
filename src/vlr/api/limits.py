"""Rate limiter — defined separately so both main.py and route files
can import it without creating a circular dependency."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])
