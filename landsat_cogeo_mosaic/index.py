"""
landsat_cogeo_mosaic.index.py: Create optimized path-row to quadkey index
"""
from typing import List

import geopandas as gpd
import mercantile
import pandas as pd
from shapely.geometry import asShape


def create_index(pathrow_path, scene_path, bounds, quadkey_zoom):
    """Create index of path-row to quadkey_zoom

    - First get mapping from _quadkey_ to pathrow
    - then optimize this mapping
    - Then reverse it to have mapping from pathrow to quadkey
    """
    # Load pathrow geometries
    pathrows = gpd.read_file(pathrow_path)
    pathrows = pathrows[['PR', 'geometry']]

    # Load scenes to find unique pathrows that actually exist
    # Many pathrows are over water
    scenes = pd.read_csv(scene_path, dtype=str)
    scene_pathrows = (scenes['path'].str.zfill(3) +
                      scenes['row'].str.zfill(3)).unique()

    # Filter on pathrows that actually exist
    pathrows = pathrows[pathrows['PR'].isin(scene_pathrows)]

    # df of mercator tiles at quadkey zoom
    tiles = create_tiles_gdf(bounds, quadkey_zoom)
    tiles = tiles[['geometry', 'quadkey']]

    # Spatial join, keeping geometry of the pathrows
    # joined is an n:n mapping between pathrows and quadkeys
    joined = gpd.sjoin(pathrows, tiles, op='intersects')

    # Optimize
    gdf = optimize_index(joined)

    gdf = gdf.set_index('PR')
    # Dict of {pathrow: [quadkeys]}
    # https://stackoverflow.com/a/29876239
    return gdf.groupby(gdf.index)['quadkey'].apply(list).to_dict()


def create_tiles_gdf(
        bounds: List[float], quadkey_zoom: int) -> gpd.GeoDataFrame:
    """Create GeoDataFrame of all tiles within bounds at quadkey_zoom
    """
    features = [
        mercantile.feature(tile, props={'quadkey': mercantile.quadkey(tile)})
        for tile in mercantile.tiles(*bounds, quadkey_zoom)
    ]
    return gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')


def optimize_index(gdf):
    """Optimize index by selecting minimal pathrows per quadkey

    Within each quadkey, optimize

    Args:
        - gdf: joined GeoDataFrame
    """
    # List to collect results
    res_df = []
    for quadkey, group in gdf.groupby('quadkey'):
        res_df.append(optimize_group(group, quadkey))

    return pd.concat(res_df)


def optimize_group(group, quadkey):
    """Try to find the minimal number of assets to cover tile
    This optimization implies _both_ that
    - assets will be ordered in the MosaicJSON in order of sort of the entire tile
    - the total number of assets is kept to a minimum
    Computing the absolute minimum of assets to cover the tile may not in
    general be possible in finite time, so this is a naive method that should
    work relatively well for this use case.

    Returns group also sorted with respect to intersection of entire tile.
    """
    tile = mercantile.quadkey_to_tile(quadkey)
    tile_geom = asShape(mercantile.feature(tile)['geometry'])
    final_assets = []

    while True:
        # Find intersection percent
        group['int_pct'] = group.geometry.intersection(
            tile_geom).area / tile_geom.area

        # Remove features with no tile overlap
        group = group.loc[group['int_pct'] > 0]

        if len(group) == 0:
            # There are many ocean/border tiles on the edges of available maps
            # that by definition don't have full coverage
            break

        # Sort by cover of region of tile that is left
        group = group.sort_values('int_pct', ascending=False)

        # Remove top asset and add to final_assets
        top_asset = group.iloc[0]
        group = group.iloc[1:]
        final_assets.append(top_asset)

        # Recompute tile_geom, removing overlap with top_asset
        tile_geom = tile_geom.difference(top_asset.geometry)

        # When total area is covered, stop
        if tile_geom.area - 1e-4 < 0:
            break

        if len(group) == 0:
            # There are many ocean/border tiles on the edges of available maps
            # that by definition don't have full coverage
            break

    return gpd.GeoDataFrame(final_assets)
