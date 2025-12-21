"""Tests for state builder output parsing and validation."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.schemas_state import BuildStateOutput


class TestBuildStateOutputValidation:
    def test_valid_output(self):
        """Test parsing valid state builder output."""
        chunk_id = str(uuid4())
        data = {
            "prd_sections": [
                {
                    "slug": "personas",
                    "label": "Personas",
                    "required": True,
                    "status": "draft",
                    "fields": {"content": "Business consultants"},
                    "client_needs": [],
                    "sources": [],
                    "evidence": [
                        {
                            "chunk_id": chunk_id,
                            "excerpt": "Consultant approves recommendations",
                            "rationale": "Shows consultant role",
                        }
                    ],
                }
            ],
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
        }

        output = BuildStateOutput.model_validate(data)
        assert len(output.prd_sections) == 1
        assert len(output.vp_steps) == 1
        assert len(output.features) == 1

    def test_valid_json_string(self):
        """Test parsing from JSON string."""
        json_str = json.dumps({
            "prd_sections": [
                {
                    "slug": "key_features",
                    "label": "Key Features",
                    "required": True,
                    "status": "draft",
                    "fields": {},
                    "client_needs": [],
                    "sources": [],
                    "evidence": [],
                }
            ],
            "vp_steps": [],
            "features": [],
        })

        data = json.loads(json_str)
        output = BuildStateOutput.model_validate(data)
        assert len(output.prd_sections) == 1

    def test_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        with pytest.raises(ValidationError):
            BuildStateOutput.model_validate({
                "prd_sections": [],
                # Missing vp_steps and features
            })

    def test_empty_arrays_valid(self):
        """Test that empty arrays are valid."""
        output = BuildStateOutput.model_validate({
            "prd_sections": [],
            "vp_steps": [],
            "features": [],
        })
        assert len(output.prd_sections) == 0
        assert len(output.vp_steps) == 0
        assert len(output.features) == 0

    def test_multiple_items(self):
        """Test parsing output with multiple items."""
        data = {
            "prd_sections": [
                {
                    "slug": "personas",
                    "label": "Personas",
                    "required": True,
                    "status": "draft",
                    "fields": {},
                    "client_needs": [],
                    "sources": [],
                    "evidence": [],
                },
                {
                    "slug": "key_features",
                    "label": "Key Features",
                    "required": True,
                    "status": "draft",
                    "fields": {},
                    "client_needs": [],
                    "sources": [],
                    "evidence": [],
                },
                {
                    "slug": "constraints",
                    "label": "Constraints",
                    "required": False,
                    "status": "draft",
                    "fields": {},
                    "client_needs": [],
                    "sources": [],
                    "evidence": [],
                },
            ],
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
        }

        output = BuildStateOutput.model_validate(data)
        assert len(output.prd_sections) == 3
        assert len(output.vp_steps) == 2
        assert len(output.features) == 2

    def test_client_needs_structure(self):
        """Test client_needs array structure."""
        data = {
            "prd_sections": [
                {
                    "slug": "personas",
                    "label": "Personas",
                    "required": True,
                    "status": "draft",
                    "fields": {},
                    "client_needs": [
                        {
                            "key": "industry_support",
                            "title": "Which industries to support?",
                            "why": "Different industries have different needs",
                            "ask": "Please specify target industries",
                        }
                    ],
                    "sources": [],
                    "evidence": [],
                }
            ],
            "vp_steps": [],
            "features": [],
        }

        output = BuildStateOutput.model_validate(data)
        assert len(output.prd_sections[0]["client_needs"]) == 1
        assert output.prd_sections[0]["client_needs"][0]["key"] == "industry_support"

