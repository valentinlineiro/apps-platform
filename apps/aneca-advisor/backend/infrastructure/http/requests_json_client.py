from collections.abc import Mapping
from typing import Any

import requests


class RequestsJsonClient:
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
        return requests.get(url, headers=headers).json()
