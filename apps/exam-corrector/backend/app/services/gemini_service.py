import json
import re
import time

import requests

from app import config
from app.services.image_service import encode_for_gemini
from app.services import template_service

BATCH_SIZE = 10

MARK_STYLES_HINT = """
Marcas válidas — cualquiera de estas formas cuenta como una respuesta marcada:
- Burbuja o círculo relleno/sombreado sobre la opción.
- Letra de la opción encerrada en un círculo.
- Cruz (X) o aspa clara sobre la opción.
- Marca de verificación (✓ / tick) sobre la opción.
- Subrayado inequívoco de la letra/texto de la opción.
- Cualquier trazo claro e intencional que señale una sola opción.

Marcas inválidas (NO cuentan como respuesta marcada):
- La opción está tachada con líneas horizontales/diagonales cruzadas encima → se interpreta como CANCELADA, no como marcada.
- Garabatos, manchas o marcas accidentales que no señalan una opción concreta.

Regla de rectificación (Regla 6):
- Si el alumno marcó una opción (marca válida) y luego la tachó claramente, esa opción está CANCELADA.
- Si además marcó otra opción distinta con una marca válida y sin tachar, esa segunda opción es la respuesta_dada.
- Solo aplica si hay exactamente una opción cancelada y exactamente una opción marcada sin cancelar.
- En cualquier otro caso de ambigüedad aplica Regla 3 (MULTIPLE) o Regla 4 (ILEGIBLE) según corresponda.
"""

PROMPT_TEMPLATE_MODEL = """
Analiza UNA imagen de plantilla de examen tipo test con respuestas correctas marcadas.
Construye un modelo intermedio reutilizable.

""" + MARK_STYLES_HINT + """

Devuelve SOLO JSON con este formato:
{
  "total": 0,
  "respuestas_correctas": [
    {"pregunta": 1, "texto": "primeras 8-12 palabras de la opción marcada"}
  ]
}

Reglas adicionales:
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

""" + MARK_STYLES_HINT + """

Reglas de corrección:
- Regla 1: correcta solo si coincide con respuesta_correcta del modelo.
- Regla 2: si no marca respuesta, respuesta_dada = null e incorrecta.
- Regla 3: si marca múltiples sin cancelar ninguna, respuesta_dada = "MULTIPLE" e incorrecta.
- Regla 4: si no legible, respuesta_dada = "ILEGIBLE" e incorrecta.
- Regla 5: no inventar preguntas fuera del modelo.
- Regla 6: rectificación — ver descripción en sección de marcas arriba.

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
      "regla_aplicada": "Regla 1",
      "confianza": 1.0
    }
  ]
}

El campo "confianza" por respuesta indica qué tan seguro estás de haber leído correctamente
la marca del alumno (1.0 = completamente seguro, 0.0 = completamente inseguro).
Usa valores bajos (< 0.8) cuando la marca sea ambigua, poco clara, o se aplicó Regla 6.
"""

PROMPT_CORRECCION_LOTE = """
Recibes __N__ imágenes de exámenes de alumnos. Cada imagen va precedida de su etiqueta [Imagen K: nombre].
También recibes un MODELO de plantilla en JSON con las respuestas correctas.

MODELO PLANTILLA:
__TEMPLATE_MODEL__

Para CADA imagen aplica exactamente las mismas reglas que para un examen individual:
- Detecta las respuestas marcadas por el alumno, en el mismo orden que el modelo.
- Compara contra la plantilla.
- Extrae el nombre del alumno de "APELLIDOS Y NOMBRE".
- Asigna confianza por cada respuesta.

""" + MARK_STYLES_HINT + """

Reglas de corrección:
- Regla 1: correcta solo si coincide con respuesta_correcta del modelo.
- Regla 2: sin marca → respuesta_dada = null, incorrecta.
- Regla 3: múltiples marcas sin cancelar ninguna → MULTIPLE, incorrecta.
- Regla 4: ilegible → ILEGIBLE, incorrecta.
- Regla 5: no inventar preguntas fuera del modelo.
- Regla 6: rectificación — ver descripción en sección de marcas arriba.
- confianza: 1.0 = completamente seguro; usa < 0.8 para marcas ambiguas, poco claras, o donde se aplicó Regla 6.

Devuelve SOLO JSON con este formato exacto (el array debe tener exactamente __N__ elementos):
{
  "resultados": [
    {
      "imagen": 1,
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
          "regla_aplicada": "Regla 1",
          "confianza": 1.0
        }
      ]
    }
  ]
}

IMPORTANTE: el campo "imagen" debe ser el índice numérico (1, 2, ..., __N__) de la imagen
correspondiente, en el mismo orden en que aparecen. No omitas ningún resultado.
"""



PROMPT_TEMPLATE_BBOXES = """
Analiza esta imagen de plantilla de examen tipo test. El profesor ya ha marcado las respuestas correctas.

Para CADA pregunta devuelve el bounding box de CADA opción de respuesta (a, b, c, d, etc.),
indicando cuál está marcada como correcta por el profesor.

Devuelve SOLO JSON con este formato exacto:
{
  "preguntas": [
    {
      "pregunta": 1,
      "opciones": [
        {
          "letra": "a",
          "texto": "primeras 5-8 palabras de esta opción",
          "es_correcta": false,
          "bbox": [ymin, xmin, ymax, xmax],
          "mark_bbox": [ymin, xmin, ymax, xmax]
        }
      ]
    }
  ]
}

REGLAS:
- bbox: bounding box completo (texto + zona de marca) de ESA opción, cuatro enteros 0-1000 normalizados.
- mark_bbox: bounding box MÁS PEQUEÑO que cubre SOLO la burbuja, casilla o zona donde el alumno
  debe colocar su marca — sin incluir el texto de la opción. Si no hay zona de marca diferenciada,
  usa el mismo valor que bbox.
- es_correcta: true únicamente para la opción que el profesor ha marcado.
- Orden de preguntas: columna izquierda arriba-abajo, luego columna derecha arriba-abajo.
- Incluye TODAS las opciones de cada pregunta, no solo la correcta.
- No inventes preguntas ni opciones que no existan en la imagen.
"""

# Template image canvas size produced by recorte_a4
_CANVAS_H = 1100
_CANVAS_W = 900


def parsear_json_de_texto(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', texto)
        if not match:
            raise ValueError(f"Gemini no devolvió JSON válido:\n{texto}")
        return json.loads(match.group())


_RETRY_DELAYS = (5, 15, 30)  # seconds to wait after 1st, 2nd, 3rd 429


def llamar_gemini(parts: list, prompt: str, timeout: int = 90) -> dict:
    from app.services import settings_service
    api_key = settings_service.get_gemini_api_key()
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY. Configúrala en Ajustes o como variable de entorno.")
    payload = {
        "contents": [{"parts": parts + [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={api_key}"
    )
    resp = None
    for attempt, delay in enumerate((*_RETRY_DELAYS, None)):
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 429 or delay is None:
            break
        # Honour Retry-After if the API provides it, otherwise use our schedule
        try:
            wait = int(resp.headers.get("Retry-After", delay))
        except (ValueError, TypeError):
            wait = delay
        time.sleep(wait)
    resp.raise_for_status()
    texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return parsear_json_de_texto(texto)


def llamar_gemini_lote(
    images: list[tuple[str, str]],  # (filename, b64_jpeg)
    template_model: dict,
    timeout: int = 180,
) -> list[dict]:
    """Send up to BATCH_SIZE exams in one Gemini call. Returns ordered list of raw results."""
    n = len(images)
    parts = []
    for i, (filename, b64) in enumerate(images, 1):
        parts.append({"text": f"[Imagen {i}: {filename}]"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

    prompt = (
        PROMPT_CORRECCION_LOTE
        .replace("__TEMPLATE_MODEL__", json.dumps(template_model, ensure_ascii=False))
        .replace("__N__", str(n))
    )
    raw = llamar_gemini(parts, prompt, timeout=timeout)

    resultados = raw.get("resultados")
    if not isinstance(resultados, list):
        raise ValueError("La respuesta del lote no contiene 'resultados'.")
    if len(resultados) != n:
        raise ValueError(f"Se esperaban {n} resultados, se recibieron {len(resultados)}.")

    resultados.sort(key=lambda r: r.get("imagen", 0))
    for i, r in enumerate(resultados, 1):
        if r.get("imagen") != i:
            raise ValueError(f"Resultado faltante para imagen {i} (se recibió {r.get('imagen')}).")

    return resultados


def obtener_bboxes_plantilla(b64_p: str, template_hash: str) -> dict | None:
    """Return per-option bounding boxes for a template, cached by hash.

    Bboxes are stored in both normalized (0-1000) and pixel coordinates
    for the 900×1100 canvas produced by recorte_a4. Returns None on any failure.
    """
    with template_service.BBOX_CACHE_LOCK:
        cached = template_service.BBOX_CACHE.get(template_hash)
    if cached:
        return cached

    try:
        result = llamar_gemini(
            parts=[{"inline_data": {"mime_type": "image/jpeg", "data": b64_p}}],
            prompt=PROMPT_TEMPLATE_BBOXES,
            timeout=90,
        )
    except Exception:
        return None

    preguntas = result.get("preguntas")
    if not isinstance(preguntas, list) or not preguntas:
        return None

    def _to_px(raw: list) -> list[int] | None:
        if not (isinstance(raw, list) and len(raw) == 4):
            return None
        yn, xn, yn2, xn2 = (int(v) for v in raw)
        return [
            max(0, min(_CANVAS_H, round(yn  * _CANVAS_H / 1000))),
            max(0, min(_CANVAS_W, round(xn  * _CANVAS_W / 1000))),
            max(0, min(_CANVAS_H, round(yn2 * _CANVAS_H / 1000))),
            max(0, min(_CANVAS_W, round(xn2 * _CANVAS_W / 1000))),
        ]

    # Convert normalized 0-1000 → pixel coords; clamp to canvas bounds
    for q in preguntas:
        for opt in q.get("opciones", []):
            px = _to_px(opt.get("bbox"))
            if px:
                opt["bbox_px"] = px
            mark_px = _to_px(opt.get("mark_bbox"))
            if mark_px:
                opt["mark_bbox_px"] = mark_px

    with template_service.BBOX_CACHE_LOCK:
        template_service.BBOX_CACHE[template_hash] = result
        template_service.guardar_bbox_cache()
    return result


def obtener_modelo_plantilla(b64_p: str, template_hash: str, progress_cb=None) -> dict:
    with template_service.TEMPLATE_CACHE_LOCK:
        cached = template_service.TEMPLATE_CACHE.get(template_hash)
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

    with template_service.TEMPLATE_CACHE_LOCK:
        template_service.TEMPLATE_CACHE[template_hash] = model
        template_service.guardar_template_cache()
    return model
