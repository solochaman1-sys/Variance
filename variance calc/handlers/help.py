from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards import start_menu_keyboard
from utils.messages import HELP_TEXT


router = Router()


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=start_menu_keyboard())


@router.callback_query(F.data == "show_help")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(HELP_TEXT, reply_markup=start_menu_keyboard())
    await callback.answer()
