import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import application.eligibility as eligibility
import application.horizon as horizon

_TU = "Titular de Universidad (TU)"


def _evaluate(**overrides):
    defaults = dict(field_key="general", figura=_TU, sexenios=0,
                    horas=240, docentia="Notable", expediente=[])
    return eligibility.evaluate(**{**defaults, **overrides})


def _art(cuartil="Q1"):
    return {"tipo": "Articulo", "cuartil": cuartil, "roles": ["Investigación"]}


class BuildActionPlanTests(unittest.TestCase):
    def test_missing_articles_produces_alta_action(self):
        result = _evaluate(expediente=[])
        actions = horizon.build_action_plan(result["detalle"])
        priorities = [a["priority"] for a in actions]
        self.assertIn("Alta", priorities)

    def test_no_gaps_produces_no_alta_actions(self):
        # Transfer points included to satisfy all criteria
        result = _evaluate(expediente=[_art() for _ in range(5)],
                           sexenio_transferencia=True, patentes=1)
        actions = horizon.build_action_plan(result["detalle"])
        self.assertFalse(any(a["priority"] == "Alta" for a in actions))

    def test_actions_sorted_by_priority(self):
        result = _evaluate(expediente=[], horas=0, docentia="No tengo")
        actions = horizon.build_action_plan(result["detalle"])
        order = {"Alta": 0, "Media": 1, "Info": 2}
        ranks = [order[a["priority"]] for a in actions]
        self.assertEqual(ranks, sorted(ranks))

    def test_each_action_has_required_keys(self):
        result = _evaluate(expediente=[])
        for action in horizon.build_action_plan(result["detalle"]):
            self.assertIn("priority", action)
            self.assertIn("title", action)
            self.assertIn("why", action)

    def test_missing_hours_action_included(self):
        result = _evaluate(expediente=[_art() for _ in range(5)], horas=0)
        titles = [a["title"] for a in horizon.build_action_plan(result["detalle"])]
        self.assertTrue(any("horas" in t.lower() for t in titles))


class BuildExplainabilityTests(unittest.TestCase):
    def test_fast_track_reflected_in_research_reason(self):
        result = _evaluate(sexenios=2)
        exp = horizon.build_explainability(result["apto"], result["detalle"])
        self.assertIn("Vía rápida", exp["research_reason"])

    def test_apto_decision_string(self):
        result = _evaluate(expediente=[_art() for _ in range(5)])
        exp = horizon.build_explainability(result["apto"], result["detalle"])
        self.assertEqual(exp["decision"], "Apto")

    def test_no_apto_decision_string(self):
        result = _evaluate(expediente=[])
        exp = horizon.build_explainability(result["apto"], result["detalle"])
        self.assertEqual(exp["decision"], "No apto")

    def test_compensation_path_reflected(self):
        result = _evaluate(expediente=[_art() for _ in range(3)],
                           sexenio_transferencia=True, patentes=2)
        exp = horizon.build_explainability(result["apto"], result["detalle"])
        self.assertEqual(exp["decision_path"], "Compensación")

    def test_explainability_has_all_keys(self):
        result = _evaluate(expediente=[])
        exp = horizon.build_explainability(result["apto"], result["detalle"])
        for key in ("decision", "decision_path", "research_reason",
                    "teaching_reason", "transfer_reason", "compensation_reason"):
            self.assertIn(key, exp)
