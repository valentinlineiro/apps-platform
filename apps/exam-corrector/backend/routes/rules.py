import json

from flask import Blueprint, render_template, request

from services.scoring_service import (
    cargar_reglas_evaluacion, guardar_reglas_evaluacion, validar_reglas_evaluacion,
)

bp = Blueprint("rules", __name__)


@bp.route("/exam-corrector/rules", methods=["GET", "POST"])
def exam_rules():
    error = ""
    success = ""
    if request.method == "POST":
        raw = (request.form.get("rules_json") or "").strip()
        try:
            parsed = json.loads(raw)
            ok, msg, normalized = validar_reglas_evaluacion(parsed)
            if not ok:
                error = msg
            else:
                guardar_reglas_evaluacion(normalized)
                success = "Reglas guardadas correctamente."
        except json.JSONDecodeError as e:
            error = f"JSON inválido: {e}"
    rules = cargar_reglas_evaluacion()
    pretty = json.dumps(rules, ensure_ascii=False, indent=2)
    return render_template("rules_editor.html", rules_json=pretty, error=error, success=success)
