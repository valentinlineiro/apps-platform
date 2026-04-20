from collections.abc import Mapping
from typing import Any


class ArticleScorer:
    PESOS_Q = {"Q1": 1000, "Q2": 500, "Q3": 100, "Q4": 10, "Sin Q": 0}
    EDITORIALES_RIESGO = ["MDPI", "Frontiers", "Hindawi", "Bentham"]

    def score(self, art: Mapping[str, Any]) -> tuple[int, bool]:
        score = 0
        score += self.PESOS_Q.get(str(art.get("cuartil", "Sin Q")), 0)
        if art.get("posicion") == "Primero":
            score += 300
        if art.get("es_corresponding"):
            score += 250
        if art.get("posicion") == "Último" and int(art.get("num_autores", 1)) > 3:
            score += 150

        revista = str(art.get("revista", ""))
        es_riesgo = any(editorial.lower() in revista.lower() for editorial in self.EDITORIALES_RIESGO)
        if es_riesgo:
            score -= 300

        score += min(int(art.get("citas", 0)) * 2, 100)
        return score, es_riesgo
