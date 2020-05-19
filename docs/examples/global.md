## Worldwide basemaps

I'm interested in creating a global, cloudless basemap for each season.

### Low-cloud per season

#### Spring

```bash
mkdir -p data/out/
for year in {2014..2019}; do
    min_date="${year}-03-21"
    max_date="${year}-06-21"
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-index data/pr_index.json.gz \
        --min-zoom 7 \
        --max-zoom 12 \
        --min-date "$min_date" \
        --max-date "$max_date" \
        --max-cloud 100 \
        --sort-preference min-cloud \
        > "data/out/mosaic_${year}_spring.json"
done
```

#### Summer

```bash
mkdir -p data/out/
for year in {2013..2019}; do
    min_date="${year}-06-21"
    max_date="${year}-09-21"
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-index data/pr_index.json.gz \
        --min-zoom 7 \
        --max-zoom 12 \
        --min-date "$min_date" \
        --max-date "$max_date" \
        --max-cloud 100 \
        --sort-preference min-cloud \
        > "data/out/mosaic_${year}_summer.json"
done
```

#### Fall

```bash
mkdir -p data/out/
for year in {2013..2019}; do
    min_date="${year}-09-21"
    max_date="${year}-12-21"
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-index data/pr_index.json.gz \
        --min-zoom 7 \
        --max-zoom 12 \
        --min-date "$min_date" \
        --max-date "$max_date" \
        --max-cloud 100 \
        --sort-preference min-cloud \
        > "data/out/mosaic_${year}_fall.json"
done
```

#### Winter

```bash
mkdir -p data/out/
for year in {2014..2020}; do
    min_date="$((year - 1))-12-21"
    max_date="${year}-03-21"
    # echo $min_date
    # echo $max_date
    landsat-cogeo-mosaic create-from-db \
        --sqlite-path data/scene_list.db \
        --pathrow-index data/pr_index.json.gz \
        --min-zoom 7 \
        --max-zoom 12 \
        --min-date "$min_date" \
        --max-date "$max_date" \
        --max-cloud 100 \
        --sort-preference min-cloud \
        > "data/out/mosaic_${year}_winter.json"
done
```

### Latest cloudless

I'll also create a "latest cloudless" mosaic, which I'll use as the base for my
[auto-updating landsat
script](https://github.com/kylebarron/landsat-mosaic-latest), which updates a
DynamoDB table as SNS notifications of new Landsat assets come in.

```bash
landsat-cogeo-mosaic create-from-db \
    `# Path to the sqlite database file` \
    --sqlite-path data/scene_list.db \
    `# Path to the path-row geometry file. This is stored in Git` \
    --pathrow-index data/pr_index.json.gz \
    `# Min zoom of mosaic, 7 is a good default for Landsat` \
    --min-zoom 7 \
    `# Max zoom of mosaic, 12 is a good default for Landsat` \
    --max-zoom 12 \
    `# Zoom level to use for quadkeys` \
    --quadkey-zoom 8 \
    `# Maximum cloud cover. This means 5%` \
    --max-cloud 5 \
    `# Preference for choosing the asset for a tile` \
    --sort-preference newest \
    > data/out/mosaic_latest.json
```

Then upload this mosaic to the DynamoDB table I use for the auto-updating
landsat mosaic. The [`cogeo-mosaic`][cogeo-mosaic] CLI contains a helper for uploading a MosaicJSON to a DynamoDB table.

```bash
cogeo-mosaic upload --url 'dynamodb://region/table-name' mosaic.json
```

[cogeo-mosaic]: https://github.com/developmentseed/cogeo-mosaic
