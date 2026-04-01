"""Call intelligence service — orchestrates recording -> transcription -> analysis pipeline.

Pipeline: Recall.ai (media) -> Deepgram (transcription) -> Claude (analysis) -> AIOS signal
"""

from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CallIntelligenceService:
    """Orchestrates the call intelligence pipeline."""

    async def process_recording(self, recording_id: UUID) -> dict:
        """
        Full pipeline: fetch media -> transcribe -> analyze -> create signal.

        Steps:
        1. Load call_recording, get recall_bot_id
        2. fetch_bot() from Recall.ai -> get media URLs
        3. Save media URLs to call_recordings
        4. Status -> transcribing
        5. transcribe_audio() via Deepgram
        6. Save transcript
        7. Status -> analyzing
        8. Build context blocks
        9. analyze_call_transcript() via Claude
        10. Save analysis + child records
        11. Auto-create AIOS signal
        12. Trigger V2 pipeline
        13. Status -> complete
        """
        from app.chains.analyze_call import analyze_call_transcript, resolve_dimensions
        from app.core.recall_service import (
            compute_duration,
            extract_media_urls,
            fetch_bot,
        )
        from app.db import call_intelligence as ci_db
        from app.services.deepgram_client import transcribe_audio

        settings = get_settings()
        recording = ci_db.get_call_recording(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        recall_bot_id = recording.get("recall_bot_id")
        if not recall_bot_id:
            raise ValueError(f"Recording {recording_id} has no recall_bot_id")

        project_id = recording["project_id"]

        try:
            # Step 2: Fetch bot details from Recall.ai
            bot_data = await fetch_bot(recall_bot_id)

            # Step 3: Extract and save media URLs
            media = extract_media_urls(bot_data)
            duration = compute_duration(bot_data)
            updates = {k: v for k, v in media.items() if v is not None}
            if duration is not None:
                updates["duration_seconds"] = duration
            if updates:
                ci_db.update_call_recording(recording_id, updates)

            audio_url = media.get("audio_url")
            if not audio_url:
                ci_db.update_call_recording(
                    recording_id,
                    {
                        "status": "failed",
                        "error_message": "No audio URL available from Recall.ai",
                        "error_step": "extract_media",
                    },
                )
                return {"status": "failed", "error": "no_audio_url"}

            # Step 4-6: Transcribe
            ci_db.update_call_recording(recording_id, {"status": "transcribing"})

            transcript_result = await transcribe_audio(audio_url)

            ci_db.save_transcript(
                recording_id=recording_id,
                full_text=transcript_result.full_text,
                segments=[s.model_dump() for s in transcript_result.segments],
                speaker_map=transcript_result.speaker_map,
                word_count=transcript_result.word_count,
                language=transcript_result.language,
                provider=transcript_result.provider,
                model=transcript_result.model,
            )

            # Step 7-10: Analyze
            ci_db.update_call_recording(recording_id, {"status": "analyzing"})

            context_blocks = self._build_context_blocks(project_id)
            dimensions = resolve_dimensions(settings.CALL_ACTIVE_PACKS)

            analysis = analyze_call_transcript(
                transcript_text=transcript_result.full_text,
                dimensions=dimensions,
                context_blocks=context_blocks,
                settings=settings,
                project_id=project_id,
            )

            # Save analysis
            ci_db.save_analysis(
                recording_id=recording_id,
                engagement_score=analysis.engagement_score,
                talk_ratio=analysis.talk_ratio,
                engagement_timeline=analysis.engagement_timeline,
                executive_summary=analysis.executive_summary,
                custom_dimensions=analysis.custom_dimensions,
                dimension_packs_used=analysis.dimension_packs_used,
                model=analysis.model,
                tokens_input=analysis.tokens_input,
                tokens_output=analysis.tokens_output,
            )

            # Save child records
            if analysis.feature_insights:
                ci_db.save_feature_insights(
                    recording_id,
                    [fi.model_dump() for fi in analysis.feature_insights],
                )
            if analysis.call_signals:
                ci_db.save_call_signals(
                    recording_id,
                    [cs.model_dump() for cs in analysis.call_signals],
                )
            if analysis.content_nuggets:
                ci_db.save_content_nuggets(
                    recording_id,
                    [cn.model_dump() for cn in analysis.content_nuggets],
                )
            if analysis.competitive_mentions:
                ci_db.save_competitive_mentions(
                    recording_id,
                    [cm.model_dump() for cm in analysis.competitive_mentions],
                )

            # Step 11-12: Create AIOS signal and trigger V2 pipeline
            signal_id = await self._create_aios_signal(
                recording_id=recording_id,
                project_id=UUID(project_id),
                meeting_id=recording.get("meeting_id"),
                transcript_text=transcript_result.full_text,
                executive_summary=analysis.executive_summary,
            )

            # Step 13: Complete
            final_updates = {"status": "complete"}
            if signal_id:
                final_updates["signal_id"] = signal_id
            ci_db.update_call_recording(recording_id, final_updates)

            # Post-call learning loop
            try:
                from app.db.call_strategy import get_brief_for_recording
                from app.services.call_goal_diff import compute_goal_diff, compute_readiness_delta

                brief = get_brief_for_recording(recording_id)
                if brief:
                    await compute_goal_diff(recording_id)
                    await compute_readiness_delta(recording_id)
            except Exception as e:
                logger.warning(f"Post-call learning loop failed: {e}")

            logger.info(
                f"Call intelligence pipeline complete: recording={recording_id}, signal={signal_id}"
            )

            return {
                "status": "complete",
                "recording_id": str(recording_id),
                "signal_id": signal_id,
                "word_count": transcript_result.word_count,
                "engagement_score": analysis.engagement_score,
            }

        except Exception as e:
            logger.error(f"Call intelligence pipeline failed: recording={recording_id}, error={e}")
            # Determine which step failed
            error_step = "unknown"
            status = ci_db.get_call_recording(recording_id)
            if status:
                current = status.get("status", "")
                if current == "pending" or current == "bot_scheduled":
                    error_step = "fetch_bot"
                elif current == "transcribing":
                    error_step = "transcription"
                elif current == "analyzing":
                    error_step = "analysis"

            ci_db.update_call_recording(
                recording_id,
                {
                    "status": "failed",
                    "error_message": str(e)[:500],
                    "error_step": error_step,
                },
            )
            raise

    async def process_from_url(self, recording_id: UUID, audio_url: str) -> dict:
        """
        Pipeline from a direct audio URL — skips Recall.ai fetch.

        Steps:
        1. Load call_recording
        2. Transcribe via Deepgram
        3. Analyze via Claude
        4. Save analysis + child records
        5. Create AIOS signal + trigger V2 pipeline
        6. Post-call learning loop (if strategy brief exists)
        7. Status → complete
        """
        from app.chains.analyze_call import analyze_call_transcript, resolve_dimensions
        from app.db import call_intelligence as ci_db
        from app.services.deepgram_client import transcribe_audio

        settings = get_settings()
        recording = ci_db.get_call_recording(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        project_id = recording["project_id"]

        try:
            # Step 2: Transcribe
            ci_db.update_call_recording(recording_id, {"status": "transcribing"})

            transcript_result = await transcribe_audio(audio_url)

            ci_db.save_transcript(
                recording_id=recording_id,
                full_text=transcript_result.full_text,
                segments=[s.model_dump() for s in transcript_result.segments],
                speaker_map=transcript_result.speaker_map,
                word_count=transcript_result.word_count,
                language=transcript_result.language,
                provider=transcript_result.provider,
                model=transcript_result.model,
            )

            # Step 3-4: Analyze
            ci_db.update_call_recording(recording_id, {"status": "analyzing"})

            context_blocks = self._build_context_blocks(project_id)
            dimensions = resolve_dimensions(settings.CALL_ACTIVE_PACKS)

            analysis = analyze_call_transcript(
                transcript_text=transcript_result.full_text,
                dimensions=dimensions,
                context_blocks=context_blocks,
                settings=settings,
                project_id=project_id,
            )

            ci_db.save_analysis(
                recording_id=recording_id,
                engagement_score=analysis.engagement_score,
                talk_ratio=analysis.talk_ratio,
                engagement_timeline=analysis.engagement_timeline,
                executive_summary=analysis.executive_summary,
                custom_dimensions=analysis.custom_dimensions,
                dimension_packs_used=analysis.dimension_packs_used,
                model=analysis.model,
                tokens_input=analysis.tokens_input,
                tokens_output=analysis.tokens_output,
            )

            if analysis.feature_insights:
                ci_db.save_feature_insights(
                    recording_id,
                    [fi.model_dump() for fi in analysis.feature_insights],
                )
            if analysis.call_signals:
                ci_db.save_call_signals(
                    recording_id,
                    [cs.model_dump() for cs in analysis.call_signals],
                )
            if analysis.content_nuggets:
                ci_db.save_content_nuggets(
                    recording_id,
                    [cn.model_dump() for cn in analysis.content_nuggets],
                )
            if analysis.competitive_mentions:
                ci_db.save_competitive_mentions(
                    recording_id,
                    [cm.model_dump() for cm in analysis.competitive_mentions],
                )

            # Step 5: Create AIOS signal and trigger V2 pipeline
            signal_id = await self._create_aios_signal(
                recording_id=recording_id,
                project_id=UUID(project_id),
                meeting_id=recording.get("meeting_id"),
                transcript_text=transcript_result.full_text,
                executive_summary=analysis.executive_summary,
            )

            # Step 6: Complete
            final_updates = {"status": "complete"}
            if signal_id:
                final_updates["signal_id"] = signal_id
            ci_db.update_call_recording(recording_id, final_updates)

            # Step 7: Post-call learning loop
            try:
                from app.db.call_strategy import get_brief_for_recording
                from app.services.call_goal_diff import compute_goal_diff, compute_readiness_delta

                brief = get_brief_for_recording(recording_id)
                if brief:
                    await compute_goal_diff(recording_id)
                    await compute_readiness_delta(recording_id)
            except Exception as e:
                logger.warning(f"Post-call learning loop failed: {e}")

            logger.info(
                f"Call intelligence pipeline (URL) complete: "
                f"recording={recording_id}, signal={signal_id}"
            )

            return {
                "status": "complete",
                "recording_id": str(recording_id),
                "signal_id": signal_id,
                "word_count": transcript_result.word_count,
                "engagement_score": analysis.engagement_score,
            }

        except Exception as e:
            logger.error(
                f"Call intelligence pipeline (URL) failed: "
                f"recording={recording_id}, error={e}"
            )
            status = ci_db.get_call_recording(recording_id)
            error_step = "unknown"
            if status:
                current = status.get("status", "")
                if current == "pending":
                    error_step = "transcription"
                elif current == "transcribing":
                    error_step = "transcription"
                elif current == "analyzing":
                    error_step = "analysis"

            ci_db.update_call_recording(
                recording_id,
                {
                    "status": "failed",
                    "error_message": str(e)[:500],
                    "error_step": error_step,
                },
            )
            raise

    async def schedule_recording(
        self,
        meeting_id: UUID,
        project_id: UUID,
        deployed_by: UUID | None = None,
    ) -> dict:
        """
        Deploy a Recall.ai bot and create a call_recording row.

        Returns:
            Dict with recording_id, recall_bot_id, meeting_bot_id
        """
        from app.core.recall_service import deploy_bot
        from app.db import call_intelligence as ci_db
        from app.db import meeting_bots as bot_db
        from app.db.meetings import get_meeting

        meeting = get_meeting(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        meeting_url = meeting.get("google_meet_link") or meeting.get("meeting_url") or meeting.get("video_url")
        if not meeting_url:
            raise ValueError(f"Meeting {meeting_id} has no meeting URL")

        # Deploy bot via Recall.ai
        bot_data = await deploy_bot(meeting_url)
        recall_bot_id = bot_data.get("id", "")

        # Create meeting_bot record (legacy compatibility)
        bot_record = bot_db.create_bot(
            meeting_id=meeting_id,
            recall_bot_id=recall_bot_id,
            deployed_by=deployed_by,
        )

        # Create call_recording record
        recording = ci_db.create_call_recording(
            project_id=project_id,
            meeting_id=meeting_id,
            recall_bot_id=recall_bot_id,
            meeting_bot_id=UUID(bot_record["id"]) if bot_record.get("id") else None,
            deployed_by=deployed_by,
            status="bot_scheduled",
        )

        # Link recording to meeting
        from app.db.meetings import update_meeting

        update_meeting(meeting_id, {"call_recording_id": recording.get("id")})

        return {
            "recording_id": recording.get("id"),
            "recall_bot_id": recall_bot_id,
            "meeting_bot_id": bot_record.get("id"),
        }

    async def trigger_analysis(
        self,
        recording_id: UUID,
        dimension_packs: str | None = None,
    ) -> dict:
        """
        Trigger (re-)analysis on an existing recording with transcript.

        Useful for re-running with different dimension packs.
        """
        from app.chains.analyze_call import analyze_call_transcript, resolve_dimensions
        from app.db import call_intelligence as ci_db

        settings = get_settings()
        recording = ci_db.get_call_recording(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        transcript = ci_db.get_transcript(recording_id)
        if not transcript:
            raise ValueError(f"No transcript found for recording {recording_id}")

        packs = dimension_packs or settings.CALL_ACTIVE_PACKS
        dimensions = resolve_dimensions(packs)

        ci_db.update_call_recording(recording_id, {"status": "analyzing"})

        context_blocks = self._build_context_blocks(recording["project_id"])

        analysis = analyze_call_transcript(
            transcript_text=transcript["full_text"],
            dimensions=dimensions,
            context_blocks=context_blocks,
            settings=settings,
            project_id=recording["project_id"],
        )

        ci_db.save_analysis(
            recording_id=recording_id,
            engagement_score=analysis.engagement_score,
            talk_ratio=analysis.talk_ratio,
            engagement_timeline=analysis.engagement_timeline,
            executive_summary=analysis.executive_summary,
            custom_dimensions=analysis.custom_dimensions,
            dimension_packs_used=analysis.dimension_packs_used,
            model=analysis.model,
            tokens_input=analysis.tokens_input,
            tokens_output=analysis.tokens_output,
        )

        if analysis.feature_insights:
            ci_db.save_feature_insights(
                recording_id,
                [fi.model_dump() for fi in analysis.feature_insights],
            )
        if analysis.call_signals:
            ci_db.save_call_signals(
                recording_id,
                [cs.model_dump() for cs in analysis.call_signals],
            )
        if analysis.content_nuggets:
            ci_db.save_content_nuggets(
                recording_id,
                [cn.model_dump() for cn in analysis.content_nuggets],
            )
        if analysis.competitive_mentions:
            ci_db.save_competitive_mentions(
                recording_id,
                [cm.model_dump() for cm in analysis.competitive_mentions],
            )

        ci_db.update_call_recording(recording_id, {"status": "complete"})

        return {
            "status": "complete",
            "engagement_score": analysis.engagement_score,
            "packs_used": analysis.dimension_packs_used,
        }

    async def create_signal_from_recording(
        self,
        recording_id: UUID,
        authority: str = "client",
    ) -> dict:
        """Manually create an AIOS signal from a completed recording."""
        from app.db import call_intelligence as ci_db

        recording = ci_db.get_call_recording(recording_id)
        if not recording:
            raise ValueError(f"Recording {recording_id} not found")

        transcript = ci_db.get_transcript(recording_id)
        if not transcript:
            raise ValueError(f"No transcript for recording {recording_id}")

        analysis = ci_db.get_analysis(recording_id)
        summary = analysis.get("executive_summary") if analysis else None

        signal_id = await self._create_aios_signal(
            recording_id=recording_id,
            project_id=UUID(recording["project_id"]),
            meeting_id=recording.get("meeting_id"),
            transcript_text=transcript["full_text"],
            executive_summary=summary,
            authority=authority,
        )

        if signal_id:
            ci_db.update_call_recording(recording_id, {"signal_id": signal_id})

        return {"signal_id": signal_id}

    def _build_context_blocks(self, project_id: str) -> list[dict]:
        """Build context blocks from project data for analysis."""
        blocks: list[dict] = []

        try:
            from app.db.supabase_client import get_supabase

            supabase = get_supabase()

            # Features
            features = (
                supabase.table("features")
                .select("name, category")
                .eq("project_id", project_id)
                .limit(30)
                .execute()
            ).data or []

            if features:
                feature_text = "\n".join(
                    f"- {f['name']}" + (f" ({f['category']})" if f.get('category') else "")
                    for f in features
                )
                blocks.append(
                    {
                        "label": "Project Features",
                        "content": feature_text,
                    }
                )

            # Personas
            personas = (
                supabase.table("personas")
                .select("name, description")
                .eq("project_id", project_id)
                .limit(10)
                .execute()
            ).data or []

            if personas:
                persona_text = "\n".join(
                    f"- {p['name']}: {p.get('description', '')[:100]}" for p in personas
                )
                blocks.append(
                    {
                        "label": "Target Personas",
                        "content": persona_text,
                    }
                )

        except Exception as e:
            logger.warning(f"Failed to load context for analysis: {e}")

        return blocks

    async def _create_aios_signal(
        self,
        recording_id: UUID,
        project_id: UUID,
        meeting_id: str | None,
        transcript_text: str,
        executive_summary: str | None = None,
        authority: str = "client",
    ) -> str | None:
        """Create an AIOS signal and trigger V2 pipeline."""
        from app.core.content_sanitizer import sanitize_transcript
        from app.db.phase0 import insert_signal

        try:
            # Get meeting title
            meeting_title = "Call Recording"
            if meeting_id:
                from app.db.meetings import get_meeting

                meeting = get_meeting(UUID(meeting_id))
                if meeting:
                    meeting_title = meeting.get("title", "Call Recording")

            sanitized = sanitize_transcript(transcript_text)

            metadata = {
                "authority": authority,
                "recording_id": str(recording_id),
                "source": "call_intelligence",
            }
            if meeting_id:
                metadata["meeting_id"] = meeting_id
            if executive_summary:
                metadata["executive_summary"] = executive_summary

            run_id = uuid4()
            signal = insert_signal(
                project_id=project_id,
                source=f"call:{meeting_title}",
                signal_type="meeting_transcript",
                raw_text=sanitized,
                metadata=metadata,
                run_id=run_id,
                source_label=f"Call Intelligence: {meeting_title}",
            )

            signal_id = signal.get("id", "")

            # Trigger V2 pipeline (fire-and-forget)
            try:
                from app.graphs.unified_processor import process_signal_v2

                await process_signal_v2(
                    signal_id=UUID(signal_id),
                    project_id=project_id,
                    run_id=run_id,
                )
            except Exception as e:
                logger.warning(f"V2 pipeline failed for signal {signal_id}: {e}")

            return signal_id

        except Exception as e:
            logger.error(f"Failed to create AIOS signal: {e}")
            return None


def get_call_intelligence_service() -> CallIntelligenceService | None:
    """Factory: returns service if Deepgram is configured, else None."""
    settings = get_settings()
    if not settings.DEEPGRAM_API_KEY:
        return None
    return CallIntelligenceService()
