from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from calculator import CalculationError, calculate_variance
from chart import render_runs_chart
from config import DEFAULT_RANDOM_SEED, DEFAULT_SAMPLE_SIZE
from keyboards import main_actions_keyboard
from models import VarianceInput
from utils.formatters import build_short_summary, build_stats_message
from utils.messages import EXAMPLE_TEXT


router = Router()
logger = logging.getLogger(__name__)


EXAMPLE_INPUT = VarianceInput(
    average_field_size=300,
    paid_percent=12,
    buyin=50,
    rake_percent=11,
    roi_percent=10,
    tournaments_count=1000,
    bankroll=10000,
)


async def _send_result(message: Message, params: VarianceInput) -> None:
    result = calculate_variance(params, sample_size=DEFAULT_SAMPLE_SIZE, seed=DEFAULT_RANDOM_SEED)

    await message.answer(build_short_summary(result))
    await message.answer_photo(BufferedInputFile(render_runs_chart(result).getvalue(), filename="runs.png"))
    await message.answer(build_stats_message(result), reply_markup=main_actions_keyboard())


@router.message(Command("example"))
async def example_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(EXAMPLE_TEXT)
    try:
        await _send_result(message, EXAMPLE_INPUT)
    except CalculationError as exc:
        await message.answer(str(exc))
    except TelegramBadRequest:
        logger.exception("Telegram API error during /example")
        await message.answer("Не удалось отправить один из результатов в Telegram. Попробуйте еще раз.")


@router.callback_query(F.data == "show_example")
async def example_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(EXAMPLE_TEXT)
    try:
        await _send_result(callback.message, EXAMPLE_INPUT)
    except CalculationError as exc:
        await callback.message.answer(str(exc))
    except TelegramBadRequest:
        logger.exception("Telegram API error during example callback")
        await callback.message.answer("Не удалось отправить один из результатов в Telegram. Попробуйте еще раз.")
    finally:
        await callback.answer()
