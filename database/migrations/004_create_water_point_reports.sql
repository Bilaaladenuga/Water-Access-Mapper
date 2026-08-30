-- Migration: Create Water Point Reports Table
-- For crowdsourced submissions and issue reports.

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

-- Spatial index for report locations
CREATE INDEX IF NOT EXISTS idx_water_point_reports_geometry
    ON water_point_reports USING GIST(geometry);

-- Index for filtering by report type
CREATE INDEX IF NOT EXISTS idx_water_point_reports_type
    ON water_point_reports(report_type);

-- Index for filtering by resolution status
CREATE INDEX IF NOT EXISTS idx_water_point_reports_resolved
    ON water_point_reports(resolved);

-- Add comments
COMMENT ON TABLE water_point_reports IS 'Crowdsourced reports: new points, broken points, incorrect locations';
COMMENT ON COLUMN water_point_reports.report_type IS 'Type: new_point, broken, incorrect_location, needs_repair';
COMMENT ON COLUMN water_point_reports.resolved IS 'Whether this report has been reviewed and resolved';
