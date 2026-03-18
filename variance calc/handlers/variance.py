from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from calculator import CalculationError, calculate_variance
from chart import render_runs_chart
from config import DEFAULT_RANDOM_SEED, DEFAULT_SAMPLE_SIZE, FIXED_PAID_PERCENT
from keyboards import main_actions_keyboard, skip_bankroll_keyboard, tournament_field_size_keyboard
from models import VarianceInput
from states import VarianceStates
from utils.formatters import build_short_summary, build_stats_message


router = Router()
logger = logging.getLogger(__name__)
FIELD_CALLBACKS = {"field_100", "field_300", "field_600", "field_1200", "field_2400", "field_5000"}


def _parse_float(raw: str) -> float:
    return float((raw or "").replace(",", ".").strip())


def _parse_int(raw: str) -> int:
    return int((raw or "").strip())


async def _start_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(VarianceStates.average_field_size)
    await message.answer(
        "Среднее количество участников?\n"
        f"Призовая зона {FIXED_PAID_PERCENT:.0f}% GGcom",
        reply_markup=tournament_field_size_keyboard(),
    )


async def _finalize(message: Message, state: FSMContext, bankroll: float | None) -> None:
    data = await state.get_data()
    params = VarianceInput(
        average_field_size=float(data["average_field_size"]),
        paid_percent=FIXED_PAID_PERCENT,
        buyin=float(data["buyin"]),
        rake_percent=float(data["rake_percent"]),
        roi_percent=float(data["roi_percent"]),
        tournaments_count=int(data["tournaments_count"]),
        bankroll=bankroll,
    )

    try:
        result = calculate_variance(params, sample_size=DEFAULT_SAMPLE_SIZE, seed=DEFAULT_RANDOM_SEED)
        await message.answer(build_short_summary(result))
        await message.answer_photo(BufferedInputFile(render_runs_chart(result).getvalue(), filename="runs.png"))
        await message.answer(build_stats_message(result), reply_markup=main_actions_keyboard())
    except CalculationError as exc:
        await message.answer(str(exc))
    except TelegramBadRequest:
        logger.exception("Telegram API error during variance flow")
        await message.answer("Telegram не принял часть сообщений или изображений. Попробуйте повторить расчет.")
    finally:
        await state.clear()


@router.message(Command("variance"))
async def variance_handler(message: Message, state: FSMContext) -> None:
    await _start_flow(message, state)


@router.callback_query(F.data.in_({"new_calculation", "menu_tournament"}))
async def new_calculation_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_flow(callback.message, state)
    await callback.answer()


@router.callback_query(StateFilter(VarianceStates.average_field_size), F.data.in_(FIELD_CALLBACKS))
async def average_field_size_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = float(callback.data.split("_", maxsplit=1)[1])
    await state.update_data(average_field_size=value)
    await state.set_state(VarianceStates.buyin)
    await callback.message.answer(f"Поле выбрано: {int(value)}.\nВведите бай-ин в долларах.")
    await callback.answer()


@router.message(VarianceStates.average_field_size)
async def average_field_size_handler(message: Message) -> None:
    await message.answer("Выберите размер поля кнопкой ниже.", reply_markup=tournament_field_size_keyboard())


@router.message(VarianceStates.buyin)
async def buyin_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text)
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный бай-ин. Значение должно быть больше 0.")
        return

    await state.update_data(buyin=value)
    await state.set_state(VarianceStates.rake_percent)
    await message.answer("Введите рейк в процентах.")


@router.message(VarianceStates.rake_percent)
async def rake_percent_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text)
        if not (0 <= value <= 30):
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный рейк от 0 до 30.")
        return

    await state.update_data(rake_percent=value)
    await state.set_state(VarianceStates.roi_percent)
    await message.answer("Введите ROI в процентах.")


@router.message(VarianceStates.roi_percent)
async def roi_percent_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_float(message.text)
        if not (-100 <= value <= 500):
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный ROI в диапазоне от -100 до 500.")
        return

    await state.update_data(roi_percent=value)
    await state.set_state(VarianceStates.tournaments_count)
    await message.answer("Сколько турниров сыграем?")


@router.message(VarianceStates.tournaments_count)
async def tournaments_count_handler(message: Message, state: FSMContext) -> None:
    try:
        value = _parse_int(message.text)
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное целое число турниров больше 0.")
        return

    await state.update_data(tournaments_count=value)
    await state.set_state(VarianceStates.bankroll)
    await message.answer(
        "Введите банкролл в долларах или нажмите кнопку пропуска.",
        reply_markup=skip_bankroll_keyboard(),
    )


@router.callback_query(StateFilter(VarianceStates.bankroll), F.data == "skip_bankroll")
async def skip_bankroll_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Расчет запускается без стартового банкролла.")
    await _finalize(callback.message, state, bankroll=None)


@router.message(VarianceStates.bankroll)
async def bankroll_handler(message: Message, state: FSMContext) -> None:
    try:
        bankroll = _parse_float(message.text)
        if bankroll <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректный банкролл больше 0 или нажмите кнопку пропуска.")
        return

    await _finalize(message, state, bankroll=bankroll)
