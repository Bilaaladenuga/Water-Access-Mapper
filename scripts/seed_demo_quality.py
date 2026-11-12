"""
Seed simulated water quality results for GRID water points — demo only.

The GRID baseline CSV contains no water quality measurements. This script
generates deterministic, plausible test results for the imported GRID points so
the quality views can be demonstrated end to end.

Every row is marked `is_simulated = TRUE`, attributed to `simulated-demo`, and
carries the note "SIMULATED — synthetic demo data, not a field measurement".
None of these values may be presented as real monitoring data.

Usage:
    # Generate (or regenerate) one simulated test per GRID point
    python scripts/seed_demo_quality.py

    # Remove every simulated record, leaving real tests untouched
    python scripts/seed_demo_quality.py --clear

Reads DATABASE_URL from apps/api/.env.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE = "grid"
NOTE = "SIMULATED — synthetic demo data, not a field measurement"
TESTED_BY = "simulated-demo"

# Share of results per water type: (good, moderate, poor)
TYPE_MIX = {
    "waterworks": (0.68, 0.24, 0.08),
    "borehole": (0.52, 0.32, 0.16),
    "well": (0.33, 0.34, 0.33),
    "spring": (0.40, 0.35, 0.25),
    "tap": (0.60, 0.28, 0.12),
    "other": (0.45, 0.35, 0.20),
}


def mulberry32(seed: int):
    """Small deterministic PRNG so re-runs produce identical values."""
    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = (t ^ (t >> 15)) * (1 | t) & 0xFFFFFFFF
        t = (t + (t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def hash_key(key: str) -> int:
    """FNV-1a hash, used to seed the PRNG per water point."""
    h = 2166136261
    for ch in key:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def pick_bucket(rand, water_type: str, lga: str | None) -> str:
    good, moderate, _poor = TYPE_MIX.get(water_type, TYPE_MIX["other"])
    # Small deterministic LGA bias so per-LGA averages differ realistically
    if lga:
        good += (hash_key(lga) % 17 - 8) / 100
    good = min(max(good, 0.15), 0.85)
    roll = rand()
    if roll < good:
        return "good"
    if roll < good + moderate:
        return "moderate"
    return "poor"


def generate_metrics(rand, bucket: str) -> tuple[float, float, int]:
    """Return (ph, turbidity, coliform) guaranteed to produce `bucket`."""
    if bucket == "good":
        return (
            round(7.02 + rand() * 0.93, 2),
            round(0.3 + rand() * 4.4, 1),
            int(rand() * 44),
        )

    if bucket == "moderate":
        defect = int(rand() * 3)
        if defect == 0:  # pH slightly out of the ideal band
            ph = 6.55 + rand() * 0.4 if rand() < 0.5 else 8.05 + rand() * 0.35
            return round(ph, 2), round(0.5 + rand() * 4.0, 1), int(rand() * 45)
        if defect == 1:  # turbidity above 5 NTU
            return round(7.05 + rand() * 0.85, 2), round(5.2 + rand() * 4.3, 1), int(rand() * 45)
        return round(7.05 + rand() * 0.85, 2), round(0.5 + rand() * 4.0, 1), 55 + int(rand() * 35)

    defect = int(rand() * 3)
    if defect == 0:  # pH outside 6.5–8.5
        ph = 5.6 + rand() * 0.8 if rand() < 0.5 else 8.6 + rand() * 0.8
        return round(ph, 2), round(0.5 + rand() * 4.0, 1), int(rand() * 45)
    if defect == 1:  # turbidity well above 10 NTU
        return round(7.05 + rand() * 0.85, 2), round(11.0 + rand() * 24.0, 1), int(rand() * 45)
    return round(7.05 + rand() * 0.85, 2), round(0.5 + rand() * 4.0, 1), 120 + int(rand() * 530)


def rate(ph: float, turbidity: float, coliform: int) -> str:
    """Same WHO thresholds as apps/api/routes/water_quality.py."""
    if ph < 6.5 or ph > 8.5 or coliform > 100 or turbidity > 10:
        return "poor"
    if ph < 7.0 or ph > 8.0 or coliform > 50 or turbidity > 5:
        return "moderate"
    return "good"


async def clear(conn) -> None:
    from sqlalchemy import text

    result = await conn.execute(
        text("DELETE FROM water_quality WHERE is_simulated = true")
    )
    print(f"Deleted {result.rowcount} simulated quality records")


async def seed(conn) -> None:
    from sqlalchemy import text

    points = await conn.execute(
        text(
            """
            SELECT id, external_id, water_type, lga
            FROM water_points
            WHERE source = :source
            ORDER BY external_id
            """
        ),
        {"source": SOURCE},
    )
    rows = points.fetchall()
    if not rows:
        sys.exit(f"No water points with source '{SOURCE}' found — run the import first.")

    # Replace previous simulated values for this source, keep real tests
    deleted = await conn.execute(
        text(
            """
            DELETE FROM water_quality
            WHERE is_simulated = true
              AND water_point_id IN (SELECT id FROM water_points WHERE source = :source)
            """
        ),
        {"source": SOURCE},
    )
    print(f"Removed {deleted.rowcount} previous simulated records")

    now = datetime.now(timezone.utc)
    records = []
    status_counts = {"good": 0, "moderate": 0, "poor": 0}

    for point_id, external_id, water_type, lga in rows:
        rand = mulberry32(hash_key(external_id or str(point_id)))
        bucket = pick_bucket(rand, water_type, lga)
        ph, turbidity, coliform = generate_metrics(rand, bucket)
        status = rate(ph, turbidity, coliform)
        status_counts[status] += 1
        tested_at = now - timedelta(days=10 + int(rand() * 520), hours=int(rand() * 24))
        records.append(
            {
                "water_point_id": point_id,
                "test_date": tested_at,
                "ph": ph,
                "turbidity": turbidity,
                "coliform": coliform,
                "conductivity": round(120 + rand() * 780, 1),
                "temperature": round(24 + rand() * 6, 1),
                "status": status,
                "notes": NOTE,
                "tested_by": TESTED_BY,
            }
        )

    insert = text(
        """
        INSERT INTO water_quality
            (water_point_id, test_date, ph, turbidity, coliform_count,
             conductivity, temperature, status, notes, tested_by, is_simulated)
        VALUES
            (:water_point_id, :test_date, :ph, :turbidity, :coliform,
             :conductivity, :temperature, :status, :notes, :tested_by, true)
        """
    )

    for start in range(0, len(records), 500):
        await conn.execute(insert, records[start : start + 500])

    lgas = len({row[3] for row in rows if row[3]})
    print(f"\nSeeded {len(records)} simulated tests across {lgas} LGAs")
    print(
        "  good: {good} · moderate: {moderate} · poor: {poor}".format(**status_counts)
    )
    print("\nAll records are flagged is_simulated = true and labelled in notes.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed simulated quality data for GRID points.")
    parser.add_argument("--clear", action="store_true", help="Delete simulated records only")
    args = parser.parse_args()

    from dotenv import load_dotenv
    from sqlalchemy.ext.asyncio import create_async_engine

    load_dotenv(Path(__file__).parent.parent / "apps" / "api" / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        sys.exit("DATABASE_URL is not set. Create apps/api/.env from .env.example first.")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    database_url = database_url.replace("sslmode=require", "ssl=require")
    if "channel_binding" in database_url:
        database_url = database_url.replace("&channel_binding=require", "")

    engine = create_async_engine(
        database_url, echo=False, connect_args={"statement_cache_size": 0}
    )
    async with engine.begin() as conn:
        if args.clear:
            await clear(conn)
        else:
            await seed(conn)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
