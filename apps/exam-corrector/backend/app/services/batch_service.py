import csv
import io
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile

from app import config
from app.services import job_service

# Limits concurrent Gemini calls across all batch items.
# Created lazily per-process so it is always initialized in the gunicorn worker
# process that will actually use it, avoiding fork+threading issues.
_semaphore: threading.Semaphore | None = None
_sem_lock = threading.Lock()

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_PDF_DPI = 150
_CHUNK_SIZE = 10   # max exams per Gemini call
_MAX_PARALLEL = 2  # concurrent Gemini batch calls


def _get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        with _sem_lock:
            if _semaphore is None:
                _semaphore = threading.Semaphore(_MAX_PARALLEL)
    return _semaphore


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.JOBS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_tables() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id          TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                total       INTEGER NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0,
                failed      INTEGER NOT NULL DEFAULT 0,
                created_at  REAL NOT NULL,
                finished_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_items (
                batch_id     TEXT NOT NULL,
                idx          INTEGER NOT NULL,
                filename     TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'queued',
                result_json  TEXT,
                error        TEXT,
                confidence   REAL,
                needs_review INTEGER NOT NULL DEFAULT 0,
                reviewed     INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (batch_id, idx)
            )
        """)


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
        conn.execute(
            "INSERT INTO batches (id, template_id, total, created_at) VALUES (?, ?, ?, ?)",
            (batch_id, template_id, total, now),
        )
        conn.executemany(
            "INSERT INTO batch_items (batch_id, idx, filename) VALUES (?, ?, ?)",
            [(batch_id, i, name) for i, (name, _) in enumerate(exam_files)],
        )

    chunks = [
        [(i, name, path) for i, (name, path) in enumerate(exam_files[start:start + _CHUNK_SIZE], start)]
        for start in range(0, len(exam_files), _CHUNK_SIZE)
    ]
    for chunk in chunks:
        t = threading.Thread(
            target=_process_chunk,
            args=(batch_id, chunk, ruta_plantilla, extract_dir),
            daemon=True,
        )
        t.start()

    return batch_id


def _store_result(batch_id: str, idx: int, result: dict) -> None:
    needs_review = int(result.get("needs_review", False))
    confidence = result.get("min_confidence")
    with _connect() as conn:
        conn.execute(
            "UPDATE batch_items SET status='done', result_json=?, confidence=?, needs_review=? "
            "WHERE batch_id=? AND idx=?",
            (json.dumps(result), confidence, needs_review, batch_id, idx),
        )
        conn.execute("UPDATE batches SET done=done+1 WHERE id=?", (batch_id,))


def _store_error(batch_id: str, idx: int, error: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE batch_items SET status='error', error=? WHERE batch_id=? AND idx=?",
            (error, batch_id, idx),
        )
        conn.execute("UPDATE batches SET failed=failed+1 WHERE id=?", (batch_id,))


def _process_chunk(
    batch_id: str,
    items: list[tuple[int, str, str]],  # (idx, filename, ruta_examen)
    ruta_plantilla: str,
    extract_dir: str,
) -> None:
    with _get_semaphore():
        with _connect() as conn:
            for idx, _, _ in items:
                conn.execute(
                    "UPDATE batch_items SET status='processing' WHERE batch_id=? AND idx=?",
                    (batch_id, idx),
                )
        try:
            examen_items = [(filename, ruta) for _, filename, ruta in items]
            results = job_service.procesar_correccion_lote(ruta_plantilla, examen_items)
            for (idx, _, _), result in zip(items, results):
                _store_result(batch_id, idx, result)
        except Exception:
            # Fallback: correct each exam individually
            for idx, filename, ruta_examen in items:
                try:
                    result = job_service.procesar_correccion(ruta_plantilla, ruta_examen)
                    _store_result(batch_id, idx, result)
                except Exception as exc:
                    _store_error(batch_id, idx, str(exc))

    for _, _, ruta_examen in items:
        try:
            os.remove(ruta_examen)
        except OSError:
            pass
    _check_finalize(batch_id, extract_dir)


def _check_finalize(batch_id: str, extract_dir: str) -> None:
    is_finished = False
    with _connect() as conn:
        row = conn.execute(
            "SELECT total, done, failed FROM batches WHERE id=?", (batch_id,)
        ).fetchone()
        if row and (row["done"] + row["failed"]) >= row["total"]:
            conn.execute(
                "UPDATE batches SET finished_at=? WHERE id=? AND finished_at IS NULL",
                (time.time(), batch_id),
            )
            is_finished = True
    if is_finished:
        shutil.rmtree(extract_dir, ignore_errors=True)


def get_status(batch_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT total, done, failed, finished_at FROM batches WHERE id=?",
            (batch_id,),
        ).fetchone()
        if row is None:
            return None
        item_row = conn.execute(
            "SELECT filename FROM batch_items WHERE batch_id=? AND status='processing' ORDER BY idx LIMIT 1",
            (batch_id,),
        ).fetchone()
        review_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM batch_items WHERE batch_id=? AND needs_review=1 AND reviewed=0",
            (batch_id,),
        ).fetchone()
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
        exists = conn.execute("SELECT 1 FROM batches WHERE id=?", (batch_id,)).fetchone()
        if not exists:
            return None
        rows = conn.execute(
            "SELECT filename, status, result_json, error, confidence, needs_review, reviewed "
            "FROM batch_items WHERE batch_id=? ORDER BY idx",
            (batch_id,),
        ).fetchall()
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
        exists = conn.execute("SELECT 1 FROM batches WHERE id=?", (batch_id,)).fetchone()
        if not exists:
            return None
        rows = conn.execute(
            "SELECT idx, filename, result_json, confidence, reviewed "
            "FROM batch_items WHERE batch_id=? AND needs_review=1 ORDER BY idx",
            (batch_id,),
        ).fetchall()
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
        result = conn.execute(
            "UPDATE batch_items SET reviewed=1 WHERE batch_id=? AND idx=? AND needs_review=1",
            (batch_id, idx),
        )
    return result.rowcount > 0


def get_csv(batch_id: str) -> str:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT filename, status, result_json, error "
            "FROM batch_items WHERE batch_id=? ORDER BY idx",
            (batch_id,),
        ).fetchall()

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
