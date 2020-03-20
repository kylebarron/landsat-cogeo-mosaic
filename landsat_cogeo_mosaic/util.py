import base64
import hashlib
import json
from typing import Dict, Tuple


def get_hash(**kwargs) -> str:
    """Create hash from dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()
    ).hexdigest()

def bbox_to_geojson(bbox: Tuple) -> Dict:
    """Return bbox geojson feature."""
    return {
        "geometry": {
            "type":
                "Polygon",
            "coordinates": [[
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]], ]], },
        "properties": {},
        "type": "Feature", }
