"""Tests for Pydantic model validation and serialization."""
import pytest
from pydantic import ValidationError

from maverick.models.schemas import (
    CreateValidationRequest,
    PainDiscoveryOutput,
    PainPoint,
    UserSegment,
    ValidationRun,
    ValidationStatus,
    Verdict,
    ViabilitySignal,
)


class TestPainPoint:
    def test_valid_pain_point(self):
        p = PainPoint(
            source="reddit",
            source_url="https://reddit.com/r/test/123",
            quote="This is annoying",
            author_context="Founder",
            pain_severity=3,
        )
        assert p.pain_severity == 3
        assert p.date is None

    def test_severity_out_of_range(self):
        with pytest.raises(ValidationError):
            PainPoint(
                source="reddit",
                source_url="https://reddit.com/r/test/123",
                quote="quote",
                author_context="Founder",
                pain_severity=6,
            )

    def test_severity_zero_rejected(self):
        with pytest.raises(ValidationError):
            PainPoint(
                source="reddit",
                source_url="https://reddit.com/r/test/123",
                quote="quote",
                author_context="Founder",
                pain_severity=0,
            )


class TestViabilitySignal:
    def test_confidence_bounds(self):
        s = ViabilitySignal(signal="test", direction="positive", confidence=0.5, source="test")
        assert s.confidence == 0.5

    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            ViabilitySignal(signal="test", direction="positive", confidence=1.5, source="test")

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            ViabilitySignal(signal="test", direction="positive", confidence=-0.1, source="test")


class TestValidationRun:
    def test_default_id_generation(self):
        run = ValidationRun(idea="test idea")
        assert run.id.startswith("val_")
        assert len(run.id) == 16  # "val_" + 12 hex chars

    def test_default_status_is_pending(self):
        run = ValidationRun(idea="test idea")
        assert run.status == ValidationStatus.PENDING

    def test_all_agent_outputs_initially_none(self):
        run = ValidationRun(idea="test idea")
        assert run.pain_discovery is None
        assert run.competitor_research is None
        assert run.viability is None
        assert run.synthesis is None


class TestCreateValidationRequest:
    def test_valid_idea(self):
        req = CreateValidationRequest(idea="AI pitch deck generator")
        assert req.idea == "AI pitch deck generator"

    def test_idea_too_short(self):
        with pytest.raises(ValidationError):
            CreateValidationRequest(idea="ab")

    def test_idea_too_long(self):
        with pytest.raises(ValidationError):
            CreateValidationRequest(idea="x" * 501)


class TestVerdict:
    def test_verdict_values(self):
        assert Verdict.BUILD == "BUILD"
        assert Verdict.SKIP == "SKIP"
        assert Verdict.MAYBE == "MAYBE"


class TestPainDiscoveryOutputSerialization:
    def test_roundtrip_json(self, sample_pain_discovery):
        json_str = sample_pain_discovery.model_dump_json()
        restored = PainDiscoveryOutput.model_validate_json(json_str)
        assert restored.idea == sample_pain_discovery.idea
        assert len(restored.pain_points) == len(sample_pain_discovery.pain_points)
        assert restored.primary_target_user.label == sample_pain_discovery.primary_target_user.label
