"""Create mosaicJSON for landsat

This code is partially derived from
https://github.com/developmentseed/awspds-mosaic/blob/master/awspds_mosaic/landsat/handlers/mosaic.py

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

import json
import os
import sys
import urllib
from datetime import datetime
from typing import Any, Dict, List, Tuple

import mercantile
from shapely.geometry import box, shape
from supermercado import burntiles

from .util import bbox_to_geojson


def features_to_mosaicJSON(
        features: List,
        minzoom: int = 7,
        maxzoom: int = 12,
        optimized_selection: bool = True,
        maximum_items_per_tile: int = 20,
) -> Dict:
    """
    Create a mosaicJSON from a stac request.

    Attributes
    ----------
    features : list
        sat-api features.
    minzoom : int, optional, (default: 7)
        Mosaic Min Zoom.
    maxzoom : int, optional (default: 12)
        Mosaic Max Zoom.
    optimized_selection : bool, optional (default: true)
        Limit one Path-Row scene per quadkey.
    maximum_items_per_tile : int, optional (default: 20)
        Limit number of scene per quadkey. Use 0 to use all items.

    Returns
    -------
    out : dict
        MosaicJSON definition.

    """
    if optimized_selection:
        dataset = []
        prs = []
        for item in features:
            pr = item["properties"]["eo:column"] + "-" + item["properties"][
                "eo:row"]
            if pr not in prs:
                prs.append(pr)
                dataset.append(item)
    else:
        dataset = features

    if query.get("bbox"):
        bounds = query["bbox"]
    else:
        bounds = burntiles.find_extrema(dataset)

    for i in range(len(dataset)):
        dataset[i]["geometry"] = shape(dataset[i]["geometry"])

    tiles = burntiles.burn([bbox_to_geojson(bounds)], minzoom)
    tiles = list(set(["{2}-{0}-{1}".format(*tile.tolist()) for tile in tiles]))

    print(f"Number tiles: {len(tiles)}", file=sys.stderr)

    mosaic_definition = dict(
        mosaicjson="0.0.1",
        minzoom=minzoom,
        maxzoom=maxzoom,
        bounds=bounds,
        center=[(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2,
                minzoom],
        tiles={},
    )

    for tile in tiles:
        z, x, y = list(map(int, tile.split("-")))
        tile = mercantile.Tile(x=x, y=y, z=z)
        quadkey = mercantile.quadkey(*tile)
        geometry = box(*mercantile.bounds(tile))
        intersect_dataset = list(
            filter(lambda x: geometry.intersects(x["geometry"]), dataset))
        if len(intersect_dataset):
            # We limit the item per quadkey to 20
            if maximum_items_per_tile:
                intersect_dataset = intersect_dataset[0:maximum_items_per_tile]

            mosaic_definition["tiles"][quadkey] = [
                scene["properties"]["landsat:product_id"]
                for scene in intersect_dataset
            ]

    return mosaic_definition
