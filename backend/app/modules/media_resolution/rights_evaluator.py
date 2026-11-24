"""VANTYX Source Eligibility & Commercial Rights Evaluator.

Enforces strict legal safeguards according to M10.1 specifications:
1. Creator-owned videos with verified channel authorization.
2. Creator-authorized partner videos with documented editing and commercial rights.
3. Explicitly licensed third-party videos, with verified license scope.
4. Sources with unresolved or insufficient permissions.

Crucial Legal Guarantees:
- Public availability on YouTube does NOT imply commercial editing or redistribution rights.
- Standard YouTube licenses grant viewing only on YouTube.
- Creative Commons (CC-BY) markers without explicit commercial adaptation contracts
  do NOT satisfy VANTYX commercial production criteria.
- Expired licenses immediately halt pipeline processing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from app.core.logging import logger
from app.db.models.creator import Creator
from app.db.models.rights import RightsRecord
from app.db.models.source import VideoSource


class SourceEligibilityCategory(str, Enum):
    CREATOR_OWNED = "creator_owned"
    AUTHORIZED_PARTNER = "authorized_partner"
    LICENSED_THIRD_PARTY = "licensed_third_party"
    UNRESOLVED = "unresolved"


@dataclass
class SourceAuthorizationResult:
    """Structured legal evaluation outcome for a video source."""

    category: SourceEligibilityCategory
    is_eligible: bool
    permission_status: str  # authorized | own_gameplay | pending | rejected | expired
    commercial_use_allowed: bool
    allowed_editing_scope: str  # full | transformative_shorts | clip_only | restricted
    evidence: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    blocker_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "is_eligible": self.is_eligible,
            "permission_status": self.permission_status,
            "commercial_use_allowed": self.commercial_use_allowed,
            "allowed_editing_scope": self.allowed_editing_scope,
            "evidence": self.evidence,
            "reason": self.reason,
            "blocker_detail": self.blocker_detail,
        }


class RightsEvaluator:
    """Evaluates video sources against legal and platform rights boundaries."""

    @classmethod
    def evaluate(cls, source: VideoSource) -> SourceAuthorizationResult:
        """Execute comprehensive rights evaluation on a VideoSource instance."""
        # 1. Synthetic test media
        if source.is_synthetic or source.discovery_method in ("synthetic_test", "synthetic"):
            return SourceAuthorizationResult(
                category=SourceEligibilityCategory.CREATOR_OWNED,
                is_eligible=True,
                permission_status="own_gameplay",
                commercial_use_allowed=False,  # strictly non-commercial
                allowed_editing_scope="transformative_shorts",
                evidence={"type": "synthetic_pipeline_test", "verified_by": "system_harness"},
                reason="Synthetic test media authorized for local pipeline testing (strictly ineligible for external publishing).",
                blocker_detail=None,
            )

        # 2. Source must have an associated RightsRecord
        rights: Optional[RightsRecord] = source.rights
        creator: Optional[Creator] = source.creator

        if not rights:
            return SourceAuthorizationResult(
                category=SourceEligibilityCategory.UNRESOLVED,
                is_eligible=False,
                permission_status="pending",
                commercial_use_allowed=False,
                allowed_editing_scope="restricted",
                evidence={"type": "missing_record"},
                reason="No rights management record found for this source.",
                blocker_detail="Source lacks a legal rights record. Ingestion must document commercial permissions.",
            )

        # 3. Check license expiration
        if rights.expires_at:
            now = datetime.now(timezone.utc)
            exp = (
                rights.expires_at
                if rights.expires_at.tzinfo
                else rights.expires_at.replace(tzinfo=timezone.utc)
            )
            if now > exp:
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.LICENSED_THIRD_PARTY
                    if rights.permission_status == "authorized"
                    else SourceEligibilityCategory.UNRESOLVED,
                    is_eligible=False,
                    permission_status="rejected",
                    commercial_use_allowed=False,
                    allowed_editing_scope="restricted",
                    evidence={
                        "type": "expired_license",
                        "expired_on": exp.isoformat(),
                        "documentation": rights.license_documentation,
                    },
                    reason=f"Usage authorization expired on {exp.strftime('%Y-%m-%d')}.",
                    blocker_detail=f"Commercial license term expired on {exp.isoformat()}. Renewal required.",
                )

        # 3b. Check Creator Revocation & Credential Expiration
        if creator:
            if creator.is_revoked or creator.oauth_status == "revoked":
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.UNRESOLVED,
                    is_eligible=False,
                    permission_status="rejected",
                    commercial_use_allowed=False,
                    allowed_editing_scope="restricted",
                    evidence={
                        "type": "revoked_authorization",
                        "creator_id": creator.id,
                        "revoked_at": creator.revoked_at.isoformat() if creator.revoked_at else None,
                        "reason": creator.revocation_reason,
                    },
                    reason=f"Channel authorization was revoked: {creator.revocation_reason or 'Revoked by owner'}.",
                    blocker_detail=f"Channel authorization revoked. Content from '{creator.verified_channel_id or creator.channel_id}' cannot be processed.",
                )

            if creator.oauth_status == "expired":
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.UNRESOLVED,
                    is_eligible=False,
                    permission_status="rejected",
                    commercial_use_allowed=False,
                    allowed_editing_scope="restricted",
                    evidence={
                        "type": "expired_credentials",
                        "creator_id": creator.id,
                        "token_expires_at": creator.token_expires_at.isoformat() if creator.token_expires_at else None,
                    },
                    reason="Creator OAuth credentials have expired. Re-authentication required.",
                    blocker_detail="OAuth credentials expired. Token refresh or re-authentication required.",
                )

        # 3c. Ownership Verification: compare authenticated channel ID with the video's channel
        video_channel_id = None
        if source.raw_metadata:
            video_channel_id = (
                source.raw_metadata.get("channel_id")
                or source.raw_metadata.get("snippet", {}).get("channelId")
            )
            if not video_channel_id and source.raw_metadata.get("author_url"):
                url = source.raw_metadata["author_url"]
                if "/channel/" in url:
                    video_channel_id = url.split("/channel/")[-1].split("/")[0]

        if creator and video_channel_id:
            expected_ch = creator.verified_channel_id or creator.channel_id
            if expected_ch and video_channel_id != expected_ch:
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.UNRESOLVED,
                    is_eligible=False,
                    permission_status="rejected",
                    commercial_use_allowed=False,
                    allowed_editing_scope="restricted",
                    evidence={
                        "type": "channel_mismatch",
                        "video_channel_id": video_channel_id,
                        "creator_verified_channel_id": expected_ch,
                    },
                    reason=f"Channel ownership mismatch: submitted video belongs to channel '{video_channel_id}', which does not match creator's verified channel '{expected_ch}'.",
                    blocker_detail=f"Ownership verification failed: video channel '{video_channel_id}' does not match authenticated channel '{expected_ch}'.",
                )

        # 4. Check Category 1: Creator-owned videos with verified channel authorization
        if (
            rights.permission_status == "own_gameplay"
            or (creator and creator.permission_tier == "own_content" and creator.approval_status == "approved")
        ):
            if rights.commercial_use_allowed or (creator and creator.approval_status == "approved"):
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.CREATOR_OWNED,
                    is_eligible=True,
                    permission_status="own_gameplay",
                    commercial_use_allowed=True,
                    allowed_editing_scope=rights.allowed_editing_scope or "full",
                    evidence={
                        "type": "creator_channel_ownership",
                        "creator_id": creator.id if creator else None,
                        "creator_name": creator.name if creator else "Channel Owner",
                        "channel_id": creator.channel_id if creator else None,
                        "documentation": rights.license_documentation or "Verified channel owner content",
                    },
                    reason="Creator-owned video with verified channel authorization.",
                    blocker_detail=None,
                )

        # 5. Check Category 2: Creator-authorized partner videos with documented editing/commercial rights
        if (
            creator
            and creator.approval_status == "approved"
            and creator.permission_tier == "authorized_partner"
        ):
            if rights.commercial_use_allowed and rights.allowed_editing_scope != "restricted":
                return SourceAuthorizationResult(
                    category=SourceEligibilityCategory.AUTHORIZED_PARTNER,
                    is_eligible=True,
                    permission_status="authorized",
                    commercial_use_allowed=True,
                    allowed_editing_scope=rights.allowed_editing_scope or "transformative_shorts",
                    evidence={
                        "type": "partner_agreement",
                        "creator_id": creator.id,
                        "creator_name": creator.name,
                        "channel_id": creator.channel_id,
                        "license_doc": rights.license_documentation,
                        "verified_by": rights.verified_by,
                        "verified_at": rights.verified_at.isoformat() if rights.verified_at else None,
                    },
                    reason=f"Authorized partner video under bilateral agreement with {creator.name}.",
                    blocker_detail=None,
                )

        # 6. Check Category 3: Explicitly licensed third-party videos with verified license scope
        if (
            rights.permission_status == "authorized"
            and rights.commercial_use_allowed
            and rights.license_documentation
            and rights.allowed_editing_scope in ("full", "transformative_shorts", "clip_only")
        ):
            return SourceAuthorizationResult(
                category=SourceEligibilityCategory.LICENSED_THIRD_PARTY,
                is_eligible=True,
                permission_status="authorized",
                commercial_use_allowed=True,
                allowed_editing_scope=rights.allowed_editing_scope,
                evidence={
                    "type": "third_party_commercial_license",
                    "license_documentation": rights.license_documentation,
                    "verified_by": rights.verified_by,
                    "verified_at": rights.verified_at.isoformat() if rights.verified_at else None,
                    "expires_at": rights.expires_at.isoformat() if rights.expires_at else None,
                },
                reason="Explicitly licensed third-party video with verified commercial adaptation scope.",
                blocker_detail=None,
            )

        # 7. Check Category 4: Sources with unresolved or insufficient permissions
        # Reject assumptions regarding public YouTube availability or bare Creative Commons
        blocker = "Insufficient commercial rights: "
        if not rights.commercial_use_allowed:
            blocker += "Commercial use is not granted by the rights holder. "
        if rights.allowed_editing_scope == "restricted":
            blocker += "Editing scope is restricted (transformative Shorts prohibited). "
        if not rights.license_documentation and (not creator or creator.approval_status != "approved"):
            blocker += "Arbitrary public YouTube URL lacks bilateral creator partnership or commercial license evidence."

        return SourceAuthorizationResult(
            category=SourceEligibilityCategory.UNRESOLVED,
            is_eligible=False,
            permission_status=rights.permission_status if rights.permission_status in ("rejected", "revoked") else "pending",
            commercial_use_allowed=False,
            allowed_editing_scope="restricted",
            evidence={
                "type": "unresolved_public_source",
                "claimed_creator_id": creator.id if creator else None,
                "claimed_creator_approval": creator.approval_status if creator else None,
                "license_doc": rights.license_documentation,
            },
            reason="Unresolved or insufficient permissions for commercial adaptation.",
            blocker_detail=blocker.strip(),
        )
