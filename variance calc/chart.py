from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from models import CalculationResult


plt.rcParams["font.family"] = "DejaVu Sans"


def _to_buffer(fig: plt.Figure) -> BytesIO:
    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def render_runs_chart(result: CalculationResult) -> BytesIO:
    params = result.params
    analytics = result.analytics
    simulation = result.simulation
    x = np.arange(1, params.tournaments_count + 1)

    fig, ax = plt.subplots(figsize=(12, 7))
    palette = plt.cm.tab20(np.linspace(0, 1, len(simulation.displayed_paths)))
    for idx, path in enumerate(simulation.displayed_paths):
        ax.plot(x, path, color=palette[idx], alpha=0.35, linewidth=1.2)

    mean_line = analytics.ev_per_tournament * x
    sigma_line = analytics.sigma_per_tournament * np.sqrt(x)
    bands = [
        ("99.7%", 3.0, "#f4c95d", 0.15),
        ("95%", 1.96, "#7ec8e3", 0.18),
        ("70%", 1.04, "#8ad18a", 0.22),
    ]
    for label, z, color, alpha in bands:
        lower = mean_line - z * sigma_line
        upper = mean_line + z * sigma_line
        ax.fill_between(x, lower, upper, color=color, alpha=alpha, label=f"Доверительный интервал {label}")

    ax.plot(x, simulation.displayed_best_path, color="#1a7f37", linewidth=2.2, label="Лучшая траектория")
    ax.plot(x, simulation.displayed_worst_path, color="#d1242f", linewidth=2.2, label="Худшая траектория")
    ax.plot(x, simulation.mean_path, color="#111111", linewidth=2.0, label="Средняя симуляция")

    ax.set_title("Случайные траектории результатов")
    ax.set_xlabel("Дистанция (турниры)")
    ax.set_ylabel("Прибыль / убыток ($)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=9)
    return _to_buffer(fig)


def render_distribution_chart(result: CalculationResult) -> BytesIO:
    finals = result.simulation.final_results
    analytics = result.analytics

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.hist(finals, bins=35, density=True, alpha=0.72, color="#4c78a8", edgecolor="white", label="Гистограмма")

    x = np.linspace(finals.min(), finals.max(), 500)
    sigma = analytics.sigma_total
    if sigma > 0:
        pdf = norm.pdf(x, loc=analytics.ev_total, scale=sigma)
        ax.plot(x, pdf, color="#d62728", linestyle="--", linewidth=2.0, label="Нормальное приближение")

    ax.axvline(analytics.ev_total, color="#1a7f37", linewidth=2.0, label="Математический EV")
    ax.axvline(0.0, color="#111111", linewidth=1.8, linestyle=":", label="Ноль")

    ax.set_title("Распределение итогового результата")
    ax.set_xlabel("Итоговый результат ($)")
    ax.set_ylabel("Плотность")
    ax.grid(True, alpha=0.2)
    ax.legend()
    return _to_buffer(fig)


def render_payout_chart(result: CalculationResult) -> BytesIO:
    entries = result.payout_structure.entries
    labels = [entry.label for entry in entries]
    values = [entry.payout for entry in entries]

    if len(entries) > 18:
        head = entries[:10]
        tail = entries[-8:]
        labels = [entry.label for entry in head + tail]
        values = [entry.payout for entry in head + tail]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(labels, values, color="#c97b63")
    ax.set_title("Структура выплат")
    ax.set_xlabel("Место")
    ax.set_ylabel("Выплата ($)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, axis="y", alpha=0.2)
    return _to_buffer(fig)
