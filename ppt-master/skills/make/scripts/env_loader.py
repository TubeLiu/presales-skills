#!/usr/bin/env python3
"""Environment variable loading helpers for AI provider backends.

Extracted from upstream `hugohe3/ppt-master/scripts/config.py` so notes_to_audio
and tts_backends can pull provider keys (ELEVENLABS / MINIMAX / QWEN /
COSYVOICE / OPENAI / etc.) from a layered .env without forcing our monorepo
`config.py` (which is a different surface) to host these helpers.

.env lookup order:
    1. CWD/.env  — useful when running scripts from a project root
    2. <repo_root>/.env
    3. ~/.ppt-master/.env  — user default
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent  # ppt-master/skills/make
REPO_ROOT = PROJECT_ROOT.parent.parent.parent  # presales-skills/

USER_CONFIG_DIR = Path.home() / '.ppt-master'
USER_ENV_FILE = USER_CONFIG_DIR / '.env'


def get_env_candidates() -> list[Path]:
    """Return the supported .env lookup order."""
    return [
        Path.cwd() / '.env',
        REPO_ROOT / '.env',
        USER_ENV_FILE,
    ]


def resolve_env_path() -> Path:
    """Return the first existing .env path.

    If no candidate exists, return the CWD .env path so callers can no-op
    consistently while still showing a useful default location in messages.
    """
    candidates = get_env_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def strip_env_quotes(value: str) -> str:
    """Strip matching surrounding quotes from a .env value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_prefixed_env_file(
    prefixes: tuple[str, ...],
    *,
    deprecated_keys: Optional[dict[str, str]] = None,
) -> Optional[Path]:
    """Load matching keys from the first supported .env file.

    Existing process environment variables always win. Keys outside the
    requested prefixes are ignored so one shared .env can hold image, search,
    and narration credentials without leaking unrelated values into the
    process.
    """
    env_path = resolve_env_path()
    if not env_path.exists():
        return None

    deprecated_keys = deprecated_keys or {}
    with env_path.open('r', encoding='utf-8') as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:].lstrip()
            if '=' not in line:
                raise ValueError(
                    f"Invalid line in {env_path}:{lineno}. Expected KEY=VALUE."
                )

            key, value = line.split('=', 1)
            key = key.strip()
            if not key:
                raise ValueError(
                    f"Invalid line in {env_path}:{lineno}. Missing variable name."
                )
            if not any(key.startswith(prefix) for prefix in prefixes):
                continue
            if key in deprecated_keys:
                raise ValueError(
                    f"Unsupported key in {env_path}:{lineno}: {key}\n"
                    f"{deprecated_keys[key]}"
                )
            os.environ.setdefault(key, strip_env_quotes(value.strip()))

    return env_path
