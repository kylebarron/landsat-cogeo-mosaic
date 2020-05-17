import json
import re
import sys
from datetime import datetime

import click
from dateutil.relativedelta import relativedelta
from shapely.geometry import asShape, box

from landsat_cogeo_mosaic.db import find_records
from landsat_cogeo_mosaic.index import create_index
from landsat_cogeo_mosaic.mosaic import StreamingParser, features_to_mosaicJSON
from landsat_cogeo_mosaic.stac import fetch_sat_api
from landsat_cogeo_mosaic.util import filter_season, list_depth
from landsat_cogeo_mosaic.validate import missing_quadkeys as _missing_quadkeys


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

    bounds = tuple(map(float, re.split(r'[, ]+', bounds)))
    start = datetime.strptime(min_date,
                              "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")

    if period:
        start_datetime = datetime.strptime(start, "%Y-%m-%dT00:00:00Z")

        if period == 'day':
            delta = relativedelta(days=period_qty)
        elif period == 'week':
            delta = relativedelta(weeks=period_qty)
        elif period == 'month':
            delta = relativedelta(months=period_qty)
        elif period == 'year':
            delta = relativedelta(years=period_qty)

        end_datetime = start_datetime + delta
        end = end_datetime.strftime("%Y-%m-%dT00:00:00Z")
    else:
        end = datetime.strptime(max_date,
                                "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

    query = {
        "bbox": bounds,
        "time": f"{start}/{end}",
        "query": {
            "eo:sun_elevation": {
                "gt": 0
            },
            "landsat:tier": {
                "eq": "T1"
            },
            "collection": {
                "eq": "landsat-8-l1"
            },
            "eo:cloud_cover": {
                "gte": min_cloud,
                "lt": max_cloud
            },
            "eo:platform": {
                "eq": "landsat-8"
            },
        },
        "sort": [{
            "field": "eo:cloud_cover",
            "direction": "asc"
        }],
    }

    if stac_collection_limit:
        query['limit'] = stac_collection_limit

    features = fetch_sat_api(query)
    if not features:
        print(
            f"No asset found for query '{json.dumps(query)}'", file=sys.stderr)
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
    '--optimized-selection/--no-optimized-selection',
    is_flag=True,
    default=True,
    show_default=True,
    help=
    'Attempt to optimize assets in tile. This optimization implies that 1) assets will be ordered in the MosaicJSON in order of cover of the entire tile and 2) the total number of assets is kept to a minimum.'
)
@click.option(
    '--season',
    multiple=True,
    default=None,
    show_default=True,
    type=click.Choice(["spring", "summer", "autumn", "winter"]),
    help='Season, can provide multiple')
@click.argument('lines', type=click.File())
def create(
        min_zoom, max_zoom, quadkey_zoom, bounds, optimized_selection, season,
        lines):
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
        bounds=bounds,
        minzoom=min_zoom,
        maxzoom=max_zoom,
        optimized_selection=optimized_selection)
    print(json.dumps(mosaic, separators=(',', ':')))


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
    default='-180,-90,180,90',
    show_default=True,
    help='Comma-separated bounding box: "west, south, east, north"')
@click.option(
    '--optimized-selection/--no-optimized-selection',
    is_flag=True,
    default=True,
    show_default=True,
    help=
    'Optimize assets in tile. Only a single asset per path-row will be included in each quadkey. Note that there will usually be multiple path-rows within a single quadkey tile.'
)
@click.option(
    '-p',
    '--preference',
    type=click.Choice(['newest', 'oldest', 'closest-to-date'],
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
@click.option(
    '--season',
    multiple=True,
    default=None,
    show_default=True,
    type=click.Choice(["spring", "summer", "autumn", "winter"]),
    help='Season, can provide multiple')
@click.argument('file', type=click.File())
def create_streaming(
        min_zoom, max_zoom, quadkey_zoom, bounds, optimized_selection,
        preference, closest_to_date, season, file):
    """Create MosaicJSON from STAC features without holding in memory
    """
    if bounds:
        bounds = tuple(map(float, re.split(r'[, ]+', bounds)))

    if (preference == 'closest-to-date') and (not closest_to_date):
        msg = 'closest-to-date parameter required when preference is closest-to-date'
        raise ValueError(msg)

    streaming_parser = StreamingParser(
        quadkey_zoom=quadkey_zoom,
        bounds=bounds,
        minzoom=min_zoom,
        maxzoom=max_zoom,
        preference=preference,
        optimized_selection=optimized_selection,
        closest_to_date=closest_to_date)

    count = 0
    for line in file:
        count += 1
        if count % 5000 == 0:
            print(f'Feature: {count}', file=sys.stderr)

        feature = json.loads(line)

        # Filter by season
        if season:
            features = filter_season([feature], season)
            if not features:
                continue

            feature = features[0]

        streaming_parser.add(feature)

    print(json.dumps(streaming_parser.mosaic, separators=(',', ':')))


@click.command()
@click.option(
    '--sqlite-path',
    type=click.Path(exists=True, readable=True),
    required=True,
    help='Path to sqlite3 db generated from scene_list')
@click.option(
    '--pathrow-xw',
    type=click.Path(exists=True, readable=True),
    required=True,
    help='Path to pathrow2coords crosswalk')
@click.option(
    '-b',
    '--bounds',
    type=str,
    default=None,
    help='Comma-separated bounding box: "west, south, east, north"')
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
    '--quadkey-zoom',
    type=int,
    required=False,
    default=None,
    show_default=True,
    help=
    'Zoom level used for quadkeys in MosaicJSON. Lower value means more assets per tile, but a smaller MosaicJSON file. Higher value means fewer assets per tile but a larger MosaicJSON file. Must be between min zoom and max zoom, inclusive.'
)
@click.option(
    '--optimized-selection/--no-optimized-selection',
    is_flag=True,
    default=True,
    show_default=True,
    help=
    'Optimize assets in tile. Only a single asset per path-row will be included in each quadkey. Note that there will usually be multiple path-rows within a single quadkey tile.'
)
@click.option(
    '-p',
    '--preference',
    type=click.Choice(['newest', 'oldest', 'closest-to-date'],
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
        sqlite_path, pathrow_xw, bounds, max_cloud, min_date, max_date,
        min_zoom, max_zoom, quadkey_zoom, optimized_selection, preference,
        closest_to_date):
    """Create MosaicJSON from SQLite database of Landsat features
    """
    if bounds:
        bounds = tuple(map(float, re.split(r'[, ]+', bounds)))
        bounds = box(*bounds)

    if (preference == 'closest-to-date') and (not closest_to_date):
        msg = 'closest-to-date parameter required when preference is closest-to-date'
        raise ValueError(msg)

    with open(pathrow_xw) as f:
        pr_xw = json.load(f)

    streaming_parser = StreamingParser(
        quadkey_zoom=quadkey_zoom,
        bounds=bounds,
        minzoom=min_zoom,
        maxzoom=max_zoom)

    count = 0
    for pathrow, coords in pr_xw.items():
        count += 1
        if count % 1000 == 0:
            print(f'Pathrow: {count}', file=sys.stderr)

        coord_depth = list_depth(coords)
        if coord_depth == 3:
            geometry = {'type': 'Polygon', 'coordinates': coords}
        elif coord_depth == 4:
            geometry = {'type': 'MultiPolygon', 'coordinates': coords}

        pathrow_geom = asShape(geometry)
        # Check in bounds
        if bounds:
            if not pathrow_geom.intersects(bounds):
                continue

        it = find_records(
            sqlite_path,
            pathrow=pathrow,
            table_name='scene_list',
            max_cloud=max_cloud,
            min_date=min_date,
            max_date=max_date,
            preference=preference,
            closest_to_date=closest_to_date,
            columns=['productId'])

        for record in it:
            streaming_parser.add_by_pathrow(record['productId'], pathrow_geom)
            break

    print(json.dumps(streaming_parser.mosaic, separators=(',', ':')))


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

    index = create_index(
        pathrow_path=wrs_path,
        scene_path=scene_path,
        bounds=bounds,
        quadkey_zoom=quadkey_zoom)

    lines = [{pr: quadkeys} for pr, quadkeys in index.items()]
    for line in lines:
        print(json.dumps(line, separators=(',', ':')))


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


main.add_command(create)
main.add_command(create_from_db)
main.add_command(create_streaming)
main.add_command(index)
main.add_command(missing_quadkeys)
main.add_command(search)

if __name__ == '__main__':
    main()
