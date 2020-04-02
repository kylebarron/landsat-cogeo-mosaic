import json
import re
from datetime import datetime
from typing import List

import click

from .stac import fetch_sat_api


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
    help='Maximum date')
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
        bounds, min_cloud, max_cloud, min_date, max_date, stac_collection_limit,
        season):

    bounds = tuple(map(float, re.split(r'[, ]+', bounds)))
    if season is None:
        season = ["spring", "summer", "autumn", "winter"]

    start = datetime.strptime(min_date,
                              "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
    end = datetime.strptime(max_date, "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

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
    print(json.dumps(features, separators=(',', ':')))


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
    '--optimized-selection/--no-optimized-selection',
    is_flag=True,
    default=True,
    show_default=True,
    help='Limit one Path-Row scene per quadkey.')
@click.option(
    '--maximum-items-per-tile',
    type=int,
    default=20,
    show_default=True,
    help='Limit number of scene per quadkey. Use 0 to use all items.')
def create(min_zoom, max_zoom, optimized_selection, maximum_items_per_tile):
    pass


main.add_command(search)
main.add_command(create)

if __name__ == '__main__':
    main()
