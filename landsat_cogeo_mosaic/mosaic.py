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
from typing import Dict, List, Optional, Set, Union

import mercantile
from cogeo_mosaic.mosaic import MosaicJSON
from rio_tiler_pds.landsat.utils import sceneid_parser

from landsat_cogeo_mosaic.db import find_records, generate_query
from landsat_cogeo_mosaic.util import coerce_to_datetime, index_data_path


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


def create_from_db(
        sqlite_path, pr_index, max_cloud, min_date, max_date, min_zoom,
        max_zoom, sort_preference, closest_to_date):
    """Create MosaicJSON from SQLite database of Landsat features
    """
    quadkey_zoom = len(list(pr_index.values())[0][0])
    streaming_parser = StreamingParser(
        quadkey_zoom=quadkey_zoom, minzoom=min_zoom, maxzoom=max_zoom)

    count = 0
    for pathrow, quadkeys in pr_index.items():
        count += 1
        if count % 1000 == 0:
            print(f'Pathrow: {count}', file=sys.stderr)

        asset = find_asset_for_pathrow(
            sqlite_path,
            pathrow=pathrow,
            max_cloud=max_cloud,
            min_date=min_date,
            max_date=max_date,
            sort_preference=sort_preference,
            closest_to_date=closest_to_date)
        product_id = asset['productId']
        for quadkey in quadkeys:
            streaming_parser.add(quadkey, product_id)

    return streaming_parser.mosaic


def find_asset_for_pathrow(sqlite_path, **kwargs):
    """Find asset from database for pathrow

    The querying is done inside a loop, so that if the query returns no results,
    it can be repeated with relaxed parameters.

    Args:
        - sqlite_path: Path to sqlite database
        - kwargs: Arguments passed to db.generate_query
    """
    while True:
        # Generate query
        query = generate_query(**kwargs)

        # Find records for query
        iterator = find_records(sqlite_path, query)

        # Return if found
        try:
            return next(iterator)
        except StopIteration:
            if kwargs.get('max_cloud') >= 100 and kwargs.get(
                    'sort_preference') == 'closest-to-date':

                pathrow = kwargs.get('pathrow')
                print(
                    f'Unable to find assets for pathrow {pathrow}',
                    file=sys.stderr)
                return

        # Modify parameters
        kwargs = relax_params(**kwargs)


def relax_params(**kwargs):
    """Relax search parameters if not found
    """
    max_cloud = kwargs.get('max_cloud', 0)
    if max_cloud < 100:
        max_cloud += 5
        kwargs['max_cloud'] = max_cloud
        pathrow = kwargs['pathrow']
        print(
            f'Trying again with max_cloud {max_cloud} for pathrow={pathrow}',
            file=sys.stderr)
        return kwargs

    # Otherwise, do a "last-ditch" of the closest to the midpoint date
    min_date = coerce_to_datetime(kwargs.get('min_date', '2013-04-11'))
    max_date = coerce_to_datetime(kwargs.get('max_date', datetime.today()))

    midpoint_date = min_date + ((max_date - min_date) / 2)
    kwargs['min_date'] = None
    kwargs['max_date'] = None
    kwargs['closest_to_date'] = midpoint_date
    kwargs['sort_preference'] = 'closest-to-date'
    return kwargs


class StreamingParser:
    """Create MosaicJSON iteratively
    """
    def __init__(
            self,
            quadkey_zoom: Optional[int] = None,
            bounds: List[float] = None,
            minzoom: int = 7,
            maxzoom: int = 12):

        self.quadkey_zoom = quadkey_zoom or minzoom
        self.bounds = bounds
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.tiles: Dict[str, Set[str]] = {}

    def add(self, quadkey, asset):
        """Add specific quadkey-asset combination to Mosaic
        """
        self.tiles[quadkey] = self.tiles.get(quadkey, set())
        self.tiles[quadkey].add(asset)

    @property
    def mosaic(self):
        # Keep tiles with at least one asset
        tiles = {k: list(v) for k, v in self.tiles.items() if v}
        bounds = self.bounds or quadkeys_to_bounds(tiles.keys())

        return {
            'mosaicjson': "0.0.2",
            'minzoom': self.minzoom,
            'maxzoom': self.maxzoom,
            'quadkey_zoom': self.quadkey_zoom,
            'bounds': bounds,
            'center': [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2,
                       self.minzoom],
            'tiles': tiles,
        }

    def check_optimized_selection(self):
        num_duplicate_quadkeys = 0
        num_duplicate_assets = 0
        for assets in self.tiles.values():
            n_assets = len(assets)
            metas = [sceneid_parser(asset) for asset in assets]

            pathrows = {meta['path'] + meta['row'] for meta in metas}
            if n_assets != len(pathrows):
                num_duplicate_quadkeys += 1
                num_duplicate_assets += n_assets - len(pathrows)

        return num_duplicate_quadkeys, num_duplicate_assets
