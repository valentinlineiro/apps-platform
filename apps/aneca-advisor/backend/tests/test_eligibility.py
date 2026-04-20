import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import application.eligibility as uc

_TU = "Titular de Universidad (TU)"
_CU = "Catedrático (CU)"


def _art(cuartil="Q1", roles=None):
    return {"tipo": "Articulo", "cuartil": cuartil, "roles": ["Investigación"] if roles is None else roles}


def _base(**overrides):
    defaults = dict(field_key="general", figura=_TU, sexenios=0, horas=240,
                    docentia="Notable", expediente=[])
    return {**defaults, **overrides}


class GetFieldsTests(unittest.TestCase):
    def test_returns_dict_with_labels(self):
        fields = uc.get_fields()
        self.assertIsInstance(fields, dict)
        self.assertIn("general", fields)
        self.assertIn("economicas", fields)

    def test_values_are_strings(self):
        for label in uc.get_fields().values():
            self.assertIsInstance(label, str)


class EvaluateAptitudTests(unittest.TestCase):
    def test_apto_when_all_criteria_met(self):
        expediente = [_art() for _ in range(5)]
        result = uc.evaluate(**_base(expediente=expediente))
        self.assertTrue(result["apto"])

    def test_no_apto_insufficient_articles(self):
        result = uc.evaluate(**_base(expediente=[_art()]))
        self.assertFalse(result["apto"])

    def test_no_apto_insufficient_hours(self):
        expediente = [_art() for _ in range(5)]
        result = uc.evaluate(**_base(expediente=expediente, horas=100))
        self.assertFalse(result["apto"])

    def test_no_apto_low_docentia(self):
        expediente = [_art() for _ in range(5)]
        result = uc.evaluate(**_base(expediente=expediente, docentia="Aprobado"))
        self.assertFalse(result["apto"])

    def test_fast_track_bypasses_article_count(self):
        result = uc.evaluate(**_base(sexenios=2, expediente=[]))
        self.assertTrue(result["apto"])
        self.assertTrue(result["fast_track"])

    def test_cu_requires_more_articles_in_economicas(self):
        five_arts = [_art() for _ in range(5)]
        tu_result = uc.evaluate(**_base(field_key="economicas", figura=_TU, expediente=five_arts))
        cu_result = uc.evaluate(**_base(field_key="economicas", figura=_CU,
                                        expediente=five_arts, horas=300))
        self.assertTrue(tu_result["apto"])
        self.assertFalse(cu_result["apto"])

    def test_q3_articles_do_not_count(self):
        expediente = [_art(cuartil="Q3") for _ in range(10)]
        result = uc.evaluate(**_base(expediente=expediente))
        self.assertFalse(result["apto"])

    def test_articles_without_roles_do_not_count(self):
        expediente = [_art(roles=[]) for _ in range(10)]
        result = uc.evaluate(**_base(expediente=expediente))
        self.assertFalse(result["apto"])

    def test_compensation_path_apto(self):
        three_arts = [_art() for _ in range(3)]
        result = uc.evaluate(**_base(
            expediente=three_arts,
            sexenio_transferencia=True,
            patentes=2,
        ))
        self.assertTrue(result["apto"])
        self.assertTrue(result["detalle"]["compensacion"]["ok"])

    def test_result_contains_all_sections(self):
        result = uc.evaluate(**_base())
        for key in ("apto", "fast_track", "detalle"):
            self.assertIn(key, result)
        for section in ("investigacion", "docencia", "transferencia", "compensacion"):
            self.assertIn(section, result["detalle"])
