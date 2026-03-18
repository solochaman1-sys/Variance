from __future__ import annotations

import numpy as np

from models import FinishDistribution, PayoutStructure, SimulationResult, VarianceInput


class FinishDistributionError(ValueError):
    """Ошибка модели вероятностей."""


def build_finish_distribution(
    params: VarianceInput,
    payout_structure: PayoutStructure,
) -> FinishDistribution:
    paid_places = payout_structure.paid_places
    places = np.arange(1, paid_places + 1, dtype=float)
    finish_weights = 1.0 / np.power(places - 1.0 + 0.7, 0.65)
    pi = finish_weights / finish_weights.sum()

    roi = params.roi_percent / 100.0
    total_buyin = payout_structure.total_buyin
    payouts = np.array(payout_structure.payouts, dtype=float)
    expected_cash_return = float(np.dot(pi, payouts))
    t = total_buyin * (1.0 + roi) / expected_cash_return

    if t > 1.0 + 1e-9:
        raise FinishDistributionError(
            "ROI слишком высокий для выбранной структуры выплат. "
            "Уменьшите ROI или измените параметры турнира."
        )

    t = min(1.0, max(0.0, t))
    cash_probabilities = t * pi
    return FinishDistribution(
        p_no_cash=1.0 - t,
        cash_probabilities=cash_probabilities,
        overall_itm_probability=t,
        warning=None,
    )


def run_monte_carlo(
    params: VarianceInput,
    payout_structure: PayoutStructure,
    finish_distribution: FinishDistribution,
    sample_size: int,
    seed: int,
    displayed_paths_count: int = 20,
) -> SimulationResult:
    rng = np.random.default_rng(seed)
    total_buyin = payout_structure.total_buyin
    payouts = np.array(payout_structure.payouts, dtype=float)
    outcomes = np.concatenate(([-total_buyin], payouts - total_buyin))
    probabilities = finish_distribution.probabilities

    tournaments = params.tournaments_count
    sampled_indices = rng.choice(
        len(outcomes),
        size=(sample_size, tournaments),
        replace=True,
        p=probabilities,
    )
    samples = outcomes[sampled_indices]
    cumulative = np.cumsum(samples, axis=1)
    final_results = cumulative[:, -1]
    mean_path = cumulative.mean(axis=0)

    display_count = min(displayed_paths_count, sample_size)
    displayed_indices = np.linspace(0, sample_size - 1, num=display_count, dtype=int)
    displayed_paths = cumulative[displayed_indices]
    display_finals = displayed_paths[:, -1]
    best_idx = int(np.argmax(display_finals))
    worst_idx = int(np.argmin(display_finals))
    min_path_values = cumulative.min(axis=1)
    required_bankroll = np.maximum(0.0, -min_path_values)

    total_buyins_spent = total_buyin * tournaments
    simulated_ev_total = float(final_results.mean())
    simulated_sigma_total = float(final_results.std(ddof=0))
    simulated_roi_percent = (simulated_ev_total / total_buyins_spent) * 100.0

    return SimulationResult(
        final_results=final_results,
        sample_paths=displayed_paths,
        mean_path=mean_path,
        displayed_best_path=displayed_paths[best_idx],
        displayed_worst_path=displayed_paths[worst_idx],
        displayed_paths=displayed_paths,
        ruin_indicator=min_path_values <= 0.0,
        required_bankroll_per_run=required_bankroll,
        simulated_ev_total=simulated_ev_total,
        simulated_sigma_total=simulated_sigma_total,
        simulated_roi_percent=simulated_roi_percent,
    )
