from typing import Dict
from datetime import datetime
import sqlite3
from dateutil.parser import parse as date_parse


def find_records(sqlite_path, **kwargs):
    # Setting the row_factory attribute allows for creating dict-like objects
    # https://stackoverflow.com/a/18788347
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    query_str = generate_query(**kwargs)
    return run_query(conn, query_str)


def generate_query(
        pathrow,
        table_name='scene_list',
        max_cloud=10,
        min_date=None,
        max_date=None,
        preference=None,
        tier_preference=['T1', 'T2', 'RT'],
        closest_to_date=None,
        limit=1,
        columns=['productId']):
    """Generate query for SQLite

    Technically you should use ? in query strings that will be interpolated by
    the DB API to avoid SQL injection attacks, but since this code is only run
    locally I'll just use string interpolation.
    """

    column_str = ', '.join(set(columns))
    execute_str = f'SELECT {column_str} FROM {table_name} WHERE '

    # Where clause
    where_clause = []
    where_clause.append(f'pathrow = "{pathrow}"')

    if min_date:
        where_clause.append(f'DATE(acquisitionDate) >= DATE("{min_date}")')

    if max_date:
        where_clause.append(f'DATE(acquisitionDate) <= DATE("{max_date}")')

    if max_cloud:
        where_clause.append(f'cloudCover <= {max_cloud}')

    execute_str += ' AND '.join(where_clause)

    # Order clause
    order_clause = []
    if tier_preference:
        # https://stackoverflow.com/a/3303876
        # `tier` is name of column
        s = 'CASE tier '
        s += ' '.join([
            f'WHEN "{val}" THEN {ind}'
            for ind, val in enumerate(tier_preference)
        ])
        s += ' END'
        order_clause.append(s)

    if closest_to_date:
        closest_to_date = coerce_to_datetime(closest_to_date)
        closest_to_date_timestamp = round(closest_to_date.timestamp())
        order_clause.append(
            f"abs(strftime('%s', datetime({closest_to_date_timestamp}, 'unixepoch')) - strftime('%s', acquisitionDate))"
        )

    if order_clause:
        execute_str += f" ORDER BY {', '.join(order_clause)}"

    if order_clause and limit:
        execute_str += f' LIMIT {limit}'

    execute_str += ';'
    return execute_str


def run_query(conn, query_str: str) -> Dict:
    """Run SQLite query on database
    Args:
        - conn: SQLite connection
        - query_str: string to run in SQLite
    """
    cursor = conn.execute(query_str)
    for row in cursor:
        yield {k: row[k] for k in row.keys()}


def coerce_to_datetime(dt):
    if isinstance(dt, datetime):
        return dt

    return date_parse(dt)