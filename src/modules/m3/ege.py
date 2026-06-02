"""
M3 IdentityOS — Entropy Governance Engine (EGE) extension.

IdentityEntropyScore (0.0–1.0) drives auto-approve vs Discriminator vs Human (WhatsApp).
Thresholds: < 0.3 auto-approve; 0.3–0.6 Discriminator; >= 0.6 escalate.
All inputs auditable and explainable.
"""

from __future__ import annotations

from typing import Any

# Thresholds per spec 5.2
AUTO_APPROVE_THRESHOLD = 0.3
DISCRIMINATOR_THRESHOLD = 0.6


def compute_identity_entropy_score(metadata: dict[str, Any], event_type: str) -> float:
    """
    Composite score: cognitive_load_norm + drift_risk_norm + reversibility_norm.
    Weights and norms tuned for explainability; default 0.0 when no M3 signals.
    """
    score = 0.0
    # Cognitive load: e.g. number of micro_actions in one plan (> 5 = +entropy)
    action_count = 0
    if "context_event_ids" in metadata and isinstance(metadata["context_event_ids"], list):
        action_count = len(metadata["context_event_ids"])
    if "micro_action_count" in metadata and isinstance(metadata["micro_action_count"], (int, float)):
        action_count = max(action_count, int(metadata["micro_action_count"]))
    cognitive_norm = min(1.0, action_count / 5.0) * 0.33  # w1 ≈ 0.33

    # Identity drift risk: pillar_deltas or trajectory change
    drift_norm = 0.0
    if "pillar_deltas" in metadata and isinstance(metadata["pillar_deltas"], dict):
        deltas = metadata["pillar_deltas"]
        if deltas:
            max_delta = max(abs(v) for v in deltas.values() if isinstance(v, (int, float)))
            drift_norm = min(1.0, max_delta) * 0.33
    if "identity_entropy_score" in metadata and isinstance(metadata["identity_entropy_score"], (int, float)):
        drift_norm = max(drift_norm, float(metadata["identity_entropy_score"]) * 0.33)

    # Reversibility: monthly_evolution and trajectory = higher cost
    reversibility_norm = 0.0
    if "m3.monthly_evolution_updated" in event_type or "monthly_evolution" in event_type:
        reversibility_norm = 0.34
    if metadata.get("new_goals") or metadata.get("pillar_shifts"):
        reversibility_norm = max(reversibility_norm, 0.34)

    score = min(1.0, cognitive_norm + drift_norm + reversibility_norm)
    return round(score, 4)


def requires_discriminator(score: float) -> bool:
    """True if 0.3 <= score < 0.6."""
    return AUTO_APPROVE_THRESHOLD <= score < DISCRIMINATOR_THRESHOLD


def requires_human_governance(score: float) -> bool:
    """True if score >= 0.6."""
    return score >= DISCRIMINATOR_THRESHOLD
