"""
Database connection module for Water Access Mapper.

Uses SQLAlchemy with asyncpg for async PostgreSQL connections.
Supports Supabase (hosted PostgreSQL + PostGIS).
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# Convert standard PostgreSQL URL to async format
# postgresql://... → postgresql+asyncpg://...
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=5,
    max_overflow=10,
)

# Session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency that yields a database session.

    Used with FastAPI's Depends() for dependency injection.

    Example:
        @app.get("/water-points")
        async def get_water_points(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> dict:
    """
    Check database connectivity.

    Returns a dict with connection status and details.
    """
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()

            # Check PostGIS availability
            postgis_result = await conn.execute(text("SELECT PostGIS_Version()"))
            postgis_version = postgis_result.scalar()

            return {
                "status": "connected",
                "postgresql_version": version,
                "postgis_version": postgis_version,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
