# landsat-cogeo-mosaic

Create mosaicJSON for Landsat imagery.

## Install

```bash
pip install git+https://github.com/kylebarron/landsat-cogeo-mosaic
```

## Using

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

## Example

### Imagery by season

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

