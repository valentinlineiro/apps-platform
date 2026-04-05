"""
Corrector de exámenes tipo test — Flask + Gemini Vision
--------------------------------------------------------
Mantiene la estructura original (rutas, templates, variables)
pero reemplaza OpenCV+Tesseract por Gemini 1.5 Flash.

Requiere:
    pip install flask opencv-python-headless requests numpy
    GEMINI_API_KEY=tu_clave (variable de entorno o hardcodeada abajo)
"""

import os
import re
import json
import base64
import time
import threading
import uuid
import hashlib
import requests
import numpy as np
import cv2
from flask import Flask, request, render_template, redirect, jsonify
from flask_cors import CORS

# ─── CONFIG ───────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = "gemini-2.5-flash"


def gemini_url():
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

app = Flask(__name__)
CORS(app, resources={r"/exam-corrector/*": {"origins": "*"}})
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
JOBS = {}
JOBS_LOCK = threading.Lock()
TEMPLATE_CACHE_PATH = os.path.join(BASE_DIR, "uploads", "template_cache.json")
TEMPLATE_CACHE = {}
TEMPLATE_CACHE_LOCK = threading.Lock()
TEMPLATE_LIBRARY_PATH = os.path.join(BASE_DIR, "uploads", "saved_templates.json")
TEMPLATE_STORE_DIR = os.path.join(BASE_DIR, "uploads", "templates")
os.makedirs(TEMPLATE_STORE_DIR, exist_ok=True)
SCORING_RULES_PATH = os.path.join(BASE_DIR, "uploads", "scoring_rules.json")


# ─── UTILIDADES IMAGEN ────────────────────────────────────────────────────────

def recorte_a4(imagen):
    """Detecta y endereza el folio en la foto (igual que el original)."""
    alto, ancho = imagen.shape[:2]
    escala = 1100 / max(1, alto)
    redimensionada = cv2.resize(imagen, (int(ancho * escala), 1100))
    gris = cv2.cvtColor(redimensionada, cv2.COLOR_BGR2GRAY)
    suavizada = cv2.GaussianBlur(gris, (7, 7), 0)

    _, blanca = cv2.threshold(suavizada, 160, 255, cv2.THRESH_BINARY)
    blanca = cv2.morphologyEx(blanca, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8), iterations=2)
    contornos, _ = cv2.findContours(blanca, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mejor = None
    mejor_area = 0
    area_total = redimensionada.shape[0] * redimensionada.shape[1]
    for c in contornos:
        area = cv2.contourArea(c)
        if area < area_total * 0.2:
            continue
        perimetro = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        if len(aprox) == 4 and area > mejor_area:
            mejor = aprox.reshape(4, 2).astype(np.float32)
            mejor_area = area

    if mejor is not None:
        suma  = mejor.sum(axis=1)
        diff  = np.diff(mejor, axis=1).reshape(-1)
        tl    = mejor[np.argmin(suma)]
        br    = mejor[np.argmax(suma)]
        tr    = mejor[np.argmin(diff)]
        bl    = mejor[np.argmax(diff)]
        dest  = np.array([[0, 0], [900, 0], [900, 1100], [0, 1100]], dtype=np.float32)
        M     = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), dest)
        return cv2.warpPerspective(redimensionada, M, (900, 1100))

    if contornos:
        cmax = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(cmax)
        if w > 100 and h > 100:
            return redimensionada[y:y + h, x:x + w]

    return redimensionada


def a_data_uri(imagen_bgr):
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def imagen_bgr_a_b64(imagen_bgr) -> str:
    """Convierte imagen OpenCV a base64 JPEG."""
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise ValueError("No se pudo codificar la imagen")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ─── GEMINI ───────────────────────────────────────────────────────────────────

PROMPT_TEMPLATE_MODEL = """
Analiza UNA imagen de plantilla de examen tipo test (economía) con respuestas correctas marcadas.
Construye un modelo intermedio reutilizable.

Devuelve SOLO JSON con este formato:
{
  "total": 0,
  "respuestas_correctas": [
    {"pregunta": 1, "texto": "primeras 8-12 palabras de la opción marcada"}
  ]
}

Reglas:
- Orden: primero columna izquierda arriba-abajo, luego columna derecha.
- Si una marca no es legible, pon texto "ILEGIBLE".
- No inventes preguntas.
"""


PROMPT_CORRECCION_DESDE_MODELO = """
Recibes:
1) Una imagen de examen de alumno.
2) Un MODELO de plantilla en JSON con respuestas correctas por pregunta.

MODELO PLANTILLA:
__TEMPLATE_MODEL__

Objetivo:
- Detectar las respuestas del alumno en el mismo orden de preguntas del modelo.
- Comparar contra la plantilla.
- Decidir compatibilidad plantilla/examen.
- Extraer nombre del alumno de "APELLIDOS Y NOMBRE".

Reglas de corrección:
- Regla 1: correcta solo si coincide con respuesta_correcta del modelo.
- Regla 2: si no marca respuesta, respuesta_dada = null e incorrecta.
- Regla 3: si marca múltiples, respuesta_dada = "MULTIPLE" e incorrecta.
- Regla 4: si no legible, respuesta_dada = "ILEGIBLE" e incorrecta.
- Regla 5: no inventar preguntas fuera del modelo.

Devuelve SOLO JSON:
{
  "tipo_examen": "test",
  "compatible": true,
  "confianza": 0.0,
  "motivo": "explicación breve",
  "nombre": "apellidos y nombre",
  "total": 0,
  "respuestas": [
    {
      "pregunta": 1,
      "respuesta_correcta": "texto plantilla",
      "respuesta_dada": "texto alumno o null o MULTIPLE o ILEGIBLE",
      "correcta": true,
      "regla_aplicada": "Regla 1"
    }
  ]
}
"""


def parsear_json_de_texto(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', texto)
        if not match:
            raise ValueError(f"Gemini no devolvió JSON válido:\n{texto}")
        return json.loads(match.group())


def cargar_template_cache() -> None:
    global TEMPLATE_CACHE
    if not os.path.exists(TEMPLATE_CACHE_PATH):
        TEMPLATE_CACHE = {}
        return
    try:
        with open(TEMPLATE_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        TEMPLATE_CACHE = data if isinstance(data, dict) else {}
    except Exception:
        TEMPLATE_CACHE = {}


def guardar_template_cache() -> None:
    tmp = TEMPLATE_CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(TEMPLATE_CACHE, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TEMPLATE_CACHE_PATH)


def cargar_template_library() -> list:
    if not os.path.exists(TEMPLATE_LIBRARY_PATH):
        return []
    try:
        with open(TEMPLATE_LIBRARY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


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
    if not os.path.exists(SCORING_RULES_PATH):
        guardar_reglas_evaluacion(defaults)
        return defaults
    try:
        with open(SCORING_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return defaults
        merged = defaults.copy()
        merged.update(data)
        return merged
    except Exception:
        return defaults


def guardar_reglas_evaluacion(rules: dict) -> None:
    tmp = SCORING_RULES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SCORING_RULES_PATH)


def validar_reglas_evaluacion(data: dict) -> tuple[bool, str, dict]:
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
        defaults = reglas_por_defecto()["test"]
        normalizado["test"] = defaults
    return True, "", normalizado


def guardar_template_library(items: list) -> None:
    tmp = TEMPLATE_LIBRARY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TEMPLATE_LIBRARY_PATH)


def listar_templates_guardadas() -> list:
    items = cargar_template_library()
    for item in items:
        item.setdefault("id", "")
        item.setdefault("name", "")
        item.setdefault("filename", "")
        item.setdefault("created_at", 0)
    items = [i for i in items if i.get("id") and i.get("filename")]
    items.sort(key=lambda it: it.get("created_at", 0), reverse=True)
    return items


def registrar_template_guardada(src_path: str, template_name: str = "") -> dict:
    extension = os.path.splitext(src_path)[1].lower() or ".jpg"
    template_id = str(uuid.uuid4())
    dst_filename = f"{template_id}{extension}"
    dst_path = os.path.join(TEMPLATE_STORE_DIR, dst_filename)
    with open(src_path, "rb") as rf, open(dst_path, "wb") as wf:
        wf.write(rf.read())

    name = (template_name or "").strip()
    if not name:
        name = f"Plantilla {time.strftime('%Y-%m-%d %H:%M')}"

    item = {
        "id": template_id,
        "name": name,
        "filename": dst_filename,
        "created_at": int(time.time()),
    }
    items = cargar_template_library()
    items = [i for i in items if i.get("id") != template_id]
    items.append(item)
    guardar_template_library(items)
    return item


def obtener_ruta_template_por_id(template_id: str) -> str:
    for item in cargar_template_library():
        if item.get("id") == template_id:
            filename = item.get("filename", "")
            if not filename:
                break
            candidate = os.path.join(TEMPLATE_STORE_DIR, filename)
            if os.path.isfile(candidate):
                return candidate
            break
    return ""


def hash_template_image(imagen_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise ValueError("No se pudo generar hash de plantilla.")
    return hashlib.sha256(buf.tobytes()).hexdigest()


def llamar_gemini(parts: list, prompt: str, timeout: int = 90) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("Falta GEMINI_API_KEY en variables de entorno.")
    payload = {
        "contents": [{
            "parts": parts + [{"text": prompt}],
        }],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}
    }
    resp = requests.post(gemini_url(), json=payload, timeout=timeout)
    resp.raise_for_status()
    texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return parsear_json_de_texto(texto)


def obtener_modelo_plantilla(plantilla_a4, b64_p: str, progress_cb=None) -> dict:
    template_hash = hash_template_image(plantilla_a4)
    with TEMPLATE_CACHE_LOCK:
        cached = TEMPLATE_CACHE.get(template_hash)
    if cached:
        if progress_cb:
            progress_cb(34, "template-cache", "Plantilla reconocida (cache).")
        return cached

    if progress_cb:
        progress_cb(38, "template-analyze", "Analizando plantilla (primera vez)...")
    model = llamar_gemini(
        parts=[{"inline_data": {"mime_type": "image/jpeg", "data": b64_p}}],
        prompt=PROMPT_TEMPLATE_MODEL,
        timeout=60,
    )
    if "respuestas_correctas" not in model:
        raise ValueError("Modelo de plantilla inválido.")

    with TEMPLATE_CACHE_LOCK:
        TEMPLATE_CACHE[template_hash] = model
        guardar_template_cache()
    return model


def normalizar_tipo_examen(value: str) -> str:
    tipo = (value or "").strip().lower()
    if "test" in tipo:
        return "test"
    return tipo or "test"


def clasificar_respuesta(respuesta_dada):
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

    correctas = 0
    incorrectas = 0
    en_blanco = 0
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
        "regla": {
            "correcta": puntos_ok,
            "incorrecta": puntos_ko,
            "en_blanco": puntos_blank,
        },
        "resumen": {
            "correctas": correctas,
            "incorrectas": incorrectas,
            "en_blanco": en_blanco,
        },
        "total_puntos": round(total_puntos, 2),
        "max_puntos": round(max_puntos, 2),
    }


def _resultado_error(msg: str, debug_plantilla: str = "", debug_examen: str = "") -> dict:
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
        "debug_plantilla": debug_plantilla,
        "debug_examen": debug_examen,
    }


def actualizar_progreso(job_id: str, progress: int, stage: str, message: str) -> None:
    with JOBS_LOCK:
        if job_id not in JOBS:
            return
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["progress"] = max(0, min(100, int(progress)))
        JOBS[job_id]["stage"] = stage
        JOBS[job_id]["message"] = message
        JOBS[job_id]["updated_at"] = time.time()


def procesar_correccion(ruta_plantilla: str, ruta_examen: str, progress_cb=None) -> dict:
    if progress_cb:
        progress_cb(8, "loading", "Leyendo imágenes...")
    img_plantilla = cv2.imread(ruta_plantilla)
    img_examen = cv2.imread(ruta_examen)
    if img_plantilla is None or img_examen is None:
        return _resultado_error("No se pudieron leer una o ambas imágenes.")

    if progress_cb:
        progress_cb(20, "preprocess", "Preparando hojas...")
    plantilla_a4 = recorte_a4(img_plantilla)
    examen_a4 = recorte_a4(img_examen)
    debug_plantilla = a_data_uri(plantilla_a4)
    debug_examen = a_data_uri(examen_a4)

    try:
        if progress_cb:
            progress_cb(28, "encode", "Codificando imágenes...")
        b64_p = imagen_bgr_a_b64(plantilla_a4)
        b64_e = imagen_bgr_a_b64(examen_a4)
        modelo_plantilla = obtener_modelo_plantilla(plantilla_a4, b64_p, progress_cb=progress_cb)
    except requests.HTTPError as e:
        return _resultado_error(f"Error en la API de Gemini: {e}", debug_plantilla, debug_examen)
    except (ValueError, KeyError) as e:
        return _resultado_error(f"No se pudo parsear la respuesta de Gemini: {e}", debug_plantilla, debug_examen)

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
        return _resultado_error(f"Error en la API de Gemini: {e}", debug_plantilla, debug_examen)
    except (ValueError, KeyError) as e:
        return _resultado_error(f"No se pudo parsear la respuesta de Gemini: {e}", debug_plantilla, debug_examen)

    if not bool(result.get("compatible", False)):
        motivo = result.get("motivo", "La plantilla no coincide con el examen.")
        try:
            conf = float(result.get("confianza", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        return _resultado_error(
            f"Plantilla incompatible (confianza {conf:.2f}). {motivo}",
            debug_plantilla,
            debug_examen,
        )

    respuestas = result.get("respuestas", [])
    if progress_cb:
        progress_cb(82, "formatting", "Preparando informe...")
    feedback = []
    for r in respuestas:
        correcta = bool(r.get("correcta", False))
        resp_correcta = r.get("respuesta_correcta") or ""
        resp_dada = r.get("respuesta_dada") or "— sin marcar —"
        feedback.append(
            {
                "pregunta": r.get("pregunta", len(feedback) + 1),
                "pregunta_label": f"Pregunta {r.get('pregunta', len(feedback) + 1)}",
                "respuesta_correcta": resp_correcta,
                "respuesta_dada": resp_dada,
                "similitud": 1.0 if correcta else 0.0,
                "detalle_opciones": r.get("regla_aplicada", "Regla no indicada"),
                "estado": "Correcta" if correcta else "Incorrecta",
                "correcta": correcta,
                "recorte_correcta": "",
                "recorte_dada": "",
            }
        )

    puntaje = sum(1 for f in feedback if f["correcta"])
    total = result.get("total", modelo_plantilla.get("total", len(feedback)))
    porcentaje = (puntaje / total * 100) if total else 0
    nombre = result.get("nombre", "Alumno desconocido")
    warning = "" if feedback else "Gemini no detectó respuestas en las imágenes."
    tipo_examen = normalizar_tipo_examen(result.get("tipo_examen", "test"))
    reglas = cargar_reglas_evaluacion()
    scoring = aplicar_reglas_puntuacion(feedback, tipo_examen, reglas)
    porcentaje_puntos = (scoring["total_puntos"] / scoring["max_puntos"] * 100) if scoring["max_puntos"] else 0
    if progress_cb:
        progress_cb(96, "finalizing", "Finalizando resultado...")

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
        "debug_plantilla": debug_plantilla,
        "debug_examen": debug_examen,
    }


def _run_job(job_id: str, ruta_plantilla: str, ruta_examen: str) -> None:
    try:
        actualizar_progreso(job_id, 5, "queued", "Trabajo en cola...")
        result = procesar_correccion(
            ruta_plantilla,
            ruta_examen,
            progress_cb=lambda p, s, m: actualizar_progreso(job_id, p, s, m),
        )
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["progress"] = 100
            JOBS[job_id]["stage"] = "done"
            JOBS[job_id]["message"] = "Corrección completada."
            JOBS[job_id]["result"] = result
            JOBS[job_id]["finished_at"] = time.time()
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["finished_at"] = time.time()


# ─── RUTAS ────────────────────────────────────────────────────────────────────
cargar_template_cache()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/exam-corrector")
@app.route("/exam-corrector/")
def exam_corrector():
    if request.path == "/exam-corrector":
        return redirect("/exam-corrector/")
    return render_template("exam_corrector.html", templates_guardadas=listar_templates_guardadas())


@app.route("/exam-corrector/rules", methods=["GET", "POST"])
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


@app.route("/exam-corrector/api/templates", methods=["GET"])
def api_templates():
    return jsonify({"ok": True, "templates": listar_templates_guardadas()})


@app.route("/corregir", methods=["POST"])
@app.route("/exam-corrector/corregir", methods=["POST"])
def corregir():
    examen_file = request.files.get("examen")
    if not examen_file:
        resultado = _resultado_error("Falta el archivo de examen.")
        return render_template("resultado.html", **resultado)

    template_id = (request.form.get("template_id") or "").strip()
    plantilla_file = request.files.get("plantilla")
    template_name = (request.form.get("template_name") or "").strip()
    save_template = (request.form.get("save_template") or "1").strip() != "0"

    ruta_plantilla = ""
    if template_id and template_id != "__upload__":
        ruta_plantilla = obtener_ruta_template_por_id(template_id)
        if not ruta_plantilla:
            resultado = _resultado_error("La plantilla seleccionada no existe o fue eliminada.")
            return render_template("resultado.html", **resultado)
    else:
        if not plantilla_file:
            resultado = _resultado_error("Debes subir una plantilla o seleccionar una guardada.")
            return render_template("resultado.html", **resultado)
        ruta_plantilla = os.path.join(UPLOAD_FOLDER, f"sync_{uuid.uuid4()}_{plantilla_file.filename}")
        plantilla_file.save(ruta_plantilla)
        if save_template:
            registrar_template_guardada(ruta_plantilla, template_name=template_name)

    ruta_examen = os.path.join(UPLOAD_FOLDER, f"sync_{uuid.uuid4()}_{examen_file.filename}")
    examen_file.save(ruta_examen)

    resultado = procesar_correccion(ruta_plantilla, ruta_examen)
    return render_template("resultado.html", **resultado)


@app.route("/exam-corrector/start", methods=["POST"])
def start_async():
    examen_file = request.files.get("examen")
    if not examen_file:
        return jsonify({"ok": False, "error": "Falta archivo de examen."}), 400

    template_id = (request.form.get("template_id") or "").strip()
    plantilla_file = request.files.get("plantilla")
    template_name = (request.form.get("template_name") or "").strip()
    save_template = (request.form.get("save_template") or "1").strip() != "0"

    job_id = str(uuid.uuid4())

    ruta_plantilla = ""
    if template_id and template_id != "__upload__":
        ruta_plantilla = obtener_ruta_template_por_id(template_id)
        if not ruta_plantilla:
            return jsonify({"ok": False, "error": "La plantilla seleccionada no existe."}), 400
    else:
        if not plantilla_file:
            return jsonify({"ok": False, "error": "Debes subir una plantilla o seleccionar una guardada."}), 400
        ruta_plantilla = os.path.join(UPLOAD_FOLDER, f"{job_id}_plantilla_{plantilla_file.filename}")
        plantilla_file.save(ruta_plantilla)
        if save_template:
            guardar = registrar_template_guardada(ruta_plantilla, template_name=template_name)
            template_id = guardar["id"]

    ruta_examen = os.path.join(UPLOAD_FOLDER, f"{job_id}_examen_{examen_file.filename}")
    examen_file.save(ruta_examen)

    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "progress": 0,
            "stage": "queued",
            "message": "Esperando procesamiento...",
            "template_id": template_id or "",
            "created_at": time.time(),
        }

    thread = threading.Thread(target=_run_job, args=(job_id, ruta_plantilla, ruta_examen), daemon=True)
    thread.start()

    actualizar_progreso(job_id, 2, "running", "Trabajo iniciado...")

    return jsonify({"ok": True, "job_id": job_id})


@app.route("/exam-corrector/status/<job_id>", methods=["GET"])
def job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404

    if job["status"] == "done":
        return jsonify(
            {
                "ok": True,
                "status": "done",
                "progress": 100,
                "stage": "done",
                "message": job.get("message", "Corrección completada."),
                "result_url": f"/exam-corrector/result/{job_id}",
            }
        )
    if job["status"] == "error":
        return jsonify({"ok": False, "status": "error", "error": job.get("error", "Error desconocido")}), 500
    return jsonify(
        {
            "ok": True,
            "status": job.get("status", "running"),
            "progress": int(job.get("progress", 0)),
            "stage": job.get("stage", "running"),
            "message": job.get("message", "Procesando..."),
        }
    )


@app.route("/exam-corrector/result/<job_id>", methods=["GET"])
def job_result(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return render_template("resultado.html", **_resultado_error("Job no encontrado."))
    if job["status"] == "error":
        return render_template("resultado.html", **_resultado_error(job.get("error", "Error desconocido.")))
    if job["status"] != "done":
        return render_template("resultado.html", **_resultado_error("El proceso aún no ha terminado."))
    return render_template("resultado.html", **job["result"])


@app.route("/exam-corrector/api/result/<job_id>", methods=["GET"])
def job_result_json(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404
    if job["status"] == "error":
        return jsonify({"ok": False, "status": "error", "error": job.get("error", "Error desconocido.")}), 500
    if job["status"] != "done":
        return jsonify({"ok": True, "status": job["status"]})
    return jsonify({"ok": True, "status": "done", "result": job["result"]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
