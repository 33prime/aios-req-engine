"""E2E test: Call Intelligence Pipeline

Downloads video from Google Drive → Deepgram transcription → Claude analysis → AIOS signal.
V2 signal pipeline is NOT auto-triggered — run separately after reviewing results.

Usage:
    uv run python scripts/test_call_intelligence_e2e.py
"""

import asyncio
import re
from uuid import UUID, uuid4

import httpx

# ── Test constants ──────────────────────────────────────────────────────────
RECORDING_ID = UUID("23babd82-b2e8-4d27-9c21-10134ad79ecb")
PROJECT_ID = UUID("517d1c9c-80ca-419c-99b2-48c74c67117d")
MEETING_ID = UUID("58841940-0b11-4f4d-8849-6b4fb1d5f11b")
LOCAL_FILE = "/Users/matt/Downloads/Intro and Discovery Call - 2026_03_17 13_57 MST - Recording.mp4"


async def transcribe_raw_bytes(audio_bytes: bytes):
    """Send raw audio/video bytes to Deepgram (bypasses URL fetch)."""
    from app.core.config import get_settings
    from app.services.deepgram_client import _parse_deepgram_response

    settings = get_settings()
    if not settings.DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY not configured")

    params = {
        "model": settings.DEEPGRAM_MODEL,
        "diarize": "true",
        "utterances": "true",
        "punctuate": "true",
        "smart_format": "true",
    }

    async with httpx.AsyncClient(timeout=300) as client:
        print(f"  → Sending {len(audio_bytes)} bytes to Deepgram (model={settings.DEEPGRAM_MODEL})...")
        response = await client.post(
            "https://api.deepgram.com/v1/listen",
            params=params,
            headers={
                "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
                "Content-Type": "video/mp4",
            },
            content=audio_bytes,
        )
        response.raise_for_status()
        return _parse_deepgram_response(response.json())


async def main():
    from app.chains.analyze_call import analyze_call_transcript, resolve_dimensions
    from app.core.config import get_settings
    from app.core.content_sanitizer import sanitize_transcript
    from app.db import call_intelligence as ci_db
    from app.db.phase0 import insert_signal
    from app.services.call_intelligence import CallIntelligenceService

    settings = get_settings()

    print("=" * 60)
    print("CALL INTELLIGENCE PIPELINE — E2E TEST")
    print("=" * 60)
    print(f"  Recording:  {RECORDING_ID}")
    print(f"  Project:    {PROJECT_ID} (BenyBox)")
    print(f"  Meeting:    {MEETING_ID}")
    print()

    # ── Steps 1-2: Already done (transcript saved from prior run) ─────────
    print("[1-2/6] Transcript already saved — loading from DB...")
    transcript_row = ci_db.get_transcript(RECORDING_ID)
    if not transcript_row:
        raise RuntimeError("No transcript found — run full pipeline first")

    class TranscriptShim:
        """Minimal shim to match TranscriptResult interface."""
        def __init__(self, row):
            self.full_text = row["full_text"]
            self.word_count = row.get("word_count", 0)
            self.segments = row.get("segments", [])
            self.speaker_map = row.get("speaker_map", {})

    transcript = TranscriptShim(transcript_row)
    print(f"  → {transcript.word_count} words, {len(transcript.segments)} segments")

    # ── Step 3: Analyze ─────────────────────────────────────────────────────
    print("[3/6] Analyzing via Claude...")
    ci_db.update_call_recording(RECORDING_ID, {"status": "analyzing"})

    svc = CallIntelligenceService()
    context_blocks = svc._build_context_blocks(str(PROJECT_ID))
    dimensions = resolve_dimensions(settings.CALL_ACTIVE_PACKS)

    analysis = analyze_call_transcript(
        transcript_text=transcript.full_text,
        dimensions=dimensions,
        context_blocks=context_blocks,
        settings=settings,
        project_id=str(PROJECT_ID),
    )

    print(f"  → Engagement score:    {analysis.engagement_score}")
    print(f"  → Talk ratio:          {analysis.talk_ratio}")
    print(f"  → Feature insights:    {len(analysis.feature_insights or [])}")
    print(f"  → Call signals:        {len(analysis.call_signals or [])}")
    print(f"  → Content nuggets:     {len(analysis.content_nuggets or [])}")
    print(f"  → Competitive mentions: {len(analysis.competitive_mentions or [])}")

    # ── Step 4: Save analysis ───────────────────────────────────────────────
    print("[4/6] Saving analysis + child records...")
    ci_db.save_analysis(
        recording_id=RECORDING_ID,
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
        ci_db.save_feature_insights(RECORDING_ID, [fi.model_dump() for fi in analysis.feature_insights])
    if analysis.call_signals:
        ci_db.save_call_signals(RECORDING_ID, [cs.model_dump() for cs in analysis.call_signals])
    if analysis.content_nuggets:
        ci_db.save_content_nuggets(RECORDING_ID, [cn.model_dump() for cn in analysis.content_nuggets])
    if analysis.competitive_mentions:
        ci_db.save_competitive_mentions(RECORDING_ID, [cm.model_dump() for cm in analysis.competitive_mentions])
    print("  → Saved to call_analyses + child tables")

    # ── Step 5: Create AIOS signal (no V2 trigger) ─────────────────────────
    print("[5/6] Creating AIOS signal...")
    sanitized = sanitize_transcript(transcript.full_text)

    run_id = uuid4()
    metadata = {
        "authority": "client",
        "recording_id": str(RECORDING_ID),
        "source": "call_intelligence",
        "meeting_id": str(MEETING_ID),
    }
    if analysis.executive_summary:
        metadata["executive_summary"] = analysis.executive_summary

    signal = insert_signal(
        project_id=PROJECT_ID,
        source="call:Discovery Call — Brandon Wilson & Joanna Harrell",
        signal_type="meeting_transcript",
        raw_text=sanitized,
        metadata=metadata,
        run_id=run_id,
        source_label="Call Intelligence: Discovery Call — Brandon Wilson & Joanna Harrell",
    )
    signal_id = signal.get("id", "")
    print(f"  → Signal created: {signal_id}")

    # ── Step 6: Finalize ────────────────────────────────────────────────────
    print("[6/6] Finalizing recording status...")
    ci_db.update_call_recording(RECORDING_ID, {
        "status": "complete",
        "signal_id": signal_id,
    })

    # ── Results ─────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("CALL INTELLIGENCE PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Recording ID:  {RECORDING_ID}")
    print(f"  Signal ID:     {signal_id}")
    print(f"  Run ID:        {run_id}")
    print(f"  Word count:    {transcript.word_count}")
    print(f"  Engagement:    {analysis.engagement_score}")
    print()
    if analysis.executive_summary:
        print("Executive Summary:")
        print(f"  {analysis.executive_summary[:500]}")
        print()

    print("─" * 60)
    print("V2 signal pipeline NOT triggered yet. Run with:")
    print()
    print(f"  uv run python -c \"")
    print(f"import asyncio; from uuid import UUID")
    print(f"from app.graphs.unified_processor import process_signal_v2")
    print(f"asyncio.run(process_signal_v2(")
    print(f"    UUID('{signal_id}'),")
    print(f"    UUID('{PROJECT_ID}'),")
    print(f"    UUID('{run_id}'),")
    print(f"))\"")
    print("─" * 60)


if __name__ == "__main__":
    asyncio.run(main())
