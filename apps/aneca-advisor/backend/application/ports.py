from collections.abc import Mapping
from typing import Any, Protocol


class JsonHttpClient(Protocol):
    def get_json(self, url: str, headers: Mapping[str, str] | None = None) -> dict[str, Any]: ...


class JournalQuartileGateway(Protocol):
    def obtener_cuartil(self, issn_input: str | None) -> str: ...
