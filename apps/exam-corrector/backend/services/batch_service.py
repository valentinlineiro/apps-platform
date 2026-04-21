import csv
import io
import json
import logging
import os
import shutil
import threading
import time
import uuid
import zipfile

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

import config
from services import job_service

_log = logging.getLogger(__name__)

# Semaphore limiting concurrent chunk-processing threads.
_semaphore: threading.Semaphore | None = None
_sem_lock = threading.Lock()

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_PDF_DPI = 150
_CHUNK_SIZE = 10   # exams per chunk
_MAX_PARALLEL = 1  # concurrent chunk threads


def _get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        with _sem_lock:
            if _semaphore is None:
                _semaphore = threading.Semaphore(_MAX_PARALLEL)
    return _semaphore


def _connect():
    conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def _extract_from_zip(zip_path: str, extract_dir: str) -> list[tuple[str, str]]:
    exam_files: list[tuple[str, str]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for entry in sorted(zf.namelist()):
            if entry.endswith("/"):
                continue
            ext = os.path.splitext(entry)[1].lower()
            if ext not in _IMAGE_EXTENSIONS:
                continue
            safe_name = os.path.basename(entry)
            dest = os.path.join(extract_dir, f"{len(exam_files):04d}_{safe_name}")
            with zf.open(entry) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            exam_files.append((safe_name, dest))
    if not exam_files:
        raise ValueError("El ZIP no contiene imágenes (.jpg, .jpeg, .png).")
    return exam_files


def _extract_from_pdf(pdf_path: str, extract_dir: str) -> list[tuple[str, str]]:
    import fitz  # pymupdf
    exam_files: list[tuple[str, str]] = []
    doc = fitz.open(pdf_path)
    try:
        if doc.page_count == 0:
            raise ValueError("El PDF no contiene páginas.")
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=_PDF_DPI)
            filename = f"pagina_{i + 1:04d}.jpg"
            dest = os.path.join(extract_dir, filename)
            pix.save(dest)
            exam_files.append((filename, dest))
    finally:
        doc.close()
    return exam_files


def _prewarm_template(ruta_plantilla: str, ready: threading.Event) -> None:
    try:
        from services import job_service
        from services.image_service import load_and_crop, hash_image

        _log.info("batch prewarm: loading template image")
        img = load_and_crop(ruta_plantilla)
        h = hash_image(img)
        bboxes = job_service._obtener_bboxes_cv(img, h)
        n_q = len(bboxes.get("preguntas", [])) if bboxes else 0
        if bboxes:
            _log.info(f"batch prewarm: {n_q} questions detected, OMR ready")
        else:
            _log.warning("batch prewarm: answer grid not detected — corrections will fail")
    except Exception as exc:
        _log.warning(f"batch prewarm: failed ({exc})")
    finally:
        ready.set()


def start_batch(file_path: str, template_id: str, ruta_plantilla: str) -> str:
    batch_id = str(uuid.uuid4())
    extract_dir = os.path.join(config.UPLOAD_FOLDER, f"batch_{batch_id}")
    os.makedirs(extract_dir, exist_ok=True)

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            exam_files = _extract_from_pdf(file_path, extract_dir)
        else:
            exam_files = _extract_from_zip(file_path, extract_dir)
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass

    if not exam_files:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise ValueError("El archivo no contiene exámenes válidos.")

    total = len(exam_files)
    now = time.time()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO batches (id, template_id, total, created_at) VALUES (%s, %s, %s, %s)",
                (batch_id, template_id, total, now),
            )
            for i, (name, _) in enumerate(exam_files):
                cur.execute(
                    "INSERT INTO batch_items (batch_id, idx, filename) VALUES (%s, %s, %s)",
                    (batch_id, i, name),
                )

    _log.info(f"batch {batch_id[:8]}: starting — {total} exams, "
              f"{(total + _CHUNK_SIZE - 1) // _CHUNK_SIZE} chunks of ≤{_CHUNK_SIZE}")

    template_ready = threading.Event()
    threading.Thread(
        target=_prewarm_template,
        args=(ruta_plantilla, template_ready),
        daemon=True,
    ).start()

    chunks = [
        [(i, name, path) for i, (name, path) in enumerate(exam_files[start:start + _CHUNK_SIZE], start)]
        for start in range(0, len(exam_files), _CHUNK_SIZE)
    ]
    for chunk in chunks:
        t = threading.Thread(
            target=_process_chunk,
            args=(batch_id, chunk, ruta_plantilla, extract_dir, template_ready),
            daemon=True,
        )
        t.start()

    return batch_id


def _store_result(batch_id: str, idx: int, result: dict) -> None:
    needs_review = int(result.get("needs_review", False))
    confidence = result.get("min_confidence")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE batch_items SET status='done', result_json=%s, confidence=%s, needs_review=%s "
                "WHERE batch_id=%s AND idx=%s",
                (json.dumps(result), confidence, needs_review, batch_id, idx),
            )
            cur.execute("UPDATE batches SET done=done+1 WHERE id=%s", (batch_id,))


def _store_error(batch_id: str, idx: int, error: str) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE batch_items SET status='error', error=%s WHERE batch_id=%s AND idx=%s",
                (error, batch_id, idx),
            )
            cur.execute("UPDATE batches SET failed=failed+1 WHERE id=%s", (batch_id,))


def _process_chunk(
    batch_id: str,
    items: list[tuple[int, str, str]],
    ruta_plantilla: str,
    extract_dir: str,
    template_ready: threading.Event | None = None,
) -> None:
    first_idx = items[0][0] if items else "?"
    tag = f"batch {batch_id[:8]} chunk@{first_idx}"

    if template_ready is not None:
        template_ready.wait(timeout=120)

    with _get_semaphore():
        _log.info(f"{tag}: acquired semaphore, processing {len(items)} items")
        with _connect() as conn:
            with conn.cursor() as cur:
                for idx, _, _ in items:
                    cur.execute(
                        "UPDATE batch_items SET status='processing' WHERE batch_id=%s AND idx=%s",
                        (batch_id, idx),
                    )
        try:
            examen_items = [(filename, ruta) for _, filename, ruta in items]
            results = job_service.procesar_correccion_lote(ruta_plantilla, examen_items)
            if len(results) != len(items):
                raise ValueError(
                    f"batch result length mismatch: expected {len(items)}, got {len(results)}"
                )
            for (idx, _, _), result in zip(items, results):
                _store_result(batch_id, idx, result)
            _log.info(f"{tag}: batch done — all {len(items)} items stored")
        except Exception as exc:
            _log.warning(f"{tag}: batch call failed ({exc}), falling back to individual corrections")
            for idx, filename, ruta_examen in items:
                try:
                    _log.info(f"{tag}: correcting item {idx} ({filename}) individually")
                    result = job_service.procesar_correccion(ruta_plantilla, ruta_examen)
                    _store_result(batch_id, idx, result)
                except Exception as exc2:
                    _log.error(f"{tag}: item {idx} failed — {exc2}")
                    _store_error(batch_id, idx, str(exc2))

    for _, _, ruta_examen in items:
        try:
            os.remove(ruta_examen)
        except OSError:
            pass
    _check_finalize(batch_id, extract_dir)


def _check_finalize(batch_id: str, extract_dir: str) -> None:
    is_finished = False
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT total, done, failed FROM batches WHERE id=%s", (batch_id,)
            )
            row = cur.fetchone()
            if row and (row["done"] + row["failed"]) >= row["total"]:
                cur.execute(
                    "UPDATE batches SET finished_at=%s WHERE id=%s AND finished_at IS NULL",
                    (time.time(), batch_id),
                )
                is_finished = True
    if is_finished:
        shutil.rmtree(extract_dir, ignore_errors=True)


def get_status(batch_id: str) -> dict | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT total, done, failed, finished_at FROM batches WHERE id=%s",
                (batch_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT filename FROM batch_items WHERE batch_id=%s AND status='processing' ORDER BY idx LIMIT 1",
                (batch_id,),
            )
            item_row = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) as cnt FROM batch_items WHERE batch_id=%s AND needs_review=1 AND reviewed=0",
                (batch_id,),
            )
            review_row = cur.fetchone()
    total = row["total"]
    done = row["done"]
    failed = row["failed"]
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "finished": row["finished_at"] is not None,
        "progress": round((done + failed) / total * 100) if total else 0,
        "current_item": item_row["filename"] if item_row else None,
        "needs_review": review_row["cnt"] if review_row else 0,
    }


def get_items(batch_id: str) -> list | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM batches WHERE id=%s", (batch_id,))
            exists = cur.fetchone()
            if not exists:
                return None
            cur.execute(
                "SELECT filename, status, result_json, error, confidence, needs_review, reviewed "
                "FROM batch_items WHERE batch_id=%s ORDER BY idx",
                (batch_id,),
            )
            rows = cur.fetchall()
    items = []
    for row in rows:
        item: dict = {
            "filename": row["filename"],
            "status": row["status"],
            "needs_review": bool(row["needs_review"]),
            "reviewed": bool(row["reviewed"]),
        }
        if row["status"] == "done" and row["result_json"]:
            r = json.loads(row["result_json"])
            item["nombre"] = r.get("nombre", "")
            item["total_puntos"] = r.get("total_puntos", 0)
            item["max_puntos"] = r.get("max_puntos", 0)
            item["porcentaje_puntos"] = r.get("porcentaje_puntos", 0)
            item["confidence"] = row["confidence"]
        elif row["status"] == "error":
            item["error"] = row["error"] or ""
        items.append(item)
    return items


def get_review_items(batch_id: str) -> list | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM batches WHERE id=%s", (batch_id,))
            exists = cur.fetchone()
            if not exists:
                return None
            cur.execute(
                "SELECT idx, filename, result_json, confidence, reviewed "
                "FROM batch_items WHERE batch_id=%s AND needs_review=1 ORDER BY idx",
                (batch_id,),
            )
            rows = cur.fetchall()
    items = []
    for row in rows:
        r = json.loads(row["result_json"]) if row["result_json"] else {}
        items.append({
            "idx": row["idx"],
            "filename": row["filename"],
            "confidence": row["confidence"],
            "reviewed": bool(row["reviewed"]),
            "nombre": r.get("nombre", ""),
            "total_puntos": r.get("total_puntos", 0),
            "max_puntos": r.get("max_puntos", 0),
            "porcentaje_puntos": r.get("porcentaje_puntos", 0),
            "feedback": r.get("feedback", []),
        })
    return items


def mark_reviewed(batch_id: str, idx: int) -> bool:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE batch_items SET reviewed=1 WHERE batch_id=%s AND idx=%s AND needs_review=1",
                (batch_id, idx),
            )
            return cur.rowcount > 0


def get_csv(batch_id: str) -> str:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT filename, status, result_json, error "
                "FROM batch_items WHERE batch_id=%s ORDER BY idx",
                (batch_id,),
            )
            rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "archivo", "nombre", "puntaje", "total", "porcentaje",
        "total_puntos", "max_puntos", "porcentaje_puntos", "estado", "error",
    ])
    for row in rows:
        if row["status"] == "done" and row["result_json"]:
            r = json.loads(row["result_json"])
            writer.writerow([
                row["filename"],
                r.get("nombre", ""),
                r.get("puntaje", 0),
                r.get("total", 0),
                r.get("porcentaje", 0),
                r.get("total_puntos", 0),
                r.get("max_puntos", 0),
                r.get("porcentaje_puntos", 0),
                "ok",
                "",
            ])
        else:
            writer.writerow([
                row["filename"], "", "", "", "", "", "", "",
                "error", row["error"] or "",
            ])
    return buf.getvalue()
