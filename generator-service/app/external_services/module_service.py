from typing import List

import requests
from uuid import UUID

from app.models.ModuleDTO import ModuleDTO
from config.load_values import BASE_URL, TOKEN


def fetch_modules_for_generation(semester_id: UUID, domain_id: UUID) -> List[ModuleDTO]:
    """
    Fetches modules for timetable generation

    Args:
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Module DTO payloads
    """
    url = f"{BASE_URL.rstrip('/')}/modules/{semester_id}/{domain_id}"

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

    # print(data)

    if not isinstance(data, list):
        raise ValueError("Expected modules endpoint to return a JSON list.")

    return data
