"""VANTYX Authorized Original Media Resolution Architecture.

Separates YouTube URL intake from media asset resolution according to M10.1:
1. Creator-Connected Original Media Storage (e.g. storage/creators/{id}/)
2. Creator-Provided Source Asset Mappings (storage/asset_mappings.json, media_manifest.json)
3. Authorized Cloud Storage Integrations (GCS / S3 / signed URIs)
4. Operator Local Staging Vault (data/media, storage)
5. Official Platform API Truthful Adapter (YouTube Data API v3 / OAuth boundaries)

Crucial Technical and Legal Boundaries:
- YouTube Data API v3 and OAuth provide metadata, upload, and analytics capabilities only.
  Official YouTube terms prohibit arbitrary automated video-file downloading without
  direct partner distribution contracts.
- VANTYX strictly avoids unauthorized stream scraping.
- Integrity verification runs ffprobe on all resolved media to prevent corrupted files
  from entering the video intelligence pipeline.
"""

import json
import os
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.source import VideoSource


@dataclass
class MediaResolutionResult:
    """Outcome of attempting to resolve an authorized media asset."""

    resolved: bool
    local_path: Optional[str]
    provider: str
    provider_display_name: str
    resolution_method: str  # creator_vault | asset_mapping | cloud_storage | local_staged | platform_api | unresolvable
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    status: str = "awaiting_authorized_media"  # media_ready | awaiting_authorized_media | invalid_mapping | corrupted | blocked
    message: str = ""
    blocker_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved": self.resolved,
            "local_path": self.local_path,
            "provider": self.provider,
            "provider_display_name": self.provider_display_name,
            "resolution_method": self.resolution_method,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "message": self.message,
            "blocker_detail": self.blocker_detail,
        }


def verify_media_file_integrity(file_path: Path) -> Tuple[bool, str, float, int]:
    """Verify physical existence, non-zero size, and FFmpeg/ffprobe readability.

    Returns: (is_valid, error_message, duration_seconds, file_size_bytes)
    """
    if not file_path.exists():
        return False, f"File does not exist: {file_path}", 0.0, 0
    if not file_path.is_file():
        return False, f"Path is not a regular file: {file_path}", 0.0, 0

    size = file_path.stat().st_size
    if size < 1024:
        return False, f"File is truncated or empty ({size} bytes, minimum required 1024 bytes)", 0.0, size

    # Probe with ffprobe or ffmpeg
    try:
        ffmpeg_exe = settings.get_ffmpeg_executable()
        ffprobe_exe = str(Path(ffmpeg_exe).parent / "ffprobe.exe")
        has_ffprobe = os.path.exists(ffprobe_exe) or shutil.which("ffprobe") is not None
        if not os.path.exists(ffprobe_exe) and shutil.which("ffprobe"):
            ffprobe_exe = shutil.which("ffprobe")

        if has_ffprobe:
            cmd = [
                ffprobe_exe,
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type",
                "-of", "json",
                str(file_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if res.returncode != 0:
                err = res.stderr.strip() or "ffprobe failed to parse video container"
                return False, f"Media container corrupt or unreadable: {err[:200]}", 0.0, size

            data = json.loads(res.stdout or "{}")
            duration = 0.0
            format_info = data.get("format", {})
            if "duration" in format_info:
                try:
                    duration = round(float(format_info["duration"]), 2)
                except (ValueError, TypeError):
                    duration = 0.0

            streams = data.get("streams", [])
            has_video = any(s.get("codec_type") == "video" for s in streams)
            if not has_video:
                return False, "Media file contains no readable video stream", duration, size

            return True, "Integrity verified", duration, size
        else:
            # Validate container integrity using FFmpeg directly (decode 1 second into null sink)
            cmd_err = [ffmpeg_exe, "-v", "error", "-i", str(file_path), "-t", "1", "-f", "null", "-"]
            res_err = subprocess.run(cmd_err, capture_output=True, text=True, timeout=12)
            if res_err.returncode != 0:
                err = res_err.stderr.strip() or "ffmpeg failed to parse video container"
                return False, f"Media container corrupt or unreadable: {err[:200]}", 0.0, size

            # Inspect streams and duration using FFmpeg header output
            cmd_info = [ffmpeg_exe, "-i", str(file_path)]
            res_info = subprocess.run(cmd_info, capture_output=True, text=True, timeout=12)
            out_info = res_info.stderr or ""
            has_video = "Video:" in out_info
            if not has_video:
                return False, "Media file contains no readable video stream", 0.0, size

            duration = 0.0
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out_info)
            if dur_match:
                try:
                    duration = round(
                        int(dur_match.group(1)) * 3600
                        + int(dur_match.group(2)) * 60
                        + float(dur_match.group(3)),
                        2,
                    )
                except Exception:
                    duration = 0.0

            return True, "Integrity verified", duration, size
    except Exception as exc:
        logger.warning(f"Integrity check exception on {file_path}: {exc}")
        return False, f"Media container corrupt or unreadable: {exc}", 0.0, size


class AuthorizedMediaResolverInterface(ABC):
    """Abstract interface defining authorized source media resolution."""

    @abstractmethod
    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        """Attempt to resolve an authorized original media asset for the given source."""
        pass


class CreatorConnectedStorageResolver(AuthorizedMediaResolverInterface):
    """Resolves master video files from creator-connected storage vaults."""

    def __init__(self, base_vault_dirs: Optional[List[Path]] = None) -> None:
        if base_vault_dirs:
            self.vault_dirs = base_vault_dirs
        else:
            self.vault_dirs = [
                Path("storage/creators").resolve(),
                Path(settings.MEDIA_DIR).resolve() / "creators",
            ]

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        vid = source.video_id
        creator = source.creator
        valid_extensions = (".mp4", ".mov", ".mkv", ".webm", ".avi")

        # Must have linked creator to use creator-connected vault
        if not creator and not source.creator_id:
            return MediaResolutionResult(
                resolved=False,
                local_path=None,
                provider="creator_connected_vault",
                provider_display_name="Creator Connected Vault",
                resolution_method="unresolvable",
                status="awaiting_authorized_media",
                message="No connected creator linked to this source.",
            )

        cid = str(creator.id if creator else source.creator_id)
        channel_id = creator.channel_id if creator else ""

        # Search creator directories: by ID, by channel_id, or by creator name
        search_dirs: List[Path] = []
        for base in self.vault_dirs:
            if not base.exists():
                continue
            if cid:
                search_dirs.append(base / cid)
            if channel_id:
                search_dirs.append(base / channel_id)
            if creator and creator.name:
                search_dirs.append(base / creator.name.strip().replace(" ", "_"))

        for c_dir in search_dirs:
            if not c_dir.exists() or not c_dir.is_dir():
                continue

            for ext in valid_extensions:
                target = c_dir / f"{vid}{ext}"
                if target.exists():
                    is_valid, msg, dur, size = verify_media_file_integrity(target)
                    if is_valid:
                        return MediaResolutionResult(
                            resolved=True,
                            local_path=str(target),
                            provider="creator_connected_vault",
                            provider_display_name="Creator Connected Vault",
                            resolution_method="creator_vault",
                            file_size_bytes=size,
                            duration_seconds=dur,
                            status="media_ready",
                            message=f"Auto-resolved from creator vault '{c_dir.name}/{target.name}'.",
                        )

            # Pattern scan in creator directory
            try:
                for f in c_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_extensions and vid in f.name:
                        is_valid, msg, dur, size = verify_media_file_integrity(f)
                        if is_valid:
                            return MediaResolutionResult(
                                resolved=True,
                                local_path=str(f),
                                provider="creator_connected_vault",
                                provider_display_name="Creator Connected Vault",
                                resolution_method="creator_vault_pattern",
                                file_size_bytes=size,
                                duration_seconds=dur,
                                status="media_ready",
                                message=f"Auto-resolved from creator vault '{c_dir.name}/{f.name}'.",
                            )
            except Exception as exc:
                logger.debug(f"Error scanning creator directory {c_dir}: {exc}")

        return MediaResolutionResult(
            resolved=False,
            local_path=None,
            provider="creator_connected_vault",
            provider_display_name="Creator Connected Vault",
            resolution_method="unresolvable",
            status="awaiting_authorized_media",
            message=f"Video '{vid}' not found in connected creator vault for Creator #{cid}.",
            blocker_detail=f"Creator #{cid} has not uploaded or synced original media for '{vid}' to their vault.",
        )


class CreatorAssetMappingResolver(AuthorizedMediaResolverInterface):
    """Resolves authorized assets through declarative JSON asset mapping manifests."""

    def __init__(self, manifest_paths: Optional[List[Path]] = None) -> None:
        if manifest_paths:
            self.manifest_paths = manifest_paths
        else:
            self.manifest_paths = [
                Path("storage").resolve() / "asset_mappings.json",
                Path(settings.DATA_DIR).resolve() / "media_manifest.json",
                Path("storage").resolve() / "manifest.json",
            ]

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        vid = source.video_id
        canon_url = source.source_url

        for m_path in self.manifest_paths:
            if not m_path.exists() or not m_path.is_file():
                continue
            try:
                with open(m_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)

                mapped_target = manifest_data.get(vid) or manifest_data.get(canon_url)
                if mapped_target:
                    # Target can be a string path or a dict with {path, license_id, etc.}
                    target_path_str = mapped_target if isinstance(mapped_target, str) else mapped_target.get("path")
                    if not target_path_str:
                        continue

                    p = Path(target_path_str)
                    if not p.is_absolute():
                        p = m_path.parent / p

                    # Check existence
                    if not p.exists() or not p.is_file():
                        return MediaResolutionResult(
                            resolved=False,
                            local_path=None,
                            provider="creator_asset_mapping",
                            provider_display_name="Creator Asset Mapping",
                            resolution_method="invalid_mapping",
                            status="invalid_mapping",
                            message=f"Asset mapping found in '{m_path.name}', but target file '{target_path_str}' does not exist on disk.",
                            blocker_detail=f"Declared mapped path '{p}' was not found. Please verify file placement.",
                        )

                    # Integrity verification
                    is_valid, err_msg, dur, size = verify_media_file_integrity(p)
                    if not is_valid:
                        return MediaResolutionResult(
                            resolved=False,
                            local_path=None,
                            provider="creator_asset_mapping",
                            provider_display_name="Creator Asset Mapping",
                            resolution_method="corrupted",
                            status="corrupted",
                            message=f"Mapped asset file '{p.name}' failed integrity check: {err_msg}",
                            blocker_detail=f"Corrupt media asset: {err_msg}",
                        )

                    return MediaResolutionResult(
                        resolved=True,
                        local_path=str(p),
                        provider="creator_asset_mapping",
                        provider_display_name="Creator Asset Mapping",
                        resolution_method="manifest_match",
                        file_size_bytes=size,
                        duration_seconds=dur,
                        status="media_ready",
                        message=f"Resolved via asset mapping ({m_path.name}) to '{p.name}'.",
                    )
            except Exception as exc:
                logger.warning(f"Error reading asset mapping manifest {m_path}: {exc}")

        return MediaResolutionResult(
            resolved=False,
            local_path=None,
            provider="creator_asset_mapping",
            provider_display_name="Creator Asset Mapping",
            resolution_method="unresolvable",
            status="awaiting_authorized_media",
            message=f"No asset mapping found for video '{vid}'.",
            blocker_detail="No entry found in asset_mappings.json or media_manifest.json.",
        )


class AuthorizedCloudStorageResolver(AuthorizedMediaResolverInterface):
    """Resolves authorized media assets from connected Cloud Storage (GCS / S3 / signed URIs)."""

    def __init__(self, cloud_config_path: Optional[Path] = None) -> None:
        self.config_path = cloud_config_path or Path("storage/cloud_assets.json").resolve()

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        vid = source.video_id

        if not self.config_path.exists():
            return MediaResolutionResult(
                resolved=False,
                local_path=None,
                provider="authorized_cloud_storage",
                provider_display_name="Authorized Cloud Storage",
                resolution_method="unresolvable",
                status="awaiting_authorized_media",
                message="Cloud storage integration not configured (storage/cloud_assets.json missing).",
                blocker_detail="No active cloud storage bucket configuration found.",
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cloud_data = json.load(f)

            entry = cloud_data.get(vid)
            if entry:
                cloud_uri = entry.get("uri") or entry.get("cloud_path")
                local_cache = entry.get("local_cache_path")
                if local_cache:
                    p = Path(local_cache)
                    if p.exists() and p.is_file():
                        is_valid, err_msg, dur, size = verify_media_file_integrity(p)
                        if is_valid:
                            return MediaResolutionResult(
                                resolved=True,
                                local_path=str(p),
                                provider="authorized_cloud_storage",
                                provider_display_name="Authorized Cloud Storage",
                                resolution_method="cloud_cache",
                                file_size_bytes=size,
                                duration_seconds=dur,
                                status="media_ready",
                                message=f"Resolved from authorized cloud storage cache for '{cloud_uri}'.",
                            )

                return MediaResolutionResult(
                    resolved=False,
                    local_path=None,
                    provider="authorized_cloud_storage",
                    provider_display_name="Authorized Cloud Storage",
                    resolution_method="cloud_pending",
                    status="awaiting_authorized_media",
                    message=f"Cloud asset registered at '{cloud_uri}', but local staging download is pending.",
                    blocker_detail="Cloud storage asset requires authentication credentials to download.",
                )
        except Exception as exc:
            logger.warning(f"Error reading cloud assets config: {exc}")

        return MediaResolutionResult(
            resolved=False,
            local_path=None,
            provider="authorized_cloud_storage",
            provider_display_name="Authorized Cloud Storage",
            resolution_method="unresolvable",
            status="awaiting_authorized_media",
            message="No cloud storage mapping for this video.",
        )


class LocalStagedMediaResolver(AuthorizedMediaResolverInterface):
    """Resolves creator-owned or operator-staged media files from authorized local directories."""

    def __init__(self, search_directories: Optional[List[Path]] = None) -> None:
        if search_directories:
            self.search_dirs = search_directories
        else:
            self.search_dirs = [
                Path(settings.MEDIA_DIR).resolve(),
                Path(settings.DATA_DIR).resolve(),
                Path("storage").resolve(),
                Path(settings.EXPORT_DIR).resolve(),
            ]

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        vid = source.video_id
        valid_extensions = (".mp4", ".mov", ".mkv", ".webm", ".avi")

        # 1. First, check if source already has an explicitly linked local_video_path
        if source.local_video_path:
            p = Path(source.local_video_path)
            if not p.is_absolute():
                p = Path(os.getcwd()) / p
            if p.exists() and p.is_file():
                is_valid, err_msg, dur, size = verify_media_file_integrity(p)
                if is_valid:
                    dur_val = source.duration_seconds or dur
                    return MediaResolutionResult(
                        resolved=True,
                        local_path=str(p),
                        provider="creator_supplied",
                        provider_display_name="Direct Attached Media",
                        resolution_method="creator_supplied",
                        file_size_bytes=size,
                        duration_seconds=dur_val,
                        status="media_ready",
                        message=f"Verified authorized attached media ({round(size / (1024*1024), 2)} MB).",
                    )
                else:
                    return MediaResolutionResult(
                        resolved=False,
                        local_path=None,
                        provider="creator_supplied",
                        provider_display_name="Direct Attached Media",
                        resolution_method="corrupted",
                        status="corrupted",
                        message=f"Attached media failed integrity check: {err_msg}",
                        blocker_detail=err_msg,
                    )

        # 2. Search configured staging directories
        candidate_filenames = [
            f"{vid}.mp4",
            f"{vid}.mov",
            f"{vid}.mkv",
            f"{vid}.webm",
            f"source_{source.id}.mp4",
        ]

        for s_dir in self.search_dirs:
            if not s_dir.exists() or not s_dir.is_dir():
                continue

            for fname in candidate_filenames:
                target = s_dir / fname
                if target.exists() and target.is_file():
                    is_valid, err_msg, dur, size = verify_media_file_integrity(target)
                    if is_valid:
                        return MediaResolutionResult(
                            resolved=True,
                            local_path=str(target),
                            provider="local_staged",
                            provider_display_name="Operator Staged Storage",
                            resolution_method="local_staged",
                            file_size_bytes=size,
                            duration_seconds=dur,
                            status="media_ready",
                            message=f"Auto-resolved matching staged asset '{target.name}' in {s_dir.name}.",
                        )

            # Pattern search
            try:
                for f in s_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_extensions:
                        if vid in f.name or f"source_{source.id}_" in f.name:
                            is_valid, err_msg, dur, size = verify_media_file_integrity(f)
                            if is_valid:
                                return MediaResolutionResult(
                                    resolved=True,
                                    local_path=str(f),
                                    provider="local_staged",
                                    provider_display_name="Operator Staged Storage",
                                    resolution_method="local_staged_pattern",
                                    file_size_bytes=size,
                                    duration_seconds=dur,
                                    status="media_ready",
                                    message=f"Auto-resolved matching staged asset '{f.name}' in {s_dir.name}.",
                                )
            except Exception as exc:
                logger.debug(f"Error scanning directory {s_dir}: {exc}")

        return MediaResolutionResult(
            resolved=False,
            local_path=None,
            provider="local_staged",
            provider_display_name="Operator Staged Storage",
            resolution_method="unresolvable",
            status="awaiting_authorized_media",
            message=f"No matching staged file found for video '{vid}'.",
            blocker_detail="Staging directories do not contain a media file matching this video ID.",
        )


class OfficialPlatformApiResolver(AuthorizedMediaResolverInterface):
    """Truthful provider adapter documenting YouTube Data API v3 and OAuth scope."""

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        vid = source.video_id
        return MediaResolutionResult(
            resolved=False,
            local_path=None,
            provider="official_platform_api",
            provider_display_name="Official YouTube API",
            resolution_method="terms_restricted",
            status="awaiting_authorized_media",
            message=(
                "Official YouTube Data API v3 and Partner OAuth provide metadata, upload, and analytics endpoints only. "
                "Official platform terms do not permit automated arbitrary raw video stream downloading. "
                "Media must be resolved via creator-connected vault or authorized asset mapping."
            ),
            blocker_detail=(
                "YouTube platform terms prohibit arbitrary stream scraping. "
                "To process this video, connect the creator's storage vault or register an asset mapping in storage/asset_mappings.json."
            ),
        )


class CompositeAuthorizedMediaResolver(AuthorizedMediaResolverInterface):
    """Composite resolver orchestrating all legitimate authorized source providers in sequence."""

    def __init__(self) -> None:
        self.creator_vault_resolver = CreatorConnectedStorageResolver()
        self.asset_mapping_resolver = CreatorAssetMappingResolver()
        self.cloud_resolver = AuthorizedCloudStorageResolver()
        self.local_staged_resolver = LocalStagedMediaResolver()
        self.platform_api_resolver = OfficialPlatformApiResolver()

    async def resolve_media(self, db: AsyncSession, source: VideoSource) -> MediaResolutionResult:
        # 1. Check Creator-Connected Storage Vault
        res = await self.creator_vault_resolver.resolve_media(db, source)
        if res.resolved:
            return res

        # 2. Check Creator Asset Mapping Manifests
        res_map = await self.asset_mapping_resolver.resolve_media(db, source)
        if res_map.resolved:
            return res_map
        # If mapping was found but failed integrity (missing target or corrupt), return that specific failure immediately
        if res_map.status in ("invalid_mapping", "corrupted"):
            return res_map

        # 3. Check Authorized Cloud Storage Integration
        res_cloud = await self.cloud_resolver.resolve_media(db, source)
        if res_cloud.resolved:
            return res_cloud

        # 4. Check Operator Local Staged Storage
        res_local = await self.local_staged_resolver.resolve_media(db, source)
        if res_local.resolved:
            return res_local
        if res_local.status in ("corrupted",):
            return res_local

        # 5. Fallback to truthful platform API explanation
        res_api = await self.platform_api_resolver.resolve_media(db, source)
        return res_api


# Backward-compatibility alias
ManifestMediaResolver = CreatorAssetMappingResolver


def get_media_resolver() -> AuthorizedMediaResolverInterface:
    """Retrieve default composite authorized media resolver."""
    return CompositeAuthorizedMediaResolver()
