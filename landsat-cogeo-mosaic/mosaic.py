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
from typing import Any, Tuple

from stac import stac_to_mosaicJSON


def create_mosaic(
        body: str,
        minzoom: int = 7,
        maxzoom: int = 12,
        optimized_selection: bool = True,
        maximum_items_per_tile: int = 20,
        stac_collection_limit: int = 500,
        seasons: str = None,
        tile_format: str = "png",
        tile_scale: int = 1,
        **kwargs: Any):
    """Create mosaic"""
    body = json.loads(body)
    print(body)

    minzoom = int(minzoom) if isinstance(minzoom, str) else minzoom
    maxzoom = int(maxzoom) if isinstance(maxzoom, str) else maxzoom
    if isinstance(optimized_selection, str):
        optimized_selection = (
            False if optimized_selection in ["False", "false"] else True)

    if seasons:
        seasons = seasons.split(",")
    else:
        seasons = ["spring", "summer", "autumn", "winter"]

    body["query"].update({"eo:platform": {"eq": "landsat-8"}})

    mosaic_definition = stac_to_mosaicJSON(
        body,
        minzoom=minzoom,
        maxzoom=maxzoom,
        optimized_selection=optimized_selection,
        maximum_items_per_tile=maximum_items_per_tile,
        stac_collection_limit=stac_collection_limit,
        seasons=seasons,
    )

    return print(json.dumps(mosaic_definition))
