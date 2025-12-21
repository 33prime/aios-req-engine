"""Tests for reconcile output parsing and validation."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_reconcile import ReconcileOutput


class TestReconcileOutputParsing:
    def test_parse_valid_output(self):
        """Test parsing a valid reconcile output."""
        chunk_id = uuid4()
        output_json = {
            "summary": "Updated PRD constraints and added 2 features",
            "prd_section_patches": [
                {
                    "slug": "constraints",
                    "set_fields": {"technical": "Must use Python 3.10+"},
                    "set_status": "needs_confirmation",
                    "add_client_needs": [],
                    "evidence": [
                        {
                            "chunk_id": str(chunk_id),
                            "excerpt": "We need Python 3.10",
                            "rationale": "Client specified version",
                        }
                    ],
                }
            ],
            "vp_step_patches": [],
            "feature_ops": [
                {
                    "op": "upsert",
                    "name": "User authentication",
                    "category": "Security",
                    "is_mvp": True,
                    "confidence": "high",
                    "set_status": "draft",
                    "evidence": [],
                    "reason": "Core requirement",
                }
            ],
            "confirmation_items": [
                {
                    "key": "prd:constraints:python_version",
                    "kind": "prd",
                    "title": "Python version confirmation",
                    "why": "Need to confirm version requirement",
                    "ask": "Is Python 3.10+ acceptable?",
                    "priority": "medium",
                    "suggested_method": "email",
                    "evidence": [],
                    "target_table": "prd_sections",
                    "target_id": None,
                }
            ],
        }

        result = ReconcileOutput.model_validate(output_json)

        assert result.summary == "Updated PRD constraints and added 2 features"
        assert len(result.prd_section_patches) == 1
        assert len(result.feature_ops) == 1
        assert len(result.confirmation_items) == 1

    def test_parse_minimal_output(self):
        """Test parsing minimal valid output (no changes)."""
        output_json = {
            "summary": "No changes needed",
            "prd_section_patches": [],
            "vp_step_patches": [],
            "feature_ops": [],
            "confirmation_items": [],
        }

        result = ReconcileOutput.model_validate(output_json)

        assert result.summary == "No changes needed"
        assert len(result.prd_section_patches) == 0
        assert len(result.feature_ops) == 0

    def test_parse_vp_step_patch(self):
        """Test parsing VP step patch."""
        output_json = {
            "summary": "Updated VP step 1",
            "prd_section_patches": [],
            "vp_step_patches": [
                {
                    "step_index": 1,
                    "set": {"label": "User Login", "description": "User logs in to system"},
                    "set_status": "draft",
                    "add_needed": [],
                    "evidence": [],
                }
            ],
            "feature_ops": [],
            "confirmation_items": [],
        }

        result = ReconcileOutput.model_validate(output_json)

        assert len(result.vp_step_patches) == 1
        assert result.vp_step_patches[0].step_index == 1
        assert result.vp_step_patches[0].set["label"] == "User Login"

    def test_parse_feature_deprecate_op(self):
        """Test parsing feature deprecate operation."""
        output_json = {
            "summary": "Deprecated old feature",
            "prd_section_patches": [],
            "vp_step_patches": [],
            "feature_ops": [
                {
                    "op": "deprecate",
                    "name": "Legacy API",
                    "category": "Integration",
                    "is_mvp": False,
                    "confidence": "high",
                    "set_status": None,
                    "evidence": [],
                    "reason": "No longer needed",
                }
            ],
            "confirmation_items": [],
        }

        result = ReconcileOutput.model_validate(output_json)

        assert len(result.feature_ops) == 1
        assert result.feature_ops[0].op == "deprecate"
        assert result.feature_ops[0].reason == "No longer needed"

    def test_parse_invalid_missing_summary(self):
        """Test parsing fails when summary is missing."""
        output_json = {
            "prd_section_patches": [],
            "vp_step_patches": [],
            "feature_ops": [],
            "confirmation_items": [],
        }

        with pytest.raises(ValidationError) as exc_info:
            ReconcileOutput.model_validate(output_json)

        assert "summary" in str(exc_info.value)

    def test_parse_invalid_status(self):
        """Test parsing fails with invalid status."""
        output_json = {
            "summary": "Test",
            "prd_section_patches": [
                {
                    "slug": "constraints",
                    "set_fields": None,
                    "set_status": "invalid_status",
                    "add_client_needs": [],
                    "evidence": [],
                }
            ],
            "vp_step_patches": [],
            "feature_ops": [],
            "confirmation_items": [],
        }

        with pytest.raises(ValidationError):
            ReconcileOutput.model_validate(output_json)

    def test_parse_confirmation_item_with_all_fields(self):
        """Test parsing confirmation item with all fields."""
        chunk_id = uuid4()
        output_json = {
            "summary": "Test",
            "prd_section_patches": [],
            "vp_step_patches": [],
            "feature_ops": [],
            "confirmation_items": [
                {
                    "key": "feature:auth:oauth",
                    "kind": "feature",
                    "title": "OAuth provider selection",
                    "why": "Multiple OAuth providers mentioned",
                    "ask": "Which OAuth providers should we support?",
                    "priority": "high",
                    "suggested_method": "meeting",
                    "evidence": [
                        {
                            "chunk_id": str(chunk_id),
                            "excerpt": "Support Google and GitHub login",
                            "rationale": "Client mentioned both providers",
                        }
                    ],
                    "target_table": "features",
                    "target_id": str(uuid4()),
                }
            ],
        }

        result = ReconcileOutput.model_validate(output_json)

        assert len(result.confirmation_items) == 1
        item = result.confirmation_items[0]
        assert item.kind == "feature"
        assert item.priority == "high"
        assert item.suggested_method == "meeting"
        assert len(item.evidence) == 1

    def test_json_serialization_roundtrip(self):
        """Test that output can be serialized and deserialized."""
        chunk_id = uuid4()
        output = ReconcileOutput(
            summary="Test output",
            prd_section_patches=[],
            vp_step_patches=[],
            feature_ops=[],
            confirmation_items=[],
        )

        # Serialize to JSON
        json_str = output.model_dump_json()

        # Deserialize back
        parsed = json.loads(json_str)
        result = ReconcileOutput.model_validate(parsed)

        assert result.summary == "Test output"

