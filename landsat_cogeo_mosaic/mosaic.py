"""Create mosaicJSON for landsat

This code is partially derived from
https://github.com/developmentseed/awspds-mosaic/blob/master/awspds_mosaic/landsat/handlers/mosaic.py

BSD 2-Clause License

Copyright (c) 2017, RemotePixel.ca
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

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

import json
import os
import urllib
from datetime import datetime
from typing import Any, List, Tuple

from .stac import stac_to_mosaicJSON


def create_mosaic(
        bounds: List[float],
        min_cloud: float,
        max_cloud: float,
        min_date: str = "2013-01-01",
        max_date: str = "2019-12-01",
        min_zoom: int = 7,
        max_zoom: int = 12,
        optimized_selection: bool = True,
        maximum_items_per_tile: int = 20,
        stac_collection_limit: int = None,
        seasons: List[str] = None):
    """Create mosaic"""
    if seasons is None:
        seasons = ["spring", "summer", "autumn", "winter"]

    start = datetime.strptime(min_date,
                              "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
    end = datetime.strptime(max_date, "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

    query = {
        "bbox": bounds,
        "time": f"{start}/{end}",
        "query": {
            "eo:sun_elevation": {
                "gt": 0},
            "landsat:tier": {
                "eq": "T1"},
            "collection": {
                "eq": "landsat-8-l1"},
            "eo:cloud_cover": {
                "gte": min_cloud,
                "lt": max_cloud},
            "eo:platform": {
                "eq": "landsat-8"}, },
        "sort": [{
            "field": "eo:cloud_cover",
            "direction": "asc"}], }

    mosaic_definition = stac_to_mosaicJSON(
        query,
        minzoom=min_zoom,
        maxzoom=max_zoom,
        optimized_selection=optimized_selection,
        maximum_items_per_tile=maximum_items_per_tile,
        stac_collection_limit=stac_collection_limit,
        seasons=seasons,
    )

    return mosaic_definition
