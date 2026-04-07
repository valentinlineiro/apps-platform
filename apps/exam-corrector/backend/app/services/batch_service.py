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


def _get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        with _sem_lock:
            if _semaphore is None:
                _semaphore = threading.Semaphore(5)
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
                batch_id    TEXT NOT NULL,
                idx         INTEGER NOT NULL,
                filename    TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'queued',
                result_json TEXT,
                error       TEXT,
                PRIMARY KEY (batch_id, idx)
            )
        """)


def start_batch(zip_path: str, template_id: str, ruta_plantilla: str) -> str:
    batch_id = str(uuid.uuid4())
    extract_dir = os.path.join(config.UPLOAD_FOLDER, f"batch_{batch_id}")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        exam_files: list[tuple[str, str]] = []  # (display_name, full_path)
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
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass

    if not exam_files:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise ValueError("El ZIP no contiene imágenes (.jpg, .jpeg, .png).")

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

    for i, (filename, exam_path) in enumerate(exam_files):
        t = threading.Thread(
            target=_process_item,
            args=(batch_id, i, filename, ruta_plantilla, exam_path, extract_dir),
            daemon=True,
        )
        t.start()

    return batch_id


def _process_item(
    batch_id: str,
    idx: int,
    filename: str,
    ruta_plantilla: str,
    ruta_examen: str,
    extract_dir: str,
) -> None:
    with _get_semaphore():
        with _connect() as conn:
            conn.execute(
                "UPDATE batch_items SET status='processing' WHERE batch_id=? AND idx=?",
                (batch_id, idx),
            )
        try:
            result = job_service.procesar_correccion(ruta_plantilla, ruta_examen)
        except Exception as exc:
            with _connect() as conn:
                conn.execute(
                    "UPDATE batch_items SET status='error', error=? WHERE batch_id=? AND idx=?",
                    (str(exc), batch_id, idx),
                )
                conn.execute(
                    "UPDATE batches SET failed=failed+1 WHERE id=?",
                    (batch_id,),
                )
        else:
            with _connect() as conn:
                conn.execute(
                    "UPDATE batch_items SET status='done', result_json=? WHERE batch_id=? AND idx=?",
                    (json.dumps(result), batch_id, idx),
                )
                conn.execute(
                    "UPDATE batches SET done=done+1 WHERE id=?",
                    (batch_id,),
                )

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
    }


def get_items(batch_id: str) -> list | None:
    with _connect() as conn:
        exists = conn.execute("SELECT 1 FROM batches WHERE id=?", (batch_id,)).fetchone()
        if not exists:
            return None
        rows = conn.execute(
            "SELECT filename, status, result_json, error FROM batch_items WHERE batch_id=? ORDER BY idx",
            (batch_id,),
        ).fetchall()
    items = []
    for row in rows:
        item: dict = {"filename": row["filename"], "status": row["status"]}
        if row["status"] == "done" and row["result_json"]:
            r = json.loads(row["result_json"])
            item["nombre"] = r.get("nombre", "")
            item["total_puntos"] = r.get("total_puntos", 0)
            item["max_puntos"] = r.get("max_puntos", 0)
            item["porcentaje_puntos"] = r.get("porcentaje_puntos", 0)
        elif row["status"] == "error":
            item["error"] = row["error"] or ""
        items.append(item)
    return items


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
