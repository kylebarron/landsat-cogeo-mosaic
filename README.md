# landsat-cogeo-mosaic

Tools to create MosaicJSONs for Landsat imagery.

## Overview

A [MosaicJSON][mosaicjson-spec] is a file that defines how to combine multiple
(satellite) imagery assets across time and space into a web mercator tile. This
repository is designed to be used to create such files, so that they can be used
for on-the-fly satellite tile generation, such as with
[`landsat-mosaic-tiler`][landsat-mosaic-tiler].

[mosaicjson-spec]: https://github.com/developmentseed/mosaicjson-spec
[landsat-mosaic-tiler]: https://github.com/kylebarron/landsat-mosaic-tiler

## Install

```bash
pip install landsat-cogeo-mosaic
```

For CLI commands and some modules, you need additional dependencies:

```bash
pip install 'landsat-cogeo-mosaic[cli]'
```

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
