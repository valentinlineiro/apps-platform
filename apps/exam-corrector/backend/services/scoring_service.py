import json
import os

import config


def reglas_por_defecto() -> dict:
    return {
        "test": {
            "correcta": 1.0,
            "incorrecta": -0.25,
            "en_blanco": 0.0,
            "descripcion": "Regla test estándar",
        }
    }


def cargar_reglas_evaluacion() -> dict:
    defaults = reglas_por_defecto()
    if not os.path.exists(config.SCORING_RULES_PATH):
        guardar_reglas_evaluacion(defaults)
        return defaults
    try:
        with open(config.SCORING_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return defaults
        merged = defaults.copy()
        merged.update(data)
        return merged
    except Exception:
        return defaults


def guardar_reglas_evaluacion(rules: dict) -> None:
    tmp = config.SCORING_RULES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.SCORING_RULES_PATH)


def validar_reglas_evaluacion(data: dict) -> tuple:
    if not isinstance(data, dict):
        return False, "El JSON debe ser un objeto con tipos de examen.", {}

    normalizado = {}
    for tipo, cfg in data.items():
        if not isinstance(tipo, str) or not tipo.strip():
            return False, "Cada tipo de examen debe tener un nombre válido.", {}
        if not isinstance(cfg, dict):
            return False, f"El tipo '{tipo}' debe ser un objeto.", {}
        faltan = [k for k in ("correcta", "incorrecta", "en_blanco") if k not in cfg]
        if faltan:
            return False, f"En '{tipo}' faltan campos: {', '.join(faltan)}.", {}
        try:
            correcta = float(cfg["correcta"])
            incorrecta = float(cfg["incorrecta"])
            en_blanco = float(cfg["en_blanco"])
        except (TypeError, ValueError):
            return False, f"En '{tipo}' los valores correcta/incorrecta/en_blanco deben ser numéricos.", {}

        normalizado[tipo.strip().lower()] = {
            "correcta": correcta,
            "incorrecta": incorrecta,
            "en_blanco": en_blanco,
            "descripcion": str(cfg.get("descripcion", "")).strip(),
        }

    if "test" not in normalizado:
        normalizado["test"] = reglas_por_defecto()["test"]
    return True, "", normalizado


def normalizar_tipo_examen(value: str) -> str:
    tipo = (value or "").strip().lower()
    if "test" in tipo:
        return "test"
    return tipo or "test"


def clasificar_respuesta(respuesta_dada) -> str:
    if respuesta_dada is None:
        return "en_blanco"
    txt = str(respuesta_dada).strip().upper()
    if txt in {"", "— SIN MARCAR —", "SIN MARCAR", "NULL"}:
        return "en_blanco"
    if txt in {"MULTIPLE", "ILEGIBLE"}:
        return "incorrecta"
    return "respondida"


def aplicar_reglas_puntuacion(feedback: list, tipo_examen: str, reglas: dict) -> dict:
    tipo = normalizar_tipo_examen(tipo_examen)
    regla = reglas.get(tipo) or reglas.get("test") or {}
    puntos_ok = float(regla.get("correcta", 1.0))
    puntos_ko = float(regla.get("incorrecta", 0.0))
    puntos_blank = float(regla.get("en_blanco", 0.0))

    correctas = incorrectas = en_blanco = 0
    total_puntos = 0.0

    for item in feedback:
        categoria = clasificar_respuesta(item.get("respuesta_dada"))
        if item.get("correcta"):
            correctas += 1
            total_puntos += puntos_ok
        elif categoria == "en_blanco":
            en_blanco += 1
            total_puntos += puntos_blank
        else:
            incorrectas += 1
            total_puntos += puntos_ko

    max_puntos = len(feedback) * puntos_ok if puntos_ok else len(feedback)
    return {
        "tipo_examen": tipo,
        "regla": {"correcta": puntos_ok, "incorrecta": puntos_ko, "en_blanco": puntos_blank},
        "resumen": {"correctas": correctas, "incorrectas": incorrectas, "en_blanco": en_blanco},
        "total_puntos": round(total_puntos, 2),
        "max_puntos": round(max_puntos, 2),
    }
