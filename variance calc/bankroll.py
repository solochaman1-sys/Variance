from __future__ import annotations

from typing import Sequence

import numpy as np

from models import BankrollAssessment, BankrollRecommendation, SimulationResult


DEFAULT_RISK_TARGETS: tuple[float, ...] = (0.50, 0.15, 0.05, 0.01)


def estimate_bankroll(
    simulation: SimulationResult,
    current_bankroll: float | None,
    risk_targets: Sequence[float] = DEFAULT_RISK_TARGETS,
) -> BankrollAssessment:
    required = simulation.required_bankroll_per_run
    recommendations: list[BankrollRecommendation] = []
    for target in risk_targets:
        quantile = float(np.quantile(required, 1.0 - target))
        recommendations.append(
            BankrollRecommendation(
                target_risk=target,
                required_bankroll=max(0.0, quantile),
            )
        )

    estimated_risk = None
    safe_run_share = None
    if current_bankroll is not None:
        estimated_risk = float(np.mean(required > current_bankroll))
        safe_run_share = float(np.mean(required <= current_bankroll))

    return BankrollAssessment(
        recommendations=recommendations,
        current_bankroll=current_bankroll,
        estimated_risk_of_ruin=estimated_risk,
        safe_run_share=safe_run_share,
    )
