from typing import List

import requests
from uuid import UUID

from app.models.AvailabilityDTO import AvailabilityDTO
from config.load_values import API_URL, TOKEN


def fetch_availabilities_for_generation(semester_id: UUID, domain_id: UUID) -> List[AvailabilityDTO]:
    """
    Fetches teacher availabilities for timetable generation

    Args:
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Availability DTO payloads
    """
    url = f"{API_URL.rstrip('/')}/availability/{semester_id}/{domain_id}"

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
        raise ValueError("Expected availabilities endpoint to return a JSON list.")

    print(f"[availabilities] fetched raw items: {len(data)}")

    return data
