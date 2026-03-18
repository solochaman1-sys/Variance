from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(slots=True)
class VarianceInput:
    average_field_size: float
    paid_percent: float
    buyin: float
    rake_percent: float
    roi_percent: float
    tournaments_count: int
    bankroll: float | None = None


@dataclass(slots=True)
class PayoutEntry:
    start_place: int
    end_place: int
    payout: float

    @property
    def label(self) -> str:
        if self.start_place == self.end_place:
            return str(self.start_place)
        return f"{self.start_place}-{self.end_place}"


@dataclass(slots=True)
class PayoutStructure:
    entrants: int
    paid_places: int
    total_buyin: float
    net_buyin: float
    prize_pool: float
    min_cash: float
    payouts: list[float]
    entries: list[PayoutEntry]


@dataclass(slots=True)
class FinishDistribution:
    p_no_cash: float
    cash_probabilities: np.ndarray
    overall_itm_probability: float
    warning: str | None = None

    @property
    def probabilities(self) -> np.ndarray:
        return np.concatenate(([self.p_no_cash], self.cash_probabilities))


@dataclass(slots=True)
class AnalyticalMetrics:
    ev_per_tournament: float
    sigma_per_tournament: float
    ev_total: float
    sigma_total: float
    confidence_intervals: dict[str, tuple[float, float]]
    probability_of_loss: float


@dataclass(slots=True)
class SimulationResult:
    final_results: np.ndarray
    sample_paths: np.ndarray
    mean_path: np.ndarray
    displayed_best_path: np.ndarray
    displayed_worst_path: np.ndarray
    displayed_paths: np.ndarray
    ruin_indicator: np.ndarray
    required_bankroll_per_run: np.ndarray
    simulated_ev_total: float
    simulated_sigma_total: float
    simulated_roi_percent: float


@dataclass(slots=True)
class BankrollRecommendation:
    target_risk: float
    required_bankroll: float


@dataclass(slots=True)
class BankrollAssessment:
    recommendations: Sequence[BankrollRecommendation]
    current_bankroll: float | None
    estimated_risk_of_ruin: float | None
    safe_run_share: float | None


@dataclass(slots=True)
class CalculationResult:
    params: VarianceInput
    payout_structure: PayoutStructure
    finish_distribution: FinishDistribution
    analytics: AnalyticalMetrics
    simulation: SimulationResult
    bankroll: BankrollAssessment
    warnings: list[str]
