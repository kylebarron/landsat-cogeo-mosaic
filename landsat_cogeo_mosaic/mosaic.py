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
import sys
from datetime import datetime
from typing import Dict, List

import mercantile
from rtree import index
from shapely.geometry import box, asShape


def features_to_mosaicJSON(
        features: List[Dict],
        quadkey_zoom: int = None,
        bounds: List[float] = None,
        minzoom: int = 7,
        maxzoom: int = 12,
        optimized_selection: bool = True,
        maximum_items_per_tile: int = 20,
) -> Dict:
    """
    Create a mosaicJSON from stac features.

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
    # Instantiate rtree
    idx = index.Index()

    # Insert features
    for i in range(len(features)):
        feature = features[i]
        idx.insert(i, asShape(feature['geometry']).bounds)

    # Find tiles at desired zoom
    bounds = bounds or idx.bounds
    quadkey_zoom = quadkey_zoom or minzoom
    tiles = mercantile.tiles(*bounds, quadkey_zoom)

    # Define mosaic
    mosaic_definition = {
        'mosaicjson': "0.0.2",
        'minzoom': minzoom,
        'maxzoom': maxzoom,
        'quadkey_zoom': quadkey_zoom,
        'bounds': bounds,
        'center': [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2,
                   minzoom],
        'tiles': {},
    }

    # Loop over tiles
    for tile in tiles:
        quadkey = mercantile.quadkey(tile)
        candidate_idx = list(idx.intersection(mercantile.bounds(tile)))

        if not candidate_idx:
            continue

        # Retrieve actual features
        candidates = [features[i] for i in candidate_idx]

        # Filter exact intersections
        tile_geom = box(*mercantile.bounds(tile))
        assets = [
            x for x in candidates
            if tile_geom.intersects(asShape(x['geometry']))
        ]

        if not assets:
            continue

        # Add to mosaic definition
        mosaic_definition["tiles"][quadkey] = [
            scene["properties"]["landsat:product_id"] for scene in assets
        ]

    return mosaic_definition
