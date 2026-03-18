from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards import start_menu_keyboard
from utils.messages import START_TEXT


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(START_TEXT, reply_markup=start_menu_keyboard())
