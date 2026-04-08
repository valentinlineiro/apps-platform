import os
import uuid

from flask import Blueprint, jsonify, request, Response, current_app

from app import config
from app.services import batch_service, template_service
from platform_sdk.observability import log_exception

bp = Blueprint("batch", __name__)


@bp.route("/exam-corrector/batch/start", methods=["POST"])
def batch_start():
    template_id = (request.form.get("template_id") or "").strip()
    if not template_id or template_id == "__upload__":
        return jsonify({"ok": False, "error": "Selecciona una plantilla guardada para la corrección en lote."}), 400

    ruta_plantilla = template_service.obtener_ruta_template_por_id(template_id)
    if not ruta_plantilla:
        return jsonify({"ok": False, "error": "La plantilla seleccionada no existe."}), 400

    zip_file = request.files.get("examenes")
    if not zip_file:
        return jsonify({"ok": False, "error": "Falta el archivo ZIP con los exámenes."}), 400

    zip_path = os.path.join(config.UPLOAD_FOLDER, f"batch_{uuid.uuid4()}.zip")
    zip_file.save(zip_path)

    try:
        batch_id = batch_service.start_batch(zip_path, template_id, ruta_plantilla)
    except ValueError as exc:
        current_app.logger.warning("Batch start validation error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        log_exception("Unexpected error starting batch")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, "batch_id": batch_id})


@bp.route("/exam-corrector/batch/status/<batch_id>", methods=["GET"])
def batch_status(batch_id: str):
    status = batch_service.get_status(batch_id)
    if status is None:
        return jsonify({"ok": False, "error": "Batch no encontrado"}), 404
    return jsonify({"ok": True, **status})


@bp.route("/exam-corrector/batch/items/<batch_id>", methods=["GET"])
def batch_items(batch_id: str):
    items = batch_service.get_items(batch_id)
    if items is None:
        return jsonify({"ok": False, "error": "Batch no encontrado"}), 404
    return jsonify({"ok": True, "items": items})


@bp.route("/exam-corrector/batch/result/<batch_id>", methods=["GET"])
def batch_result(batch_id: str):
    status = batch_service.get_status(batch_id)
    if status is None:
        return jsonify({"ok": False, "error": "Batch no encontrado"}), 404

    csv_content = batch_service.get_csv(batch_id)
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=resultados_{batch_id[:8]}.csv"
        },
    )
