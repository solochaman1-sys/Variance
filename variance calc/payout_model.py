from __future__ import annotations

import numpy as np

from models import PayoutEntry, PayoutStructure, VarianceInput


class PayoutModelError(ValueError):
    """Ошибка генерации payout structure."""


FIELD_SIZE_PAYOUT_EXAMPLES = {
    100: {
        "paid_percent": 12,
        "paid_places": 12,
        "ladder_units": {
            "1": 23.0,
            "2": 14.0,
            "3": 9.0,
            "4": 7.0,
            "5": 6.0,
            "6": 5.0,
            "7": 4.0,
            "8": 3.5,
            "9": 3.0,
            "10": 2.5,
            "11": 1.5,
            "12": 1.5,
        },
    },
    300: {
        "paid_percent": 12,
        "paid_places": 36,
        "ladder_units": {
            "1": 58.0,
            "2": 34.0,
            "3": 22.0,
            "4": 17.0,
            "5": 14.0,
            "6": 11.0,
            "7": 9.0,
            "8": 7.2,
            "9": 5.8,
            "10": 4.8,
            "11-15": 3.6,
            "16-20": 2.6,
            "21-25": 2.0,
            "26-36": 1.5,
        },
    },
    600: {
        "paid_percent": 12,
        "paid_places": 72,
        "ladder_units": {
            "1": 112.0,
            "2": 66.0,
            "3": 42.0,
            "4": 32.0,
            "5": 26.0,
            "6": 21.0,
            "7": 17.0,
            "8": 13.5,
            "9": 10.5,
            "10": 8.5,
            "11-15": 6.2,
            "16-20": 4.4,
            "21-25": 3.3,
            "26-30": 2.6,
            "31-40": 2.1,
            "41-55": 1.7,
            "56-72": 1.5,
        },
    },
    1200: {
        "paid_percent": 12,
        "paid_places": 144,
        "ladder_units": {
            "1": 220.0,
            "2": 130.0,
            "3": 83.0,
            "4": 63.0,
            "5": 51.0,
            "6": 41.0,
            "7": 33.0,
            "8": 26.0,
            "9": 20.0,
            "10": 16.0,
            "11-15": 11.8,
            "16-20": 8.6,
            "21-25": 6.4,
            "26-30": 5.0,
            "31-40": 4.0,
            "41-50": 3.2,
            "51-75": 2.6,
            "76-100": 2.1,
            "101-120": 1.8,
            "121-144": 1.5,
        },
    },
    2400: {
        "paid_percent": 12,
        "paid_places": 288,
        "ladder_units": {
            "1": 430.0,
            "2": 255.0,
            "3": 162.0,
            "4": 123.0,
            "5": 99.0,
            "6": 79.0,
            "7": 63.0,
            "8": 49.0,
            "9": 38.0,
            "10": 30.0,
            "11-15": 22.0,
            "16-20": 16.0,
            "21-25": 12.0,
            "26-30": 9.5,
            "31-40": 7.5,
            "41-50": 6.0,
            "51-75": 4.8,
            "76-100": 3.9,
            "101-150": 3.2,
            "151-200": 2.6,
            "201-240": 2.1,
            "241-288": 1.5,
        },
    },
    5000: {
        "paid_percent": 12,
        "paid_places": 600,
        "ladder_units": {
            "1": 900.0,
            "2": 530.0,
            "3": 340.0,
            "4": 260.0,
            "5": 210.0,
            "6": 168.0,
            "7": 134.0,
            "8": 105.0,
            "9": 82.0,
            "10": 65.0,
            "11-15": 48.0,
            "16-20": 35.0,
            "21-25": 26.0,
            "26-30": 20.0,
            "31-40": 16.0,
            "41-50": 13.0,
            "51-75": 10.5,
            "76-100": 8.5,
            "101-150": 6.8,
            "151-200": 5.5,
            "201-300": 4.4,
            "301-400": 3.6,
            "401-475": 2.9,
            "476-550": 2.3,
            "551-600": 1.8,
        },
    },
}


def _expand_ladder_units(field_size: int) -> tuple[int, list[float], list[PayoutEntry]]:
    if field_size not in FIELD_SIZE_PAYOUT_EXAMPLES:
        raise PayoutModelError("Для выбранного размера поля нет заданной структуры выплат.")

    example = FIELD_SIZE_PAYOUT_EXAMPLES[field_size]
    paid_places = int(example["paid_places"])
    per_place_units = [0.0] * paid_places
    entries: list[PayoutEntry] = []

    for label, unit in example["ladder_units"].items():
        if "-" in label:
            start_text, end_text = label.split("-", maxsplit=1)
            start = int(start_text)
            end = int(end_text)
        else:
            start = int(label)
            end = int(label)

        for place in range(start, end + 1):
            if 1 <= place <= paid_places:
                per_place_units[place - 1] = float(unit)

        entries.append(PayoutEntry(start_place=start, end_place=end, payout=float(unit)))

    if any(unit <= 0 for unit in per_place_units):
        raise PayoutModelError("Якорная структура выплат заполнена не полностью.")

    return paid_places, per_place_units, entries


def build_payout_structure(params: VarianceInput) -> PayoutStructure:
    entrants = int(round(params.average_field_size))
    if entrants not in FIELD_SIZE_PAYOUT_EXAMPLES:
        raise PayoutModelError("Доступны только поля: 100, 300, 600, 1200, 2400 и 5000.")

    example = FIELD_SIZE_PAYOUT_EXAMPLES[entrants]
    paid_percent = float(example["paid_percent"])
    total_buyin = float(params.buyin)
    rake = params.rake_percent / 100.0
    net_buyin = total_buyin / (1.0 + rake)
    prize_pool = entrants * net_buyin
    paid_places, per_place_units, bucket_entries = _expand_ladder_units(entrants)

    expected_paid_places = max(1, int(round(entrants * paid_percent / 100.0)))
    if expected_paid_places != paid_places:
        raise PayoutModelError("Якорная структура выплат не совпадает с paid_percent для выбранного поля.")

    min_cash = 1.5 * net_buyin
    base_pool = paid_places * min_cash
    if base_pool - prize_pool > 1e-9:
        raise PayoutModelError(
            "Выбранные параметры несовместимы с минимальным кэшем 1.5 бай-ина. "
            "Уменьшите поле или измените экономику турнира."
        )

    units = np.array(per_place_units, dtype=float)
    extra_units = np.maximum(0.0, units - 1.5)
    extra_pool = prize_pool - base_pool
    payouts = np.full(paid_places, min_cash, dtype=float)
    if extra_pool > 0 and extra_units.sum() > 0:
        payouts += extra_pool * (extra_units / extra_units.sum())

    payout_cents = np.round(payouts * 100).astype(int)
    payout_cents[-1] = max(payout_cents[-1], int(round(min_cash * 100)))
    target_cents = int(round(prize_pool * 100))
    remainder = target_cents - int(payout_cents.sum())
    payout_cents[0] += remainder

    final_payouts = payout_cents.astype(float) / 100.0
    entries = [
        PayoutEntry(
            start_place=entry.start_place,
            end_place=entry.end_place,
            payout=float(final_payouts[entry.start_place - 1 : entry.end_place].mean()),
        )
        for entry in bucket_entries
    ]

    return PayoutStructure(
        entrants=entrants,
        paid_places=paid_places,
        total_buyin=total_buyin,
        net_buyin=net_buyin,
        prize_pool=prize_pool,
        min_cash=min_cash,
        payouts=final_payouts.tolist(),
        entries=entries,
    )
