-- Migration: Enable PostGIS Extension
-- Run this first to enable spatial operations in PostgreSQL.

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify PostGIS is installed
SELECT PostGIS_Version();
