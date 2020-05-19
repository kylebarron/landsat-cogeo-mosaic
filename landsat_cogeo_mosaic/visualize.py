"""
landsat_cogeo_mosaic.visualize: Visualize mosaic with kepler.gl
"""
from typing import Dict, List

import geopandas as gpd
import pandas as pd
from keplergl_cli import Visualize
from rio_tiler.io.landsat8 import landsat_parser


def visualize(
        mosaics: List[Dict],
        pathrow_path: str,
        names: List[str] = None,
        api_key: str = None):
    """Visualize Landsat mosaic in kepler.gl

    Args:
        - mosaics: List of Dicts of Mosaics
        - pathrow_path: Path to WRS2 shapefile
        - names: List of strings to use in kepler.gl
        - api_key: Mapbox API key
    """
    gdf = gpd.read_file(pathrow_path)
    gdf = gdf[['PR', 'geometry']]

    mosaic_gdfs = []
    for mosaic in mosaics:
        mosaic_gdfs.append(get_mosaic_geometries(mosaic, gdf))

    Visualize(
        data=mosaic_gdfs,
        names=names,
        read_only=False,
        api_key=api_key,
        style='outdoors')


def get_mosaic_geometries(mosaic, gdf):
    """Get GeoDataFrame of geometries of assets in mosaic
    """
    # Get all assets
    all_assets = set()
    for assets in mosaic['tiles'].values():
        all_assets.update(assets)

    assets_df = pd.DataFrame(all_assets, columns=['asset'])
    assets_df['pathrow'] = assets_df['asset'].apply(get_pathrow)

    merged = pd.merge(gdf, assets_df, left_on='PR', right_on='pathrow')
    merged = merged.drop('PR', axis=1)
    return merged


def get_pathrow(asset):
    """Get pathrow for asset string
    """
    meta = landsat_parser(asset)
    return meta['path'].zfill(3) + meta['row'].zfill(3)
