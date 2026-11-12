-- Water Access Mapper — Complete Migration
-- Run this file against your Supabase database to set up all tables.
--
-- Usage (Supabase SQL Editor):
--   Copy and paste this entire file into the SQL Editor and run it.
--
-- Usage (psql):
--   psql -f database/migrations/run_all.sql

-- ============================================================
-- 1. Enable PostGIS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- 2. Study Areas Table
-- ============================================================
CREATE TABLE IF NOT EXISTS study_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_study_areas_geometry
    ON study_areas USING GIST(geometry);

COMMENT ON TABLE study_areas IS 'Geographic boundaries defining areas of analysis';

-- ============================================================
-- 3. Water Points Table
-- ============================================================
CREATE TABLE IF NOT EXISTS water_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    water_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'operational',
    source VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geometry GEOMETRY(Point, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_water_points_geometry
    ON water_points USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_water_points_status
    ON water_points(status);
CREATE INDEX IF NOT EXISTS idx_water_points_type
    ON water_points(water_type);
CREATE INDEX IF NOT EXISTS idx_water_points_source
    ON water_points(source);

COMMENT ON TABLE water_points IS 'Water point locations with attributes and verification status';

-- ============================================================
-- 4. Water Point Reports Table
-- ============================================================
CREATE TABLE IF NOT EXISTS water_point_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    water_point_id UUID REFERENCES water_points(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    description TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geometry GEOMETRY(Point, 4326),
    reported_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_water_point_reports_geometry
    ON water_point_reports USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_water_point_reports_type
    ON water_point_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_water_point_reports_resolved
    ON water_point_reports(resolved);

COMMENT ON TABLE water_point_reports IS 'Crowdsourced reports: new points, broken points, incorrect locations';

-- ============================================================
-- 5. GRID dataset fields + stable external identifiers
-- ============================================================
ALTER TABLE water_points
    ADD COLUMN IF NOT EXISTS external_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS ward_code VARCHAR(30),
    ADD COLUMN IF NOT EXISTS lga VARCHAR(100);

CREATE UNIQUE INDEX IF NOT EXISTS idx_water_points_source_external_id
    ON water_points(source, external_id);

CREATE INDEX IF NOT EXISTS idx_water_points_ward_code
    ON water_points(ward_code);

-- ============================================================
-- 6. Water Quality Table
-- ============================================================
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

ALTER TABLE water_quality
    ADD COLUMN IF NOT EXISTS is_simulated BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_water_quality_is_simulated
    ON water_quality(is_simulated);

COMMENT ON TABLE water_quality
    IS 'Water quality test results: pH, turbidity, coliform, conductivity';
