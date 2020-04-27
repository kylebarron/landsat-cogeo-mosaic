# landsat-cogeo-mosaic

Tools to create MosaicJSONs for Landsat imagery.

## Overview

A [MosaicJSON](https://github.com/developmentseed/mosaicjson-spec) is a file
that defines how to combine multiple (satellite) imagery assets across time and
space into a web mercator tile. This repository is designed to be used to create
such files, so that they can be used for on-the-fly satellite tile generation,
such as with
[`awspds-mosaic`](https://github.com/developmentseed/awspds-mosaic).

## Install

```bash
git clone https://github.com/kylebarron/landsat-cogeo-mosaic
cd landsat-cogeo-mosaic
pip install .
```

For other parts below, you may need SQLite installed.

## Create Mosaics

In order to create the mosaic, you need the metadata on where and when Landsat
took images, and also the cloud cover of each image. There are a couple ways to
get this data. One is to ping the [Sat
API](https://sat-utils.github.io/sat-api/) hosted by Development Seed. This
allows you to find the metadata from specific regions and times, and is easier
when you're creating a mosaic for a specific region.

Alternatively, for large mosaics it's easier to do bulk processing. In order to
not overload the Sat API, I download a file from AWS with metadata from all
images.

### Global -- Bulk processing

First, I'll describe the bulk approach. Use this when you want a large
MosaicJSON, such as one spanning the entire globe.

#### Download

Make sure you're in the top-level folder of the repository. Then download the
metadata from S3. This is about a 500MB file (uncompressed) as of April 2020,
but it grows over time as new scenes are added.

```bash
aws s3 cp s3://landsat-pds/c1/L8/scene_list.gz data/
gzip -c data/scene_list.gz > data/scene_list
```

#### Import into SQLite

I use SQLite to speed up processing with lots of data. The `csv_import.sql`
script creates a new table, imports the csv file, creates a couple new columns,
and creates indices. Note that the script must be run from the directory where
the file `scene_list` from above is stored.

```bash
cd data/
sqlite3 scene_list.db < ../scripts/csv_import.sql
cd -
```

The database takes up about 750MB, including indices.

#### Create mosaic

```bash
landsat-cogeo-mosaic create-from-db \
    `# Path to the sqlite database file` \
    --sqlite-path data/scene_list.db \
    `# Path to the path-row geometry file. This is stored in Git` \
    --pathrow-xw data/pr2coords.json \
    `# Min zoom of mosaic, 7 is a good default for Landsat` \
    --min-zoom 7 \
    `# Max zoom of mosaic, 12 is a good default for Landsat` \
    --max-zoom 12 \
    `# Zoom level to use for quadkeys` \
    --quadkey-zoom 8 \
    `# Maximum cloud cover. This means 5%` \
    --max-cloud 5 \
    `# Preference for choosing the asset for a tile` \
    --preference closest-to-date \
    `# Date used for comparisons when preference is closest-to-date` \
    --closest-to-date '2018-04-01' \
    > out_mosaic.json
```

### Smaller regions

Download metadata from a STAC API. This outputs newline-delimited GeoJSON
features. By default this searches the metdata of the Landsat 8 collection using
an API instance hosted by Development Seed.

```bash
landsat-cogeo-mosaic search \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --max-cloud 10 \
    --min-date 2019-01-01 \
    --max-date 2020-01-01 \
    --season summer > features.json
```

Note that if the query would return more than 10,000 scenes, an error is
produced, as 10,000 is the [max the API can
return](https://github.com/sat-utils/sat-api/issues/225). However, since the
output is _newline-delimited_ GeoJSON, you can append features easily:

```bash
landsat-cogeo-mosaic search ... >> features.json
```

Create a MosaicJSON from those features

```bash
landsat-cogeo-mosaic create \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --min-zoom 7 \
    --max-zoom 12 \
    --quadkey-zoom 8 \
    --optimized-selection \
    --season summer \
    features.json > mosaic.json
```

Now the `mosaic.json` is a file you can use with the rest of the MosaicJSON
ecosystem.

## API

### Download STAC Metadata

```
Usage: landsat-cogeo-mosaic search [OPTIONS]

  Retrieve features from sat-api

Options:
  -b, --bounds TEXT               Comma-separated bounding box: "west, south,
                                  east, north"  [required]

  --min-cloud FLOAT               Minimum cloud percentage  [default: 0]
  --max-cloud FLOAT               Maximum cloud percentage  [default: 100]
  --min-date TEXT                 Minimum date  [default: 2013-01-01]
  --max-date TEXT                 Maximum date, inclusive  [default:
                                  2020-04-19]

  --period [day|week|month|year]  Time period. If provided, overwrites `max-
                                  date` with the given period after `min-
                                  date`.

  --period-qty INTEGER            Number of periods to apply after `min-date`.
                                  Only applies if `period` is provided.
                                  [default: 1]

  --season [spring|summer|autumn|winter]
                                  Season, can provide multiple
  --stac-collection-limit INTEGER
                                  Limits the number of items per page returned
                                  by sat-api.  [default: 500]

  --help                          Show this message and exit.
```

### Create MosaicJSON

```
Usage: landsat-cogeo-mosaic create [OPTIONS] LINES

  Create MosaicJSON from STAC features

Options:
  --min-zoom INTEGER              Minimum zoom  [default: 7]
  --max-zoom INTEGER              Maximum zoom  [default: 12]
  --quadkey-zoom INTEGER          Zoom level used for quadkeys in MosaicJSON.
                                  Lower value means more assets per tile, but
                                  a smaller MosaicJSON file. Higher value
                                  means fewer assets per tile but a larger
                                  MosaicJSON file. Must be between min zoom
                                  and max zoom, inclusive.
  -b, --bounds TEXT               Comma-separated bounding box: "west, south,
                                  east, north"
  --optimized-selection / --no-optimized-selection
                                  Attempt to optimize assets in tile. This
                                  optimization implies that 1) assets will be
                                  ordered in the MosaicJSON in order of cover
                                  of the entire tile and 2) the total number
                                  of assets is kept to a minimum.  [default:
                                  True]
  --season [spring|summer|autumn|winter]
                                  Season, can provide multiple
  --help                          Show this message and exit.
```

### Create MosaicJSON by streaming

If you have a large MosaicJSON, you may not want to load it all into memory at
once. This streams one feature at a time, and so is low on memory usage.

```
Usage: landsat-cogeo-mosaic create-streaming [OPTIONS] FILE

  Create MosaicJSON from STAC features without holding in memory

Options:
  --min-zoom INTEGER              Minimum zoom  [default: 7]
  --max-zoom INTEGER              Maximum zoom  [default: 12]
  --quadkey-zoom INTEGER          Zoom level used for quadkeys in MosaicJSON.
                                  Lower value means more assets per tile, but
                                  a smaller MosaicJSON file. Higher value
                                  means fewer assets per tile but a larger
                                  MosaicJSON file. Must be between min zoom
                                  and max zoom, inclusive.

  -b, --bounds TEXT               Comma-separated bounding box: "west, south,
                                  east, north"

  --optimized-selection / --no-optimized-selection
                                  Optimize assets in tile. Only a single asset
                                  per path-row will be included in each
                                  quadkey. Note that there will usually be
                                  multiple path-rows within a single quadkey
                                  tile.  [default: True]

  -p, --preference [newest|oldest]
                                  Method for choosing scenes in the same path-
                                  row  [default: newest]

  --season [spring|summer|autumn|winter]
                                  Season, can provide multiple
  --help                          Show this message and exit.
```

### Create MosaicJSON from SQLite

```
Usage: landsat-cogeo-mosaic create-from-db [OPTIONS]

Options:
  --sqlite-path PATH              Path to sqlite3 db generated from scene_list
                                  [required]

  --pathrow-xw PATH               Path to pathrow2coords crosswalk  [required]
  -b, --bounds TEXT               Comma-separated bounding box: "west, south,
                                  east, north"

  --max-cloud FLOAT               Maximum cloud percentage  [default: 100]
  --min-date TEXT                 Minimum date  [default: 2013-01-01]
  --max-date TEXT                 Maximum date, inclusive  [default:
                                  2020-04-26]

  --min-zoom INTEGER              Minimum zoom  [default: 7]
  --max-zoom INTEGER              Maximum zoom  [default: 12]
  --quadkey-zoom INTEGER          Zoom level used for quadkeys in MosaicJSON.
                                  Lower value means more assets per tile, but
                                  a smaller MosaicJSON file. Higher value
                                  means fewer assets per tile but a larger
                                  MosaicJSON file. Must be between min zoom
                                  and max zoom, inclusive.

  --optimized-selection / --no-optimized-selection
                                  Optimize assets in tile. Only a single asset
                                  per path-row will be included in each
                                  quadkey. Note that there will usually be
                                  multiple path-rows within a single quadkey
                                  tile.  [default: True]

  -p, --preference [closest-to-date]
                                  Method for choosing scenes in the same path-
                                  row  [default: closest-to-date]

  --closest-to-date TEXT          Date used for comparisons when preference is
                                  closest-to-date. Format must be YYYY-MM-DD

  --help                          Show this message and exit.
```

### Validate MosaicJSON

Find missing quadkeys within `bounds` that are over land. The `shp-path` expects
to point to the unzipped 10m [land polygons vector dataset
shapefile](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/)
from Natural Earth.

```
Usage: landsat-cogeo-mosaic missing-quadkeys [OPTIONS] FILE

  Find quadkeys over land missing from mosaic

Options:
  --shp-path PATH             path to Natural Earth shapefile of land
                              boundaries  [required]

  -b, --bounds TEXT           force bounding box: "west, south, east, north"
  --simplify / --no-simplify  Reduce size of the output tileset as much as
                              possible by merging leaves into parents.
                              [default: True]

  --help                      Show this message and exit.
```

## Example

### Imagery by season (small-ish region)

This example uses the non-bulk approach described above.

I'm interested in creating a seamless cloudless mosaicJSON of imagery for the
continental U.S. Some areas very often have clouds, so I first download metadata
for all low-cloud Landsat imagery from 2013-2020, and then merge them.

```bash
rm features.geojson
for year in {2013..2019}; do
    next_year=$((year + 1))
    landsat-cogeo-mosaic search \
        --bounds '-127.64,23.92,-64.82,52.72' \
        --max-cloud 5 \
        --min-date "${year}-01-01" \
        --max-date "${next_year}-01-01" >> features.geojson
done
```

Now `features.geojson` is a newline-delimited GeoJSON where the geometries are
polygons indicating the extent of the scene.

Landsat 8 took 22,000 images of the continental U.S. between 2013 and 2020 where
less than 5% of the image was clouds!

```
> wc -l features.geojson
   22081 features.geojson
```

Note that currently `features.geojson` cover year-round scenes. Let's see how
many are in December, January, and February, using `jq` and my [Kepler.gl
cli](https://github.com/kylebarron/keplergl_cli).

```bash
cat features.geojson | jq -c 'if .properties.datetime | .[0:19] + "Z" | fromdate | strftime("%m") | tonumber | select(. <= 2 or . >= 12) then . else empty end' > temp.geojson
kepler temp.geojson
```

![image](https://user-images.githubusercontent.com/15164633/78316235-660ec700-751c-11ea-8378-145a645868e0.png)

Well, the Northwest and Northeast are both cloudy pretty often in the winter. In
some places, there wasn't a single pass of Landsat from 2013-2020 for much of
those areas that caught imagery without clouds! In contrast, for much of the
Southwest, there were many cloudless days.

How about summer months between June and August?

```bash
cat features.geojson | jq -c 'if .properties.datetime | .[0:19] + "Z" | fromdate | strftime("%m") | tonumber | select(. >= 6 and . <= 8) then . else empty end' > temp.geojson
kepler temp.geojson
```

![image](https://user-images.githubusercontent.com/15164633/78316070-f3055080-751b-11ea-8e7c-a2985bab451c.png)

Now the Southeast is cloudy! You really can't win can you?

For now, just create a non-winter one:

```bash
landsat-cogeo-mosaic create \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --min-zoom 7 \
    --max-zoom 12 \
    --quadkey-zoom 8 \
    --optimized-selection \
    --season summer \
    --season spring \
    --season autumn \
    features.geojson > mosaic.json
```

### Worldwide basemaps

I'm interested in creating a global, cloudless basemap for each season.

```bash
mkdir -p data/out/
for year in {2014..2019}; do
    for month in "02" "05" "08" "11"; do
        echo "${year}-${month}"
        landsat-cogeo-mosaic create-from-db \
            --sqlite-path data/scene_list.db \
            --pathrow-xw data/pr2coords.json \
            --min-zoom 7 \
            --max-zoom 12 \
            --quadkey-zoom 8 \
            --max-cloud 5 \
            --preference closest-to-date \
            --closest-to-date "$year-$month-01" \
            > "data/out/mosaic_$year_$month_01.json"
    done
done
```

Then include a couple in 2013 and 2020

```bash
export year=2013
for month in "05" "08" "11"; do
    echo "${year}-${month}"
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-xw data/pr2coords.json \
        --min-zoom 7 \
        --max-zoom 12 \
        --quadkey-zoom 8 \
        --max-cloud 5 \
        --preference closest-to-date \
        --closest-to-date "$year-$month-01" \
        > "data/out/mosaic_$year_$month_01.json"
done
export year=2020
for month in "02" "05"; do
    echo "${year}-${month}"
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-xw data/pr2coords.json \
        --min-zoom 7 \
        --max-zoom 12 \
        --quadkey-zoom 8 \
        --max-cloud 5 \
        --preference closest-to-date \
        --closest-to-date "$year-$month-01" \
        > "data/out/mosaic_$year_$month_01.json"
done
```

For the May 2020, I'll also use that as the base for my [auto-updating landsat
script](https://github.com/kylebarron/landsat-mosaic-latest), which updates a
DynamoDB table as SNS notifications of new Landsat assets come in.
