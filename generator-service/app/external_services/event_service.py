from typing import List

import requests
from uuid import UUID

from app.models.EventDTO import EventDTO
from config.load_values import BASE_URL, TOKEN


def fetch_events_for_generation(semester_id: UUID, domain_id: UUID) -> List[EventDTO]:
    """
    Fetches timetable events for generation

    Args:
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Event DTO payloads
    """
    url = f"{BASE_URL.rstrip('/')}/timetable-events/{semester_id}/{domain_id}"

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
        raise ValueError("Expected events endpoint to return a JSON list.")

    print(f"[events] fetched raw items: {len(data)}")

    return data
