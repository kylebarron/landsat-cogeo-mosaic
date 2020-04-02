import hashlib
import json


def get_hash(**kwargs) -> str:
    """Create hash from dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()
