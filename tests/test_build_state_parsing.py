"""Tests for state builder output parsing and validation."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_state import BuildStateOutput


def _make_personas(n=2):
    """Helper to create n persona dicts for BuildStateOutput."""
    return [
        {
            "slug": f"persona-{i}",
            "name": f"Persona {i}",
            "role": f"Role {i}",
            "demographics": {},
            "psychographics": {},
            "goals": [f"Goal {i}"],
            "pain_points": [f"Pain {i}"],
            "description": f"Description {i}",
        }
        for i in range(1, n + 1)
    ]


class TestBuildStateOutputValidation:
    def test_valid_output(self):
        """Test parsing valid state builder output."""
        data = {
            "vp_steps": [
                {
                    "step_index": 1,
                    "label": "Step 1 — Initial Assessment",
                    "status": "draft",
                    "description": "Consultant performs initial assessment",
                    "user_benefit_pain": "Faster diagnosis",
                    "ui_overview": "Dashboard with metrics",
                    "value_created": "Quick insights",
                    "kpi_impact": "Reduced time to value",
                    "needed": [],
                    "sources": [],
                    "evidence": [],
                }
            ],
            "features": [
                {
                    "name": "Diagnostic Wizard",
                    "category": "Core",
                    "is_mvp": True,
                    "confidence": "high",
                    "status": "draft",
                    "evidence": [],
                }
            ],
            "personas": _make_personas(2),
        }

        output = BuildStateOutput.model_validate(data)
        assert len(output.vp_steps) == 1
        assert len(output.features) == 1
        assert len(output.personas) == 2

    def test_valid_json_string(self):
        """Test parsing from JSON string."""
        json_str = json.dumps({
            "vp_steps": [],
            "features": [],
            "personas": _make_personas(2),
        })

        data = json.loads(json_str)
        output = BuildStateOutput.model_validate(data)
        assert len(output.personas) == 2

    def test_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        with pytest.raises(ValidationError):
            BuildStateOutput.model_validate({
                "vp_steps": [],
                # Missing features and personas
            })

    def test_personas_min_length_enforced(self):
        """Test that personas requires at least 2 items."""
        with pytest.raises(ValidationError):
            BuildStateOutput.model_validate({
                "vp_steps": [],
                "features": [],
                "personas": _make_personas(1),  # Only 1 — should fail
            })

    def test_empty_vp_and_features_valid(self):
        """Test that empty vp_steps and features are valid."""
        output = BuildStateOutput.model_validate({
            "vp_steps": [],
            "features": [],
            "personas": _make_personas(2),
        })
        assert len(output.vp_steps) == 0
        assert len(output.features) == 0
        assert len(output.personas) == 2

    def test_multiple_items(self):
        """Test parsing output with multiple items."""
        data = {
            "vp_steps": [
                {
                    "step_index": 1,
                    "label": "Step 1",
                    "status": "draft",
                    "description": "First step",
                    "user_benefit_pain": "",
                    "ui_overview": "",
                    "value_created": "",
                    "kpi_impact": "",
                    "needed": [],
                    "sources": [],
                    "evidence": [],
                },
                {
                    "step_index": 2,
                    "label": "Step 2",
                    "status": "draft",
                    "description": "Second step",
                    "user_benefit_pain": "",
                    "ui_overview": "",
                    "value_created": "",
                    "kpi_impact": "",
                    "needed": [],
                    "sources": [],
                    "evidence": [],
                },
            ],
            "features": [
                {
                    "name": "Feature 1",
                    "category": "Core",
                    "is_mvp": True,
                    "confidence": "high",
                    "status": "draft",
                    "evidence": [],
                },
                {
                    "name": "Feature 2",
                    "category": "Security",
                    "is_mvp": False,
                    "confidence": "medium",
                    "status": "draft",
                    "evidence": [],
                },
            ],
            "personas": _make_personas(3),
        }

        output = BuildStateOutput.model_validate(data)
        assert len(output.vp_steps) == 2
        assert len(output.features) == 2
        assert len(output.personas) == 3
