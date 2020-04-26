CREATE TABLE scene_list (
    productId TEXT,
    entityId TEXT,
    -- Come back to this
    acquisitionDate TEXT,
    cloudCover REAL,
    processingLevel TEXT,
    path TEXT,
    row TEXT,
    min_lat REAL,
    min_lon REAL,
    max_lat REAL,
    max_lon REAL,
    download_url TEXT
);
.mode csv
.import scene_list scene_list

-- Delete header line
DELETE FROM scene_list WHERE productId LIKE 'productId';

-- Create new pathrow column
ALTER TABLE scene_list ADD COLUMN pathrow TEXT;

-- Add values to pathrow column, left padding both `path` and `row` and concatenating
-- https://stackoverflow.com/a/6134463/7319250
UPDATE scene_list SET pathrow = substr('000' || path, -3, 3) || substr('000' || row, -3, 3);

-- Create new tier column
ALTER TABLE scene_list ADD COLUMN tier TEXT;

-- Add values to tier column, substring of productId
UPDATE scene_list SET tier = substr(productId, -2, 2);

-- Create indices
-- Not exactly sure which index is most important, but disk size isn't an issue
CREATE INDEX pathrow_idx ON scene_list(pathrow);
CREATE INDEX acquisitionDate_idx on scene_list(acquisitionDate);
CREATE INDEX cloudCover_idx on scene_list(cloudCover);
CREATE INDEX tier_idx on scene_list(tier);
