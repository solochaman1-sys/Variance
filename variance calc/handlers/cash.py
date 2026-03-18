from __future__ import annotations

import logging
import math

import numpy as np
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from scipy.stats import norm

from chart import render_runs_chart
from config import DEFAULT_RANDOM_SEED, DEFAULT_SAMPLE_SIZE
from keyboards import cash_stddev_keyboard, main_actions_keyboard, skip_bankroll_keyboard
from models import (
    AnalyticalMetrics,
    BankrollAssessment,
    BankrollRecommendation,
    CalculationResult,
    FinishDistribution,
    PayoutStructure,
    SimulationResult,
    VarianceInput,
)
from states import CashVarianceStates


router = Router()
logger = logging.getLogger(__name__)
STDDEV_PRESETS = {
    "cash_std_70": 70.0,
    "cash_std_98": 98.0,
    "cash_std_120": 120.0,
    "cash_std_140": 140.0,
    "cash_std_200": 200.0,
}


def _parse_float(raw: str) -> float:
    return float((raw or "").replace(",", ".").strip())


def _parse_int(raw: str) -> int:
    return int((raw or "").strip())


def _build_cash_result(
    winrate_bb100: float,
    stddev_bb100: float,
    hands_count: int,
    big_blind_value: float,
    bankroll: float | None,
) -> CalculationResult:
    rng = np.random.default_rng(DEFAULT_RANDOM_SEED)
    blocks = max(1, hands_count // 100)
    effective_hands = blocks * 100
    mu_per_block = winrate_bb100 * big_blind_value
    sigma_per_block = stddev_bb100 * big_blind_value

    samples = rng.normal(
        loc=mu_per_block,
        scale=sigma_per_block,
        size=(DEFAULT_SAMPLE_SIZE, blocks),
    )
    cumulative = np.cumsum(samples, axis=1)
    final_results = cumulative[:, -1]
    mean_path = cumulative.mean(axis=0)
    displayed_paths = cumulative[np.linspace(0, DEFAULT_SAMPLE_SIZE - 1, num=20, dtype=int)]
    displayed_finals = displayed_paths[:, -1]
    best_idx = int(np.argmax(displayed_finals))
    worst_idx = int(np.argmin(displayed_finals))
    required_bankroll = np.maximum(0.0, -cumulative.min(axis=1))

    mu_total = mu_per_block * blocks
    sigma_total = math.sqrt(blocks) * sigma_per_block
    intervals = {
        "70%": (mu_total - 1.04 * sigma_total, mu_total + 1.04 * sigma_total),
        "95%": (mu_total - 1.96 * sigma_total, mu_total + 1.96 * sigma_total),
        "99.7%": (mu_total - 3.0 * sigma_total, mu_total + 3.0 * sigma_total),
    }
    loss_probability = float(norm.cdf((-mu_total) / sigma_total)) if sigma_total > 0 else 0.0

    recommendations = []
    for risk in (0.50, 0.15, 0.05, 0.01):
        recommendations.append(
            BankrollRecommendation(
                target_risk=risk,
                required_bankroll=float(np.quantile(required_bankroll, 1.0 - risk)),
            )
        )

    bankroll_assessment = BankrollAssessment(
        recommendations=recommendations,
        current_bankroll=bankroll,
        estimated_risk_of_ruin=float(np.mean(required_bankroll > bankroll)) if bankroll is not None else None,
        safe_run_share=float(np.mean(required_bankroll <= bankroll)) if bankroll is not None else None,
    )

    params = VarianceInput(
        average_field_size=0,
        paid_percent=0,
        buyin=big_blind_value,
        rake_percent=0,
        roi_percent=0,
        tournaments_count=blocks,
        bankroll=bankroll,
    )
    payout_structure = PayoutStructure(
        entrants=0,
        paid_places=0,
        total_buyin=big_blind_value,
        net_buyin=big_blind_value,
        prize_pool=0,
        min_cash=0,
        payouts=[],
        entries=[],
    )
    finish_distribution = FinishDistribution(
        p_no_cash=0.0,
        cash_probabilities=np.array([], dtype=float),
        overall_itm_probability=0.0,
        warning=None,
    )
    analytics = AnalyticalMetrics(
        ev_per_tournament=mu_per_block,
        sigma_per_tournament=sigma_per_block,
        ev_total=mu_total,
        sigma_total=sigma_total,
        confidence_intervals=intervals,
        probability_of_loss=loss_probability,
    )
    simulation = SimulationResult(
        final_results=final_results,
        sample_paths=displayed_paths,
        mean_path=mean_path,
        displayed_best_path=displayed_paths[best_idx],
        displayed_worst_path=displayed_paths[worst_idx],
        displayed_paths=displayed_paths,
        ruin_indicator=cumulative.min(axis=1) <= 0,
        required_bankroll_per_run=required_bankroll,
        simulated_ev_total=float(final_results.mean()),
        simulated_sigma_total=float(final_results.std(ddof=0)),
        simulated_roi_percent=0.0,
    )
    result = CalculationResult(
        params=params,
        payout_structure=payout_structure,
        finish_distribution=finish_distribution,
        analytics=analytics,
        simulation=simulation,
        bankroll=bankroll_assessment,
        warnings=[],
    )
    return result


def _cash_summary(
    winrate_bb100: float,
    stddev_bb100: float,
    hands_count: int,
    big_blind_value: float,
) -> str:
    return (
        "<b>Расчет дисперсии в кэш-играх готов</b>\n"
        f"Winrate: <b>{winrate_bb100:.2f} bb/100</b>\n"
        f"StdDev: <b>{stddev_bb100:.2f} bb/100</b>\n"
        f"Дистанция: <b>{hands_count:,}</b> рук\n"
        f"Размер BB: <b>{big_blind_value:.2f} $</b>"
    ).replace(",", " ")


def _cash_stats(
    result: CalculationResult,
    winrate_bb100: float,
    stddev_bb100: float,
    hands_count: int,
    big_blind_value: float,
) -> str:
    bankroll = result.bankroll
    analytics = result.analytics
    simulation = result.simulation
    lines = [
        "<b>Статистический блок: кэш-игры</b>",
        f"Winrate: {winrate_bb100:.2f} bb/100",
        f"StdDev: {stddev_bb100:.2f} bb/100",
        f"Дистанция: {hands_count:,} рук".replace(",", " "),
        f"Размер BB: {big_blind_value:.2f} $",
        f"EV (математически): {analytics.ev_total:,.2f} $".replace(",", " "),
        f"EV (по симуляции): {simulation.simulated_ev_total:,.2f} $".replace(",", " "),
        f"SD (математически): {analytics.sigma_total:,.2f} $".replace(",", " "),
        f"SD (по симуляции): {simulation.simulated_sigma_total:,.2f} $".replace(",", " "),
        f"Интервал 70%: {analytics.confidence_intervals['70%'][0]:,.2f} .. {analytics.confidence_intervals['70%'][1]:,.2f} $".replace(",", " "),
        f"Интервал 95%: {analytics.confidence_intervals['95%'][0]:,.2f} .. {analytics.confidence_intervals['95%'][1]:,.2f} $".replace(",", " "),
        f"Интервал 99.7%: {analytics.confidence_intervals['99.7%'][0]:,.2f} .. {analytics.confidence_intervals['99.7%'][1]:,.2f} $".replace(",", " "),
        f"Вероятность закончить в минусе: {analytics.probability_of_loss * 100:.2f}%".replace(".", ","),
        f"Рекомендованный банкролл для 50%: {bankroll.recommendations[0].required_bankroll:,.2f} $".replace(",", " "),
        f"Рекомендованный банкролл для 15%: {bankroll.recommendations[1].required_bankroll:,.2f} $".replace(",", " "),
        f"Рекомендованный банкролл для 5%: {bankroll.recommendations[2].required_bankroll:,.2f} $".replace(",", " "),
        f"Рекомендованный банкролл для 1%: {bankroll.recommendations[3].required_bankroll:,.2f} $".replace(",", " "),
    ]
    if bankroll.current_bankroll is not None:
        lines.append(f"Текущий банкролл: {bankroll.current_bankroll:,.2f} $".replace(",", " "))
        lines.append(f"Оценка риска разорения: {(bankroll.estimated_risk_of_ruin or 0.0) * 100:.2f}%".replace(".", ","))
    return "\n".join(lines)


async def _start_cash_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CashVarianceStates.winrate_bb100)
    await message.answer(
        "Введите ваш винрейт в bb/100 (одной цифрой)\n\n"
        "Winrate = (прибыль в больших блайндах / количество раздач) × 100"
    )


async def _finish_cash_flow(message: Message, state: FSMContext, bankroll: float | None) -> None:
    data = await state.get_data()
    winrate_bb100 = float(data["winrate_bb100"])
    stddev_bb100 = float(data["stddev_bb100"])
    hands_count = int(data["hands_count"])
    big_blind_value = float(data["big_blind_value"])
    result = _build_cash_result(winrate_bb100, stddev_bb100, hands_count, big_blind_value, bankroll)

    await message.answer(_cash_summary(winrate_bb100, stddev_bb100, hands_count, big_blind_value))
    await message.answer_photo(BufferedInputFile(render_runs_chart(result).getvalue(), filename="cash_runs.png"))
    await message.answer(_cash_stats(result, winrate_bb100, stddev_bb100, hands_count, big_blind_value), reply_markup=main_actions_keyboard())
    await state.clear()


@router.message(Command("cash"))
async def cash_handler(message: Message, state: FSMContext) -> None:
    await _start_cash_flow(message, state)


@router.callback_query(F.data == "menu_cash")
async def cash_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_cash_flow(callback.message, state)
    await callback.answer()


@router.message(CashVarianceStates.winrate_bb100)
async def cash_winrate_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text or "")
    except ValueError:
        await message.answer("Введите корректный winrate, например 4.5")
        return
    await state.update_data(winrate_bb100=value)
    await state.set_state(CashVarianceStates.stddev_bb100)
    await message.answer(
        "Выберите тип игр, отклонение зависит от выбранного формата",
        reply_markup=cash_stddev_keyboard(),
    )


async def _set_cash_stddev(message: Message, state: FSMContext, value: float) -> None:
    await state.update_data(stddev_bb100=value)
    await state.set_state(CashVarianceStates.hands_count)
    await message.answer(
        f"Принято стандартное отклонение: {value:.0f} bb/100.\n"
        "Введите дистанцию в раздачах."
    )


@router.callback_query(StateFilter(CashVarianceStates.stddev_bb100), F.data.in_(set(STDDEV_PRESETS)))
async def cash_stddev_preset_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = STDDEV_PRESETS[callback.data]
    await _set_cash_stddev(callback.message, state, value)
    await callback.answer()


@router.message(CashVarianceStates.stddev_bb100)
async def cash_stddev_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text or "")
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Выберите один из пресетов кнопкой или введите положительное значение stddev вручную."
        )
        return
    await _set_cash_stddev(message, state, value)


@router.message(CashVarianceStates.hands_count)
async def cash_hands_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_int(message.text or "")
        if value < 100:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное количество рук. Минимум 100.")
        return
    await state.update_data(hands_count=value)
    await state.set_state(CashVarianceStates.big_blind_value)
    await message.answer("Введите размер большого блайнда в долларах.")


@router.message(CashVarianceStates.big_blind_value)
async def cash_bb_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text or "")
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный размер большого блайнда больше 0.")
        return
    await state.update_data(big_blind_value=value)
    await state.set_state(CashVarianceStates.bankroll)
    await message.answer("Введите банкролл в долларах или нажмите кнопку пропуска.", reply_markup=skip_bankroll_keyboard())


@router.callback_query(StateFilter(CashVarianceStates.bankroll), F.data == "skip_bankroll")
async def cash_skip_bankroll_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_cash_flow(callback.message, state, bankroll=None)
    await callback.answer()


@router.message(CashVarianceStates.bankroll)
async def cash_bankroll_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text or "")
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный банкролл больше 0 или нажмите кнопку пропуска.")
        return
    await _finish_cash_flow(message, state, bankroll=value)
