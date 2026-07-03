from typing import List

import requests

from app.models.DayDTO import DayDTO
from config.load_values import BASE_URL, TOKEN


def fetch_days_for_generation() -> List[DayDTO]:
    """
    Fetches generation days

    Args:
        None

    Returns:
        Day DTO payloads
    """
    url = f"{BASE_URL.rstrip('/')}/days"

    headers = {
        "Accept": "application/json",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    response = requests.get(
        url,
        headers=headers,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Expected days endpoint to return a JSON list.")

    return data
