from __future__ import annotations

from typing import Iterable

import pandas as pd

from config import DEFAULT_SAMPLE_SIZE
from models import CalculationResult, PayoutEntry


def format_money(value: float) -> str:
    return f"{value:,.2f} $".replace(",", " ")


def format_percent(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def _interval_line(label: str, interval: tuple[float, float]) -> str:
    return f"{label}: {format_money(interval[0])} .. {format_money(interval[1])}"


def build_short_summary(result: CalculationResult) -> str:
    params = result.params
    payout = result.payout_structure
    lines = [
        "<b>Расчет готов</b>",
        f"Среднее поле: <b>{payout.entrants}</b>",
        f"Призовых мест: <b>{payout.paid_places}</b> ({format_percent(params.paid_percent)})",
        f"Бай-ин: <b>{format_money(params.buyin)}</b>, рейк: <b>{format_percent(params.rake_percent)}</b>",
        f"ROI: <b>{format_percent(params.roi_percent)}</b>",
        f"Дистанция: <b>{params.tournaments_count}</b> турниров",
        f"Структура выплат сгенерирована автоматически, симуляция фиксирована: <b>{DEFAULT_SAMPLE_SIZE}</b> прогонов.",
    ]
    return "\n".join(lines)


def build_stats_message(result: CalculationResult) -> str:
    params = result.params
    payout = result.payout_structure
    analytics = result.analytics
    simulation = result.simulation
    bankroll = result.bankroll
    total_buyins = params.buyin * params.tournaments_count

    lines = [
        "<b>Результат</b>",
        f"Среднее количество участников: {payout.entrants}",
        f"Бай-ин: {format_money(params.buyin)}",
        f"Рейк: {format_percent(params.rake_percent)}",
        f"ROI: {format_percent(params.roi_percent)}",
        f"Количество турниров: {params.tournaments_count}",
        f"Общая сумма входов: {format_money(total_buyins)}",
        f"EV (математически): {format_money(analytics.ev_total)}",
        f"EV (симуляции): {format_money(simulation.simulated_ev_total)}",
        f"ROI (по симуляции): {format_percent(simulation.simulated_roi_percent)}",
        f"Среднее отклонение +- : {format_money(simulation.simulated_sigma_total)}",
        f"В 70% случаев произойдет: {format_money(analytics.confidence_intervals['70%'][0])} .. {format_money(analytics.confidence_intervals['70%'][1])}",
        f"В 5%: {format_money(analytics.confidence_intervals['95%'][0])} .. {format_money(analytics.confidence_intervals['95%'][1])}",
        f"В 0.3 %: {format_money(analytics.confidence_intervals['99.7%'][0])} .. {format_money(analytics.confidence_intervals['99.7%'][1])}",
        f"<b>Вероятность закончить в минусе: {format_percent(analytics.probability_of_loss * 100.0)}</b>",
        f"Банкролл для 50%: {format_money(bankroll.recommendations[0].required_bankroll)}",
        f"Банкролл для 15%: {format_money(bankroll.recommendations[1].required_bankroll)}",
        f"Банкролл для 5%: {format_money(bankroll.recommendations[2].required_bankroll)}",
        f"Банкролл для 1%: {format_money(bankroll.recommendations[3].required_bankroll)}",
    ]

    if bankroll.current_bankroll is not None:
        lines.extend(
            [
                f"Текущий банкролл: {format_money(bankroll.current_bankroll)}",
                f"Оценка риска разорения: {format_percent((bankroll.estimated_risk_of_ruin or 0.0) * 100.0)}",
                f"Доля прогонов без нуля: {format_percent((bankroll.safe_run_share or 0.0) * 100.0)}",
            ]
        )
        if bankroll.recommendations[2].required_bankroll > bankroll.current_bankroll:
            lines.append("Предупреждение: текущий банкролл ниже умеренно-консервативной рекомендации для 5% RoR.")

    return "\n".join(lines)


def build_payout_preview(entries: Iterable[PayoutEntry]) -> str:
    rows = [{"Место": entry.label, "Выплата": format_money(entry.payout)} for entry in entries]
    frame = pd.DataFrame(rows)
    preview = frame.to_string(index=False)
    return f"<b>Превью структуры выплат</b>\n<pre>{preview}</pre>"
