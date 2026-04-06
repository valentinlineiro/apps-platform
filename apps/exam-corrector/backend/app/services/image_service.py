import base64
import hashlib

import cv2
import numpy as np


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


def a_data_uri(imagen_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return ""
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def imagen_bgr_a_b64(imagen_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise ValueError("No se pudo codificar la imagen")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def hash_template_image(imagen_bgr) -> str:
    ok, buf = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise ValueError("No se pudo generar hash de plantilla.")
    return hashlib.sha256(buf.tobytes()).hexdigest()
