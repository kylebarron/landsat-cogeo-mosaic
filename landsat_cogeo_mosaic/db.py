import sqlite3
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Union

from dateutil.parser import parse as date_parse


def find_records(sqlite_path, **kwargs) -> Iterable[Dict]:
    """Find records for query from sqlite

    Args:
        - pathrow: 6-character pathrow
        - table_name: name of table in sqlite. Default 'scene_list'
        - max_cloud: maximum cloud cover percent. Range from 0-100.
        - min_date: min date as str: 'YYYY-MM-DD'
        - max_date: max date as str: 'YYYY-MM-DD'
        - preference: preference for selecting pathrow
        - tier_preference: preference of tiers, by default ['T1', 'T2', 'RT']
        - closest_to_date: datetime used for comparisons when preference is closest-to-date. Must be datetime or str of format YYYY-MM-DD
        - limit: Max number of results to return
        - columns: columns to return

    Returns:
        iterator that creates dict records
    """
    # Setting the row_factory attribute allows for creating dict-like objects
    # https://stackoverflow.com/a/18788347
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    query_str = generate_query(**kwargs)
    return run_query(conn, query_str)


def generate_query(
        pathrow,
        table_name: str = 'scene_list',
        max_cloud: float = 10,
        min_date: str = None,
        max_date: str = None,
        sort_preference: Optional[str] = None,
        tier_preference: List[str] = ['T1', 'T2', 'RT'],
        closest_to_date: Optional[Union[datetime, str]] = None,
        limit: int = 1,
        columns: List[str] = ['productId']) -> str:
    """Generate query for SQLite

    Technically you should use ? in query strings that will be interpolated by
    the DB API to avoid SQL injection attacks, but since this code is only run
    locally I'll just use string interpolation.

    Args:
        - pathrow: 6-character pathrow
        - table_name: name of table in sqlite. Default 'scene_list'
        - max_cloud: maximum cloud cover percent. Range from 0-100.
        - min_date: min date as str: 'YYYY-MM-DD'
        - max_date: max date as str: 'YYYY-MM-DD'
        - sort_preference: preference for selecting pathrow
        - tier_preference: preference of tiers, by default ['T1', 'T2', 'RT']
        - closest_to_date: datetime used for comparisons when preference is closest-to-date. Must be datetime or str of format YYYY-MM-DD
        - limit: Max number of results to return
        - columns: columns to return

    Returns:
        string with query
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

    if sort_preference == 'closest-to-date':
        closest_to_date = coerce_to_datetime(closest_to_date)
        closest_to_date_timestamp = round(closest_to_date.timestamp())
        order_clause.append(
            f"abs(strftime('%s', datetime({closest_to_date_timestamp}, 'unixepoch')) - strftime('%s', acquisitionDate))"
        )
    elif sort_preference == 'oldest':
        # Set very early "closest_to_date"
        closest_to_date = coerce_to_datetime('1970-01-01')
        closest_to_date_timestamp = round(closest_to_date.timestamp())
        order_clause.append(
            f"abs(strftime('%s', datetime({closest_to_date_timestamp}, 'unixepoch')) - strftime('%s', acquisitionDate))"
        )
    elif sort_preference == 'newest':
        # Set "closest_to_date" in the future
        closest_to_date = coerce_to_datetime('2050-01-01')
        closest_to_date_timestamp = round(closest_to_date.timestamp())
        order_clause.append(
            f"abs(strftime('%s', datetime({closest_to_date_timestamp}, 'unixepoch')) - strftime('%s', acquisitionDate))"
        )
    elif sort_preference == 'min-cloud':
        order_clause.append('cloudCover')

    else:
        raise ValueError('sort_preference not supported')

    # Sort by tier after sorting by preference
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
