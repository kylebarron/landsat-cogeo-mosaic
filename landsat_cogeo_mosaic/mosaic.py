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

import sys
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

import mercantile
from rio_tiler.io.landsat8 import landsat_parser
from rtree import index
from shapely.geometry import Polygon, asShape, box


def features_to_mosaicJSON(
        features: List[Dict],
        quadkey_zoom: int = None,
        bounds: List[float] = None,
        minzoom: int = 7,
        maxzoom: int = 12,
        optimized_selection: bool = True,
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
        Attempt to optimize assets in tile.

        This optimization implies _both_ that

        - assets will be ordered in the MosaicJSON in order of cover of the
          entire tile
        - the total number of assets is kept to a minimum

        Computing the absolute minimum of assets to cover the tile may not in
        general be possible in finite time, so this is a naive method that
        should work relatively well for this use case.

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

        # Optimize assets to be added
        if optimized_selection:
            assets = optimize_assets(tile, assets)

        # Add to mosaic definition
        if assets:
            mosaic_definition["tiles"][quadkey] = [
                scene["properties"]["landsat:product_id"] for scene in assets
            ]

    return mosaic_definition


def optimize_assets(tile, assets):
    """Try to find the minimal number of assets to cover tile

    This optimization implies _both_ that

    - assets will be ordered in the MosaicJSON in order of cover of the entire tile
    - the total number of assets is kept to a minimum

    Computing the absolute minimum of assets to cover the tile may not in
    general be possible in finite time, so this is a naive method that should
    work relatively well for this use case.
    """
    if not assets:
        return assets

    final_assets = []
    tile_geom = box(*mercantile.bounds(tile))
    assets = deepcopy(assets)

    while True:
        # Sort by cover of region of tile that is left
        assets = sort_assets_by_cover(tile_geom, assets)

        # Remove top asset and add to final_assets
        top_asset = assets.pop(0)
        final_assets.append(top_asset)

        # Recompute tile_geom, removing overlap with top_asset
        tile_geom = tile_geom.difference(asShape(top_asset['geometry']))

        # When total area is covered, stop
        if tile_geom.area == 0:
            break

        # If all assets are spent and the tile still not covered, raise
        # exception
        if len(assets) == 0:
            print(
                f'Warning: Not enough assets to cover {tile}', file=sys.stderr)
            break

    return final_assets


def sort_assets_by_cover(tile_geom: Polygon, assets: List[Dict]) -> List[Dict]:
    """Sort assets by cover percent of tile
    """
    # Add overlap percent to properties
    new_assets = []
    for asset in assets:
        asset['properties']['tile_overlap'] = pct_overlap(tile_geom, asset)
        new_assets.append(asset)

    # Sort by tile overlap
    return sorted(
        new_assets, key=lambda k: k['properties']['tile_overlap'], reverse=True)


def pct_overlap(tile_geom: Polygon, asset: Dict) -> float:
    asset_geom = asShape(asset['geometry'])
    return tile_geom.intersection(asset_geom).area / tile_geom.area


class StreamingParser:
    """Create Mosaic from stream of GeoJSON Features

    Instead of first laying out all features and then splitting them up into
    tiles, this works by first laying out all _tiles_ and then adding features
    one by one.
    """
    def __init__(
            self,
            quadkey_zoom: Optional[int] = None,
            bounds: Optional[List[float]] = None,
            minzoom: int = 7,
            maxzoom: int = 12,
            preference: str = 'newest',
            optimized_selection: bool = True):

        if optimized_selection and preference not in ['newest', 'oldest']:
            raise ValueError('Unsupported preference')

        self.quadkey_zoom = quadkey_zoom or minzoom
        self.bounds = bounds or [-180, -90, 180, 90]
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.preference = preference
        self.optimized_selection = optimized_selection

        # Find tiles at desired zoom
        tiles = list(mercantile.tiles(*bounds, quadkey_zoom))
        quadkeys = [mercantile.quadkey(tile) for tile in tiles]

        self.tiles: Dict[str, List[str]] = {k: [] for k in quadkeys}

    def add(self, feature: Dict):
        # Find overlapping quadkeys
        feature_geom = asShape(feature['geometry'])
        tiles = list(mercantile.tiles(*feature_geom.bounds, self.quadkey_zoom))

        # Keep tiles that intersect the feature geometry
        tiles = [
            tile for tile in tiles if asShape(
                mercantile.feature(tile)['geometry']).intersects(feature_geom)
        ]

        quadkeys = [mercantile.quadkey(tile) for tile in tiles]

        for quadkey in quadkeys:
            self.tiles[quadkey] = self._add_feature_to_quadkey(quadkey, feature)

    def _add_feature_to_quadkey(self, quadkey, feature):
        scene_id = feature['properties']['landsat:product_id']
        meta = landsat_parser(scene_id)
        path = meta['path']
        row = meta['row']

        new_scene_ids = []
        if self.optimized_selection:
            inserted = False
            for existing_scene_id in self.tiles[quadkey]:
                existing_scene_meta = landsat_parser(existing_scene_id)
                existing_path = existing_scene_meta['path']
                existing_row = existing_scene_meta['row']
                if (path != existing_path) and (row != existing_row):
                    new_scene_ids.append(existing_scene_id)
                    continue

                # Choose between scenes in the same path-row
                chosen_scene_id = self._choose(existing_scene_id, scene_id)
                new_scene_ids.append(chosen_scene_id)
                inserted = True

            if not inserted:
                new_scene_ids.append(scene_id)

        else:
            new_scene_ids.append(scene_id)

        return new_scene_ids

    @staticmethod
    def _choose(scene1, scene2):
        scene1_meta = landsat_parser(scene1)
        scene2_meta = landsat_parser(scene2)

        scene1_date = datetime.strptime(scene1_meta['date'], "%Y-%m-%d")
        scene2_date = datetime.strptime(scene2_meta['date'], "%Y-%m-%d")

        if self.preference == 'newest':
            return scene1 if scene1_date > scene2_date else scene2

        if self.preference == 'oldest':
            return scene1 if scene1_date < scene2_date else scene2

    @property
    def mosaic(self):
        # Keep tiles with at least one asset
        tiles = {k: v for k, v in self.tiles.items() if v}

        return {
            'mosaicjson': "0.0.2",
            'minzoom': self.minzoom,
            'maxzoom': self.maxzoom,
            'quadkey_zoom': self.quadkey_zoom,
            'bounds': self.bounds,
            'center': [(self.bounds[0] + self.bounds[2]) / 2,
                       (self.bounds[1] + self.bounds[3]) / 2, self.minzoom],
            'tiles': tiles,
        }
