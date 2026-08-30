"""
Run database migrations against Neon PostgreSQL.
Usage: python scripts/run_migration.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


DATABASE_URL = (
    "postgresql+asyncpg://neondb_owner:npg_D5vLKF1paIUu"
    "@ep-purple-mountain-zata3wty-pooler.c-2.eu-west-2.aws.neon.tech"
    "/neondb?ssl=require"
)


async def run_migration():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # 1. Enable PostGIS
        print("Enabling PostGIS...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        result = await conn.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.scalar()
        print(f"  PostGIS version: {postgis_version}")

        # 2. Create study_areas table
        print("Creating study_areas table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS study_areas (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                geometry GEOMETRY(Polygon, 4326) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_study_areas_geometry "
            "ON study_areas USING GIST(geometry)"
        ))
        print("  Done")

        # 3. Create water_points table
        print("Creating water_points table...")
        await conn.execute(text("""
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
            )
        """))
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_water_points_geometry ON water_points USING GIST(geometry)",
            "CREATE INDEX IF NOT EXISTS idx_water_points_status ON water_points(status)",
            "CREATE INDEX IF NOT EXISTS idx_water_points_type ON water_points(water_type)",
            "CREATE INDEX IF NOT EXISTS idx_water_points_source ON water_points(source)",
        ]:
            await conn.execute(text(idx))
        print("  Done")

        # 4. Create water_point_reports table
        print("Creating water_point_reports table...")
        await conn.execute(text("""
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
            )
        """))
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_water_point_reports_geometry ON water_point_reports USING GIST(geometry)",
            "CREATE INDEX IF NOT EXISTS idx_water_point_reports_type ON water_point_reports(report_type)",
        ]:
            await conn.execute(text(idx))
        print("  Done")

        # 5. Verify
        print()
        print("Verifying tables...")
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        for t in tables:
            print(f"  OK {t}")

        await conn.commit()

    await engine.dispose()
    print()
    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(run_migration())
