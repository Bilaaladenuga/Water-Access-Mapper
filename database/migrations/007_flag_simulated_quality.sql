-- Migration: Flag simulated water quality records
-- Demo/simulated test results must never be mistaken for field measurements.
-- Every generated row is marked here, described in `notes`, and attributed to
-- the `simulated-demo` tester.

ALTER TABLE water_quality
    ADD COLUMN IF NOT EXISTS is_simulated BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_water_quality_is_simulated
    ON water_quality(is_simulated);

COMMENT ON COLUMN water_quality.is_simulated
    IS 'TRUE for generated demo values — never real field measurements';
