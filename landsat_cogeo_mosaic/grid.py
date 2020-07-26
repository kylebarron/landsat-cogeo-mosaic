"""
landsat_cogeo_mosaic.grid.py: Generate WRS2 Grid as Sqlite DB
"""
import sqlite3
from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd
from shapely import wkb
from shapely.geometry import box


def generate_grid(
        wrs2_path,
        out_db_path,
        pathrows: List[str] = None,
        bounds: List[float] = None):
    """Generate WRS2 Grid as Sqlite DB

    Args:
        - wrs2_path: path to shapefile containing wrs2 geometries
        - out_db_path: path for writing sqlite3 db
        - pathrows: (optional), pathrows to include in DB. Intended to allow
          creating a sqlite db of pathrows only over land or that actually exist
          in the Landsat dataset. A smaller pathrow-index will create a smaller
          DB file.
        - bounds: (optional): minx, miny, maxx, maxy of area of interest
    """
    gdf = gpd.read_file(wrs2_path)

    # Clip within bounds
    if bounds:
        bounds = box(*bounds)
        gdf = gdf[gdf.geometry.intersects(bounds)]

    if pathrows:
        gdf = gdf[gdf['PR'].isin(pathrows)]

    # Keep only pathrow and geometry columns
    gdf = gdf[['PR', 'geometry']]
    gdf = gdf.rename({'PR': 'pathrow'}, axis=1)

    # Delete DB if already exists
    if Path(out_db_path).exists():
        Path(out_db_path).unlink()

    # Create DB
    create_db(gdf, out_db_path)


def create_db(gdf, out_db_path):
    create_table_sql = f"""\
    CREATE TABLE IF NOT EXISTS wrs2 (
    	pathrow TEXT PRIMARY KEY,
        geometry BLOB
    );
    """

    create_index_sql = f"""\
    CREATE UNIQUE INDEX pathrow_idx
    ON wrs2(pathrow);
    """

    # Convert geometry to wkb blob
    gdf['wkb_geometry'] = gdf.geometry.apply(wkb.dumps)
    gdf = gdf.drop('geometry', axis=1)
    df = pd.DataFrame(gdf)
    df = df.rename({'wkb_geometry': 'geometry'}, axis=1)

    conn = sqlite3.connect(out_db_path)
    with sqlite3.connect(out_db_path) as conn:
        cur = conn.cursor()

        # Create table
        cur.execute(create_table_sql)

        df.to_sql('wrs2', conn, if_exists='append', index=False)

        # Create index on pathrow
        cur.execute(create_index_sql)
