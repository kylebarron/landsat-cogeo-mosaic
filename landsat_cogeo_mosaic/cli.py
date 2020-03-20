import json
import re
from datetime import datetime
from typing import List

import click

from mosaic import create_mosaic


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
    '--season',
    multiple=True,
    default=None,
    show_default=True,
    type=click.Choice(["spring", "summer", "autumn", "winter"]))
@click.option(
    '--maximum-items-per-tile',
    type=int,
    default=20,
    show_default=True,
    help='Limit number of scene per quadkey. Use 0 to use all items.')
@click.option(
    '--stac-collection-limit',
    type=int,
    default=None,
    show_default=True,
    help='Limits the number of items returned by sat-api.')
def create(
        bounds, min_cloud, max_cloud, min_date, max_date, min_zoom, max_zoom,
        optimized_selection, maximum_items_per_tile, stac_collection_limit,
        season):

    bounds = tuple(map(float, re.split(r'[, ]+', bounds)))
    mosaic = create_mosaic(
        bounds=bounds,
        min_cloud=min_cloud,
        max_cloud=max_cloud,
        min_date=min_date,
        max_date=max_date,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        optimized_selection=optimized_selection,
        maximum_items_per_tile=maximum_items_per_tile,
        stac_collection_limit=stac_collection_limit,
        seasons=season)
    print(json.dumps(mosaic))


main.add_command(create)

if __name__ == '__main__':
    main()
