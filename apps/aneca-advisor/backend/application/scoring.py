from typing import Any

from domain.article_scoring import ArticleScorer

_scorer = ArticleScorer()


def score_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for art in articles:
        score, es_riesgo = _scorer.score(art)
        result.append({**art, "score": score, "es_riesgo": es_riesgo})
    return sorted(result, key=lambda a: a["score"], reverse=True)
