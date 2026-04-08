import json
import os
import threading
import time
import uuid
from typing import Optional

from concurrent.futures import ThreadPoolExecutor

import requests

from app import config
from app.models.job import Job
from app.services.image_service import load_and_crop, encode_for_gemini
from app.services.gemini_service import obtener_modelo_plantilla, llamar_gemini, PROMPT_CORRECCION_DESDE_MODELO
from app.services.scoring_service import (
    cargar_reglas_evaluacion, aplicar_reglas_puntuacion,
    normalizar_tipo_examen, reglas_por_defecto,
)
from app.services.job_store import JobStore

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
        "template_cache.json", "saved_templates.json",
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


def procesar_correccion(ruta_plantilla: str, ruta_examen: str, progress_cb=None) -> dict:
    if progress_cb:
        progress_cb(8, "loading", "Leyendo y preparando imágenes en paralelo...")
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_p = ex.submit(load_and_crop, ruta_plantilla)
            fut_e = ex.submit(load_and_crop, ruta_examen)
            plantilla_a4 = fut_p.result()
            examen_a4 = fut_e.result()
    except ValueError as e:
        return _resultado_error(str(e))

    try:
        if progress_cb:
            progress_cb(28, "encode", "Codificando imágenes...")
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_bp = ex.submit(encode_for_gemini, plantilla_a4)
            fut_be = ex.submit(encode_for_gemini, examen_a4)
            b64_p, template_hash = fut_bp.result()
            b64_e, _ = fut_be.result()
        modelo_plantilla = obtener_modelo_plantilla(b64_p, template_hash, progress_cb=progress_cb)
    except requests.HTTPError as e:
        return _resultado_error(f"Error en la API de Gemini: {e}")
    except (ValueError, KeyError) as e:
        return _resultado_error(f"No se pudo parsear la respuesta de Gemini: {e}")

    try:
        if progress_cb:
            progress_cb(62, "grading", "Corrigiendo examen...")
        prompt = PROMPT_CORRECCION_DESDE_MODELO.replace(
            "__TEMPLATE_MODEL__",
            json.dumps(modelo_plantilla, ensure_ascii=False),
        )
        result = llamar_gemini(
            parts=[{"inline_data": {"mime_type": "image/jpeg", "data": b64_e}}],
            prompt=prompt,
            timeout=90,
        )
    except requests.HTTPError as e:
        return _resultado_error(f"Error en la API de Gemini: {e}")
    except (ValueError, KeyError) as e:
        return _resultado_error(f"No se pudo parsear la respuesta de Gemini: {e}")

    if not bool(result.get("compatible", False)):
        motivo = result.get("motivo", "La plantilla no coincide con el examen.")
        try:
            conf = float(result.get("confianza", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        return _resultado_error(f"Plantilla incompatible (confianza {conf:.2f}). {motivo}")

    if progress_cb:
        progress_cb(82, "formatting", "Preparando informe...")
    formatted = _formatear_resultado(result, modelo_plantilla)
    if progress_cb:
        progress_cb(96, "finalizing", "Finalizando resultado...")
    return formatted


_CONFIDENCE_THRESHOLD = 0.80


def _formatear_resultado(result: dict, modelo_plantilla: dict) -> dict:
    """Convert a raw Gemini correction response into the final result dict."""
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
            "detalle_opciones": r.get("regla_aplicada", "Regla no indicada"),
            "estado": "Correcta" if correcta else "Incorrecta",
            "correcta": correcta,
            "confianza": round(confianza, 3),
            "recorte_correcta": "",
            "recorte_dada": "",
        })

    puntaje = sum(1 for f in feedback if f["correcta"])
    total = result.get("total", modelo_plantilla.get("total", len(feedback)))
    porcentaje = (puntaje / total * 100) if total else 0
    nombre = result.get("nombre", "Alumno desconocido")
    warning = "" if feedback else "Gemini no detectó respuestas en las imágenes."
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
    """Correct up to BATCH_SIZE exams in one Gemini call. Returns results in input order."""
    from app.services.gemini_service import llamar_gemini_lote, obtener_modelo_plantilla, BATCH_SIZE

    # Load and encode plantilla
    with ThreadPoolExecutor(max_workers=1) as ex:
        plantilla_a4 = ex.submit(load_and_crop, ruta_plantilla).result()
    b64_p, template_hash = encode_for_gemini(plantilla_a4)
    modelo_plantilla = obtener_modelo_plantilla(b64_p, template_hash)

    # Load and encode all exam images in parallel
    def _load_exam(item: tuple[str, str]) -> tuple[str, str]:
        filename, ruta = item
        try:
            img = load_and_crop(ruta)
            b64, _ = encode_for_gemini(img)
            return filename, b64
        except ValueError:
            return filename, ""

    with ThreadPoolExecutor(max_workers=min(len(examen_items), BATCH_SIZE)) as ex:
        encoded = list(ex.map(_load_exam, examen_items))

    # Separate items that failed image loading
    good: list[tuple[int, str, str]] = []   # (original_idx, filename, b64)
    bad_indices: set[int] = set()
    for orig_idx, (filename, b64) in enumerate(encoded):
        if b64:
            good.append((orig_idx, filename, b64))
        else:
            bad_indices.add(orig_idx)

    results: list[dict | None] = [None] * len(examen_items)

    # Fill errors for failed image loads
    for i in bad_indices:
        results[i] = _resultado_error("No se pudo leer la imagen del examen.")

    if good:
        images = [(filename, b64) for _, filename, b64 in good]
        raw_list = llamar_gemini_lote(images, modelo_plantilla)
        for (orig_idx, _, _), raw in zip(good, raw_list):
            results[orig_idx] = _formatear_resultado(raw, modelo_plantilla)

    return [r for r in results if r is not None]


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
