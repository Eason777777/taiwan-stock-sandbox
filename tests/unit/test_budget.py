"""T071: BudgetGovernor — caps fire at correct thresholds; should_auto_stop requires all preconditions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Minimal stubs mirroring the real BudgetGovernor logic
# ---------------------------------------------------------------------------

@dataclass
class BudgetConfig:
    spend_cap_usd: Optional[float] = None
    time_cap_hours: Optional[float] = None
    yield_threshold: float = 2.0
    yield_window_usd: float = 5.0
    min_runtime_hours: float = 0.5
    severity_weights: dict = field(default_factory=lambda: {
        "critical": 100, "high": 31, "medium": 10, "low": 3
    })
    exploited_multiplier: float = 2.0


@dataclass
class EvalConfig:
    budget: BudgetConfig = field(default_factory=BudgetConfig)


def check_caps(
    total_spend: float,
    elapsed_hours: float,
    config: EvalConfig,
) -> Optional[str]:
    b = config.budget
    if b.spend_cap_usd is not None and total_spend >= b.spend_cap_usd:
        return "spend_cap"
    if b.time_cap_hours is not None and elapsed_hours >= b.time_cap_hours:
        return "time_cap"
    return None


def should_auto_stop(
    total_spend: float,
    elapsed_hours: float,
    coverage_complete: bool,
    trailing_yield: float,
    accumulated_window: float,
    config: EvalConfig,
) -> bool:
    b = config.budget
    full_window = accumulated_window >= b.yield_window_usd
    min_runtime_met = elapsed_hours >= b.min_runtime_hours
    below_threshold = trailing_yield < b.yield_threshold
    return full_window and min_runtime_met and coverage_complete and below_threshold


# ---------------------------------------------------------------------------
# Tests: check_caps
# ---------------------------------------------------------------------------

def test_spend_cap_fires_at_threshold():
    cfg = EvalConfig(budget=BudgetConfig(spend_cap_usd=10.0))
    assert check_caps(10.0, 0.1, cfg) == "spend_cap"


def test_spend_cap_fires_above_threshold():
    cfg = EvalConfig(budget=BudgetConfig(spend_cap_usd=10.0))
    assert check_caps(15.0, 0.1, cfg) == "spend_cap"


def test_spend_cap_does_not_fire_below():
    cfg = EvalConfig(budget=BudgetConfig(spend_cap_usd=10.0))
    assert check_caps(9.99, 0.1, cfg) is None


def test_time_cap_fires_at_threshold():
    cfg = EvalConfig(budget=BudgetConfig(time_cap_hours=2.0))
    assert check_caps(0.0, 2.0, cfg) == "time_cap"


def test_time_cap_does_not_fire_below():
    cfg = EvalConfig(budget=BudgetConfig(time_cap_hours=2.0))
    assert check_caps(0.0, 1.9, cfg) is None


def test_no_caps_configured_always_none():
    cfg = EvalConfig(budget=BudgetConfig())
    assert check_caps(999.0, 999.0, cfg) is None


def test_spend_cap_takes_priority_over_time_cap():
    cfg = EvalConfig(budget=BudgetConfig(spend_cap_usd=5.0, time_cap_hours=1.0))
    result = check_caps(10.0, 2.0, cfg)
    assert result == "spend_cap"


# ---------------------------------------------------------------------------
# Tests: should_auto_stop (all three preconditions required)
# ---------------------------------------------------------------------------

def test_auto_stop_requires_all_three_conditions():
    cfg = EvalConfig(budget=BudgetConfig(yield_threshold=2.0, yield_window_usd=5.0, min_runtime_hours=0.5))
    # All met
    assert should_auto_stop(
        total_spend=10.0, elapsed_hours=1.0, coverage_complete=True,
        trailing_yield=1.0, accumulated_window=6.0, config=cfg
    ) is True


def test_auto_stop_false_if_coverage_incomplete():
    cfg = EvalConfig(budget=BudgetConfig(yield_threshold=2.0, yield_window_usd=5.0, min_runtime_hours=0.5))
    assert should_auto_stop(
        total_spend=10.0, elapsed_hours=1.0, coverage_complete=False,
        trailing_yield=1.0, accumulated_window=6.0, config=cfg
    ) is False


def test_auto_stop_false_if_min_runtime_not_met():
    cfg = EvalConfig(budget=BudgetConfig(yield_threshold=2.0, yield_window_usd=5.0, min_runtime_hours=0.5))
    assert should_auto_stop(
        total_spend=10.0, elapsed_hours=0.2, coverage_complete=True,
        trailing_yield=1.0, accumulated_window=6.0, config=cfg
    ) is False


def test_auto_stop_false_if_window_not_full():
    cfg = EvalConfig(budget=BudgetConfig(yield_threshold=2.0, yield_window_usd=5.0, min_runtime_hours=0.5))
    assert should_auto_stop(
        total_spend=10.0, elapsed_hours=1.0, coverage_complete=True,
        trailing_yield=1.0, accumulated_window=3.0, config=cfg
    ) is False


def test_auto_stop_false_if_yield_above_threshold():
    cfg = EvalConfig(budget=BudgetConfig(yield_threshold=2.0, yield_window_usd=5.0, min_runtime_hours=0.5))
    assert should_auto_stop(
        total_spend=10.0, elapsed_hours=1.0, coverage_complete=True,
        trailing_yield=5.0, accumulated_window=6.0, config=cfg
    ) is False
