"""T039: Evidence gate logic — three-leg citations required for true-positive."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GateResult:
    passed: bool
    missing_legs: list[str] = field(default_factory=list)
    unresolved_citations: list[str] = field(default_factory=list)


def check_evidence_gate(
    citations: dict[str, Optional[str]],
    resolvable: set[str],
) -> GateResult:
    """
    Minimal gate implementation for testing.

    citations: {"reachability": symbol_or_None, "trust_boundary": ..., "impact": ...}
    resolvable: set of symbol names that exist in the code index.
    """
    required_legs = ["reachability", "trust_boundary", "impact"]
    missing_legs = [leg for leg in required_legs if not citations.get(leg)]
    unresolved = []
    for leg in required_legs:
        sym = citations.get(leg)
        if sym and sym not in resolvable:
            unresolved.append(sym)

    passed = not missing_legs and not unresolved
    return GateResult(passed=passed, missing_legs=missing_legs, unresolved_citations=unresolved)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_three_legs_present_and_resolvable():
    result = check_evidence_gate(
        citations={
            "reachability": "app.routes.login",
            "trust_boundary": "app.middleware.auth",
            "impact": "app.db.query",
        },
        resolvable={"app.routes.login", "app.middleware.auth", "app.db.query"},
    )
    assert result.passed is True
    assert not result.missing_legs
    assert not result.unresolved_citations


def test_missing_reachability_leg_fails():
    result = check_evidence_gate(
        citations={
            "reachability": None,
            "trust_boundary": "app.middleware.auth",
            "impact": "app.db.query",
        },
        resolvable={"app.middleware.auth", "app.db.query"},
    )
    assert result.passed is False
    assert "reachability" in result.missing_legs


def test_missing_trust_boundary_leg_fails():
    result = check_evidence_gate(
        citations={
            "reachability": "app.routes.login",
            "trust_boundary": None,
            "impact": "app.db.query",
        },
        resolvable={"app.routes.login", "app.db.query"},
    )
    assert result.passed is False
    assert "trust_boundary" in result.missing_legs


def test_missing_impact_leg_fails():
    result = check_evidence_gate(
        citations={
            "reachability": "app.routes.login",
            "trust_boundary": "app.middleware.auth",
            "impact": None,
        },
        resolvable={"app.routes.login", "app.middleware.auth"},
    )
    assert result.passed is False
    assert "impact" in result.missing_legs


def test_unresolvable_citation_demotes():
    result = check_evidence_gate(
        citations={
            "reachability": "app.routes.login",
            "trust_boundary": "nonexistent.function",
            "impact": "app.db.query",
        },
        resolvable={"app.routes.login", "app.db.query"},
    )
    assert result.passed is False
    assert "nonexistent.function" in result.unresolved_citations


def test_all_missing_legs_reported():
    result = check_evidence_gate(
        citations={"reachability": None, "trust_boundary": None, "impact": None},
        resolvable=set(),
    )
    assert result.passed is False
    assert len(result.missing_legs) == 3
