"""PostgreSQL database adapter using SQLAlchemy 2.0."""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar
from datetime import datetime
from uuid import UUID

from sqlalchemy import create_engine, text, String, Integer, Float, Boolean, JSON, TIMESTAMP, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings
from app.core.di import DatabaseProtocol
from app.core.errors import DatabaseError
from app.domain.models import User, Message, Intent, Task

T = TypeVar('T')


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# SQLAlchemy models
class UserModel(Base):
    """SQLAlchemy model for User."""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="ru")
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    roles: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    last_seen: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))


class MessageModel(Base):
    """SQLAlchemy model for Message."""
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[Optional[UUID]] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    channel: Mapped[Optional[str]] = mapped_column(String(50))
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    content: Mapped[str] = mapped_column(Text)  # Large text field
    message_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    intent_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("intents.id"))

    # Relationships
    user: Mapped[UserModel] = relationship("UserModel")
    intent: Mapped[Optional["IntentModel"]] = relationship("IntentModel")


class IntentModel(Base):
    """SQLAlchemy model for Intent."""
    __tablename__ = "intents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[Optional[UUID]] = mapped_column(index=True)
    message_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("messages.id"))
    intent_type: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    slots: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), index=True)
    language: Mapped[Optional[str]] = mapped_column(String(10))
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    plan_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped[UserModel] = relationship("UserModel")
    message: Mapped[Optional[MessageModel]] = relationship("MessageModel")


class TaskModel(Base):
    """SQLAlchemy model for Task."""
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    cron_spec: Mapped[Optional[str]] = mapped_column(String(255))
    next_run: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    last_run: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserModel] = relationship("UserModel")


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
