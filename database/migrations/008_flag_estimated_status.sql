-- Migration: Flag modelled water point status
-- The GRID baseline CSV has no status/functionality attribute. Where a status
-- is assigned by assumption (e.g. "72% operational") rather than recorded in
-- the source, it must be distinguishable from surveyed values.

ALTER TABLE water_points
    ADD COLUMN IF NOT EXISTS status_estimated BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_water_points_status_estimated
    ON water_points(status_estimated);

COMMENT ON COLUMN water_points.status_estimated
    IS 'TRUE when status is modelled/assumed, not recorded in the source dataset';
