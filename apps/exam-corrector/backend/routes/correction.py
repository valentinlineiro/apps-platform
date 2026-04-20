import os
import uuid

from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename

import config
from services import job_service, template_service

bp = Blueprint("correction", __name__)


@bp.route("/exam-corrector/start", methods=["POST"])
def start_async():
    examen_file = request.files.get("examen")
    if not examen_file:
        return jsonify({"ok": False, "error": "Falta archivo de examen."}), 400

    template_id = (request.form.get("template_id") or "").strip()
    plantilla_file = request.files.get("plantilla")
    template_name = (request.form.get("template_name") or "").strip()
    save_template = (request.form.get("save_template") or "1").strip() != "0"

    job_service.cleanup_old_uploads()

    job_id = str(uuid.uuid4())

    if template_id and template_id != "__upload__":
        ruta_plantilla = template_service.obtener_ruta_template_por_id(template_id)
        if not ruta_plantilla:
            return jsonify({"ok": False, "error": "La plantilla seleccionada no existe."}), 400
    else:
        if not plantilla_file:
            return jsonify({"ok": False, "error": "Debes subir una plantilla o seleccionar una guardada."}), 400
        safe_name = secure_filename(plantilla_file.filename) or "plantilla"
        ruta_plantilla = os.path.join(config.UPLOAD_FOLDER, f"{job_id}_plantilla_{safe_name}")
        plantilla_file.save(ruta_plantilla)
        if save_template:
            saved = template_service.registrar_template_guardada(ruta_plantilla, template_name=template_name)
            template_id = saved["id"]

    safe_examen = secure_filename(examen_file.filename) or "examen"
    ruta_examen = os.path.join(config.UPLOAD_FOLDER, f"{job_id}_examen_{safe_examen}")
    examen_file.save(ruta_examen)

    job_service.submit_job(job_id, ruta_plantilla, ruta_examen, template_id=template_id)

    return jsonify({"ok": True, "job_id": job_id})


@bp.route("/exam-corrector/status/<job_id>", methods=["GET"])
def job_status(job_id: str):
    job = job_service.get_store().get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404

    if job.status == "done":
        return jsonify({
            "ok": True,
            "status": "done",
            "progress": 100,
            "stage": "done",
            "message": job.message or "Corrección completada.",
            "result_url": f"/exam-corrector/result/{job_id}",
        })
    if job.status == "error":
        return jsonify({"ok": False, "status": "error", "error": job.error or "Error desconocido"}), 500
    return jsonify({
        "ok": True,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "message": job.message or "Procesando...",
    })


@bp.route("/exam-corrector/result/<job_id>", methods=["GET"])
def job_result(job_id: str):
    job = job_service.get_store().get(job_id)
    if not job:
        return render_template("resultado.html", **job_service._resultado_error("Job no encontrado."))
    if job.status == "error":
        return render_template("resultado.html", **job_service._resultado_error(job.error or "Error desconocido."))
    if job.status != "done":
        return render_template("resultado.html", **job_service._resultado_error("El proceso aún no ha terminado."))
    return render_template("resultado.html", **job.result)


@bp.route("/exam-corrector/api/result/<job_id>", methods=["GET"])
def job_result_json(job_id: str):
    job = job_service.get_store().get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404
    if job.status == "error":
        return jsonify({"ok": False, "status": "error", "error": job.error or "Error desconocido."}), 500
    if job.status != "done":
        return jsonify({"ok": True, "status": job.status})
    return jsonify({"ok": True, "status": "done", "result": job.result})
