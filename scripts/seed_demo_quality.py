"""
Seed simulated water quality results for GRID water points — demo only.

The GRID baseline CSV contains no water quality measurements (verified against
the GRID3 Nigeria FeatureServer: 16 attributes, none of them quality or
functionality). This script generates deterministic, plausible test results for
the imported GRID points so the quality views can be demonstrated end to end.

CALIBRATION
-----------
Per-point values cannot come from a source that never collected them, so the
*rate of contamination* is calibrated to the published Lagos State figure:

    34% of people in Lagos State drink water contaminated with E. coli
    at source or at the household level.
    — WASHNORM 2021, Lagos State Fact Sheet
      (FMWR / NBS / UNICEF / World Bank, June 2022)

Exactly 34% of GRID points therefore receive a coliform_count > 0; the
remaining 66% receive 0, matching the app's WHO "zero tolerance" test
(`coliform_count === 0`). Among contaminated points the CFU/100ml bands follow
the WASHNORM concentration scale (1-10, 11-100, >100).

pH and turbidity are separate WHO parameters with no Lagos-specific published
distribution, so they are varied plausibly rather than calibrated.

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
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE = "grid"
NOTE = "SIMULATED — synthetic demo data, not a field measurement"
TESTED_BY = "simulated-demo"

# --- Calibration target -----------------------------------------------------
# WASHNORM 2021, Lagos State Fact Sheet: 34% E. coli contamination.
CONTAMINATION_RATE = 0.34

# Severity mix among contaminated points, on the WASHNORM E. coli scale:
# Moderate (1-10 CFU) · High (11-100 CFU) · Very High (>100 CFU)
CONTAMINATION_BANDS = (
    (1, 10, 0.45),
    (11, 100, 0.35),
    (101, 650, 0.20),
)

# Share of results per water type driving pH/turbidity severity:
# (good, moderate, poor) — no Lagos-specific published split exists for these.
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


def assign_contamination(keys: list[str]) -> set[str]:
    """Mark exactly CONTAMINATION_RATE of points as E. coli contaminated.

    Points are ranked by a stable hash and the top N are flagged, so the
    headline rate is exact rather than merely expected, and the same points
    are chosen on every run.
    """
    target = math.floor(len(keys) * CONTAMINATION_RATE)
    ranked = sorted(keys, key=lambda k: (hash_key(k), k))
    return set(ranked[:target])


def pick_ph_turbidity_bucket(rand, water_type: str, lga: str | None) -> str:
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


def generate_ph_turbidity(rand, bucket: str) -> tuple[float, float]:
    """Return (ph, turbidity) consistent with `bucket`."""
    if bucket == "good":
        return round(7.02 + rand() * 0.93, 2), round(0.3 + rand() * 4.4, 1)

    if bucket == "moderate":
        defect = int(rand() * 3)
        if defect == 0:  # pH slightly out of the ideal band
            ph = 6.55 + rand() * 0.4 if rand() < 0.5 else 8.05 + rand() * 0.35
            return round(ph, 2), round(0.5 + rand() * 4.0, 1)
        if defect == 1:  # turbidity above 5 NTU
            return round(7.05 + rand() * 0.85, 2), round(5.2 + rand() * 4.3, 1)
        return round(7.05 + rand() * 0.85, 2), round(0.5 + rand() * 4.0, 1)

    defect = int(rand() * 3)
    if defect == 0:  # pH outside 6.5-8.5
        ph = 5.6 + rand() * 0.8 if rand() < 0.5 else 8.6 + rand() * 0.8
        return round(ph, 2), round(0.5 + rand() * 4.0, 1)
    if defect == 1:  # turbidity well above 10 NTU
        return round(7.05 + rand() * 0.85, 2), round(11.0 + rand() * 24.0, 1)
    return round(7.05 + rand() * 0.85, 2), round(0.5 + rand() * 4.0, 1)


def generate_coliform(rand, contaminated: bool) -> int:
    """E. coli count: 0 when clean, WASHNORM severity band when contaminated."""
    if not contaminated:
        return 0
    roll = rand()
    cumulative = 0.0
    for low, high, share in CONTAMINATION_BANDS:
        cumulative += share
        if roll < cumulative:
            return low + int(rand() * (high - low + 1))
    low, high, _ = CONTAMINATION_BANDS[-1]
    return high


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

    # Decide contamination once, over the whole set, so the rate is exact.
    keys = [str(external_id or point_id) for point_id, external_id, _, _ in rows]
    contaminated = assign_contamination(keys)

    now = datetime.now(timezone.utc)
    records = []
    status_counts = {"good": 0, "moderate": 0, "poor": 0}
    band_counts = {"1-10": 0, "11-100": 0, ">100": 0}

    for point_id, external_id, water_type, lga in rows:
        key = str(external_id or point_id)
        rand = mulberry32(hash_key(key))
        bucket = pick_ph_turbidity_bucket(rand, water_type, lga)
        ph, turbidity = generate_ph_turbidity(rand, bucket)
        is_contaminated = key in contaminated
        coliform = generate_coliform(rand, is_contaminated)
        if is_contaminated:
            if coliform <= 10:
                band_counts["1-10"] += 1
            elif coliform <= 100:
                band_counts["11-100"] += 1
            else:
                band_counts[">100"] += 1
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

    n = len(records)
    n_contam = len(contaminated)
    lgas = len({row[3] for row in rows if row[3]})
    print(f"\nSeeded {n} simulated tests across {lgas} LGAs")
    print(
        f"  E. coli contaminated (coliform > 0): {n_contam} "
        f"({n_contam / n * 100:.1f}%) — target {CONTAMINATION_RATE * 100:.0f}% "
        f"(WASHNORM 2021, Lagos)"
    )
    print(
        "  bands: {1-10} low · {11-100} high · {>100} very high".format(**band_counts)
    )
    print(
        "  status: {good} good · {moderate} moderate · {poor} poor".format(
            **status_counts
        )
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
