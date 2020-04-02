# landsat-cogeo-mosaic
Create mosaicJSON for landsat imagery

TODO: sort by percent overlap

<!--
landsat-cogeo-mosaic create \
    --bounds '-127.64,23.92,-64.82,52.72' \
    --max-cloud 05 \
    --stac-collection-limit 500 --season summer > landsat_new_mosaic.json
 -->
```bash
landsat-cogeo-mosaic create \
    --bounds '-122.5674,46.7713,-121.2771,47.719' \
    --max-cloud 20 \
    --season summer > mosaic.json
```

<!-- ```bash
landsat-cogeo-mosaic create \
    --bounds '-81.5625,38.8225909761771,-78.75,40.97989806962013' \
    --max-cloud 20 \
    --season summer
``` -->

```
> landsat-cogeo-mosaic create --help

Usage: cli.py create [OPTIONS]

Options:
  -b, --bounds TEXT               Comma-separated bounding box: "west, south,
                                  east, north"  [required]
  --min-cloud FLOAT               Minimum cloud percentage  [default: 0]
  --max-cloud FLOAT               Maximum cloud percentage  [default: 100]
  --min-date TEXT                 Minimum date  [default: 2013-01-01]
  --max-date TEXT                 Maximum date  [default: 2020-03-19]
  --min-zoom INTEGER              Minimum zoom  [default: 7]
  --max-zoom INTEGER              Maximum zoom  [default: 12]
  --optimized-selection / --no-optimized-selection
                                  Limit one Path-Row scene per quadkey.
                                  [default: True]
  --season [spring|summer|autumn|winter]
  --maximum-items-per-tile INTEGER
                                  Limit number of scene per quadkey. Use 0 to
                                  use all items.  [default: 20]
  --stac-collection-limit INTEGER
                                  Limits the number of items returned by sat-
                                  api.
  --help                          Show this message and exit.
```


### Notes

Each `feature` response  from the sat-api looks like:
```json
{
    "type": "Feature",
    "id": "LC80130232018047LGN00",
    "bbox": [
        -70.2256,
        51.99805,
        -66.59103,
        54.17422
    ],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    -69.42426820176219,
                    54.17152972335197
                ],
                [
                    -66.59175802628593,
                    53.71148638134195
                ],
                [
                    -67.39579803217413,
                    51.998631572536034
                ],
                [
                    -70.22314041605,
                    52.46818674526225
                ],
                [
                    -69.42426820176219,
                    54.17152972335197
                ]
            ]
        ]
    },
    "properties": {
        "collection": "landsat-8-l1",
        "datetime": "2018-02-16T15:29:54.514158+00:00",
        "eo:sun_azimuth": 159.35550039,
        "eo:sun_elevation": 22.60025928,
        "eo:cloud_cover": 0,
        "eo:row": "023",
        "eo:column": "013",
        "landsat:product_id": "LC08_L1TP_013023_20180216_20180307_01_T1",
        "landsat:scene_id": "LC80130232018047LGN00",
        "landsat:processing_level": "L1TP",
        "landsat:tier": "T1",
        "eo:epsg": 32619,
        "eo:instrument": "OLI_TIRS",
        "eo:off_nadir": 0,
        "eo:platform": "landsat-8",
        "eo:bands": [
            {
                "full_width_half_max": 0.02,
                "center_wavelength": 0.44,
                "name": "B1",
                "gsd": 30,
                "common_name": "coastal"
            },
            {
                "full_width_half_max": 0.06,
                "center_wavelength": 0.48,
                "name": "B2",
                "gsd": 30,
                "common_name": "blue"
            },
            {
                "full_width_half_max": 0.06,
                "center_wavelength": 0.56,
                "name": "B3",
                "gsd": 30,
                "common_name": "green"
            },
            {
                "full_width_half_max": 0.04,
                "center_wavelength": 0.65,
                "name": "B4",
                "gsd": 30,
                "common_name": "red"
            },
            {
                "full_width_half_max": 0.03,
                "center_wavelength": 0.86,
                "name": "B5",
                "gsd": 30,
                "common_name": "nir"
            },
            {
                "full_width_half_max": 0.08,
                "center_wavelength": 1.6,
                "name": "B6",
                "gsd": 30,
                "common_name": "swir16"
            },
            {
                "full_width_half_max": 0.2,
                "center_wavelength": 2.2,
                "name": "B7",
                "gsd": 30,
                "common_name": "swir22"
            },
            {
                "full_width_half_max": 0.18,
                "center_wavelength": 0.59,
                "name": "B8",
                "gsd": 15,
                "common_name": "pan"
            },
            {
                "full_width_half_max": 0.02,
                "center_wavelength": 1.37,
                "name": "B9",
                "gsd": 30,
                "common_name": "cirrus"
            },
            {
                "full_width_half_max": 0.8,
                "center_wavelength": 10.9,
                "name": "B10",
                "gsd": 100,
                "common_name": "lwir11"
            },
            {
                "full_width_half_max": 1,
                "center_wavelength": 12,
                "name": "B11",
                "gsd": 100,
                "common_name": "lwir12"
            }
        ],
        "eo:gsd": 15
    },
    "assets": {
        "index": {
            "type": "text/html",
            "title": "HTML index page",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/index.html"
        },
        "thumbnail": {
            "title": "Thumbnail image",
            "type": "image/jpeg",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_thumb_large.jpg"
        },
        "B1": {
            "type": "image/x.geotiff",
            "eo:bands": [
                0
            ],
            "title": "Band 1 (coastal)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B1.TIF"
        },
        "B2": {
            "type": "image/x.geotiff",
            "eo:bands": [
                1
            ],
            "title": "Band 2 (blue)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B2.TIF"
        },
        "B3": {
            "type": "image/x.geotiff",
            "eo:bands": [
                2
            ],
            "title": "Band 3 (green)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B3.TIF"
        },
        "B4": {
            "type": "image/x.geotiff",
            "eo:bands": [
                3
            ],
            "title": "Band 4 (red)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B4.TIF"
        },
        "B5": {
            "type": "image/x.geotiff",
            "eo:bands": [
                4
            ],
            "title": "Band 5 (nir)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B5.TIF"
        },
        "B6": {
            "type": "image/x.geotiff",
            "eo:bands": [
                5
            ],
            "title": "Band 6 (swir16)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B6.TIF"
        },
        "B7": {
            "type": "image/x.geotiff",
            "eo:bands": [
                6
            ],
            "title": "Band 7 (swir22)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B7.TIF"
        },
        "B8": {
            "type": "image/x.geotiff",
            "eo:bands": [
                7
            ],
            "title": "Band 8 (pan)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B8.TIF"
        },
        "B9": {
            "type": "image/x.geotiff",
            "eo:bands": [
                8
            ],
            "title": "Band 9 (cirrus)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B9.TIF"
        },
        "B10": {
            "type": "image/x.geotiff",
            "eo:bands": [
                9
            ],
            "title": "Band 10 (lwir)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B10.TIF"
        },
        "B11": {
            "type": "image/x.geotiff",
            "eo:bands": [
                10
            ],
            "title": "Band 11 (lwir)",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_B11.TIF"
        },
        "ANG": {
            "title": "Angle coefficients file",
            "type": "text/plain",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_ANG.txt"
        },
        "MTL": {
            "title": "original metadata file",
            "type": "text/plain",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_MTL.txt"
        },
        "BQA": {
            "title": "Band quality data",
            "type": "image/x.geotiff",
            "href": "https://s3-us-west-2.amazonaws.com/landsat-pds/c1/L8/013/023/LC08_L1TP_013023_20180216_20180307_01_T1/LC08_L1TP_013023_20180216_20180307_01_T1_BQA.TIF"
        }
    },
    "links": [
        {
            "rel": "self",
            "href": "https://sat-api.developmentseed.org/collections/landsat-8-l1/items/LC80130232018047LGN00"
        },
        {
            "rel": "parent",
            "href": "https://sat-api.developmentseed.org/collections/landsat-8-l1"
        },
        {
            "rel": "collection",
            "href": "https://sat-api.developmentseed.org/collections/landsat-8-l1"
        },
        {
            "rel": "root",
            "href": "https://sat-api.developmentseed.org/stac"
        }
    ]
}
```
