import json
import re

import requests

from app import config
from app.services.image_service import hash_template_image
from app.services import template_service

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


def _gemini_url() -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    )


def parsear_json_de_texto(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', texto)
        if not match:
            raise ValueError(f"Gemini no devolvió JSON válido:\n{texto}")
        return json.loads(match.group())


def llamar_gemini(parts: list, prompt: str, timeout: int = 90) -> dict:
    if not config.GEMINI_API_KEY:
        raise ValueError("Falta GEMINI_API_KEY en variables de entorno.")
    payload = {
        "contents": [{"parts": parts + [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    resp = requests.post(_gemini_url(), json=payload, timeout=timeout)
    resp.raise_for_status()
    texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return parsear_json_de_texto(texto)


def obtener_modelo_plantilla(plantilla_a4, b64_p: str, progress_cb=None) -> dict:
    template_hash = hash_template_image(plantilla_a4)
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
