from dataclasses import dataclass
from typing import Any


CRITERIA_CONFIG: dict[str, dict[str, Any]] = {
    "economicas": {
        "label": "Ciencias Económicas",
        "fast_track_sexenios": {"TU": 2, "CU": 3},
        "investigacion": {"min_q1_q2_con_roles": {"TU": 5, "CU": 8}},
        "docencia": {
            "min_horas": {"TU": 240, "CU": 300},
            "docentia_levels": ["No tengo", "Aprobado", "Notable", "Excelente"],
            "min_docentia": {"TU": "Notable", "CU": "Notable"},
        },
        "transferencia": {
            "min_compensation_validos": {"TU": 3, "CU": 5},
            "min_points": {"TU": 3, "CU": 4},
        },
    },
    "general": {
        "label": "General (simulador)",
        "fast_track_sexenios": {"TU": 2, "CU": 3},
        "investigacion": {"min_q1_q2_con_roles": {"TU": 5, "CU": 5}},
        "docencia": {
            "min_horas": {"TU": 240, "CU": 240},
            "docentia_levels": ["No tengo", "Aprobado", "Notable", "Excelente"],
            "min_docentia": {"TU": "Notable", "CU": "Notable"},
        },
        "transferencia": {
            "min_compensation_validos": {"TU": 3, "CU": 3},
            "min_points": {"TU": 3, "CU": 3},
        },
    },
}


@dataclass
class EligibilityResult:
    apto: bool
    fast_track: bool
    detalle: dict[str, Any]


class EligibilityEvaluator:
    FIGURA_MAP = {
        "Titular de Universidad (TU)": "TU",
        "Catedrático (CU)": "CU",
    }

    def __init__(self, config: dict[str, dict[str, Any]] | None = None):
        self.config = config or CRITERIA_CONFIG

    def get_available_fields(self) -> dict[str, str]:
        return {key: value["label"] for key, value in self.config.items()}

    def evaluate(
        self,
        *,
        field_key: str,
        figura: str,
        sexenios: int,
        horas: int,
        docentia: str,
        expediente: list[dict[str, Any]],
        sexenio_transferencia: bool = False,
        patentes: int = 0,
        spin_offs: int = 0,
        contratos_art83: int = 0,
        divulgacion: bool = False,
    ) -> EligibilityResult:
        field_rules = self.config.get(field_key, self.config["general"])
        figura_key = self.FIGURA_MAP[figura]

        min_sexenios = field_rules["fast_track_sexenios"][figura_key]
        fast_track = sexenios >= min_sexenios

        if fast_track:
            investigacion_ok = True
            validos = None
            min_validos = 0
        else:
            min_validos = field_rules["investigacion"]["min_q1_q2_con_roles"][figura_key]
            validos = sum(
                1
                for articulo in expediente
                if articulo.get("tipo") == "Articulo"
                and articulo.get("cuartil") in {"Q1", "Q2"}
                and len(articulo.get("roles", [])) > 0
            )
            investigacion_ok = validos >= min_validos

        doc_levels = field_rules["docencia"]["docentia_levels"]
        min_doc = field_rules["docencia"]["min_docentia"][figura_key]
        min_hours = field_rules["docencia"]["min_horas"][figura_key]

        docentia_ok = doc_levels.index(docentia) >= doc_levels.index(min_doc)
        horas_ok = horas >= min_hours
        docencia_ok = docentia_ok and horas_ok
        apto = investigacion_ok and docencia_ok

        transferencia_points = (
            (2 if sexenio_transferencia else 0)
            + min(patentes, 2)
            + min(spin_offs, 2)
            + min(contratos_art83, 2)
            + (1 if divulgacion else 0)
        )
        transferencia_min_points = field_rules["transferencia"]["min_points"][figura_key]
        transferencia_ok = transferencia_points >= transferencia_min_points

        min_compensation_validos = field_rules["transferencia"]["min_compensation_validos"][figura_key]
        compensation_ok = (
            not investigacion_ok
            and docencia_ok
            and validos is not None
            and validos >= min_compensation_validos
            and transferencia_ok
        )
        if compensation_ok:
            apto = True

        detalle = {
            "field_label": field_rules["label"],
            "figura": figura,
            "investigacion": {
                "ok": investigacion_ok,
                "fast_track": fast_track,
                "sexenios": sexenios,
                "min_sexenios": min_sexenios,
                "validos": validos,
                "min_validos": min_validos,
            },
            "docencia": {
                "ok": docencia_ok,
                "horas": horas,
                "min_horas": min_hours,
                "horas_ok": horas_ok,
                "docentia": docentia,
                "min_docentia": min_doc,
                "docentia_ok": docentia_ok,
            },
            "transferencia": {
                "ok": transferencia_ok,
                "sexenio_transferencia": sexenio_transferencia,
                "patentes": patentes,
                "spin_offs": spin_offs,
                "contratos_art83": contratos_art83,
                "divulgacion": divulgacion,
                "points": transferencia_points,
                "min_points": transferencia_min_points,
            },
            "compensacion": {
                "ok": compensation_ok,
                "min_validos": min_compensation_validos,
            },
        }
        return EligibilityResult(apto=apto, fast_track=fast_track, detalle=detalle)
