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

import gzip
import json
import sys
from datetime import datetime
from typing import Callable, Dict, List, Optional, Union

import mercantile
from cogeo_mosaic.mosaic import MosaicJSON
from rio_tiler.io.landsat8 import landsat_parser
from shapely.geometry import asShape, box

from landsat_cogeo_mosaic.util import index_data_path


def landsat_accessor(feature: Dict):
    return feature['properties']['landsat:product_id']


def features_to_mosaicJSON(
        features: List[Dict],
        quadkey_zoom: int = None,
        minzoom: int = 7,
        maxzoom: int = 12,
        index: Union[bool, Dict] = True,
        sort='min-cloud') -> Dict:
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
    if not index:
        mosaic = MosaicJSON.from_features(
            features=features,
            minzoom=minzoom,
            maxzoom=maxzoom,
            quadkey_zoom=quadkey_zoom,
            accessor=landsat_accessor)
        return mosaic.dict(exclude_none=True)

    if not isinstance(index, dict):
        path = index_data_path()
        with gzip.open(path, 'rt') as f:
            index = json.load(f)

    # Define quadkey zoom from index
    quadkey_zoom = len(list(index.values())[0][0])

    pr_keys = set(index.keys())
    sorted_features = {}
    for feature in features:
        pathrow = feature['properties']['eo:column'].zfill(
            3) + feature['properties']['eo:row'].zfill(3)
        if pathrow not in pr_keys:
            continue

        sorted_features[pathrow] = sorted_features.get(pathrow, [])
        sorted_features[pathrow].append(feature)

    tiles = {}
    for pathrow, feats in sorted_features.items():
        if sort == 'min-cloud':
            selected = min(
                feats, key=lambda x: x['properties']['eo:cloud_cover'])
        elif sort == 'max-cloud':
            selected = max(
                feats, key=lambda x: x['properties']['eo:cloud_cover'])
        else:
            selected = feats[0]

        product_id = landsat_accessor(selected)
        quadkeys = index[pathrow]

        for qk in quadkeys:
            tiles[qk] = tiles.get(qk, set())
            tiles[qk].add(product_id)

    bounds = quadkeys_to_bounds(tiles.keys())
    mosaic = MosaicJSON(
        mosaicjson="0.0.2",
        minzoom=minzoom,
        maxzoom=maxzoom,
        quadkey_zoom=quadkey_zoom,
        bounds=bounds,
        tiles=tiles)
    return mosaic.dict(exclude_none=True)


def quadkeys_to_bounds(quadkeys: List[str]):
    """Convert list of quadkeys to bounds

    Args:
        - quadkeys: List of quadkeys
    """
    tile_bounds = [
        mercantile.bounds(mercantile.quadkey_to_tile(qk)) for qk in quadkeys
    ]

    minx = 180
    miny = 90
    maxx = -180
    maxy = -90
    for tb in tile_bounds:
        minx = min(minx, tb[0])
        miny = min(miny, tb[1])
        maxx = max(maxx, tb[2])
        maxy = max(maxy, tb[3])

    return [minx, miny, maxx, maxy]


class StreamingParser:
    """Create Mosaic from stream of GeoJSON Features

    Instead of first laying out all features and then splitting them up into
    tiles, this works by first laying out all _tiles_ and then adding features
    one by one.
    """
    def __init__(
            self,
            quadkey_zoom: Optional[int] = None,
            bounds: List[float] = None,
            minzoom: int = 7,
            maxzoom: int = 12,
            preference: str = 'newest',
            optimized_selection: bool = True,
            accessor: Callable = lambda d: d['properties']['landsat:product_id'
                                                          ],
            closest_to_date: Optional[datetime] = None):

        if optimized_selection and preference not in ['newest', 'oldest',
                                                      'closest-to-date']:
            raise ValueError('Unsupported preference')

        self.quadkey_zoom = quadkey_zoom or minzoom
        self.bounds = bounds or [-180, -90, 180, 90]
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.preference = preference
        self.optimized_selection = optimized_selection
        self.accessor = accessor

        if (preference == 'closest-to-date') and (not closest_to_date):
            msg = 'closest_to_date required when preference is closest-to-date'
            raise ValueError(msg)

        if preference != 'closest-to-date':
            self.closest_to_date = None
        elif isinstance(closest_to_date, datetime):
            self.closest_to_date = closest_to_date
        else:
            self.closest_to_date = datetime.strptime(
                closest_to_date, "%Y-%m-%d")

        # Find tiles at desired zoom
        tiles = list(mercantile.tiles(*self.bounds, quadkey_zoom))
        quadkeys = [mercantile.quadkey(tile) for tile in tiles]

        self.tiles: Dict[str, List[str]] = {k: set() for k in quadkeys}

    def add_by_pathrow(self, scene_id, pathrow_geom):
        """Add scene to tiles dict by pathrow

        Args:
            - feature: GeoJSON Feature derived from STAC
        """
        tiles = list(mercantile.tiles(*pathrow_geom.bounds, self.quadkey_zoom))

        # Keep tiles that intersect the feature geometry
        tiles = [
            tile for tile in tiles if asShape(
                mercantile.feature(tile)['geometry']).intersects(pathrow_geom)
        ]

        quadkeys = [mercantile.quadkey(tile) for tile in tiles]

        for quadkey in quadkeys:
            # If quadkey wasn't initialized, it's outside bounds
            if quadkey not in self.tiles.keys():
                continue

            self.tiles[quadkey].add(scene_id)

    def add(self, feature: Dict):
        """Add feature to tiles dict

        Args:
            - feature: GeoJSON Feature derived from STAC
        """
        # Find overlapping quadkeys
        if 'geometry' in feature:
            feature_geom = asShape(feature['geometry'])
        elif 'bounds' in feature:
            feature_geom = box(*feature['bounds'])
        else:
            raise ValueError('No geometry information')

        tiles = list(mercantile.tiles(*feature_geom.bounds, self.quadkey_zoom))

        # Keep tiles that intersect the feature geometry
        tiles = [
            tile for tile in tiles if asShape(
                mercantile.feature(tile)['geometry']).intersects(feature_geom)
        ]

        quadkeys = [mercantile.quadkey(tile) for tile in tiles]

        for quadkey in quadkeys:
            # If quadkey wasn't initialized, it's outside bounds
            if quadkey not in self.tiles.keys():
                continue

            self._add_feature_to_quadkey(quadkey, feature)

    def _add_feature_to_quadkey(self, quadkey: str, feature: Dict):
        """Add feature to specific quadkey

        Args:
            - quadkey: quadkey to add feature to
            - feature: feature to add
        """
        scene_id = self.accessor(feature)
        meta = landsat_parser(scene_id)
        path = meta['path']
        row = meta['row']

        if not self.optimized_selection:
            self.tiles[quadkey].add(scene_id)
            return

        existing_scene_ids = self.tiles[quadkey].copy()

        # Same scene id already exists
        if scene_id in existing_scene_ids:
            return

        # Loop through existing assets to see if _any_ are overlapping
        # Note: If I do this correctly, there should only ever be _one_
        # overlapping
        existing_overlapping_scene_id = None
        for existing_scene_id in existing_scene_ids:
            existing_scene_meta = landsat_parser(existing_scene_id)
            existing_path = existing_scene_meta['path']
            existing_row = existing_scene_meta['row']

            if (path == existing_path) and (row == existing_row):
                existing_overlapping_scene_id = existing_scene_id
                break

        # If not set, no existing overlapping scene exists
        if not existing_overlapping_scene_id:
            self.tiles[quadkey].add(scene_id)
            return

        # An existing overlapping scene exists
        keep_existing = self._choose_first(
            existing_overlapping_scene_id, scene_id)
        if keep_existing:
            return

        # Remove existing and add new
        self.tiles[quadkey].remove(existing_overlapping_scene_id)
        self.tiles[quadkey].add(scene_id)

    def _choose_first(self, scene1: str, scene2: str) -> bool:
        """Decide whether to choose first or second scene

        Uses self.preference to decide whether to choose the first or second
        scene passed as arguments.

        Args:
            - scene1: landsat scene id
            - scene2: landsat scene id

        Returns:
            bool: True if the first is chosen, False if the second is chosen.
        """
        scene1_meta = landsat_parser(scene1)
        scene2_meta = landsat_parser(scene2)

        scene1_date = datetime.strptime(scene1_meta['date'], "%Y-%m-%d")
        scene2_date = datetime.strptime(scene2_meta['date'], "%Y-%m-%d")

        if self.preference == 'newest':
            return scene1_date > scene2_date

        if self.preference == 'oldest':
            return scene1_date < scene2_date

        if self.preference == 'closest-to-date':
            dist1 = abs(scene1_date - self.closest_to_date)
            dist2 = abs(scene2_date - self.closest_to_date)
            return dist1 < dist2

        return True

    @property
    def mosaic(self):
        # Check that selection correctly optimized
        if self.optimized_selection:
            num_duplicate_quadkeys, num_duplicate_assets = self.check_optimized_selection(
            )
            if num_duplicate_quadkeys or num_duplicate_assets:
                print(
                    'Warning: selection not correctly optimized.',
                    file=sys.stderr)
                print(
                    f'# of quadkeys with duplicate path-rows: {num_duplicate_quadkeys}',
                    file=sys.stderr)
                print(
                    f'# of duplicate path-rows overall: {num_duplicate_assets}',
                    file=sys.stderr)

        # Keep tiles with at least one asset
        tiles = {k: list(v) for k, v in self.tiles.items() if v}

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

    def check_optimized_selection(self):
        num_duplicate_quadkeys = 0
        num_duplicate_assets = 0
        for assets in self.tiles.values():
            n_assets = len(assets)
            metas = [landsat_parser(asset) for asset in assets]

            pathrows = {meta['path'] + meta['row'] for meta in metas}
            if n_assets != len(pathrows):
                num_duplicate_quadkeys += 1
                num_duplicate_assets += n_assets - len(pathrows)

        return num_duplicate_quadkeys, num_duplicate_assets
