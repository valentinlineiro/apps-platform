from typing import Any

from application.ports import JournalQuartileGateway, JsonHttpClient


class OrcidSyncUseCase:
    def __init__(self, *, http_client: JsonHttpClient, quartile_gateway: JournalQuartileGateway):
        self.http_client = http_client
        self.quartile_gateway = quartile_gateway

    def execute(self, orcid_id: str) -> list[dict[str, Any]]:
        expediente: list[dict[str, Any]] = []
        resp = self.http_client.get_json(
            f"https://pub.orcid.org/v3.0/{orcid_id}/works",
            headers={"Accept": "application/json"},
        )

        for group in resp.get("group", []):
            summary = group["work-summary"][0]
            doi = next(
                (
                    eid["external-id-value"]
                    for eid in summary.get("external-ids", {}).get("external-id", [])
                    if eid["external-id-type"] == "doi"
                ),
                None,
            )
            if not doi:
                continue

            alex = self.http_client.get_json(f"https://api.openalex.org/works/doi:{doi}")
            authors = alex.get("authorships", [])
            num_authors = len(authors)
            posicion, es_corr = "Co-autor", False

            for idx, auth in enumerate(authors):
                raw_orcid = auth.get("author", {}).get("orcid")
                current_orcid = str(raw_orcid) if raw_orcid else ""
                if current_orcid.endswith(orcid_id):
                    if idx == 0:
                        posicion = "Primero"
                    elif idx == num_authors - 1:
                        posicion = "Último"
                    if auth.get("is_corresponding"):
                        es_corr = True

            issn = alex.get("primary_location", {}).get("source", {}).get("issn", [None])[0]
            cuartil = self.quartile_gateway.obtener_cuartil(issn)
            expediente.append(
                {
                    "tipo": "Articulo",
                    "titulo": summary["title"]["title"]["value"],
                    "revista": alex.get("primary_location", {}).get("source", {}).get("display_name", "Desconocida"),
                    "cuartil": cuartil,
                    "posicion": posicion,
                    "es_corresponding": es_corr,
                    "num_autores": num_authors,
                    "citas": alex.get("cited_by_count", 0),
                    "roles": [],
                }
            )

        return expediente
