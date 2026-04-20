from typing import Any

from domain.eligibility import CRITERIA_CONFIG, EligibilityEvaluator

_evaluator = EligibilityEvaluator(config=CRITERIA_CONFIG)


def get_fields() -> dict[str, str]:
    return _evaluator.get_available_fields()


def evaluate(
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
) -> dict[str, Any]:
    result = _evaluator.evaluate(
        field_key=field_key,
        figura=figura,
        sexenios=sexenios,
        horas=horas,
        docentia=docentia,
        expediente=expediente,
        sexenio_transferencia=sexenio_transferencia,
        patentes=patentes,
        spin_offs=spin_offs,
        contratos_art83=contratos_art83,
        divulgacion=divulgacion,
    )
    return {"apto": result.apto, "fast_track": result.fast_track, "detalle": result.detalle}
