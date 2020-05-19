"""Create mosaicJSON from a stac query.

This is derived from
https://github.com/developmentseed/awspds-mosaic/blob/master/awspds_mosaic/landsat/stac.py

BSD 2-Clause License

Copyright (c) 2017, RemotePixel.ca
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import itertools
import json
import sys
from datetime import datetime
from typing import List

import requests
from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta


def search(
        bounds: List[float],
        min_cloud: float = 0,
        max_cloud: float = 100,
        min_date='2013-01-01',
        max_date=datetime.today(),
        period: str = None,
        period_qty: int = 1,
        stac_collection_limit: int = 500,
        stac_url: str = "https://sat-api.developmentseed.org"):
    """Search STAC API given parameters

    Args:
        - bounds: minx, miny, maxx, maxy
        - min_cloud: Minimum cloud percentage
        - max_cloud: Maximum cloud percentage
        - min_date: (str or datetime.datetime) Minimum date
        - max_date: (str or datetime.datetime) Maximum date, inclusive
        - period: Time period. If provided, overwrites `max-date` with the given period after `min-date`. One of 'day', 'week', 'month', 'year'
        - period_qty: Number of periods to apply after `min-date`. Only applies if `period` is provided.
        - stac_collection_limit: Limits the number of items per page returned by sat-api.
        - stac_url: Endpoint to use. Defaults to Development Seed's Sat API
    """

    period_choices = ['day', 'week', 'month', 'year']
    if period and period not in period_choices:
        raise ValueError(f'period must be one of {period_choices}')

    if not isinstance(min_date, datetime):
        min_date = date_parse(min_date)
    if not isinstance(max_date, datetime):
        max_date = date_parse(max_date)

    if period:
        if period == 'day':
            delta = relativedelta(days=period_qty)
        elif period == 'week':
            delta = relativedelta(weeks=period_qty)
        elif period == 'month':
            delta = relativedelta(months=period_qty)
        elif period == 'year':
            delta = relativedelta(years=period_qty)

        max_date = min_date + delta

    start = min_date.strftime("%Y-%m-%dT00:00:00Z")
    end = max_date.strftime("%Y-%m-%dT23:59:59Z")

    query = {
        "bbox": bounds,
        "time": f"{start}/{end}",
        "query": {
            "eo:sun_elevation": {
                "gt": 0
            },
            "landsat:tier": {
                "eq": "T1"
            },
            "collection": {
                "eq": "landsat-8-l1"
            },
            "eo:cloud_cover": {
                "gte": min_cloud,
                "lt": max_cloud
            },
            "eo:platform": {
                "eq": "landsat-8"
            },
        },
        "sort": [{
            "field": "eo:cloud_cover",
            "direction": "asc"
        }],
    }

    if stac_collection_limit:
        query['limit'] = stac_collection_limit

    return fetch_sat_api(query, stac_url=stac_url)


def fetch_sat_api(query, stac_url: str = "https://sat-api.developmentseed.org"):
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Accept": "application/geo+json",
    }

    url = f"{stac_url}/stac/search"
    data = requests.post(url, headers=headers, json=query).json()
    error = data.get("message", "")
    if error:
        raise Exception(f"SAT-API failed and returned: {error}")

    meta = data.get("meta", {})
    if not meta.get("found"):
        return []

    if meta['found'] >= 10000:
        raise ValueError(f'Found {meta["found"]} results; max is 10,000')

    print(json.dumps(meta), file=sys.stderr)

    features = data["features"]
    if data["links"]:
        curr_page = int(meta["page"])
        query["page"] = curr_page + 1
        query["limit"] = meta["limit"]

        features = list(itertools.chain(features, fetch_sat_api(query)))

    return features
