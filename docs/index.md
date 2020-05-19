# landsat-cogeo-mosaic

![](assets/awspds_readme_screenshot.jpg)

`landsat-cogeo-mosaic` is a Python library and CLI to create and work with
MosaicJSON files.

[MosaicJSON][mosaicjson] is a specification that defines how to combine multiple
(satellite) imagery assets across time and space into web mercator tiles. These
files can then be used for on-the-fly satellite tile generation, using
[`awspds-mosaic`][awspds-mosaic].

[mosaicjson]: https://github.com/developmentseed/mosaicjson-spec
[awspds-mosaic]: https://github.com/developmentseed/awspds-mosaic
