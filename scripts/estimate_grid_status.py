"""
Assign modelled operational status to GRID water points — clearly flagged.

The GRID baseline CSV contains no functionality/status attribute, so every
imported point starts as `unknown`. This script applies a documented,
deterministic assumption instead:

    ~72% of GRID points are operational, ~28% are broken.

Every row it touches is marked `status_estimated = TRUE`, so modelled values
are never confused with surveyed ones. The assumption rate is configurable.

Usage:
    # Apply the default 72% operational assumption
    python scripts/estimate_grid_status.py

    # Use a different assumption (e.g. 65%)
    python scripts/estimate_grid_status.py --operational-rate 0.65

    # Revert every modelled status back to unknown
    python scripts/estimate_grid_status.py --clear

Reads DATABASE_URL from apps/api/.env.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

SOURCE = "grid"
DEFAULT_RATE = 0.72

# Per-LGA variation around the headline rate (±4 percentage points) so the
# LGA table is not identical everywhere. Deterministic, not random.
LGA_SPREAD = 0.04


def hash_key(value: str) -> int:
    """FNV-1a hash — stable ordering across runs and machines."""
    h = 2166136261
    for ch in value:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def unit_interval(value: str) -> float:
    return hash_key(value) / 4294967296


def lga_rate(lga: str | None, base: float) -> float:
    if not lga:
        return base
    # Offset in [-1, 1] scaled by LGA_SPREAD
    offset = (hash_key(lga) % 2001 - 1000) / 1000 * LGA_SPREAD
    return min(max(base + offset, 0.35), 0.95)


def decide_status(external_id: str, lga: str | None, base: float) -> str:
    target = lga_rate(lga, base)
    roll = unit_interval(f"{external_id}:{lga or ''}")
    return "operational" if roll < target else "broken"


async def clear(conn) -> None:
    from sqlalchemy import text

    result = await conn.execute(
        text(
            """
            UPDATE water_points
            SET status = 'unknown', status_estimated = false
            WHERE status_estimated = true
            """
        )
    )
    print(f"Reverted {result.rowcount} modelled statuses to unknown")


async def apply(conn, base_rate: float) -> None:
    from sqlalchemy import text

    rows = (
        await conn.execute(
            text(
                """
                SELECT id, external_id, lga
                FROM water_points
                WHERE source = :source
                ORDER BY external_id
                """
            ),
            {"source": SOURCE},
        )
    ).fetchall()

    if not rows:
        sys.exit(f"No water points with source '{SOURCE}' found — run the import first.")

    updates = []
    per_lga: dict[str, list[int]] = {}
    for point_id, external_id, lga in rows:
        status = decide_status(str(external_id or point_id), lga, base_rate)
        updates.append({"id": point_id, "status": status})
        bucket = per_lga.setdefault(lga or "Unknown", [0, 0])
        bucket[0 if status == "operational" else 1] += 1

    statement = text(
        """
        UPDATE water_points
        SET status = :status, status_estimated = true
        WHERE id = :id
        """
    )
    for start in range(0, len(updates), 500):
        await conn.execute(statement, updates[start : start + 500])

    operational = sum(b[0] for b in per_lga.values())
    total = len(updates)
    print(f"\nApplied modelled status to {total} GRID points")
    print(f"  operational: {operational} ({operational / total * 100:.1f}%)")
    print(f"  broken:      {total - operational} ({(total - operational) / total * 100:.1f}%)")
    print("\n  By LGA:")
    for name, (op, broken) in sorted(per_lga.items(), key=lambda kv: -sum(kv[1])):
        n = op + broken
        print(f"    {name:<18} {n:>4} points · {op / n * 100:5.1f}% operational")
    print("\nAll rows are flagged status_estimated = true (no field measurement).")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a modelled operational-status assumption to GRID points."
    )
    parser.add_argument(
        "--operational-rate",
        type=float,
        default=DEFAULT_RATE,
        help=f"Share of points assumed operational (default {DEFAULT_RATE})",
    )
    parser.add_argument("--clear", action="store_true", help="Revert modelled statuses")
    args = parser.parse_args()

    if not args.clear and not (0 < args.operational_rate <= 1):
        sys.exit("--operational-rate must be between 0 and 1 (exclusive of 0)")

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
            await apply(conn, args.operational_rate)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
