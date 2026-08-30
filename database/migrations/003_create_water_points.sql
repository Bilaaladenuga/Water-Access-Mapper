-- Migration: Create Water Points Table
-- Core table storing all water point locations and attributes.

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

-- Spatial index for geometry queries (nearest neighbor, radius search, etc.)
CREATE INDEX IF NOT EXISTS idx_water_points_geometry
    ON water_points USING GIST(geometry);

-- Indexes for common filter queries
CREATE INDEX IF NOT EXISTS idx_water_points_status
    ON water_points(status);

CREATE INDEX IF NOT EXISTS idx_water_points_type
    ON water_points(water_type);

CREATE INDEX IF NOT EXISTS idx_water_points_source
    ON water_points(source);

-- Add comments
COMMENT ON TABLE water_points IS 'Water point locations with attributes and verification status';
COMMENT ON COLUMN water_points.water_type IS 'Type of water source: well, tap, spring, rainwater, borehole, etc.';
COMMENT ON COLUMN water_points.status IS 'Current status: operational, broken, unknown, abandoned';
COMMENT ON COLUMN water_points.source IS 'Data source: osm, government, crowdsourced';
COMMENT ON COLUMN water_points.geometry IS 'Point geometry in WGS84 (EPSG:4326)';
COMMENT ON COLUMN water_points.verified IS 'Whether this water point has been verified by a human';
