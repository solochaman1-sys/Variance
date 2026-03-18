from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Турнирная дисперсия", callback_data="menu_tournament")
    builder.button(text="Дисперсия в кэш играх", callback_data="menu_cash")
    builder.button(text="Информация", callback_data="menu_info")
    builder.adjust(1)
    return builder.as_markup()


def main_actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Турнирная дисперсия", callback_data="menu_tournament")
    builder.button(text="Дисперсия в кэш играх", callback_data="menu_cash")
    builder.button(text="Информация", callback_data="menu_info")
    builder.adjust(1)
    return builder.as_markup()


def skip_bankroll_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить банкролл", callback_data="skip_bankroll")
    return builder.as_markup()


def cash_stddev_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="NLH full ring 70", callback_data="cash_std_70")
    builder.button(text="NLH 6-max 98", callback_data="cash_std_98")
    builder.button(text="PLO full ring 120", callback_data="cash_std_120")
    builder.button(text="PLO 6-max 140", callback_data="cash_std_140")
    builder.button(text="Heads-Up 200", callback_data="cash_std_200")
    builder.adjust(1)
    return builder.as_markup()


def tournament_field_size_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for size in (100, 300, 600, 1200, 2400, 5000):
        builder.button(text=str(size), callback_data=f"field_{size}")
    builder.adjust(3, 3)
    return builder.as_markup()
