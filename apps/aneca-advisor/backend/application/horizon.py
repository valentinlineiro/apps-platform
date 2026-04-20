from typing import Any

_DOCENTIA_LEVELS = ["No tengo", "Aprobado", "Notable", "Excelente"]
_PRIORITY_ORDER = {"Alta": 0, "Media": 1, "Info": 2}


def build_action_plan(detalle: dict[str, Any]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    inv = detalle["investigacion"]
    doc = detalle["docencia"]
    transf = detalle["transferencia"]
    compensacion = detalle["compensacion"]

    if not inv["ok"] and not inv["fast_track"]:
        missing = max(inv["min_validos"] - int(inv["validos"] or 0), 0)
        if missing > 0:
            actions.append({
                "priority": "Alta",
                "title": f"Conseguir {missing} artículos Q1/Q2 con roles CRediT",
                "why": "La investigación todavía no alcanza el umbral mínimo para la figura objetivo.",
            })

    if not doc["horas_ok"]:
        missing_hours = max(doc["min_horas"] - doc["horas"], 0)
        actions.append({
            "priority": "Alta",
            "title": f"Completar {missing_hours} horas docentes adicionales",
            "why": "Las horas de docencia son requisito estructural y no se compensan por sí solas.",
        })

    if not doc["docentia_ok"]:
        current_idx = _DOCENTIA_LEVELS.index(doc["docentia"])
        target_idx = _DOCENTIA_LEVELS.index(doc["min_docentia"])
        jump = target_idx - current_idx
        actions.append({
            "priority": "Media" if jump == 1 else "Alta",
            "title": f"Subir DOCENTIA a {doc['min_docentia']}",
            "why": "La evaluación docente mínima es obligatoria para un resultado apto.",
        })

    if not transf["ok"]:
        needed = max(transf["min_points"] - transf["points"], 0)
        actions.append({
            "priority": "Media",
            "title": f"Aumentar transferencia en {needed} punto(s)",
            "why": "Mejora tu robustez global y habilita la vía de compensación si fuese necesaria.",
        })

    if compensacion["ok"]:
        actions.append({
            "priority": "Info",
            "title": "Consolidar investigación para no depender de compensación",
            "why": "Tu perfil ya es apto, pero reducir dependencia de la compensación baja riesgo evaluador.",
        })

    if not actions:
        actions.append({
            "priority": "Info",
            "title": "Mantener evidencias actualizadas y reforzar aportaciones top",
            "why": "No hay brechas críticas; toca preparar mejor el expediente para evaluación formal.",
        })

    return sorted(actions, key=lambda a: _PRIORITY_ORDER[a["priority"]])


def build_explainability(apto: bool, detalle: dict[str, Any]) -> dict[str, Any]:
    inv = detalle["investigacion"]
    doc = detalle["docencia"]
    transf = detalle["transferencia"]
    compensacion = detalle["compensacion"]

    if inv["fast_track"]:
        research_reason = (
            f"Vía rápida activa por sexenios ({inv['sexenios']}/{inv['min_sexenios']}). "
            "La investigación se considera cumplida sin contar artículos mínimos."
        )
    elif inv["ok"]:
        research_reason = f"Investigación válida ({inv['validos']}/{inv['min_validos']} artículos Q1/Q2 con roles)."
    else:
        research_reason = f"Investigación insuficiente ({inv['validos']}/{inv['min_validos']} artículos válidos)."

    teaching_reason = (
        f"Docencia {'cumplida' if doc['ok'] else 'insuficiente'}: "
        f"{doc['horas']}/{doc['min_horas']} horas y DOCENTIA {doc['docentia']} (mínimo {doc['min_docentia']})."
    )
    transfer_reason = (
        f"Transferencia {'suficiente' if transf['ok'] else 'insuficiente'}: "
        f"{transf['points']}/{transf['min_points']} puntos."
    )

    return {
        "decision": "Apto" if apto else "No apto",
        "decision_path": "Compensación" if compensacion["ok"] else "Ordinaria",
        "research_reason": research_reason,
        "teaching_reason": teaching_reason,
        "transfer_reason": transfer_reason,
        "compensation_reason": (
            "Compensación activada: docencia sólida + transferencia suficiente + déficit investigador leve."
            if compensacion["ok"]
            else "Compensación no activada."
        ),
    }
