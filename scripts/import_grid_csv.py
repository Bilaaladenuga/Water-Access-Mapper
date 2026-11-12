"""
Import GRID water points CSV into PostGIS — Water Access Mapper

Converts `lagos-water-points.csv` (GRID baseline export) into the project's
water point schema, and optionally inserts it into the database.

Usage:
    # 1. Convert to a cleaned GeoJSON (no database needed)
    python scripts/import_grid_csv.py lagos-water-points.csv \
        --geojson data/processed/grid_water_points.geojson

    # 2. Convert and import into PostGIS (reads DATABASE_URL from apps/api/.env)
    python scripts/import_grid_csv.py lagos-water-points.csv --import

Notes:
    - The CSV's `lat`/`lon` columns are rounded to 2 decimals (≈1 km). The
      `X` (longitude) and `Y` (latitude) columns carry full precision, so those
      are used instead.
    - The dataset has no status or water-quality fields. Points are imported
      with status `unknown`, and no synthetic quality records are created.
    - Re-running is safe: rows are matched on `(source, external_id)`.
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from pathlib import Path

SOURCE = "grid"
DEFAULT_STATUS = "unknown"

# GRID `type_waterpoint` values -> project water types
TYPE_MAP = {
    "borehole": "borehole",
    "wells": "well",
    "well": "well",
    "waterworks": "waterworks",
    "waterwork": "waterworks",
}

# Lagos State bounding box (see geospatial/ingestion/geojson_loader.py)
STUDY_AREA_BOUNDS = {
    "min_lon": 2.7,
    "max_lon": 4.4,
    "min_lat": 6.35,
    "max_lat": 6.75,
}


def load_csv(filepath: Path) -> list[dict]:
    """Read the GRID CSV into cleaned water point records."""
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    records = []
    skipped = 0
    seen_coords = set()

    # utf-8-sig strips the BOM that Excel exports add to the header row
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        for row_number, row in enumerate(csv.DictReader(f), start=2):
            try:
                lon = float(row["X"])
                lat = float(row["Y"])
            except (TypeError, ValueError):
                print(f"  Skipped row {row_number}: invalid coordinates")
                skipped += 1
                continue

            if not (
                STUDY_AREA_BOUNDS["min_lon"] <= lon <= STUDY_AREA_BOUNDS["max_lon"]
                and STUDY_AREA_BOUNDS["min_lat"] <= lat <= STUDY_AREA_BOUNDS["max_lat"]
            ):
                print(f"  Skipped row {row_number}: outside Lagos ({lat}, {lon})")
                skipped += 1
                continue

            # The export contains no duplicate coordinates, but guard anyway
            coord_key = (round(lon, 6), round(lat, 6))
            if coord_key in seen_coords:
                print(f"  Skipped row {row_number}: duplicate coordinate {coord_key}")
                skipped += 1
                continue
            seen_coords.add(coord_key)

            raw_type = (row.get("type_waterpoint") or "").strip()
            water_type = TYPE_MAP.get(raw_type.lower(), "other")
            external_id = (row.get("OBJECTID") or "").strip()
            name = (row.get("name") or "").strip() or f"{water_type} {external_id}"

            records.append(
                {
                    "external_id": external_id,
                    "name": name,
                    "water_type": water_type,
                    "status": DEFAULT_STATUS,
                    "source": SOURCE,
                    "ward_code": (row.get("wardcode") or "").strip() or None,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "gridded_at": (row.get("report_date") or "").strip() or None,
                }
            )

    print(f"Loaded {len(records)} records ({skipped} skipped) from {filepath.name}")
    return records


def to_geojson(records: list[dict]) -> dict:
    """Convert records to a GeoJSON FeatureCollection."""
    features = []
    for record in records:
        properties = {k: v for k, v in record.items() if k not in ("latitude", "longitude")}
        properties["latitude"] = record["latitude"]
        properties["longitude"] = record["longitude"]
        features.append(
            {
                "type": "Feature",
                "id": record["external_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [record["longitude"], record["latitude"]],
                },
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def write_geojson(records: list[dict], out_path: Path) -> None:
    """Write records to a GeoJSON file for inspection or static display."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(to_geojson(records), f)
    print(f"Wrote {len(records)} features to {out_path}")


async def import_to_db(records: list[dict]) -> None:
    """Insert records into PostGIS. Requires migration 005."""
    from dotenv import load_dotenv
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    load_dotenv(Path(__file__).parent.parent / "apps" / "api" / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        sys.exit(
            "DATABASE_URL is not set. Create apps/api/.env from .env.example first."
        )

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    database_url = database_url.replace("sslmode=require", "ssl=require")
    if "channel_binding" in database_url:
        database_url = database_url.replace("&channel_binding=require", "")

    engine = create_async_engine(
        database_url, echo=False, connect_args={"statement_cache_size": 0}
    )

    insert_sql = text(
        """
        INSERT INTO water_points
            (name, water_type, status, source, external_id, ward_code,
             latitude, longitude, geometry)
        VALUES
            (:name, :water_type, :status, :source, :external_id, :ward_code,
             CAST(:lat AS DOUBLE PRECISION),
             CAST(:lon AS DOUBLE PRECISION),
             ST_SetSRID(ST_MakePoint(CAST(:lon AS DOUBLE PRECISION),
                                     CAST(:lat AS DOUBLE PRECISION)), 4326))
        ON CONFLICT (source, external_id) DO NOTHING
        """
    )

    async with engine.begin() as conn:
        columns = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'water_points'
                  AND column_name IN ('external_id', 'ward_code')
                """
            )
        )
        present = {row[0] for row in columns.fetchall()}
        missing = {"external_id", "ward_code"} - present
        if missing:
            sys.exit(
                "water_points is missing columns: "
                f"{', '.join(sorted(missing))}. "
                "Run database/migrations/005_add_grid_fields.sql first."
            )

        before = await conn.scalar(
            text("SELECT COUNT(*) FROM water_points WHERE source = :source"),
            {"source": SOURCE},
        )

        for batch_start in range(0, len(records), 500):
            batch = records[batch_start : batch_start + 500]
            await conn.execute(
                insert_sql,
                [
                    {
                        "name": r["name"],
                        "water_type": r["water_type"],
                        "status": r["status"],
                        "source": r["source"],
                        "external_id": r["external_id"],
                        "ward_code": r["ward_code"],
                        "lat": r["latitude"],
                        "lon": r["longitude"],
                    }
                    for r in batch
                ],
            )
            print(f"  Batch {batch_start // 500 + 1}: {len(batch)} rows processed")

        after = await conn.scalar(
            text("SELECT COUNT(*) FROM water_points WHERE source = :source"),
            {"source": SOURCE},
        )

    inserted = after - before
    await engine.dispose()

    print("\nImport summary:")
    print(f"  Records in file: {len(records)}")
    print(f"  Newly inserted:  {inserted}")
    print(f"  Total {SOURCE} points in database: {after}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the GRID Lagos water points CSV and/or import it into PostGIS."
    )
    parser.add_argument("csv", type=Path, help="Path to lagos-water-points.csv")
    parser.add_argument(
        "--geojson",
        type=Path,
        help="Write a cleaned GeoJSON FeatureCollection to this path",
    )
    parser.add_argument(
        "--import", dest="do_import", action="store_true", help="Insert into PostGIS"
    )
    args = parser.parse_args()

    records = load_csv(args.csv)

    if args.geojson:
        write_geojson(records, args.geojson)

    if args.do_import:
        asyncio.run(import_to_db(records))

    if not args.geojson and not args.do_import:
        print("Nothing to do — pass --geojson and/or --import")


if __name__ == "__main__":
    main()
