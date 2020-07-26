import json
import re
import sys
from datetime import datetime
from pathlib import Path

import click

from landsat_cogeo_mosaic.grid import generate_grid
from landsat_cogeo_mosaic.index import create_index
from landsat_cogeo_mosaic.mosaic import create_from_db as _create_from_db
from landsat_cogeo_mosaic.mosaic import features_to_mosaicJSON
from landsat_cogeo_mosaic.stac import search as _search
from landsat_cogeo_mosaic.util import filter_season, load_index_data
from landsat_cogeo_mosaic.validate import missing_quadkeys as _missing_quadkeys
from landsat_cogeo_mosaic.visualize import visualize as _visualize


@click.group()
def main():
    pass


@click.command()
@click.option(
    '-b',
    '--bounds',
    type=str,
    required=True,
    help='Comma-separated bounding box: "west, south, east, north"')
@click.option(
    '--min-cloud',
    type=float,
    required=False,
    default=0,
    show_default=True,
    help='Minimum cloud percentage')
@click.option(
    '--max-cloud',
    type=float,
    required=False,
    default=100,
    show_default=True,
    help='Maximum cloud percentage')
@click.option(
    '--min-date',
    type=str,
    required=False,
    default='2013-01-01',
    show_default=True,
    help='Minimum date')
@click.option(
    '--max-date',
    type=str,
    required=False,
    default=datetime.strftime(datetime.today(), "%Y-%m-%d"),
    show_default=True,
    help='Maximum date, inclusive')
@click.option(
    '--period',
    type=click.Choice(["day", "week", "month", "year"], case_sensitive=False),
    required=False,
    default=None,
    show_default=True,
    help=
    'Time period. If provided, overwrites `max-date` with the given period after `min-date`.'
)
@click.option(
    '--period-qty',
    type=int,
    required=False,
    default=1,
    show_default=True,
    help=
    'Number of periods to apply after `min-date`. Only applies if `period` is provided.'
)
@click.option(
    '--season',
    multiple=True,
    default=None,
    show_default=True,
    type=click.Choice(["spring", "summer", "autumn", "winter"]),
    help='Season, can provide multiple')
@click.option(
    '--stac-collection-limit',
    type=int,
    default=500,
    show_default=True,
    help='Limits the number of items per page returned by sat-api.')
def search(
        bounds, min_cloud, max_cloud, min_date, max_date, period, period_qty,
        stac_collection_limit, season):
    """Retrieve features from sat-api
    """
    bounds = tuple(map(float, bounds.split(',')))
    features = _search(
        bounds=bounds,
        min_cloud=min_cloud,
        max_cloud=max_cloud,
        min_date=min_date,
        max_date=max_date,
        period=period,
        period_qty=period_qty,
        stac_collection_limit=stac_collection_limit)
    if not features:
        print(f"No assets found for query", file=sys.stderr)
        return

    if season:
        features = filter_season(features, season)

    # Write to stdout as newline delimited features
    for feature in features:
        print(json.dumps(feature, separators=(',', ':')))


@click.command()
@click.option(
    '--min-zoom',
    type=int,
    required=False,
    default=7,
    show_default=True,
    help='Minimum zoom')
@click.option(
    '--max-zoom',
    type=int,
    required=False,
    default=12,
    show_default=True,
    help='Maximum zoom')
@click.option(
    '--quadkey-zoom',
    type=int,
    required=False,
    default=None,
    show_default=True,
    help=
    'Zoom level used for quadkeys in MosaicJSON. Lower value means more assets per tile, but a smaller MosaicJSON file. Higher value means fewer assets per tile but a larger MosaicJSON file. Must be between min zoom and max zoom, inclusive.'
)
@click.option(
    '-b',
    '--bounds',
    type=str,
    required=False,
    default=None,
    help='Comma-separated bounding box: "west, south, east, north"')
@click.option(
    '--season',
    multiple=True,
    default=None,
    show_default=True,
    type=click.Choice(["spring", "summer", "autumn", "winter"]),
    help='Season, can provide multiple')
@click.argument('lines', type=click.File())
def create(min_zoom, max_zoom, quadkey_zoom, bounds, season, lines):
    """Create MosaicJSON from STAC features
    """
    if bounds:
        bounds = tuple(map(float, re.split(r'[, ]+', bounds)))

    features = [json.loads(l) for l in lines]

    if season:
        features = filter_season(features, season)

    mosaic = features_to_mosaicJSON(
        features=features,
        quadkey_zoom=quadkey_zoom,
        minzoom=min_zoom,
        maxzoom=max_zoom)
    print(json.dumps(mosaic, separators=(',', ':')))


@click.command()
@click.option(
    '--sqlite-path',
    type=click.Path(exists=True, readable=True),
    required=True,
    help='Path to sqlite3 db generated from scene_list')
@click.option(
    '--pathrow-index',
    type=click.Path(exists=True, readable=True),
    required=False,
    default=None,
    help='Path to pathrow-quadkey index. Loads bundled index by default.')
@click.option(
    '--max-cloud',
    type=float,
    required=False,
    default=100,
    show_default=True,
    help='Maximum cloud percentage')
@click.option(
    '--min-date',
    type=str,
    required=False,
    default='2013-01-01',
    show_default=True,
    help='Minimum date, inclusive')
@click.option(
    '--max-date',
    type=str,
    required=False,
    default=datetime.strftime(datetime.today(), "%Y-%m-%d"),
    show_default=True,
    help='Maximum date, inclusive')
@click.option(
    '--min-zoom',
    type=int,
    required=False,
    default=7,
    show_default=True,
    help='Minimum zoom')
@click.option(
    '--max-zoom',
    type=int,
    required=False,
    default=12,
    show_default=True,
    help='Maximum zoom')
@click.option(
    '-p',
    '--sort-preference',
    type=click.Choice(['newest', 'oldest', 'closest-to-date', 'min-cloud'],
                      case_sensitive=False),
    default='newest',
    show_default=True,
    help='Method for choosing scenes in the same path-row')
@click.option(
    '--closest-to-date',
    type=str,
    default=None,
    help=
    'Date used for comparisons when preference is closest-to-date. Format must be YYYY-MM-DD'
)
def create_from_db(
        sqlite_path, pathrow_index, max_cloud, min_date, max_date, min_zoom,
        max_zoom, sort_preference, closest_to_date):
    """Create MosaicJSON from SQLite database of Landsat features
    """
    if (sort_preference == 'closest-to-date') and (not closest_to_date):
        msg = 'closest-to-date parameter required when sort_preference is closest-to-date'
        raise ValueError(msg)

    pr_index = load_index_data(pathrow_index)
    mosaic = _create_from_db(
        sqlite_path=sqlite_path,
        pr_index=pr_index,
        max_cloud=max_cloud,
        min_date=min_date,
        max_date=max_date,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        sort_preference=sort_preference,
        closest_to_date=closest_to_date)

    print(json.dumps(mosaic, separators=(',', ':')))


@click.command()
@click.option(
    '--wrs-path',
    required=True,
    type=click.Path(exists=True, readable=True),
    help=
    'Path to Shapefile (.shp) of WRS2 polygons. You can download then extract from here https://www.usgs.gov/media/files/landsat-wrs-2-descending-path-row-shapefile'
)
@click.option(
    '--scene-path',
    required=True,
    type=click.Path(exists=True, readable=True),
    help='Path to CSV of scene metadata downloaded from AWS S3.')
@click.option(
    '-b',
    '--bounds',
    type=str,
    default='-180,-90,180,90',
    show_default=True,
    help='force bounding box: "west, south, east, north"')
@click.option(
    '--quadkey-zoom',
    type=int,
    required=False,
    default=8,
    show_default=True,
    help=
    'Zoom level used for quadkeys in MosaicJSON. Lower value means more assets per tile, but a smaller MosaicJSON file. Higher value means fewer assets per tile but a larger MosaicJSON file. Must be between min zoom and max zoom, inclusive.'
)
def index(wrs_path, scene_path, bounds, quadkey_zoom):
    """Create optimized index of path-row to quadkey_zoom
    """
    if bounds:
        bounds = tuple(map(float, bounds.split(',')))

    _index = create_index(
        pathrow_path=wrs_path,
        scene_path=scene_path,
        bounds=bounds,
        quadkey_zoom=quadkey_zoom)

    print(json.dumps(_index, separators=(',', ':')))


@click.command()
@click.option(
    '--wrs-path',
    required=True,
    type=click.Path(exists=True, readable=True),
    help=
    'Path to Shapefile (.shp) of WRS2 polygons. You can download then extract from here https://www.usgs.gov/media/files/landsat-wrs-2-descending-path-row-shapefile'
)
@click.option(
    '-o',
    '--out-path',
    required=True,
    type=click.Path(exists=False, writable=True),
    help='Path of new SQLite DB. Will overwrite any existing file.')
@click.option(
    '--pr-index',
    type=click.Path(exists=True, readable=True),
    required=False,
    default=None,
    show_default=True,
    help=
    'Pathrow index JSON file to use for filtering pathrows in DB. Useful, for example, to include only pathrows over land.'
)
@click.option(
    '-b',
    '--bounds',
    type=str,
    default=None,
    show_default=True,
    help='force bounding box: "west, south, east, north"')
def grid(wrs_path, out_path, pr_index, bounds):
    """Generate WRS2 Grid as SQLite DB
    """
    if bounds:
        bounds = tuple(map(float, bounds.split(',')))

    pathrows = None
    if pr_index:
        with open(pr_index) as f:
            pathrows = json.load(f).keys()

    generate_grid(wrs_path, out_path, pathrows=pathrows, bounds=bounds)


@click.command()
@click.option(
    '--shp-path',
    required=True,
    type=click.Path(exists=True, readable=True),
    help='path to Natural Earth shapefile of land boundaries')
@click.option(
    '-b',
    '--bounds',
    type=str,
    default=None,
    help='force bounding box: "west, south, east, north"')
@click.option(
    '--simplify/--no-simplify',
    is_flag=True,
    default=True,
    show_default=True,
    help=
    'Reduce size of the output tileset as much as possible by merging leaves into parents.'
)
@click.argument('file', type=click.File())
def missing_quadkeys(shp_path, bounds, simplify, file):
    """Find quadkeys over land missing from mosaic
    """
    if bounds:
        bounds = tuple(map(float, re.split(r'[, ]+', bounds)))

    mosaic = json.load(file)

    fc = _missing_quadkeys(
        mosaic=mosaic, shp_path=shp_path, bounds=bounds, simplify=simplify)
    print(json.dumps(fc, separators=(',', ':')))


@click.command()
@click.option(
    '-p',
    '--wrs-path',
    required=True,
    type=click.Path(exists=True, readable=True),
    help=
    'Path to Shapefile (.shp) of WRS2 polygons. You can download then extract from here https://www.usgs.gov/media/files/landsat-wrs-2-descending-path-row-shapefile'
)
@click.option(
    '--api-key',
    required=False,
    default=None,
    type=str,
    help=
    'Mapbox API key. Can also be read from the MAPBOX_API_KEY environment variable.'
)
@click.argument('mosaic-paths', type=click.Path(exists=True), nargs=-1)
def visualize(wrs_path, mosaic_paths, api_key):
    """Visualize Landsat mosaic in kepler.gl
    """
    mosaics = []
    for mosaic_path in mosaic_paths:
        with open(mosaic_path) as f:
            mosaics.append(json.load(f))

    mosaic_names = [Path(path).name for path in mosaic_paths]
    _visualize(
        mosaics=mosaics,
        pathrow_path=wrs_path,
        names=mosaic_names,
        api_key=api_key)


main.add_command(create)
main.add_command(create_from_db)
main.add_command(grid)
main.add_command(index)
main.add_command(missing_quadkeys)
main.add_command(search)
main.add_command(visualize)

if __name__ == '__main__':
    main()
