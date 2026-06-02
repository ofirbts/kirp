from pathlib import Path

import pytest
from sqlalchemy.orm import DeclarativeBase

_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "name,needle",
    [
        ("RUNTIME_REALITY_MATRIX.md", "Runtime Reality Matrix"),
        ("FAILURE_SEMANTICS.md", "Kafka unavailable"),
        ("ARCHITECTURE_TRACEABILITY.md", "Architecture traceability"),
        ("OPERATIONAL_CONFIDENCE.md", "Operational confidence"),
        ("PRODUCTION_READINESS_REVIEW.md", "Production readiness review"),
        ("RUNTIME_GUARANTEES.md", "Runtime guarantees matrix"),
        ("TENANT_ISOLATION_REVIEW.md", "Tenant isolation review"),
        ("SIDE_EFFECT_AND_REPLAY_SAFETY.md", "Side-effect and replay safety"),
        ("OBSERVABILITY_REVIEW.md", "Observability review"),
        ("CHAOS_AND_RECOVERY.md", "Chaos and recovery"),
        ("SKEPTICAL_STAFF_REVIEW.md", "Skeptical staff review"),
        ("RISK_REGISTER.md", "Risk register"),
        ("AUTHORIZATION_BOUNDARY_AUDIT.md", "Authorization boundary audit"),
        ("REMEDIATION_PLAN.md", "Remediation plan"),
        ("VERIFICATION_STRATEGY.md", "Verification strategy"),
        ("PRODUCTION_GATES.md", "Production gates"),
        ("ENGINEERING_COMMAND_MODEL.md", "Engineering command model"),
    ],
)
def test_operational_truth_docs_exist_and_anchor(name: str, needle: str) -> None:
    path = _ROOT / "docs" / name
    text = path.read_text(encoding="utf-8")
    assert path.is_file()
    assert needle in text


def test_runtime_matrix_has_subsystem_table_header() -> None:
    text = (_ROOT / "docs" / "RUNTIME_REALITY_MATRIX.md").read_text(encoding="utf-8")
    assert "| Subsystem |" in text
    assert "doc_only" in text


def test_runtime_guarantees_matrix_has_delivery_column() -> None:
    text = (_ROOT / "docs" / "RUNTIME_GUARANTEES.md").read_text(encoding="utf-8")
    assert "| Delivery |" in text or "| Operation |" in text
    assert "UNVERIFIED" in text


def test_tenant_isolation_review_flags_governance() -> None:
    text = (_ROOT / "docs" / "TENANT_ISOLATION_REVIEW.md").read_text(encoding="utf-8")
    assert "governance" in text.lower()
    assert "get_by_id" in text


def test_production_gates_lists_blockers() -> None:
    text = (_ROOT / "docs" / "PRODUCTION_GATES.md").read_text(encoding="utf-8")
    assert "PG-01" in text
    assert "FAIL" in text


def test_risk_register_has_p0_governance() -> None:
    text = (_ROOT / "docs" / "RISK_REGISTER.md").read_text(encoding="utf-8")
    assert "R-001" in text
    assert "P0" in text


def test_skeptical_review_has_scores() -> None:
    text = (_ROOT / "docs" / "SKEPTICAL_STAFF_REVIEW.md").read_text(encoding="utf-8")
    assert "/ 10" in text
    assert "Would I approve" in text


def test_sqlalchemy_base_is_declarative_v2() -> None:
    from src.models.base import Base

    assert issubclass(Base, DeclarativeBase)
    assert Base.metadata is not None
