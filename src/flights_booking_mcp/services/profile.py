"""Passenger profile management — save and load travel profiles."""

import json
import os
import logging

logger = logging.getLogger(__name__)

PROFILE_DIR = os.path.expanduser("~/.config/flights-booking-mcp")
PROFILE_PATH = os.path.join(PROFILE_DIR, "profile.json")


def _ensure_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)


def load_profile() -> dict | None:
    """Load the saved passenger profile, or None."""
    if not os.path.exists(PROFILE_PATH):
        return None
    try:
        with open(PROFILE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load profile: {e}")
        return None


def save_profile(profile: dict):
    """Save or update the passenger profile."""
    _ensure_dir()
    existing = load_profile() or {}
    existing.update(profile)
    with open(PROFILE_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    logger.info(f"Profile saved to {PROFILE_PATH}")


def profile_exists() -> bool:
    """Check if a profile has been saved."""
    return os.path.exists(PROFILE_PATH)


def merge_with_profile(kwargs: dict) -> dict:
    """Fill missing booking fields from the saved profile."""
    profile = load_profile()
    if not profile:
        return kwargs

    defaults = {
        "title": profile.get("title"),
        "given_name": profile.get("given_name"),
        "family_name": profile.get("family_name"),
        "gender": profile.get("gender"),
        "born_on": profile.get("born_on"),
        "phone_number": profile.get("phone_number"),
        "email": profile.get("email"),
    }

    for key, val in defaults.items():
        if val is not None and (key not in kwargs or not kwargs.get(key)):
            kwargs[key] = val

    return kwargs
