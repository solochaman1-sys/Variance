from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class VarianceStates(StatesGroup):
    average_field_size = State()
    buyin = State()
    rake_percent = State()
    roi_percent = State()
    tournaments_count = State()
    bankroll = State()


class CashVarianceStates(StatesGroup):
    winrate_bb100 = State()
    stddev_bb100 = State()
    hands_count = State()
    big_blind_value = State()
    bankroll = State()
