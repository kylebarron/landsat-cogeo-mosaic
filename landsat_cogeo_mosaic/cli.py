import json
import re
import sys
from datetime import datetime

import click
from dateutil.relativedelta import relativedelta

from landsat_cogeo_mosaic.mosaic import features_to_mosaicJSON, StreamingParser
from landsat_cogeo_mosaic.stac import fetch_sat_api
from landsat_cogeo_mosaic.util import filter_season


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
        if count % 1000 == 0:
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


main.add_command(search)
main.add_command(create)
main.add_command(create_streaming)

if __name__ == '__main__':
    main()
