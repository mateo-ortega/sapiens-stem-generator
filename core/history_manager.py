"""
Gestor de historial de generaciones para evitar repetición temática.

Persiste un registro JSON local con los últimos temas y contextos usados
por cada combinación (área × nivel). El generador consulta este historial
antes de cada nueva generación para inyectar al prompt una lista de
"contextos a evitar", forzando variedad temática.

Almacenamiento: ~/Sapiens/.history.json
Estructura:
{
  "science|primaria": [
    {"timestamp": "2026-04-27T10:30:00", "topic": "...", "contexts": [...]},
    ...
  ],
  "math|secundaria": [...],
  ...
}

Tope: MAX_RECORDS_PER_BUCKET por (área × nivel), con rotación FIFO.
"""

import os
import json
from datetime import datetime
from typing import Iterable

# ─── Configuración ────────────────────────────────────────────────────────────

# Carpeta base de Sapiens (la misma donde se guardan los PDFs en main.py).
# Usar archivo oculto (.history.json) para no contaminar el listado de PDFs.
_SAPIENS_DIR = os.path.join(os.path.expanduser("~"), "Sapiens")
HISTORY_PATH = os.path.join(_SAPIENS_DIR, ".history.json")

MAX_RECORDS_PER_BUCKET = 50  # tope por (área × nivel) con rotación FIFO
DEFAULT_RECENT_N = 10        # cuántos contextos recientes inyectar al prompt


# ─── Utilidades ───────────────────────────────────────────────────────────────

def _bucket_key(area: str, level: str) -> str:
    """Construye la clave del bucket combinando área y nivel."""
    return f"{(area or 'default').strip().lower()}|{(level or 'default').strip().lower()}"


def _ensure_dir() -> None:
    """Garantiza que el directorio del historial existe."""
    os.makedirs(_SAPIENS_DIR, exist_ok=True)


# ─── API pública ──────────────────────────────────────────────────────────────

def load_history() -> dict:
    """
    Carga el historial completo desde disco.

    Returns:
        diccionario con la estructura descrita en el módulo. Vacío si no existe
        o si está corrupto (en cuyo caso se reinicia silenciosamente).
    """
    if not os.path.exists(HISTORY_PATH):
        return {}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        # Archivo corrupto o ilegible: empezar de cero sin abortar la app
        return {}


def _save_history(history: dict) -> None:
    """Persiste el historial completo a disco con codificación UTF-8."""
    _ensure_dir()
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError as e:
        # No abortar la generación si el historial no se puede escribir;
        # solo reportar para debug.
        print(f"[history_manager] No se pudo escribir el historial: {e}")


def get_recent_topics(area: str, level: str, n: int = DEFAULT_RECENT_N) -> list:
    """
    Devuelve los últimos N contextos usados en (área × nivel).

    Combina temas y contextos de cada registro en una lista plana de strings,
    útil para inyectar al prompt como "EVITA repetir estos contextos recientes".

    Args:
        area: clave de área (math/science/engineering/cs/humanities/default)
        level: clave de nivel normalizada
        n: número máximo de contextos a devolver
    Returns:
        lista de strings con los contextos más recientes (ordenada de más a menos reciente)
    """
    history = load_history()
    bucket = history.get(_bucket_key(area, level), [])

    # Recorrer del más reciente al más antiguo, recogiendo contextos sin duplicar
    seen = set()
    result = []
    for record in reversed(bucket):
        topic = (record.get("topic") or "").strip()
        if topic and topic.lower() not in seen:
            seen.add(topic.lower())
            result.append(topic)
            if len(result) >= n:
                return result
        for ctx in record.get("contexts") or []:
            ctx_str = str(ctx).strip()
            if ctx_str and ctx_str.lower() not in seen:
                seen.add(ctx_str.lower())
                result.append(ctx_str)
                if len(result) >= n:
                    return result
    return result


def append_generation(
    area: str,
    level: str,
    topic: str,
    contexts_used: Iterable = (),
) -> None:
    """
    Agrega un nuevo registro al historial y rota si excede el tope.

    Args:
        area: clave de área detectada o forzada
        level: clave de nivel normalizada
        topic: tema solicitado por el usuario
        contexts_used: iterable de contextos extraídos del JSON generado
    """
    history = load_history()
    key = _bucket_key(area, level)

    bucket = history.get(key, [])
    bucket.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "topic": (topic or "").strip(),
        "contexts": [str(c).strip() for c in contexts_used if str(c).strip()],
    })

    # Rotación FIFO: conservar solo los últimos MAX_RECORDS_PER_BUCKET
    if len(bucket) > MAX_RECORDS_PER_BUCKET:
        bucket = bucket[-MAX_RECORDS_PER_BUCKET:]

    history[key] = bucket
    _save_history(history)


def extract_contexts_from_questions(questions_data: dict) -> list:
    """
    Extrae los contextos efectivamente usados de un JSON de preguntas generado.

    Recorre los stems de cada pregunta y la introducción en busca de menciones
    a contextos del mundo real. Como heurística simple, toma las primeras
    palabras significativas hasta el primer punto. El objetivo es alimentar
    el historial con frases identificables, no extracción semántica perfecta.

    Args:
        questions_data: dict con estructura {"introduction": str, "questions": [...]}
    Returns:
        lista de fragmentos extraídos (deduplicada, orden de aparición)
    """
    fragments = []
    seen = set()

    def _push(text: str) -> None:
        snippet = text.strip()
        if not snippet:
            return
        # Tomar la primera oración (hasta el primer punto, o 120 caracteres)
        first_dot = snippet.find(".")
        if 20 <= first_dot <= 200:
            snippet = snippet[:first_dot].strip()
        else:
            snippet = snippet[:120].strip()
        key = snippet.lower()
        if snippet and key not in seen:
            seen.add(key)
            fragments.append(snippet)

    intro = questions_data.get("introduction", "")
    if isinstance(intro, str):
        _push(intro)

    for q in questions_data.get("questions") or []:
        if not isinstance(q, dict):
            continue
        content = q.get("content") or {}
        stem = content.get("stem") if isinstance(content, dict) else None
        if isinstance(stem, str):
            _push(stem)

    return fragments
