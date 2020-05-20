import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List


def index_data_path():
    """Find path to bundled pr_index.json.gz
    """
    pkg_path = 'data/pr_index.json.gz'
    lambda_root = os.getenv('LAMBDA_TASK_ROOT')
    if lambda_root:
        return f'{lambda_root}/landsat_cogeo_mosaic/{pkg_path}'

    try:
        # pkg_resources isn't necessarily available in all environments
        from pkg_resources import resource_filename
        return resource_filename('landsat_cogeo_mosaic', pkg_path)
    except (ImportError, ModuleNotFoundError):
        pass

    return str((Path(__file__) / pkg_path).resolve())


def get_hash(**kwargs) -> str:
    """Create hash from dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()


def _get_season(date, lat=0):
    if lat > 0:
        season_names = {1: "winter", 2: "spring", 3: "summer", 4: "autumn"}
    else:
        season_names = {4: "winter", 3: "spring", 2: "summer", 1: "autumn"}

    month = datetime.strptime(date[0:10], "%Y-%m-%d").month

    # from https://stackoverflow.com/questions/44124436/python-datetime-to-season
    idx = (month % 12 + 3) // 3

    return season_names[idx]


def filter_season(features, seasons):
    return list(
        filter(
            lambda x: _get_season(
                x["properties"]["datetime"], max(x["bbox"][1], x["bbox"][3])) in
            seasons,
            features,
        ))


def bounds_intersect(bounds1: List[float], bounds2: List[float]) -> bool:
    # https://stackoverflow.com/a/306332
    if ((bounds1[0] < bounds2[2]) and (bounds1[2] > bounds2[0])
            and (bounds1[3] > bounds2[1]) and (bounds1[1] < bounds2[3])):
        return True

    return False


list_depth = lambda L: isinstance(L, list) and max(map(list_depth, L)) + 1
