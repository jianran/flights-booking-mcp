"""Configuration — load env vars."""

import os
from dotenv import load_dotenv

load_dotenv()


def get_duffel_token() -> str | None:
    """Get the Duffel API token."""
    return os.getenv("DUFFEL_API_TOKEN")


def get_serpapi_key() -> str | None:
    """Get the SerpAPI key (optional, for richer Google Flights data)."""
    return os.getenv("SERPAPI_API_KEY")


def has_duffel() -> bool:
    """Check if Duffel credentials are configured."""
    token = get_duffel_token()
    return token is not None and token != ""
