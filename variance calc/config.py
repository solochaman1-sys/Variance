from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SAMPLE_SIZE = 5000
DEFAULT_RANDOM_SEED = 42
FIXED_PAID_PERCENT = 12.0


@dataclass(slots=True)
class Settings:
    bot_token: str
    sample_size: int = DEFAULT_SAMPLE_SIZE
    random_seed: int = DEFAULT_RANDOM_SEED
    log_level: str = "INFO"


def load_settings() -> Settings:
    env_file = os.getenv("ENV_FILE", ".env").strip() or ".env"
    env_path = (BASE_DIR / env_file).resolve()
    load_dotenv(dotenv_path=env_path)

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError(f"BOT_TOKEN is not set (ENV_FILE={env_path.name}).")

    return Settings(
        bot_token=token,
        sample_size=DEFAULT_SAMPLE_SIZE,
        random_seed=DEFAULT_RANDOM_SEED,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
