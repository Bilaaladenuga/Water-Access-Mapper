"""
Import GeoJSON water points into PostGIS.

Usage:
    python scripts/import_geojson.py data/sample/water_points.geojson
"""

import json
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Load .env from apps/api
load_dotenv(Path(__file__).parent.parent / "apps" / "api" / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
if "channel_binding" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")


def load_geojson(filepath: str) -> list[dict]:
    """Load features from a GeoJSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return data.get("features", [])


async def import_water_points(filepath: str):
    """Import water points from GeoJSON into PostGIS."""
    features = load_geojson(filepath)
    print(f"Loaded {len(features)} features from {filepath}")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        inserted = 0
        skipped = 0

        for i, feature in enumerate(features):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            if len(coords) < 2:
                print(f"  Skipped feature {i}: invalid coordinates")
                skipped += 1
                continue

            name = props.get("name", f"Water Point {i}")
            water_type = props.get("water_type", "unknown")
            status = props.get("status", "operational")
            source = props.get("source", "sample")
            lon, lat = coords[0], coords[1]

            try:
                # Cast to float to avoid asyncpg type ambiguity
                lat_f = float(lat)
                lon_f = float(lon)
                await conn.execute(text("""
                    INSERT INTO water_points
                        (name, water_type, status, source, latitude, longitude, geometry)
                    VALUES
                        (:name, :water_type, :status, :source,
                         CAST(:lat AS DOUBLE PRECISION),
                         CAST(:lon AS DOUBLE PRECISION),
                         ST_SetSRID(ST_MakePoint(CAST(:lon AS DOUBLE PRECISION),
                                                 CAST(:lat AS DOUBLE PRECISION)), 4326))
                """), {
                    "name": name,
                    "water_type": water_type,
                    "status": status,
                    "source": source,
                    "lat": lat_f,
                    "lon": lon_f,
                })
                inserted += 1
                print(f"  Inserted: {name}")
            except Exception as e:
                print(f"  Error inserting {name}: {e}")
                skipped += 1

        await conn.commit()

    await engine.dispose()

    print(f"\nImport Summary:")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {len(features)}")


async def import_study_area(filepath: str):
    """Import study area from GeoJSON into PostGIS."""
    features = load_geojson(filepath)
    print(f"Loaded {len(features)} study areas from {filepath}")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        for i, feature in enumerate(features):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            name = props.get("name", f"Study Area {i}")
            description = props.get("description", "")

            try:
                geom_json = json.dumps(geom)
                await conn.execute(text("""
                    INSERT INTO study_areas (name, description, geometry)
                    VALUES (:name, :description, ST_GeomFromGeoJSON(:geometry))
                """), {
                    "name": name,
                    "description": description,
                    "geometry": geom_json,
                })
                print(f"  Inserted: {name}")
            except Exception as e:
                print(f"  Error inserting {name}: {e}")

        await conn.commit()

    await engine.dispose()
    print("Study area import complete!")


async def verify_import():
    """Verify imported data."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Count water points
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM water_points"
        ))
        wp_count = result.scalar()
        print(f"\nVerification:")
        print(f"  Water points: {wp_count}")

        # Count by status
        result = await conn.execute(text(
            "SELECT status, COUNT(*) FROM water_points GROUP BY status ORDER BY status"
        ))
        for row in result.fetchall():
            print(f"    {row[0]}: {row[1]}")

        # Count by type
        result = await conn.execute(text(
            "SELECT water_type, COUNT(*) FROM water_points GROUP BY water_type ORDER BY water_type"
        ))
        for row in result.fetchall():
            print(f"    {row[0]}: {row[1]}")

        # Count study areas
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM study_areas"
        ))
        sa_count = result.scalar()
        print(f"  Study areas: {sa_count}")

        # Sample query with PostGIS
        result = await conn.execute(text("""
            SELECT name, water_type, status,
                   ST_X(geometry) as lon, ST_Y(geometry) as lat,
                   ST_AsGeoJSON(geometry) as geojson
            FROM water_points
            LIMIT 3
        """))
        print(f"\n  Sample records:")
        for row in result.fetchall():
            print(f"    {row[0]} ({row[1]}, {row[2]}) at [{row[3]}, {row[4]}]")

    await engine.dispose()


async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/import_geojson.py water <water_points.geojson>")
        print("  python scripts/import_geojson.py area <study_area.geojson>")
        print("  python scripts/import_geojson.py verify")
        sys.exit(1)

    command = sys.argv[1]

    if command == "water":
        await import_water_points(sys.argv[2])
    elif command == "area":
        await import_study_area(sys.argv[2])
    elif command == "verify":
        await verify_import()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
