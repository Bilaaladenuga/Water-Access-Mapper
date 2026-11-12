-- Migration: Create Water Quality Table
-- Required by apps/api/routes/water_quality.py. Each row is one test result;
-- a water point can have many results over time.

CREATE TABLE IF NOT EXISTS water_quality (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    water_point_id UUID NOT NULL REFERENCES water_points(id) ON DELETE CASCADE,
    test_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ph NUMERIC(4, 2),
    turbidity NUMERIC(8, 2),
    coliform_count INTEGER,
    conductivity NUMERIC(8, 2),
    temperature NUMERIC(5, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    notes TEXT,
    tested_by VARCHAR(255) DEFAULT 'anonymous',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_water_quality_water_point
    ON water_quality(water_point_id);

CREATE INDEX IF NOT EXISTS idx_water_quality_test_date
    ON water_quality(test_date DESC);

CREATE INDEX IF NOT EXISTS idx_water_quality_status
    ON water_quality(status);

COMMENT ON TABLE water_quality
    IS 'Water quality test results: pH, turbidity, coliform, conductivity';
COMMENT ON COLUMN water_quality.status
    IS 'Derived WHO rating: good, moderate, poor';
COMMENT ON COLUMN water_quality.tested_by
    IS 'Who performed the test (anonymous, field team, partner)';
