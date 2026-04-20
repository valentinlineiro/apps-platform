import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.scoring import score_articles


def _art(**kwargs):
    base = {"tipo": "Articulo", "cuartil": "Q1", "posicion": "Co-autor",
            "es_corresponding": False, "num_autores": 2, "citas": 0, "roles": [], "revista": "Nature"}
    return {**base, **kwargs}


class ScoreArticlesTests(unittest.TestCase):
    def test_q1_scores_higher_than_q2(self):
        results = score_articles([_art(cuartil="Q2"), _art(cuartil="Q1")])
        self.assertEqual(results[0]["cuartil"], "Q1")

    def test_first_author_bonus(self):
        co = score_articles([_art(posicion="Co-autor")])[0]
        first = score_articles([_art(posicion="Primero")])[0]
        self.assertGreater(first["score"], co["score"])

    def test_corresponding_bonus(self):
        plain = score_articles([_art()])[0]
        corr = score_articles([_art(es_corresponding=True)])[0]
        self.assertGreater(corr["score"], plain["score"])

    def test_risky_publisher_flagged(self):
        result = score_articles([_art(revista="MDPI Journal")])[0]
        self.assertTrue(result["es_riesgo"])

    def test_safe_publisher_not_flagged(self):
        result = score_articles([_art(revista="Nature")])[0]
        self.assertFalse(result["es_riesgo"])

    def test_citations_add_capped_bonus(self):
        low = score_articles([_art(citas=0)])[0]
        high = score_articles([_art(citas=100)])[0]
        capped = score_articles([_art(citas=999)])[0]
        self.assertGreater(high["score"], low["score"])
        self.assertEqual(high["score"], capped["score"])

    def test_results_sorted_descending_by_score(self):
        arts = [_art(cuartil="Q3"), _art(cuartil="Q1"), _art(cuartil="Q2")]
        results = score_articles(arts)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_score_and_es_riesgo_added_to_output(self):
        result = score_articles([_art()])[0]
        self.assertIn("score", result)
        self.assertIn("es_riesgo", result)

    def test_original_fields_preserved(self):
        art = _art(titulo="My Paper")
        result = score_articles([art])[0]
        self.assertEqual(result["titulo"], "My Paper")


class ArticleScorerTests(unittest.TestCase):
    """Tests on the domain scorer directly."""

    def setUp(self):
        from domain.article_scoring import ArticleScorer
        self.scorer = ArticleScorer()

    def test_ultimo_bonus_only_with_multiple_authors(self):
        single = {"cuartil": "Q1", "posicion": "Último", "num_autores": 1,
                  "es_corresponding": False, "citas": 0, "revista": "X"}
        multi = {**single, "num_autores": 5}
        s_single, _ = self.scorer.score(single)
        s_multi, _ = self.scorer.score(multi)
        self.assertGreater(s_multi, s_single)
