# Sat API Example

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
