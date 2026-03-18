from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards import start_menu_keyboard
from utils.messages import INFO_TEXT


router = Router()


@router.message(Command("info"))
async def info_handler(message: Message) -> None:
    await message.answer(INFO_TEXT, reply_markup=start_menu_keyboard())


@router.callback_query(F.data == "menu_info")
async def info_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(INFO_TEXT, reply_markup=start_menu_keyboard())
    await callback.answer()
