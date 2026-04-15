import base64
import hashlib

import cv2
import numpy as np

GEMINI_JPEG_QUALITY = 75  # Gemini doesn't need high fidelity; 75 cuts payload ~35%

# ── OMR alignment ────────────────────────────────────────────────────────────
_ECC_CRITERIA = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
_MIN_ECC_CORRELATION = 0.70   # below this the alignment is too poor to trust
_BBOX_PADDING = 4             # expand each bbox side by N pixels before measuring

# ── OMR mark classification ───────────────────────────────────────────────────
_MARK_DELTA_MIN = 0.04          # min ink delta to consider a region "active"
_CANCEL_ASPECT_MIN = 2.5        # connected component aspect ratio ≥ this → stroke
_CANCEL_SPAN_RATIO = 0.38       # CC spanning ≥38 % of region width or height → cancellation
_SELECT_EXTENT_MIN = 0.10       # compact CC fill ratio ≥ this → selection mark
_AMBIGUITY_TOP2_GAP = 0.025     # if top-2 active-option deltas within this → uncertain


def _apply_clahe(gray: np.ndarray) -> np.ndarray:
    """Normalize local contrast so ink measurements are lighting-independent."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _ink_density(region: np.ndarray) -> float:
    """Fraction of dark pixels in a grayscale region (0 = white, 1 = black)."""
    if region.size == 0:
        return 0.0
    return float(1.0 - np.mean(region.astype(np.float32)) / 255.0)


def _extra_ink_mask(student: np.ndarray, template: np.ndarray) -> np.ndarray:
    """Binary mask of pixels that are darker in the student image than the template."""
    diff = template.astype(np.int16) - student.astype(np.int16)
    diff = np.clip(diff, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
    return mask


def _classify_ink(mask: np.ndarray) -> tuple[bool, bool]:
    """Analyse connected components of extra ink to distinguish mark types.

    Returns (has_selection_mark, has_cancellation):
    - Selection mark: compact blob (filled bubble, tick, circle, checkmark)
    - Cancellation: elongated stroke(s) crossing the region (Rule 6 cross-out)
    """
    if mask is None or mask.size == 0:
        return False, False
    h, w = mask.shape
    if h == 0 or w == 0:
        return False, False

    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    has_selection = False
    has_cancellation = False

    for i in range(1, n_labels):  # skip background label 0
        area = int(stats[i, cv2.CC_STAT_AREA])
        cc_w = int(stats[i, cv2.CC_STAT_WIDTH])
        cc_h = int(stats[i, cv2.CC_STAT_HEIGHT])
        if area < 8:           # noise
            continue
        extent = area / max(cc_w * cc_h, 1)        # fill ratio of component bbox
        aspect = max(cc_w, cc_h) / max(min(cc_w, cc_h), 1)  # elongation
        span_x = cc_w / max(w, 1)
        span_y = cc_h / max(h, 1)

        # Long stroke crossing ≥ 38 % of region → likely a cancellation line
        if aspect >= _CANCEL_ASPECT_MIN and (span_x >= _CANCEL_SPAN_RATIO or span_y >= _CANCEL_SPAN_RATIO):
            has_cancellation = True
        # Compact, well-filled blob → selection mark
        elif extent >= _SELECT_EXTENT_MIN and aspect < _CANCEL_ASPECT_MIN:
            has_selection = True

    return has_selection, has_cancellation


def _classify_option(
    student_region: np.ndarray,
    template_region: np.ndarray,
) -> tuple[str, float]:
    """Classify the ink state of a single option's mark zone.

    Returns (state, confidence) where state ∈ {blank, selected, cancelled, uncertain}.
    """
    delta = _ink_density(student_region) - _ink_density(template_region)
    if delta < _MARK_DELTA_MIN:
        return "blank", 1.0

    mask = _extra_ink_mask(student_region, template_region)
    has_sel, has_cancel = _classify_ink(mask)

    if has_sel and has_cancel:
        # Compact mark + crossing stroke: the selection was subsequently cancelled
        return "cancelled", 0.75
    if has_cancel and not has_sel:
        return "cancelled", 0.85
    if has_sel and not has_cancel:
        conf = min(1.0, delta / 0.20)
        return "selected", round(conf, 3)
    # Extra ink present but geometry is unclear
    return "uncertain", 0.45


def alinear_examen(
    template_img: np.ndarray,
    student_img: np.ndarray,
) -> tuple[np.ndarray | None, float]:
    """Fine-align student image to template using ECC with an affine motion model.

    Both images are assumed to be pre-corrected to the same 900×1100 canvas by
    recorte_a4, so only small residual misalignment needs to be corrected here.

    Returns (warp_matrix_2x3, correlation) or (None, 0.0) on failure.
    """
    h, w = template_img.shape[:2]
    tg = _apply_clahe(cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY))
    sg = _apply_clahe(cv2.cvtColor(student_img, cv2.COLOR_BGR2GRAY))

    warp = np.eye(2, 3, dtype=np.float32)
    try:
        cc, warp_out = cv2.findTransformECC(
            tg, sg, warp, cv2.MOTION_AFFINE, _ECC_CRITERIA,
            inputMask=None, gaussFiltSize=5,
        )
    except cv2.error:
        return None, 0.0

    if float(cc) < _MIN_ECC_CORRELATION:
        return None, 0.0
    return warp_out, float(cc)


def _get_mark_region(
    gray: np.ndarray, opt: dict, h: int, w: int
) -> np.ndarray | None:
    """Extract the mark zone for an option, preferring mark_bbox_px over bbox_px."""
    bbox = opt.get("mark_bbox_px") or opt.get("bbox_px")
    if not (isinstance(bbox, list) and len(bbox) == 4):
        return None
    y1, x1, y2, x2 = bbox
    y1 = max(0, y1 - _BBOX_PADDING)
    x1 = max(0, x1 - _BBOX_PADDING)
    y2 = min(h, y2 + _BBOX_PADDING)
    x2 = min(w, x2 + _BBOX_PADDING)
    if y2 <= y1 or x2 <= x1:
        return None
    return gray[y1:y2, x1:x2]


def corregir_con_omr(
    template_img: np.ndarray,
    student_img: np.ndarray,
    bbox_data: dict,
) -> dict | None:
    """Correct a student exam using ECC alignment + per-option state classification.

    For each answer option, classifies the mark zone as:
      blank / selected / cancelled / uncertain

    Then applies:
      - Regla 2: no active option → blank
      - Regla 1: exactly one selected → answer
      - Regla 6: exactly one cancelled + one selected → rectification (Rule 6)
      - Regla 3: multiple selected with no cancellation → MULTIPLE
      - uncertain: falls back to Gemini for the whole exam

    Returns a dict compatible with _formatear_resultado, or None if:
      - alignment fails
      - any question is uncertain (→ Gemini handles the exam)
      - zero marks detected across the whole exam (→ bboxes unreliable)
    """
    preguntas = bbox_data.get("preguntas")
    if not preguntas:
        return None

    warp, ecc = alinear_examen(template_img, student_img)
    if warp is None:
        return None

    h, w = template_img.shape[:2]
    aligned = cv2.warpAffine(student_img, warp, (w, h), flags=cv2.INTER_LINEAR)

    template_gray = _apply_clahe(cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY))
    student_gray  = _apply_clahe(cv2.cvtColor(aligned,      cv2.COLOR_BGR2GRAY))

    respuestas = []
    for q in preguntas:
        q_num = q.get("pregunta", len(respuestas) + 1)
        opciones = q.get("opciones", [])

        # ── Per-option state classification ───────────────────────────────
        correct_texto = next(
            (o.get("texto", "") for o in opciones if o.get("es_correcta")), ""
        )
        classified: list[dict] = []
        for opt in opciones:
            tmpl_r = _get_mark_region(template_gray, opt, h, w)
            stud_r = _get_mark_region(student_gray,  opt, h, w)
            if tmpl_r is None or stud_r is None:
                continue
            state, conf = _classify_option(stud_r, tmpl_r)
            classified.append({
                "letra": opt.get("letra", "?"),
                "texto": opt.get("texto", ""),
                "es_correcta": bool(opt.get("es_correcta")),
                "state": state,
                "conf": conf,
                "delta": _ink_density(stud_r) - _ink_density(tmpl_r),
            })

        if not classified:
            # No valid bboxes for this question — skip gracefully
            continue

        selected  = [o for o in classified if o["state"] == "selected"]
        cancelled = [o for o in classified if o["state"] == "cancelled"]
        uncertain = [o for o in classified if o["state"] == "uncertain"]

        # ── Relative-ranking ambiguity check ──────────────────────────────
        # If top-2 deltas are very close, confidence is low → fall back
        active_deltas = sorted(
            (o["delta"] for o in classified if o["state"] != "blank"),
            reverse=True,
        )
        if (
            len(active_deltas) >= 2
            and (active_deltas[0] - active_deltas[1]) < _AMBIGUITY_TOP2_GAP
            and active_deltas[0] > _MARK_DELTA_MIN
        ):
            uncertain = uncertain or [classified[0]]  # force fallback

        # ── Any uncertain option → Gemini handles this exam ───────────────
        if uncertain:
            return None

        # ── Apply correction rules ─────────────────────────────────────────
        if not selected and not cancelled:
            # Regla 2: blank
            respuestas.append({
                "pregunta": q_num,
                "respuesta_correcta": correct_texto,
                "respuesta_dada": None,
                "correcta": False,
                "regla_aplicada": "Regla 2",
                "confianza": round(ecc * 0.9, 3),
            })

        elif len(selected) == 1 and not cancelled:
            # Regla 1: clear single selection
            opt = selected[0]
            clarity = min(1.0, opt["delta"] / 0.20)
            conf = round(ecc * (0.65 + 0.35 * clarity), 3)
            respuestas.append({
                "pregunta": q_num,
                "respuesta_correcta": correct_texto,
                "respuesta_dada": opt["texto"],
                "correcta": opt["es_correcta"],
                "regla_aplicada": "OMR",
                "confianza": conf,
            })

        elif len(selected) == 1 and len(cancelled) == 1:
            # Regla 6: exactly one cancelled + one selected → rectification
            opt = selected[0]
            conf = round(ecc * 0.75, 3)   # lower confidence for rectified answers
            respuestas.append({
                "pregunta": q_num,
                "respuesta_correcta": correct_texto,
                "respuesta_dada": opt["texto"],
                "correcta": opt["es_correcta"],
                "regla_aplicada": "Regla 6",
                "confianza": conf,
            })

        elif not selected and len(cancelled) >= 1:
            # All active options were cancelled → blank (Regla 2)
            respuestas.append({
                "pregunta": q_num,
                "respuesta_correcta": correct_texto,
                "respuesta_dada": None,
                "correcta": False,
                "regla_aplicada": "Regla 2",
                "confianza": round(ecc * 0.6, 3),
            })

        else:
            # Multiple selected (or multiple cancelled) → ambiguous → Gemini
            return None

    if not respuestas:
        return None

    # If zero questions have any mark, bboxes are probably misaligned
    n_answered = sum(1 for r in respuestas if r.get("respuesta_dada") is not None)
    if n_answered == 0:
        return None

    return {
        "tipo_examen": "test",
        "compatible": True,
        "confianza": round(ecc, 3),
        "motivo": f"OMR (ECC {ecc:.2f})",
        "nombre": "",
        "total": len(respuestas),
        "respuestas": respuestas,
    }


def recorte_a4(imagen):
    """Detects and perspective-corrects the exam sheet in the photo."""
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
        suma = mejor.sum(axis=1)
        diff = np.diff(mejor, axis=1).reshape(-1)
        tl = mejor[np.argmin(suma)]
        br = mejor[np.argmax(suma)]
        tr = mejor[np.argmin(diff)]
        bl = mejor[np.argmax(diff)]
        dest = np.array([[0, 0], [900, 0], [900, 1100], [0, 1100]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), dest)
        return cv2.warpPerspective(redimensionada, M, (900, 1100))

    if contornos:
        cmax = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(cmax)
        if w > 100 and h > 100:
            return redimensionada[y:y + h, x:x + w]

    return redimensionada


def encode_for_gemini(imagen_bgr) -> tuple[str, str]:
    """Single JPEG encode → returns (base64_string, sha256_hash).
    Avoids encoding the same image twice for hashing and API upload."""
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), GEMINI_JPEG_QUALITY])
    if not ok:
        raise ValueError("No se pudo codificar la imagen")
    data = buf.tobytes()
    return base64.b64encode(data).decode("utf-8"), hashlib.sha256(data).hexdigest()


def load_and_crop(path: str):
    """Read image from disk and perspective-correct in one call."""
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {path}")
    return recorte_a4(img)


def hash_image(imagen_bgr: np.ndarray) -> str:
    """Stable SHA-256 of an image (via JPEG encode) — used as cache key."""
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), GEMINI_JPEG_QUALITY])
    if not ok:
        raise ValueError("No se pudo codificar la imagen")
    return hashlib.sha256(buf.tobytes()).hexdigest()


# ── CV-based template analysis (no AI) ───────────────────────────────────────

def _cluster_1d(values: list[float], gap_ratio: float, ref_size: float) -> list[float]:
    """Group sorted 1-D values into clusters separated by gaps > gap_ratio × ref_size.
    Returns the mean of each cluster."""
    if not values:
        return []
    min_gap = gap_ratio * ref_size
    sorted_v = sorted(values)
    clusters: list[list[float]] = [[sorted_v[0]]]
    for v in sorted_v[1:]:
        if v - clusters[-1][-1] <= min_gap:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [float(np.mean(c)) for c in clusters]


def detectar_bboxes_cv(template_img: np.ndarray) -> dict | None:
    """Detect answer mark zones in a template image using pure OpenCV (no AI).

    Algorithm:
    1. Find compact dark regions (mark candidates) using contour analysis.
    2. Cluster them into option columns and question rows.
    3. Detect two-column exam layouts from large gaps in column spacing.
    4. Identify the correct answer per question by highest ink density on the template.

    Returns a dict in the same format as obtener_bboxes_plantilla (with bbox_px /
    mark_bbox_px entries), or None if a reliable grid cannot be found.
    """
    gray = _apply_clahe(cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY))
    h, w = gray.shape

    # ── 1. Find candidate mark regions ───────────────────────────────────
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[dict] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (80 <= area <= 4000):
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        if max(cw, ch) / max(min(cw, ch), 1) > 4.0:   # too elongated → text / line
            continue
        candidates.append({"x": x, "y": y, "w": cw, "h": ch,
                            "cx": x + cw // 2, "cy": y + ch // 2})

    if len(candidates) < 8:
        return None

    # ── 2. Cluster into option columns and question rows ──────────────────
    x_clusters = _cluster_1d([c["cx"] for c in candidates], gap_ratio=0.025, ref_size=w)
    y_clusters = _cluster_1d([c["cy"] for c in candidates], gap_ratio=0.015, ref_size=h)

    n_cols, n_rows = len(x_clusters), len(y_clusters)
    if n_cols < 2 or n_rows < 2:
        return None

    # ── 3. Assign candidates to grid cells ────────────────────────────────
    def _nearest(val: float, centers: list[float]) -> int:
        return int(np.argmin([abs(val - c) for c in centers]))

    grid: dict[tuple[int, int], dict] = {}
    for c in candidates:
        ri = _nearest(c["cy"], y_clusters)
        ci = _nearest(c["cx"], x_clusters)
        key = (ri, ci)
        if key not in grid:
            grid[key] = c
        else:
            prev = grid[key]
            d_new = abs(c["cx"] - x_clusters[ci]) + abs(c["cy"] - y_clusters[ri])
            d_old = abs(prev["cx"] - x_clusters[ci]) + abs(prev["cy"] - y_clusters[ri])
            if d_new < d_old:
                grid[key] = c

    # Require ≥55 % cell fill — sparser structures are likely false detections
    if len(grid) < n_rows * n_cols * 0.55:
        return None

    # ── 4. Detect two-column layout ───────────────────────────────────────
    # A large gap between consecutive x-clusters (> 2× the median spacing)
    # signals two independent sets of option columns (left and right exam columns).
    col_groups: list[list[int]] = [[0]]
    if n_cols >= 3:
        x_spacings = [x_clusters[i + 1] - x_clusters[i] for i in range(n_cols - 1)]
        med_sp = float(np.median(x_spacings))
        for i, sp in enumerate(x_spacings):
            if sp > med_sp * 2.2:
                col_groups.append([])       # start a new column group
            col_groups[-1].append(i + 1)
    else:
        col_groups = [list(range(n_cols))]

    # Validate column regularity within each group
    for grp in col_groups:
        if len(grp) >= 3:
            sp = [x_clusters[grp[i + 1]] - x_clusters[grp[i]] for i in range(len(grp) - 1)]
            cv_sp = float(np.std(sp)) / (float(np.mean(sp)) + 1)
            if cv_sp > 0.45:
                return None   # option positions too irregular

    # ── 5. Build preguntas with correct-answer detection ──────────────────
    med_w = int(np.median([c["w"] for c in grid.values()]))
    med_h = int(np.median([c["h"] for c in grid.values()]))
    pad = max(4, min(med_w, med_h) // 3)
    letras = "abcdefghij"

    preguntas: list[dict] = []
    q_num = 0
    for col_group in col_groups:
        for ri in range(n_rows):
            row = {ci: grid[(ri, ci)] for ci in col_group if (ri, ci) in grid}
            if len(row) < 2:
                continue

            # Ink density per option on the TEMPLATE → filled option = correct answer
            densities = {}
            for ci, c in row.items():
                y1 = max(0, c["y"] - pad); x1 = max(0, c["x"] - pad)
                y2 = min(h, c["y"] + c["h"] + pad); x2 = min(w, c["x"] + c["w"] + pad)
                densities[ci] = _ink_density(gray[y1:y2, x1:x2])
            best_ci = max(densities, key=densities.get)

            opciones: list[dict] = []
            for local_i, ci in enumerate(sorted(row.keys())):
                c = row[ci]
                y1 = max(0, c["y"] - pad); x1 = max(0, c["x"] - pad)
                y2 = min(h, c["y"] + c["h"] + pad); x2 = min(w, c["x"] + c["w"] + pad)
                letra = letras[local_i] if local_i < len(letras) else str(local_i + 1)
                opciones.append({
                    "letra": letra,
                    "texto": letra.upper(),     # no OCR — use letter as display text
                    "es_correcta": (ci == best_ci),
                    "bbox_px": [y1, x1, y2, x2],
                    "mark_bbox_px": [y1, x1, y2, x2],
                })

            q_num += 1
            preguntas.append({"pregunta": q_num, "opciones": opciones})

    if not preguntas:
        return None

    return {"preguntas": preguntas}
