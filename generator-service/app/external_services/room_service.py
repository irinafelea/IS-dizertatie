from typing import List
from uuid import UUID

import requests

from app.models.RoomDTO import RoomDTO
from config.load_values import BASE_URL, TOKEN



def fetch_rooms_for_generation(domain_id: UUID) -> List[RoomDTO]:
    """
    Fetches active rooms for timetable generation

    Args:
        domain_id: Domain id

    Returns:
        Room DTO payloads
    """
    url = f"{BASE_URL.rstrip('/')}/rooms/active/{domain_id}"

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
        raise ValueError("Expected rooms endpoint to return a JSON list.")

    print(f"[rooms] fetched raw items: {len(data)}")

    return data
