"""Canonical labels. Original strings stay on the row."""

from __future__ import annotations

import re

CUISINE_ALIASES = {
    "hot dog": "HOT_DOG",
    "hot dogs": "HOT_DOG",
    "bbq": "BBQ",
    "cafe": "CAFE",
}


def canonicalize_token(label: str | None) -> str | None:
    if label is None:
        return None
    key = re.sub(r"\s+", " ", str(label).strip().lower())
    if not key:
        return None
    if key in CUISINE_ALIASES:
        return CUISINE_ALIASES[key]
    token = re.sub(r"[^a-z0-9]+", "_", key).strip("_").upper()
    return token or None


def split_cuisines(cuisine_string: str | None) -> list[str]:
    if cuisine_string is None:
        return []
    tokens = []
    for part in str(cuisine_string).split(","):
        token = canonicalize_token(part)
        if token and token not in tokens:
            tokens.append(token)
    return tokens
