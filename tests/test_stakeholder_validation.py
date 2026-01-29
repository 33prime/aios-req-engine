"""Tests for stakeholder validation (people-only filter)."""

import pytest
from app.core.stakeholder_validation import is_likely_person, filter_people_only


class TestIsLikelyPerson:
    """Tests for is_likely_person function."""

    def test_valid_person_names(self):
        """Should accept valid person names."""
        assert is_likely_person("John Smith") is True
        assert is_likely_person("Sarah Johnson") is True
        assert is_likely_person("Dr. Jane Doe") is True
        assert is_likely_person("Michael O'Brien") is True
        assert is_likely_person("Jean-Pierre Dubois") is True
        assert is_likely_person("Mary Jane Watson") is True

    def test_organization_names_rejected(self):
        """Should reject organization names."""
        assert is_likely_person("Engineering Team") is False
        assert is_likely_person("Sales Department") is False
        assert is_likely_person("The Board") is False
        assert is_likely_person("Acme Inc") is False
        assert is_likely_person("Product Committee") is False
        assert is_likely_person("HR Group") is False
        assert is_likely_person("Finance Division") is False

    def test_department_only_names_rejected(self):
        """Should reject single department names."""
        assert is_likely_person("Engineering") is False
        assert is_likely_person("Sales") is False
        assert is_likely_person("Marketing") is False
        assert is_likely_person("Product") is False
        assert is_likely_person("Design") is False
        assert is_likely_person("HR") is False
        assert is_likely_person("Finance") is False
        assert is_likely_person("Legal") is False
        assert is_likely_person("Ops") is False
        assert is_likely_person("Operations") is False

    def test_edge_cases(self):
        """Should handle edge cases."""
        assert is_likely_person("") is False
        assert is_likely_person("A") is False
        assert is_likely_person("  ") is False

    def test_single_names(self):
        """Should accept single names (might be nicknames)."""
        assert is_likely_person("Sarah") is True
        assert is_likely_person("Mike") is True
        assert is_likely_person("Bob") is True

    def test_company_suffixes_rejected(self):
        """Should reject names with company suffixes."""
        assert is_likely_person("Acme Corp") is False
        assert is_likely_person("Smith LLC") is False
        assert is_likely_person("Johnson Ltd") is False
        assert is_likely_person("Tech Company") is False
        assert is_likely_person("Acme Inc") is False

    def test_title_prefixes_accepted(self):
        """Should accept names with title prefixes."""
        assert is_likely_person("Dr. Smith") is True
        assert is_likely_person("Mr. Johnson") is True
        assert is_likely_person("Mrs. Williams") is True
        assert is_likely_person("Ms. Davis") is True
        assert is_likely_person("Prof. Miller") is True


class TestFilterPeopleOnly:
    """Tests for filter_people_only function."""

    def test_filters_mixed_list(self):
        """Should filter out non-people from mixed list."""
        stakeholders = [
            {"name": "John Smith", "role": "CEO"},
            {"name": "Engineering Team", "role": "Developers"},
            {"name": "Sarah Johnson", "role": "PM"},
            {"name": "The Board", "role": "Governance"},
        ]

        result = filter_people_only(stakeholders)

        assert len(result) == 2
        names = [s["name"] for s in result]
        assert "John Smith" in names
        assert "Sarah Johnson" in names
        assert "Engineering Team" not in names
        assert "The Board" not in names

    def test_empty_list(self):
        """Should handle empty list."""
        assert filter_people_only([]) == []

    def test_all_people(self):
        """Should preserve list of all people."""
        stakeholders = [
            {"name": "John Smith"},
            {"name": "Jane Doe"},
        ]

        result = filter_people_only(stakeholders)

        assert len(result) == 2

    def test_all_organizations(self):
        """Should return empty list if all are organizations."""
        stakeholders = [
            {"name": "Engineering Team"},
            {"name": "Sales Department"},
            {"name": "Marketing Group"},
        ]

        result = filter_people_only(stakeholders)

        assert len(result) == 0

    def test_preserves_other_fields(self):
        """Should preserve other fields in stakeholder dicts."""
        stakeholders = [
            {"name": "John Smith", "role": "CEO", "email": "john@example.com"},
        ]

        result = filter_people_only(stakeholders)

        assert len(result) == 1
        assert result[0]["role"] == "CEO"
        assert result[0]["email"] == "john@example.com"

    def test_handles_missing_name_field(self):
        """Should handle stakeholders without name field."""
        stakeholders = [
            {"role": "CEO"},  # No name field
            {"name": "John Smith", "role": "CFO"},
        ]

        result = filter_people_only(stakeholders)

        assert len(result) == 1
        assert result[0]["name"] == "John Smith"
