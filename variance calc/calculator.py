from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from bankroll import estimate_bankroll
from models import AnalyticalMetrics, CalculationResult, VarianceInput
from payout_model import PayoutModelError, build_payout_structure
from simulator import FinishDistributionError, build_finish_distribution, run_monte_carlo


class CalculationError(ValueError):
    """Пользовательская ошибка расчета."""


def validate_inputs(params: VarianceInput) -> None:
    if params.average_field_size <= 2:
        raise CalculationError("Среднее поле должно быть больше 2.")
    if not (0 < params.paid_percent < 50):
        raise CalculationError("Процент призовых мест должен быть больше 0 и меньше 50.")
    if params.buyin <= 0:
        raise CalculationError("Бай-ин должен быть больше 0.")
    if not (0 <= params.rake_percent <= 30):
        raise CalculationError("Рейк должен быть в диапазоне от 0% до 30%.")
    if not (-100 <= params.roi_percent <= 500):
        raise CalculationError("ROI должен быть в диапазоне от -100% до 500%.")
    if params.tournaments_count <= 0:
        raise CalculationError("Количество турниров должно быть больше 0.")
    if params.bankroll is not None and params.bankroll <= 0:
        raise CalculationError("Банкролл должен быть больше 0.")


def compute_analytical_metrics(
    params: VarianceInput,
    payouts: np.ndarray,
    probabilities: np.ndarray,
) -> AnalyticalMetrics:
    buyin = params.buyin
    roi = params.roi_percent / 100.0
    outcomes = np.concatenate(([-buyin], payouts - buyin))
    mu = buyin * roi
    second_moment = float(np.sum(probabilities * np.square(outcomes)))
    variance = max(0.0, second_moment - mu**2)
    sigma = math.sqrt(variance)

    tournaments = params.tournaments_count
    mu_total = tournaments * mu
    sigma_total = math.sqrt(tournaments) * sigma
    z_values = {"70%": 1.04, "95%": 1.96, "99.7%": 3.0}
    intervals = {
        label: (mu_total - z * sigma_total, mu_total + z * sigma_total)
        for label, z in z_values.items()
    }

    if sigma_total == 0:
        probability_of_loss = 1.0 if mu_total < 0 else 0.0
    else:
        probability_of_loss = float(norm.cdf((-mu_total) / sigma_total))

    return AnalyticalMetrics(
        ev_per_tournament=mu,
        sigma_per_tournament=sigma,
        ev_total=mu_total,
        sigma_total=sigma_total,
        confidence_intervals=intervals,
        probability_of_loss=probability_of_loss,
    )


def calculate_variance(
    params: VarianceInput,
    sample_size: int,
    seed: int,
) -> CalculationResult:
    validate_inputs(params)
    warnings: list[str] = []

    try:
        payout_structure = build_payout_structure(params)
        finish_distribution = build_finish_distribution(params, payout_structure)
    except (PayoutModelError, FinishDistributionError) as exc:
        raise CalculationError(str(exc)) from exc

    payouts = np.array(payout_structure.payouts, dtype=float)
    probabilities = finish_distribution.probabilities
    analytics = compute_analytical_metrics(params, payouts, probabilities)
    simulation = run_monte_carlo(
        params=params,
        payout_structure=payout_structure,
        finish_distribution=finish_distribution,
        sample_size=sample_size,
        seed=seed,
    )
    bankroll = estimate_bankroll(simulation, params.bankroll)

    return CalculationResult(
        params=params,
        payout_structure=payout_structure,
        finish_distribution=finish_distribution,
        analytics=analytics,
        simulation=simulation,
        bankroll=bankroll,
        warnings=warnings,
    )
