"""Tests for call intelligence pipeline.

Covers: schemas, Deepgram client, Recall service extensions, analysis chain, DB smoke tests.
"""

from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Schema validation tests
# ============================================================================


class TestSchemas:
    """Test Pydantic schema validation."""

    def test_transcript_segment_valid(self):
        from app.core.schemas_call_intelligence import TranscriptSegment

        seg = TranscriptSegment(
            speaker="Speaker 0",
            text="Hello, how are you?",
            start=0.0,
            end=2.5,
            confidence=0.95,
        )
        assert seg.speaker == "Speaker 0"
        assert seg.confidence == 0.95

    def test_transcript_segment_defaults(self):
        from app.core.schemas_call_intelligence import TranscriptSegment

        seg = TranscriptSegment(speaker="Speaker 1", text="Fine.")
        assert seg.start == 0.0
        assert seg.end == 0.0
        assert seg.confidence == 0.0

    def test_transcript_result_defaults(self):
        from app.core.schemas_call_intelligence import TranscriptResult

        result = TranscriptResult()
        assert result.full_text == ""
        assert result.segments == []
        assert result.speaker_map == {}
        assert result.word_count == 0
        assert result.provider == "deepgram"

    def test_analysis_result_defaults(self):
        from app.core.schemas_call_intelligence import AnalysisResult

        result = AnalysisResult()
        assert result.engagement_score is None
        assert result.feature_insights == []
        assert result.call_signals == []
        assert result.content_nuggets == []
        assert result.competitive_mentions == []

    def test_analysis_result_with_data(self):
        from app.core.schemas_call_intelligence import (
            AnalysisResult,
            CallSignalInsight,
            FeatureInsight,
        )

        result = AnalysisResult(
            engagement_score=0.85,
            executive_summary="Great discovery call.",
            feature_insights=[
                FeatureInsight(
                    feature_name="Dashboard",
                    reaction="excited",
                    quote="I love the dashboard concept!",
                    is_aha_moment=True,
                )
            ],
            call_signals=[
                CallSignalInsight(
                    signal_type="pain_point",
                    title="Manual reporting",
                    intensity=0.9,
                )
            ],
        )
        assert result.engagement_score == 0.85
        assert len(result.feature_insights) == 1
        assert result.feature_insights[0].is_aha_moment is True
        assert result.call_signals[0].signal_type == "pain_point"

    def test_recording_status_literal(self):
        from app.core.schemas_call_intelligence import RecordingResponse

        resp = RecordingResponse(
            id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            status="transcribing",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert resp.status == "transcribing"

    def test_feature_insight_reaction_types(self):
        from app.core.schemas_call_intelligence import FeatureInsight

        for reaction in ["excited", "interested", "neutral", "confused", "resistant"]:
            fi = FeatureInsight(feature_name="Test", reaction=reaction)
            assert fi.reaction == reaction

    def test_call_signal_types(self):
        from app.core.schemas_call_intelligence import CallSignalInsight

        for stype in [
            "pain_point",
            "goal",
            "budget_indicator",
            "timeline",
            "decision_criteria",
            "risk_factor",
        ]:
            cs = CallSignalInsight(signal_type=stype, title="Test")
            assert cs.signal_type == stype

    def test_nugget_types(self):
        from app.core.schemas_call_intelligence import ContentNugget

        for ntype in [
            "testimonial",
            "soundbite",
            "statistic",
            "use_case",
            "objection",
            "vision_statement",
        ]:
            cn = ContentNugget(nugget_type=ntype, content="Test content")
            assert cn.nugget_type == ntype


# ============================================================================
# Deepgram client tests
# ============================================================================


class TestDeepgramClient:
    """Test Deepgram transcription client (mocked httpx)."""

    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        """Test successful transcription with mocked Deepgram response."""
        from app.services.deepgram_client import _parse_deepgram_response

        mock_response = {
            "results": {
                "channels": [
                    {"alternatives": [{"transcript": "Hello, how are you? I am fine, thank you."}]}
                ],
                "utterances": [
                    {
                        "speaker": 0,
                        "transcript": "Hello, how are you?",
                        "start": 0.0,
                        "end": 2.5,
                        "confidence": 0.95,
                    },
                    {
                        "speaker": 1,
                        "transcript": "I am fine, thank you.",
                        "start": 3.0,
                        "end": 5.5,
                        "confidence": 0.92,
                    },
                ],
            }
        }

        result = _parse_deepgram_response(mock_response)

        assert result.word_count > 0
        assert len(result.segments) == 2
        assert result.segments[0].speaker == "Speaker 0"
        assert result.segments[1].speaker == "Speaker 1"
        assert "0" in result.speaker_map
        assert "1" in result.speaker_map

    @pytest.mark.asyncio
    async def test_transcribe_no_api_key(self):
        """Test that missing API key raises ValueError."""
        from app.services.deepgram_client import transcribe_audio

        with patch("app.services.deepgram_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(DEEPGRAM_API_KEY=None)

            with pytest.raises(ValueError, match="DEEPGRAM_API_KEY"):
                await transcribe_audio("https://example.com/audio.mp3")

    @pytest.mark.asyncio
    async def test_parse_empty_response(self):
        """Test parsing an empty Deepgram response."""
        from app.services.deepgram_client import _parse_deepgram_response

        result = _parse_deepgram_response({})
        assert result.full_text == ""
        assert result.segments == []
        assert result.word_count == 0

    @pytest.mark.asyncio
    async def test_parse_no_utterances(self):
        """Test parsing response with channels but no utterances."""
        from app.services.deepgram_client import _parse_deepgram_response

        mock_response = {
            "results": {
                "channels": [{"alternatives": [{"transcript": "Some text here."}]}],
                "utterances": [],
            }
        }

        result = _parse_deepgram_response(mock_response)
        assert result.full_text == "Some text here."
        assert result.segments == []
        assert result.word_count == 3


# ============================================================================
# Recall service extension tests
# ============================================================================


class TestRecallExtensions:
    """Test new Recall service functions."""

    def test_extract_media_urls_full(self):
        """Test extracting URLs from a complete bot response."""
        from app.core.recall_service import extract_media_urls

        bot_data = {
            "output_media": {"camera": {"download_url": "https://recall.ai/video.mp4"}},
            "media": {
                "audio_url": "https://recall.ai/audio.wav",
                "video_url": "https://recall.ai/video2.mp4",
            },
            "recording": "https://recall.ai/recording.wav",
        }

        urls = extract_media_urls(bot_data)
        assert urls["video_url"] == "https://recall.ai/video.mp4"
        assert urls["audio_url"] == "https://recall.ai/audio.wav"
        assert urls["recording_url"] == "https://recall.ai/recording.wav"

    def test_extract_media_urls_minimal(self):
        """Test extracting URLs with minimal data."""
        from app.core.recall_service import extract_media_urls

        bot_data = {
            "recording_url": "https://recall.ai/recording.wav",
        }

        urls = extract_media_urls(bot_data)
        assert urls["video_url"] is None
        assert urls["audio_url"] == "https://recall.ai/recording.wav"  # fallback
        assert urls["recording_url"] == "https://recall.ai/recording.wav"

    def test_extract_media_urls_empty(self):
        """Test extracting URLs from empty bot data."""
        from app.core.recall_service import extract_media_urls

        urls = extract_media_urls({})
        assert urls["video_url"] is None
        assert urls["audio_url"] is None
        assert urls["recording_url"] is None

    def test_compute_duration_valid(self):
        """Test duration calculation from status changes."""
        from app.core.recall_service import compute_duration

        bot_data = {
            "status_changes": [
                {"code": "joining_call", "created_at": "2026-01-01T10:00:00Z"},
                {"code": "in_call_recording", "created_at": "2026-01-01T10:01:00Z"},
                {"code": "call_ended", "created_at": "2026-01-01T10:31:00Z"},
            ]
        }

        duration = compute_duration(bot_data)
        assert duration == 1800  # 30 minutes

    def test_compute_duration_missing(self):
        """Test duration calculation with missing timestamps."""
        from app.core.recall_service import compute_duration

        assert compute_duration({}) is None
        assert compute_duration({"status_changes": []}) is None
        assert (
            compute_duration(
                {
                    "status_changes": [
                        {"code": "joining_call", "created_at": "2026-01-01T10:00:00Z"},
                    ]
                }
            )
            is None
        )


# ============================================================================
# Analysis chain tests
# ============================================================================


class TestAnalysisChain:
    """Test analysis chain functions."""

    def test_resolve_dimensions_single_pack(self):
        """Test resolving a single dimension pack."""
        from app.chains.analyze_call import resolve_dimensions

        dims = resolve_dimensions("core")
        assert "engagement_score" in dims
        assert "talk_ratio" in dims
        assert "executive_summary" in dims
        assert len(dims) == 4

    def test_resolve_dimensions_multiple_packs(self):
        """Test resolving multiple dimension packs."""
        from app.chains.analyze_call import resolve_dimensions

        dims = resolve_dimensions("core,research")
        assert "engagement_score" in dims
        assert "feature_insights" in dims
        assert "content_nuggets" in dims
        assert len(dims) == 8

    def test_resolve_dimensions_unknown_pack(self):
        """Test that unknown packs are skipped."""
        from app.chains.analyze_call import resolve_dimensions

        dims = resolve_dimensions("core,nonexistent")
        assert len(dims) == 4
        assert "engagement_score" in dims

    def test_resolve_dimensions_empty(self):
        """Test resolving empty string."""
        from app.chains.analyze_call import resolve_dimensions

        dims = resolve_dimensions("")
        assert dims == []

    def test_dimension_packs_defined(self):
        """Verify expected packs are defined."""
        from app.chains.analyze_call import DIMENSION_PACKS

        assert "core" in DIMENSION_PACKS
        assert "research" in DIMENSION_PACKS
        assert len(DIMENSION_PACKS) == 2


# ============================================================================
# Config tests
# ============================================================================


class TestConfig:
    """Test config additions."""

    def test_call_intelligence_defaults(self):
        """Verify default config values for call intelligence."""

        # Just check the field definitions exist on Settings
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "DEEPGRAM_API_KEY" in fields
        assert "DEEPGRAM_MODEL" in fields
        assert "CALL_ANALYSIS_MODEL" in fields
        assert "CALL_ANALYSIS_MAX_TOKENS" in fields
        assert "CALL_ACTIVE_PACKS" in fields

        # Check defaults
        assert fields["DEEPGRAM_MODEL"].default == "nova-2"
        assert fields["CALL_ANALYSIS_MODEL"].default == "claude-sonnet-4-6"
        assert fields["CALL_ANALYSIS_MAX_TOKENS"].default == 16384
        assert fields["CALL_ACTIVE_PACKS"].default == "core,research"


# ============================================================================
# Service factory test
# ============================================================================


class TestServiceFactory:
    """Test get_call_intelligence_service factory."""

    def test_returns_none_without_deepgram(self):
        """Service factory returns None when DEEPGRAM_API_KEY is not set."""
        from app.services.call_intelligence import get_call_intelligence_service

        with patch("app.services.call_intelligence.get_settings") as mock:
            mock.return_value = MagicMock(DEEPGRAM_API_KEY=None)
            assert get_call_intelligence_service() is None

    def test_returns_service_with_deepgram(self):
        """Service factory returns service when DEEPGRAM_API_KEY is set."""
        from app.services.call_intelligence import (
            CallIntelligenceService,
            get_call_intelligence_service,
        )

        with patch("app.services.call_intelligence.get_settings") as mock:
            mock.return_value = MagicMock(DEEPGRAM_API_KEY="test-key")
            service = get_call_intelligence_service()
            assert isinstance(service, CallIntelligenceService)
