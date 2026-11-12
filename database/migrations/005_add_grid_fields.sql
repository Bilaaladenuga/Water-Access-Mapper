-- Migration: GRID dataset fields + stable external identifiers
-- Adds the columns needed to ingest government/GRID baseline data and to
-- re-run imports without creating duplicates.

ALTER TABLE water_points
    ADD COLUMN IF NOT EXISTS external_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS ward_code VARCHAR(30),
    ADD COLUMN IF NOT EXISTS lga VARCHAR(100);

-- One row per (source, external id); NULL external ids stay unconstrained
CREATE UNIQUE INDEX IF NOT EXISTS idx_water_points_source_external_id
    ON water_points(source, external_id);

CREATE INDEX IF NOT EXISTS idx_water_points_ward_code
    ON water_points(ward_code);

COMMENT ON COLUMN water_points.external_id
    IS 'Stable identifier from the source dataset (e.g. GRID OBJECTID)';
COMMENT ON COLUMN water_points.ward_code
    IS 'Administrative ward code from the source dataset (e.g. LASIKA08)';
COMMENT ON COLUMN water_points.lga
    IS 'Local Government Area name, if known';
