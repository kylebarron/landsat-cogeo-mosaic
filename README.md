# landsat-cogeo-mosaic

Create mosaicJSON for landsat imagery

## Install

```bash
pip install git+https://github.com/kylebarron/landsat-cogeo-mosaic
```

## Using

Download metadata from a STAC API. This outputs newline-delimited GeoJSON
features.

```bash
landsat-cogeo-mosaic search \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --max-cloud 10 \
    --min-date 2019-01-01 \
    --max-date 2020-01-01 \
    --season summer > features.json
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

```
landsat-cogeo-mosaic create \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --max-cloud 05 \
    --stac-collection-limit 500 --season summer > landsat_new_mosaic.json

```

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
  --max-date TEXT                 Maximum date  [default: 2020-04-02]
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
