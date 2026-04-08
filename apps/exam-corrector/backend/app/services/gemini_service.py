import json
import re

import requests

from app import config
from app.services.image_service import encode_for_gemini
from app.services import template_service

BATCH_SIZE = 10

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
      "regla_aplicada": "Regla 1",
      "confianza": 1.0
    }
  ]
}

El campo "confianza" por respuesta indica qué tan seguro estás de haber leído correctamente
la marca del alumno (1.0 = completamente seguro, 0.0 = completamente inseguro).
Usa valores bajos (< 0.8) cuando la marca sea ambigua, tachada, poco clara o haya múltiples marcas.
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

Reglas de corrección:
- Regla 1: correcta solo si coincide con respuesta_correcta del modelo.
- Regla 2: sin marca → respuesta_dada = null, incorrecta.
- Regla 3: múltiples marcas → MULTIPLE, incorrecta.
- Regla 4: ilegible → ILEGIBLE, incorrecta.
- Regla 5: no inventar preguntas fuera del modelo.
- confianza: 1.0 = completamente seguro; usa < 0.8 para marcas ambiguas, tachadas o poco claras.

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



def parsear_json_de_texto(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', texto)
        if not match:
            raise ValueError(f"Gemini no devolvió JSON válido:\n{texto}")
        return json.loads(match.group())


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
    resp = requests.post(url, json=payload, timeout=timeout)
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
