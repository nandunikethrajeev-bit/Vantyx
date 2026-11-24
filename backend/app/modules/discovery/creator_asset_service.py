"""VANTYX Creator Media Vault & Asset Association Service.

Manages:
1. Creator-connected vault status inspection (storage/creators/{id}/).
2. Explicit master asset mapping between local vault files and YouTube video IDs.
3. Media file integrity validation using FFmpeg/ffprobe.
4. Auto-synchronization with storage/asset_mappings.json for instant resolver discovery.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.creator import Creator, CreatorAssetAssociation
from app.modules.discovery.creator_oauth_service import CreatorOAuthService
from app.modules.media_resolution.media_resolver import verify_media_file_integrity
from app.schemas.discovery import (
    CreatorAssetAssociationCreate,
    CreatorAssetAssociationResponse,
    CreatorVaultStatusResponse,
)


class CreatorAssetService:
    """Manages master media assets inside creator vaults and explicit YouTube associations."""

    @classmethod
    def get_creator_vault_dir(cls, creator_id: int) -> Path:
        """Resolve and ensure the local filesystem vault directory for a creator."""
        vault_path = Path("storage/creators").resolve() / str(creator_id)
        vault_path.mkdir(parents=True, exist_ok=True)
        return vault_path

    @classmethod
    async def get_vault_status(
        cls,
        db: AsyncSession,
        creator_id: int,
    ) -> CreatorVaultStatusResponse:
        """Scan creator vault on disk and return file inventory, integrity, and associations."""
        creator = await db.get(Creator, creator_id)
        if not creator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

        vault_dir = cls.get_creator_vault_dir(creator_id)

        # Existing associations from DB
        stmt = (
            select(CreatorAssetAssociation)
            .where(CreatorAssetAssociation.creator_id == creator_id)
            .order_by(CreatorAssetAssociation.created_at.desc())
        )
        associations = (await db.execute(stmt)).scalars().all()
        assoc_by_file = {a.asset_filename: a for a in associations}

        files_info: List[Dict[str, Any]] = []
        total_size = 0
        valid_extensions = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

        if vault_dir.exists():
            for item in vault_dir.iterdir():
                if item.is_file() and item.suffix.lower() in valid_extensions:
                    size = item.stat().st_size
                    total_size += size
                    is_valid, msg, dur, _ = verify_media_file_integrity(item)
                    assoc = assoc_by_file.get(item.name)
                    files_info.append({
                        "filename": item.name,
                        "relative_path": f"storage/creators/{creator_id}/{item.name}",
                        "file_size_bytes": size,
                        "duration_seconds": dur,
                        "is_valid": is_valid,
                        "integrity_message": msg,
                        "associated_video_id": assoc.video_id if assoc else None,
                        "is_associated": assoc is not None,
                    })

        return CreatorVaultStatusResponse(
            creator_id=creator.id,
            vault_directory=f"storage/creators/{creator.id}",
            total_files=len(files_info),
            total_size_bytes=total_size,
            files=files_info,
            associations=[CreatorAssetAssociationResponse.model_validate(a) for a in associations],
        )

    @classmethod
    async def associate_asset(
        cls,
        db: AsyncSession,
        creator_id: int,
        data: CreatorAssetAssociationCreate,
    ) -> CreatorAssetAssociationResponse:
        """Explicitly link a creator vault file to a YouTube video ID."""
        creator = await db.get(Creator, creator_id)
        if not creator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

        vault_dir = cls.get_creator_vault_dir(creator_id)
        target_file = vault_dir / data.asset_filename

        # If not directly in creator vault, check data/media or general storage
        if not target_file.exists():
            alt_candidates = [
                Path(settings.MEDIA_DIR).resolve() / data.asset_filename,
                Path("data/media").resolve() / data.asset_filename,
                Path("storage").resolve() / data.asset_filename,
            ]
            for alt in alt_candidates:
                if alt.exists():
                    target_file = alt
                    break

        if not target_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Master asset '{data.asset_filename}' not found in creator vault storage/creators/{creator_id}/",
            )

        # Validate file integrity via FFmpeg
        is_valid, msg, dur, size = verify_media_file_integrity(target_file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Media file failed integrity verification: {msg}",
            )

        # Check existing association
        stmt = select(CreatorAssetAssociation).where(
            CreatorAssetAssociation.creator_id == creator_id,
            CreatorAssetAssociation.video_id == data.video_id,
        )
        existing = (await db.execute(stmt)).scalars().first()

        rel_path = f"storage/creators/{creator_id}/{target_file.name}"
        if existing:
            existing.asset_filename = target_file.name
            existing.asset_path = rel_path
            existing.file_size_bytes = size
            existing.duration_seconds = dur
            existing.is_verified = True
            existing.notes = data.notes
            record = existing
        else:
            record = CreatorAssetAssociation(
                creator_id=creator.id,
                video_id=data.video_id,
                asset_filename=target_file.name,
                asset_path=rel_path,
                file_size_bytes=size,
                duration_seconds=dur,
                is_verified=True,
                notes=data.notes,
            )
            db.add(record)

        # Sync with storage/asset_mappings.json for multi-resolver compatibility
        cls._sync_asset_mapping(data.video_id, str(target_file))

        await CreatorOAuthService.record_audit_log(
            db,
            creator_id=creator.id,
            event_type="asset_associated",
            channel_id=creator.verified_channel_id or creator.channel_id,
            details=f"Associated YouTube video '{data.video_id}' with master asset '{target_file.name}' ({dur:.1f}s, {size} bytes)",
        )
        await db.commit()
        await db.refresh(record)

        return CreatorAssetAssociationResponse.model_validate(record)

    @classmethod
    def _sync_asset_mapping(cls, video_id: str, file_path: str) -> None:
        """Sync explicit mapping to storage/asset_mappings.json."""
        mapping_path = Path("storage/asset_mappings.json").resolve()
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mappings = {}
        if mapping_path.exists():
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mappings = json.load(f)
            except Exception:
                mappings = {}
        mappings[video_id] = file_path
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2)

    @classmethod
    async def delete_association(
        cls,
        db: AsyncSession,
        creator_id: int,
        association_id: int,
    ) -> None:
        """Remove a video asset association."""
        record = await db.get(CreatorAssetAssociation, association_id)
        if not record or record.creator_id != creator_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Association not found")

        # Clean from asset_mappings.json if present
        mapping_path = Path("storage/asset_mappings.json").resolve()
        if mapping_path.exists():
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mappings = json.load(f)
                if record.video_id in mappings:
                    del mappings[record.video_id]
                    with open(mapping_path, "w", encoding="utf-8") as f:
                        json.dump(mappings, f, indent=2)
            except Exception as exc:
                logger.debug(f"Note deleting asset mapping: {exc}")

        await db.delete(record)
        await db.commit()
