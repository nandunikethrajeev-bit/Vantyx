"""VANTYX Intelligent Clip Selection Service.

Evaluates AI-indexed video scenes, scores hook strength, retention potential,
context completeness, audio quality, prevents timestamp overlaps and duplicates,
and ranks top candidate clips targeting 4 high-quality publishable Shorts per day.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.intelligence import VideoScene
from app.db.models.selection import CandidateClip
from app.schemas.selection import CandidateClipUpdate, RankingWeightsSchema


@dataclass
class RankingWeights:
    """Configurable weights for ranking moment scores."""
    hook_weight: float = 0.35
    retention_weight: float = 0.35
    context_weight: float = 0.15
    audio_weight: float = 0.15

    def normalize(self) -> "RankingWeights":
        """Ensure sum of weights equals 1.0."""
        total = self.hook_weight + self.retention_weight + self.context_weight + self.audio_weight
        if total <= 0:
            return RankingWeights()
        return RankingWeights(
            hook_weight=round(self.hook_weight / total, 3),
            retention_weight=round(self.retention_weight / total, 3),
            context_weight=round(self.context_weight / total, 3),
            audio_weight=round(self.audio_weight / total, 3),
        )

    @classmethod
    def from_schema(cls, schema: Optional[RankingWeightsSchema]) -> "RankingWeights":
        if not schema:
            return cls()
        return cls(
            hook_weight=schema.hook_weight,
            retention_weight=schema.retention_weight,
            context_weight=schema.context_weight,
            audio_weight=schema.audio_weight,
        ).normalize()


class SelectionService:
    """Algorithmically evaluates and ranks candidate Shorts clips from video scenes."""

    is_active: bool = False

    async def rank_candidate_moments(self, video_id: str) -> List[Dict[str, Any]]:
        """Legacy interface helper."""
        return []

    # ---------------- Component Scoring Evaluators ----------------

    @staticmethod
    def evaluate_hook_strength(scene: VideoScene) -> float:
        """Evaluate opening impact within the first 3 seconds.
        
        Considers action intensity, opening speech cue, and dynamic visual tags.
        Returns a score in range [20.0, 100.0].
        """
        # Base factor from action intensity (0.0 to 1.0)
        action_component = scene.action_intensity * 60.0

        # Speech component: early spoken cue catches attention fast
        speech_component = 25.0 if (scene.speech_transcript and len(scene.speech_transcript.strip()) > 5) else 10.0

        # Tag bonus: explosive or high-energy gameplay tags
        tag_bonus = 0.0
        if scene.tags:
            high_hook_tags = {"chase", "stunt", "explosion", "shootout", "drift", "action", "heist", "wanted"}
            scene_tags_lower = {t.lower() for t in scene.tags}
            if any(t in scene_tags_lower for t in high_hook_tags):
                tag_bonus = 15.0

        raw_score = 15.0 + action_component + speech_component + tag_bonus
        return round(min(100.0, max(20.0, raw_score)), 1)

    @staticmethod
    def evaluate_retention_potential(scene: VideoScene, duration: float) -> float:
        """Evaluate pacing, excitement climax, and viewer drop-off resistance.
        
        Returns a score in range [15.0, 100.0].
        """
        # Excitement (70%) and action (30%) drive middle-to-end retention
        base_retention = (scene.excitement_score * 0.70 + scene.action_intensity * 0.30) * 100.0

        # Duration pacing penalty: vertical shorts have an engagement sweet spot (30-55s)
        duration_penalty = 0.0
        if duration < 25.0:
            duration_penalty = (25.0 - duration) * 2.0
        elif duration > 58.0:
            duration_penalty = (duration - 58.0) * 2.0

        retention_score = base_retention - duration_penalty
        return round(min(100.0, max(15.0, retention_score)), 1)

    @staticmethod
    def evaluate_context_completeness(scene: VideoScene, duration: float) -> float:
        """Evaluate narrative completeness and standalone comprehensibility.
        
        Penalizes abrupt or fragmented segments and rewards self-contained arcs.
        Returns a score in range [20.0, 100.0].
        """
        # Segment duration adequacy
        if duration < 20.0:
            # Under 20s severely truncates context before payoff
            duration_score = 20.0 + (duration / 20.0) * 25.0
            narrative_bonus = 0.0
        elif 30.0 <= duration <= 55.0:
            # Optimal duration for complete narrative arc
            duration_score = 85.0
            narrative_bonus = 10.0 if (scene.description and len(scene.description.strip()) > 20) else 0.0
        elif duration > 58.0:
            duration_score = 60.0
            narrative_bonus = 5.0 if (scene.description and len(scene.description.strip()) > 20) else 0.0
        else:
            duration_score = 70.0
            narrative_bonus = 5.0 if (scene.description and len(scene.description.strip()) > 20) else 0.0

        return round(min(100.0, max(20.0, duration_score + narrative_bonus)), 1)

    @staticmethod
    def evaluate_audio_quality(scene: VideoScene) -> float:
        """Evaluate presence, clarity, and richness of the audio track.
        
        Returns a score in range [25.0, 100.0].
        """
        base_score = 55.0  # default adequate game SFX

        # Speech transcript presence indicates voice commentary or dialogue
        if scene.speech_transcript and len(scene.speech_transcript.strip()) > 10:
            base_score += 25.0

        # Audio-related cues from tags
        if scene.tags:
            audio_favorable_tags = {"dialogue", "commentary", "engine", "radio", "music", "speech"}
            scene_tags_lower = {t.lower() for t in scene.tags}
            if any(t in scene_tags_lower for t in audio_favorable_tags):
                base_score += 15.0

        return round(min(100.0, max(25.0, base_score)), 1)

    # ---------------- Deduplication & Overlap Prevention ----------------

    @staticmethod
    def is_duplicate_moment(
        candidate_tags: Set[str],
        candidate_label: str,
        chosen_candidates: List[Dict[str, Any]],
        similarity_threshold: float = 0.70,
    ) -> bool:
        """Check if candidate duplicates an already selected moment's theme or scene."""
        candidate_tokens = set(candidate_label.lower().split()) | candidate_tags
        if not candidate_tokens:
            return False

        for chosen in chosen_candidates:
            chosen_tokens = chosen.get("tokens", set())
            if not chosen_tokens:
                continue
            intersection = candidate_tokens.intersection(chosen_tokens)
            union = candidate_tokens.union(chosen_tokens)
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard >= similarity_threshold:
                return True
        return False

    @staticmethod
    def has_timestamp_overlap(
        start: float,
        end: float,
        chosen_candidates: List[Dict[str, Any]],
        tolerance_seconds: float = 3.0,
    ) -> bool:
        """Check if [start, end] overlaps with any chosen interval beyond tolerance."""
        for chosen in chosen_candidates:
            c_start = chosen["start_time"]
            c_end = chosen["end_time"]
            overlap_start = max(start, c_start)
            overlap_end = min(end, c_end)
            if overlap_end - overlap_start > tolerance_seconds:
                return True
        return False

    # ---------------- Core Ranking & Generation Engine ----------------

    @classmethod
    def calculate_scores(
        cls,
        scene: VideoScene,
        weights: Optional[RankingWeights] = None,
        feedback_multipliers: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, float, float, float, float, str, str]:
        """Evaluate hook, retention, context, audio, overall score, rationale, and title.
        
        Returns:
            (hook_score, retention_score, context_score, audio_score, overall_score, rationale, title_suggestion)
        """
        active_weights = (weights or RankingWeights()).normalize()
        duration = round(scene.end_time - scene.start_time, 1)

        # 1. Component Scores
        hook_score = cls.evaluate_hook_strength(scene)
        retention_score = cls.evaluate_retention_potential(scene, duration)
        context_score = cls.evaluate_context_completeness(scene, duration)
        audio_score = cls.evaluate_audio_quality(scene)

        # 2. Configurable Weighted Overall Score
        raw_overall = (
            active_weights.hook_weight * hook_score
            + active_weights.retention_weight * retention_score
            + active_weights.context_weight * context_score
            + active_weights.audio_weight * audio_score
        )

        feedback_adjustment_text = ""
        overall_score = round(raw_overall, 1)

        # Apply closed-loop analytics feedback if enabled and present
        if feedback_multipliers and feedback_multipliers.get("feedback_enabled"):
            cat_mults = feedback_multipliers.get("category_multipliers", {})
            dur_mults = feedback_multipliers.get("duration_multipliers", {})
            max_impact = feedback_multipliers.get("max_impact", 0.15)

            # Inferred category
            tags_str = " ".join(scene.tags or []).lower()
            label_str = scene.scene_label.lower()
            combined_text = f"{label_str} {tags_str}"
            if any(w in combined_text for w in ["heist", "bank", "robbery"]):
                cat = "heist"
            elif any(w in combined_text for w in ["chase", "police", "cop"]):
                cat = "chase"
            elif any(w in combined_text for w in ["stunt", "drift", "jump", "plane"]):
                cat = "stunt"
            elif any(w in combined_text for w in ["shootout", "combat", "fight"]):
                cat = "combat"
            else:
                cat = "general"

            if duration < 25.0:
                dur_bucket = "15-25s"
            elif duration < 35.0:
                dur_bucket = "25-35s"
            elif duration < 45.0:
                dur_bucket = "35-45s"
            else:
                dur_bucket = "45-60s"

            c_mult = cat_mults.get(cat, 1.0)
            d_mult = dur_mults.get(dur_bucket, 1.0)
            combined_mult = c_mult * d_mult
            clamped_mult = max(1.0 - max_impact, min(1.0 + max_impact, combined_mult))

            if abs(clamped_mult - 1.0) >= 0.005:
                overall_score = round(min(100.0, max(0.0, raw_overall * clamped_mult)), 1)
                feedback_adjustment_text = (
                    f" [Analytics Feedback: {clamped_mult:+.2f}x calibrated modifier for {cat}/{dur_bucket}]"
                )

        # 3. Explainable Rationale
        rationale_parts = []
        if hook_score >= 80.0:
            rationale_parts.append(f"High hook velocity ({hook_score:.0f}/100)")
        elif hook_score >= 60.0:
            rationale_parts.append(f"Solid opening hook ({hook_score:.0f}/100)")
        else:
            rationale_parts.append(f"Moderate opening hook ({hook_score:.0f}/100)")

        if retention_score >= 80.0:
            rationale_parts.append(f"Strong retention pacing ({retention_score:.0f}/100)")

        if 30.0 <= duration <= 55.0:
            rationale_parts.append(f"Optimal Shorts duration ({duration}s, context: {context_score:.0f})")
        else:
            rationale_parts.append(f"Duration {duration}s (context: {context_score:.0f})")

        if audio_score >= 75.0:
            rationale_parts.append("Rich audio/speech")

        rationale = ". ".join(rationale_parts) + "." + feedback_adjustment_text

        # 4. Punchy Shorts Title Suggestion
        clean_label = scene.scene_label.replace("GTA 6", "").replace("Gameplay", "").strip()
        if not clean_label:
            clean_label = "Unreal Moment"
        title_suggestion = f"GTA 6: {clean_label} #Shorts"[:100]

        return (
            hook_score,
            retention_score,
            context_score,
            audio_score,
            overall_score,
            rationale,
            title_suggestion,
        )

    @classmethod
    async def generate_candidates_for_source(
        cls,
        db: AsyncSession,
        source_id: int,
        min_score_threshold: float = 60.0,
        max_candidates: int = 8,
        weights: Optional[RankingWeights] = None,
        feedback_multipliers: Optional[Dict[str, Any]] = None,
    ) -> List[CandidateClip]:
        """Generate, score, deduplicate, and persist candidate clips for a source."""
        # Retrieve indexed scenes for this source
        stmt = (
            select(VideoScene)
            .where(VideoScene.source_id == source_id)
            .order_by(VideoScene.start_time.asc())
        )
        scenes = list((await db.execute(stmt)).scalars().all())
        if not scenes:
            logger.warning(f"No indexed scenes found for source ID {source_id}")
            return []

        active_weights = (weights or RankingWeights()).normalize()

        if feedback_multipliers is None:
            try:
                from app.modules.analytics.service import AnalyticsService
                feedback_multipliers = await AnalyticsService.get_feedback_multipliers(db)
            except Exception:
                feedback_multipliers = None

        # 1. Score all scenes deterministically
        scored_items: List[Dict[str, Any]] = []
        for scene in scenes:
            hook, ret, ctx, aud, overall, rationale, title = cls.calculate_scores(
                scene, active_weights, feedback_multipliers
            )
            if overall >= min_score_threshold:
                tags_set = {t.lower() for t in (scene.tags or [])}
                tokens = set(scene.scene_label.lower().split()) | tags_set
                scored_items.append(
                    {
                        "scene": scene,
                        "hook_score": hook,
                        "retention_score": ret,
                        "context_score": ctx,
                        "audio_score": aud,
                        "overall_score": overall,
                        "rationale": rationale,
                        "title": title,
                        "start_time": scene.start_time,
                        "end_time": scene.end_time,
                        "duration": round(scene.end_time - scene.start_time, 1),
                        "tags_set": tags_set,
                        "tokens": tokens,
                        "label": scene.scene_label,
                    }
                )

        # 2. Sort by overall_score descending
        scored_items.sort(key=lambda x: x["overall_score"], reverse=True)

        # 3. Non-overlapping & Duplicate-Prevention Selection Algorithm
        selected_candidates: List[Dict[str, Any]] = []
        for item in scored_items:
            if len(selected_candidates) >= max_candidates:
                break

            # Prevent timestamp collision
            if cls.has_timestamp_overlap(item["start_time"], item["end_time"], selected_candidates):
                continue

            # Prevent duplicate scene themes
            if cls.is_duplicate_moment(item["tags_set"], item["label"], selected_candidates):
                continue

            selected_candidates.append(item)

        # 4. Remove previous unapproved candidate clips for this source to keep state clean
        del_stmt = select(CandidateClip).where(
            CandidateClip.source_id == source_id, CandidateClip.status == "candidate"
        )
        existing_unapproved = list((await db.execute(del_stmt)).scalars().all())
        for e in existing_unapproved:
            await db.delete(e)

        # 5. Persist selected candidates
        persisted_clips: List[CandidateClip] = []
        for item in selected_candidates:
            clip = CandidateClip(
                source_id=source_id,
                scene_id=item["scene"].id,
                start_time=item["start_time"],
                end_time=item["end_time"],
                duration_seconds=item["duration"],
                title_suggestion=item["title"],
                hook_score=item["hook_score"],
                retention_score=item["retention_score"],
                context_score=item["context_score"],
                audio_score=item["audio_score"],
                overall_score=item["overall_score"],
                status="candidate",
                rationale=item["rationale"],
            )
            db.add(clip)
            persisted_clips.append(clip)

        await db.commit()
        for c in persisted_clips:
            await db.refresh(c)

        logger.info(
            f"Candidate generation complete for source {source_id}: {len(persisted_clips)} candidates ranked (threshold: {min_score_threshold})"
        )
        return persisted_clips

    @staticmethod
    async def list_candidates(
        db: AsyncSession,
        source_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[CandidateClip]:
        """List candidate clips ordered by overall engagement score."""
        stmt = select(CandidateClip).order_by(CandidateClip.overall_score.desc())
        if source_id is not None:
            stmt = stmt.where(CandidateClip.source_id == source_id)
        if status is not None:
            stmt = stmt.where(CandidateClip.status == status)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_candidate(db: AsyncSession, candidate_id: int) -> Optional[CandidateClip]:
        """Retrieve candidate clip by ID."""
        return await db.get(CandidateClip, candidate_id)

    @staticmethod
    async def update_candidate(
        db: AsyncSession, candidate_id: int, data: CandidateClipUpdate
    ) -> Optional[CandidateClip]:
        """Update candidate clip review status, title, or trimmed timestamps."""
        clip = await db.get(CandidateClip, candidate_id)
        if not clip:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(clip, key, value)

        if "start_time" in update_dict or "end_time" in update_dict:
            clip.duration_seconds = round(clip.end_time - clip.start_time, 1)

        await db.commit()
        await db.refresh(clip)
        logger.info(f"Updated candidate clip ID {candidate_id}: status={clip.status}")
        return clip

    @staticmethod
    async def get_daily_selection(
        db: AsyncSession, target_count: int = 4
    ) -> Tuple[List[CandidateClip], bool]:
        """Select up to `target_count` highest-scoring candidates for daily production.
        
        Returns:
            Tuple of (selected_clips, has_sufficient_moments)
        """
        # Prioritize explicitly approved clips, then highest-scoring candidates
        stmt = (
            select(CandidateClip)
            .where(CandidateClip.status.in_(["approved", "candidate"]))
            .order_by(CandidateClip.overall_score.desc())
            .limit(target_count)
        )
        clips = list((await db.execute(stmt)).scalars().all())
        has_sufficient = len(clips) >= target_count
        return clips, has_sufficient
