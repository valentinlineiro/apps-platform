import os
import uuid

from flask import Blueprint, redirect, render_template, request
from werkzeug.utils import secure_filename

from app import config
from app.services import job_service, template_service

bp = Blueprint("legacy", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/exam-corrector")
@bp.route("/exam-corrector/")
def exam_corrector():
    if request.path == "/exam-corrector":
        return redirect("/exam-corrector/")
    return render_template("exam_corrector.html", templates_guardadas=template_service.listar_templates_guardadas())


@bp.route("/corregir", methods=["POST"])
@bp.route("/exam-corrector/corregir", methods=["POST"])
def corregir():
    examen_file = request.files.get("examen")
    if not examen_file:
        return render_template("resultado.html", **job_service._resultado_error("Falta el archivo de examen."))

    template_id = (request.form.get("template_id") or "").strip()
    plantilla_file = request.files.get("plantilla")
    template_name = (request.form.get("template_name") or "").strip()
    save_template = (request.form.get("save_template") or "1").strip() != "0"

    if template_id and template_id != "__upload__":
        ruta_plantilla = template_service.obtener_ruta_template_por_id(template_id)
        if not ruta_plantilla:
            return render_template(
                "resultado.html",
                **job_service._resultado_error("La plantilla seleccionada no existe o fue eliminada."),
            )
    else:
        if not plantilla_file:
            return render_template(
                "resultado.html",
                **job_service._resultado_error("Debes subir una plantilla o seleccionar una guardada."),
            )
        safe_name = secure_filename(plantilla_file.filename) or "plantilla"
        ruta_plantilla = os.path.join(config.UPLOAD_FOLDER, f"sync_{uuid.uuid4()}_{safe_name}")
        plantilla_file.save(ruta_plantilla)
        if save_template:
            template_service.registrar_template_guardada(ruta_plantilla, template_name=template_name)

    safe_examen = secure_filename(examen_file.filename) or "examen"
    ruta_examen = os.path.join(config.UPLOAD_FOLDER, f"sync_{uuid.uuid4()}_{safe_examen}")
    examen_file.save(ruta_examen)

    resultado = job_service.procesar_correccion(ruta_plantilla, ruta_examen)
    return render_template("resultado.html", **resultado)
