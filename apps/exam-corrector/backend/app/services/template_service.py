import json
import os
import threading
import time
import uuid

from app import config

TEMPLATE_CACHE: dict = {}
TEMPLATE_CACHE_LOCK = threading.Lock()


def cargar_template_cache() -> None:
    global TEMPLATE_CACHE
    if not os.path.exists(config.TEMPLATE_CACHE_PATH):
        TEMPLATE_CACHE = {}
        return
    try:
        with open(config.TEMPLATE_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        TEMPLATE_CACHE = data if isinstance(data, dict) else {}
    except Exception:
        TEMPLATE_CACHE = {}


def guardar_template_cache() -> None:
    tmp = config.TEMPLATE_CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(TEMPLATE_CACHE, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.TEMPLATE_CACHE_PATH)


def cargar_template_library() -> list:
    if not os.path.exists(config.TEMPLATE_LIBRARY_PATH):
        return []
    try:
        with open(config.TEMPLATE_LIBRARY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def guardar_template_library(items: list) -> None:
    tmp = config.TEMPLATE_LIBRARY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.TEMPLATE_LIBRARY_PATH)


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
    dst_path = os.path.join(config.TEMPLATE_STORE_DIR, dst_filename)
    with open(src_path, "rb") as rf, open(dst_path, "wb") as wf:
        wf.write(rf.read())

    name = (template_name or "").strip() or f"Plantilla {time.strftime('%Y-%m-%d %H:%M')}"
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
            candidate = os.path.join(config.TEMPLATE_STORE_DIR, filename)
            if os.path.isfile(candidate):
                return candidate
            break
    return ""
