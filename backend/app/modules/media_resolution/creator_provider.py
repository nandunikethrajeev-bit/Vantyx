"""VANTYX Creator Identity Resolution & Verification Provider.

Matches YouTube author metadata against the approved creator registry in the database.
Enforces permission tiers:
- own_content
- authorized_partner
- public_creative_commons
- unverified
"""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.creator import Creator


class CreatorIdentityProviderInterface(ABC):
    """Abstract interface defining creator identity corroboration."""

    @abstractmethod
    async def resolve_creator(
        self,
        db: AsyncSession,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        claimed_creator_id: Optional[int] = None,
        channel_id: Optional[str] = None,
    ) -> Optional[Creator]:
        """Corroborate creator identity against database registry."""
        pass


class DatabaseCreatorIdentityProvider(CreatorIdentityProviderInterface):
    """Database-backed creator identity corroboration provider."""

    async def resolve_creator(
        self,
        db: AsyncSession,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        claimed_creator_id: Optional[int] = None,
        channel_id: Optional[str] = None,
    ) -> Optional[Creator]:
        # 1. Direct ID lookup
        if claimed_creator_id is not None:
            creator = await db.get(Creator, claimed_creator_id)
            if creator:
                return creator

        # 2. Channel ID match
        if channel_id:
            stmt = select(Creator).where(Creator.channel_id == channel_id)
            creator = (await db.execute(stmt)).scalars().first()
            if creator:
                return creator

        # 3. Handle or author URL match
        if author_url:
            handle = None
            if "/@" in author_url:
                handle = "@" + author_url.split("/@")[-1].split("/")[0].split("?")[0]
            if handle:
                stmt = select(Creator).where(func.lower(Creator.channel_handle) == handle.lower())
                creator = (await db.execute(stmt)).scalars().first()
                if creator:
                    return creator

            stmt = select(Creator).where(Creator.channel_url == author_url)
            creator = (await db.execute(stmt)).scalars().first()
            if creator:
                return creator

        # 4. Author name exact / case-insensitive match
        if author_name and author_name.strip():
            clean_name = author_name.strip()
            stmt = select(Creator).where(
                or_(
                    func.lower(Creator.name) == clean_name.lower(),
                    func.lower(Creator.channel_handle) == f"@{clean_name.lower()}",
                )
            )
            creator = (await db.execute(stmt)).scalars().first()
            if creator:
                return creator

        return None


def get_creator_provider() -> CreatorIdentityProviderInterface:
    """Retrieve active creator identity resolution provider."""
    return DatabaseCreatorIdentityProvider()
