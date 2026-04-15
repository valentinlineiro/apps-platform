import logging
import os
import threading
import time
import uuid
from typing import Optional

from concurrent.futures import ThreadPoolExecutor

from app import config
from app.models.job import Job
from app.services.image_service import (
    load_and_crop, hash_image, corregir_con_omr, detectar_bboxes_cv,
)
from app.services.scoring_service import (
    cargar_reglas_evaluacion, aplicar_reglas_puntuacion,
    normalizar_tipo_examen, reglas_por_defecto,
)
from app.services.job_store import JobStore
from app.services import template_service

_log = logging.getLogger(__name__)
_store: Optional[JobStore] = None


def init(store: JobStore) -> None:
    global _store
    _store = store


def get_store() -> JobStore:
    if _store is None:
        raise RuntimeError("JobStore not initialized. Call job_service.init(store) first.")
    return _store


def cleanup_old_uploads() -> None:
    """Delete temp upload files older than UPLOAD_MAX_AGE_SECONDS; keep library/config files."""
    cutoff = time.time() - config.UPLOAD_MAX_AGE_SECONDS
    protected = {
        "template_bbox_cache.json", "saved_templates.json",
        "scoring_rules.json", "jobs.db", "jobs.db-wal", "jobs.db-shm",
    }
    for fname in os.listdir(config.UPLOAD_FOLDER):
        if fname in protected or fname == "templates":
            continue
        fpath = os.path.join(config.UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
            try:
                os.remove(fpath)
            except OSError:
                pass
    get_store().delete_finished_before(cutoff)


def _resultado_error(msg: str) -> dict:
    default_scoring = reglas_por_defecto().get("test", {"correcta": 1.0, "incorrecta": 0.0, "en_blanco": 0.0})
    return {
        "puntaje": 0,
        "total": 0,
        "porcentaje": 0,
        "porcentaje_puntos": 0,
        "feedback": [],
        "warning": msg,
        "tipo_examen": "test",
        "scoring_regla": default_scoring,
        "scoring_resumen": {"correctas": 0, "incorrectas": 0, "en_blanco": 0},
        "total_puntos": 0,
        "max_puntos": 0,
    }


def actualizar_progreso(job_id: str, progress: int, stage: str, message: str) -> None:
    get_store().update(
        job_id,
        status="running",
        progress=max(0, min(100, int(progress))),
        stage=stage,
        message=message,
    )


def _obtener_bboxes_cv(plantilla_a4, template_hash: str) -> dict | None:
    """Return CV-detected bboxes for the template, using the in-memory cache."""
    with template_service.BBOX_CACHE_LOCK:
        cached = template_service.BBOX_CACHE.get(template_hash)
    if cached:
        return cached

    _log.info("detectando zonas de respuesta en plantilla (CV)...")
    result = detectar_bboxes_cv(plantilla_a4)
    if result is None:
        _log.warning("detectar_bboxes_cv: no se encontró cuadrícula de respuestas")
        return None

    n_q = len(result.get("preguntas", []))
    _log.info(f"detectar_bboxes_cv: {n_q} preguntas detectadas")
    with template_service.BBOX_CACHE_LOCK:
        template_service.BBOX_CACHE[template_hash] = result
        template_service.guardar_bbox_cache()
    return result


def procesar_correccion(ruta_plantilla: str, ruta_examen: str, progress_cb=None) -> dict:
    if progress_cb:
        progress_cb(8, "loading", "Leyendo imágenes...")
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_p = ex.submit(load_and_crop, ruta_plantilla)
            fut_e = ex.submit(load_and_crop, ruta_examen)
            plantilla_a4 = fut_p.result()
            examen_a4 = fut_e.result()
    except ValueError as e:
        return _resultado_error(str(e))

    if progress_cb:
        progress_cb(28, "template-analyze", "Analizando plantilla...")
    try:
        template_hash = hash_image(plantilla_a4)
    except ValueError as e:
        return _resultado_error(str(e))

    bbox_data = _obtener_bboxes_cv(plantilla_a4, template_hash)
    if bbox_data is None:
        return _resultado_error(
            "No se pudo detectar la cuadrícula de respuestas en la plantilla. "
            "Compruebe que sea una imagen clara de un examen tipo test."
        )

    if progress_cb:
        progress_cb(62, "grading", "Corrigiendo examen (OMR)...")
    try:
        omr_result = corregir_con_omr(plantilla_a4, examen_a4, bbox_data)
    except Exception as exc:
        _log.warning(f"corregir_con_omr error: {exc}")
        omr_result = None

    if omr_result is None:
        return _resultado_error(
            "No se pudo corregir el examen automáticamente. "
            "La alineación o la detección de marcas falló."
        )

    _log.info(f"procesar_correccion: OMR ok (ecc={omr_result.get('confianza')})")
    if progress_cb:
        progress_cb(82, "formatting", "Preparando informe...")
    formatted = _formatear_resultado(omr_result)
    if progress_cb:
        progress_cb(96, "finalizing", "Finalizando resultado...")
    return formatted


_CONFIDENCE_THRESHOLD = 0.80


def _formatear_resultado(result: dict) -> dict:
    """Convert an OMR correction result into the final result dict."""
    respuestas = result.get("respuestas", [])
    feedback = []
    for r in respuestas:
        correcta = bool(r.get("correcta", False))
        resp_correcta = r.get("respuesta_correcta") or ""
        resp_dada = r.get("respuesta_dada") or "— sin marcar —"
        try:
            confianza = float(r.get("confianza", 1.0))
        except (TypeError, ValueError):
            confianza = 1.0
        feedback.append({
            "pregunta": r.get("pregunta", len(feedback) + 1),
            "pregunta_label": f"Pregunta {r.get('pregunta', len(feedback) + 1)}",
            "respuesta_correcta": resp_correcta,
            "respuesta_dada": resp_dada,
            "similitud": 1.0 if correcta else 0.0,
            "detalle_opciones": r.get("regla_aplicada", "OMR"),
            "estado": "Correcta" if correcta else "Incorrecta",
            "correcta": correcta,
            "confianza": round(confianza, 3),
            "recorte_correcta": "",
            "recorte_dada": "",
        })

    puntaje = sum(1 for f in feedback if f["correcta"])
    total = result.get("total", len(feedback))
    porcentaje = (puntaje / total * 100) if total else 0
    nombre = result.get("nombre") or "Alumno desconocido"
    warning = "" if feedback else "OMR no detectó respuestas en las imágenes."
    min_confidence = min((f["confianza"] for f in feedback), default=1.0)
    needs_review = min_confidence < _CONFIDENCE_THRESHOLD
    tipo_examen = normalizar_tipo_examen(result.get("tipo_examen", "test"))
    reglas = cargar_reglas_evaluacion()
    scoring = aplicar_reglas_puntuacion(feedback, tipo_examen, reglas)
    porcentaje_puntos = (scoring["total_puntos"] / scoring["max_puntos"] * 100) if scoring["max_puntos"] else 0

    return {
        "nombre": nombre,
        "puntaje": puntaje,
        "total": total,
        "porcentaje": round(porcentaje, 1),
        "porcentaje_puntos": round(porcentaje_puntos, 1),
        "feedback": feedback,
        "warning": warning,
        "tipo_examen": scoring["tipo_examen"],
        "scoring_regla": scoring["regla"],
        "scoring_resumen": scoring["resumen"],
        "total_puntos": scoring["total_puntos"],
        "max_puntos": scoring["max_puntos"],
        "min_confidence": round(min_confidence, 3),
        "needs_review": needs_review,
    }


def procesar_correccion_lote(
    ruta_plantilla: str,
    examen_items: list[tuple[str, str]],  # (filename, ruta_examen)
) -> list[dict]:
    """Correct a batch of exams using CV-only OMR (no network calls)."""

    plantilla_a4 = load_and_crop(ruta_plantilla)
    template_hash = hash_image(plantilla_a4)
    bbox_data = _obtener_bboxes_cv(plantilla_a4, template_hash)

    if bbox_data is None:
        err = _resultado_error(
            "No se pudo detectar la cuadrícula de respuestas en la plantilla."
        )
        return [err] * len(examen_items)

    # Load all student images in parallel
    def _load_exam(item: tuple[str, str]) -> tuple[str, object]:
        filename, ruta = item
        try:
            return filename, load_and_crop(ruta)
        except Exception:
            return filename, None

    with ThreadPoolExecutor(max_workers=min(len(examen_items), 8)) as ex:
        loaded = list(ex.map(_load_exam, examen_items))

    # Correct each exam via OMR (CPU-only, safe to run in parallel)
    def _correct_one(filename: str, img) -> dict:
        if img is None:
            return _resultado_error("No se pudo leer la imagen del examen.")
        try:
            omr_result = corregir_con_omr(plantilla_a4, img, bbox_data)
        except Exception as exc:
            return _resultado_error(f"Error OMR: {exc}")
        if omr_result is None:
            return _resultado_error(
                "OMR no pudo determinar las respuestas del alumno. "
                "Compruebe que el examen esté bien enfocado y alineado."
            )
        return _formatear_resultado(omr_result)

    with ThreadPoolExecutor(max_workers=min(len(loaded), 8)) as ex:
        results = list(ex.map(lambda t: _correct_one(*t), loaded))

    n_ok = sum(1 for r in results if not r.get("warning"))
    n_err = len(results) - n_ok
    _log.info(
        f"procesar_correccion_lote: {len(examen_items)} exams — "
        f"{n_ok} OMR ok, {n_err} failed"
    )
    return results


def submit_job(job_id: str, ruta_plantilla: str, ruta_examen: str, template_id: str = "") -> None:
    now = time.time()
    job = Job(
        id=job_id,
        status="queued",
        progress=0,
        stage="queued",
        message="Esperando procesamiento...",
        template_id=template_id,
        created_at=now,
        updated_at=now,
    )
    get_store().create(job)
    thread = threading.Thread(target=_run_job, args=(job_id, ruta_plantilla, ruta_examen), daemon=True)
    thread.start()
    actualizar_progreso(job_id, 2, "running", "Trabajo iniciado...")


def _run_job(job_id: str, ruta_plantilla: str, ruta_examen: str) -> None:
    try:
        actualizar_progreso(job_id, 5, "queued", "Trabajo en cola...")
        result = procesar_correccion(
            ruta_plantilla,
            ruta_examen,
            progress_cb=lambda p, s, m: actualizar_progreso(job_id, p, s, m),
        )
        get_store().update(
            job_id,
            status="done",
            progress=100,
            stage="done",
            message="Corrección completada.",
            result=result,
            finished_at=time.time(),
        )
    except Exception as e:
        get_store().update(
            job_id,
            status="error",
            error=str(e),
            finished_at=time.time(),
        )
