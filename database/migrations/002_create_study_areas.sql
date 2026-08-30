-- Migration: Create Study Areas Table
-- Study areas define geographic boundaries for analysis.

CREATE TABLE IF NOT EXISTS study_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Spatial index for study areas
CREATE INDEX IF NOT EXISTS idx_study_areas_geometry
    ON study_areas USING GIST(geometry);

-- Add comment
COMMENT ON TABLE study_areas IS 'Geographic boundaries defining areas of analysis for water access mapping';
COMMENT ON COLUMN study_areas.geometry IS 'Polygon geometry in WGS84 (EPSG:4326)';
