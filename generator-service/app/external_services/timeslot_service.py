from typing import List
from uuid import UUID

import requests

from app.models.TimeslotDTO import TimeslotDTO
from config.load_values import BASE_URL, TOKEN



def fetch_timeslots_for_generation(domain_id: UUID) -> List[TimeslotDTO]:
    """
    Fetches timeslots for timetable generation

    Args:
        domain_id: Domain id

    Returns:
        Timeslot DTO payloads
    """
    url = f"{BASE_URL.rstrip('/')}/timeslots/bachelor/{domain_id}"

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
        raise ValueError("Expected timeslots endpoint to return a JSON list.")

    print(f"[timeslots] fetched raw items: {len(data)}")

    return data
