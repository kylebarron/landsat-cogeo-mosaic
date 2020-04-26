from typing import Dict, List

import geopandas as gpd
import mercantile
from shapely.geometry import shape


def missing_quadkeys(
        mosaic: Dict,
        shp_path: str,
        bounds: List[float] = None,
        simplify: bool = True) -> Dict:
    """Find quadkeys over land missing from mosaic

    Args:
        - mosaic: mosaic definition
        - shp_path: path to Natural Earth shapefile of land boundaries
        - bounds: force given bounds
        - simplify: reduce size of the tileset as much as possible by merging leaves into parents

    Returns:
        - GeoJSON FeatureCollection of missing tiles
    """
    bounds = bounds or mosaic['bounds']
    top_tile = mercantile.bounding_tile(*bounds)
    gdf = gpd.read_file(shp_path)
    quadkey_zoom = mosaic.get('quadkey_zoom', mosaic['minzoom'])

    # Remove null island
    # Keep the landmasses that are visible at given zoom
    gdf = gdf[gdf['max_zoom'] <= quadkey_zoom]

    land_tiles = find_child_land_tiles(top_tile, gdf, quadkey_zoom)
    quadkeys = {mercantile.quadkey(tile) for tile in land_tiles}

    mosaic_quadkeys = set(mosaic['tiles'].keys())
    not_in_mosaic = quadkeys.difference(mosaic_quadkeys)
    not_in_mosaic = [mercantile.quadkey_to_tile(qk) for qk in not_in_mosaic]

    if simplify:
        not_in_mosaic = mercantile.simplify(not_in_mosaic)

    features = [mercantile.feature(tile) for tile in not_in_mosaic]

    return {'type': 'FeatureCollection', 'features': features}


def find_child_land_tiles(
        tile: mercantile.Tile, gdf: gpd.GeoDataFrame,
        maxzoom: int) -> List[mercantile.Tile]:
    """Recursively find tiles at desired zoom that intersect land areas

    Args:
        - tile: tile to recursively search within
        - gdf: GeoDataFrame with geometries of land masses
        - maxzoom: zoom at which to stop recursing

    Returns:
        List of tiles intersecting land
    """
    land_tiles = []

    for child in mercantile.children(tile):
        tile_geom = shape(mercantile.feature(tile)['geometry'])

        intersects_land = gdf.intersects(tile_geom).any()

        if not intersects_land:
            continue

        if child.z == maxzoom:
            land_tiles.append(child)
            continue

        land_tiles.extend(find_child_land_tiles(child, gdf, maxzoom))

    return land_tiles
