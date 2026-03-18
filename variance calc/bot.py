from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_settings, setup_logging
from handlers import cash_router, example_router, help_router, info_router, start_router, variance_router


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(help_router)
    dp.include_router(info_router)
    dp.include_router(example_router)
    dp.include_router(cash_router)
    dp.include_router(variance_router)

    logger = logging.getLogger(__name__)
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
