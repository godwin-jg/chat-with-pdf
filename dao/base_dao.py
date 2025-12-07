"""
Base DAO with common database operations.
"""
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from dao.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseDAO(Generic[ModelType]):
    """Base DAO class with common CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        """
        Initialize DAO with a model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, id: str, load_relationships: bool = False
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            session: Database session
            id: Record ID (UUID)
            load_relationships: Whether to eagerly load relationships

        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        if load_relationships:
            pass
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, **kwargs
    ) -> ModelType:
        """
        Create a new record.

        Args:
            session: Database session
            **kwargs: Model attributes

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def update(
        self, session: AsyncSession, id: str, **kwargs
    ) -> Optional[ModelType]:
        """
        Update a record by ID.

        Args:
            session: Database session
            id: Record ID
            **kwargs: Attributes to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_id(session, id)
        if not instance:
            return None

        for key, value in kwargs.items():
            setattr(instance, key, value)

        await session.flush()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, id: str) -> bool:
        """
        Delete a record by ID.

        Args:
            session: Database session
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(session, id)
        if not instance:
            return False

        await session.delete(instance)
        await session.flush()
        return True

    async def list(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        order_by=None,
    ) -> tuple[List[ModelType], int]:
        """
        List records with pagination.

        Args:
            session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Column to order by (default: created_at desc)

        Returns:
            Tuple of (list of records, total count)
        """
        if order_by is None:
            order_by = self.model.created_at.desc()

        count_query = select(func.count()).select_from(self.model)
        count_result = await session.execute(count_query)
        total = count_result.scalar()

        query = select(self.model).order_by(order_by).limit(limit).offset(offset)
        result = await session.execute(query)
        records = result.scalars().all()

        return list(records), total

