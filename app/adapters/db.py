"""PostgreSQL database adapter using SQLAlchemy 2.0."""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings
from app.core.di import DatabaseProtocol
from app.core.errors import DatabaseError

T = TypeVar('T')


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseAdapter(DatabaseProtocol):
    """PostgreSQL database adapter."""

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the database."""
        try:
            # Convert sync URL to async URL
            database_url = settings.database_url
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self._engine = create_async_engine(
                database_url,
                echo=settings.is_dev,
                poolclass=AsyncAdaptedQueuePool,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )

            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._connected = True

        except Exception as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._engine:
            await self._engine.dispose()
            self._connected = False

    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self._session_factory:
            raise DatabaseError("Database not connected")
        return self._session_factory()

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query."""
        async with self.get_session() as session:
            try:
                result = await session.execute(text(query), params or {})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Query execution failed: {e}")

    async def execute_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Execute a SQL command (INSERT, UPDATE, DELETE)."""
        async with self.get_session() as session:
            try:
                result = await session.execute(text(command), params or {})
                await session.commit()
                return result.rowcount
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Command execution failed: {e}")

    async def create_tables(self) -> None:
        """Create all tables."""
        if not self._engine:
            raise DatabaseError("Database not connected")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables."""
        if not self._engine:
            raise DatabaseError("Database not connected")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected


# Global database instance
db_adapter = DatabaseAdapter()
