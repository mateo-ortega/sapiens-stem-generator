"""
Pipeline de generación de tareas STEM con validación pedagógica.

Proveedor: Groq — cadena de fallback entre modelos con cuotas independientes:
  1. llama-3.3-70b-versatile  (principal, 100k tokens/día)
  2. llama-3.1-70b-versatile  (fallback, 100k tokens/día)
  3. deepseek-r1-distill-llama-70b (último recurso, 100k tokens/día)

Flujo de dos pasos:
1. Generación: prompt enriquecido con instrucciones por área + contexto curado + web
2. Validación: segundo LLM pass que revisa Bloom, LaTeX, realismo y completitud
"""

import os
import json
import random
import time
from groq import Groq

from core.knowledge_retriever import get_context
from core.prompts import (
    detect_subject_area,
    estimate_question_count,
    GENERATION_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    AREA_INSTRUCTIONS,
    build_anti_pattern_rules,
    build_language_guidelines,
    TYPE_INSTRUCTIONS,
    LEVEL_QUESTION_TYPES,
)
from core.subject_knowledge import get_contexts_for, normalize_level_key
from core import history_manager

# ─── Modelos ──────────────────────────────────────────────────────────────────

# Cadena de fallback: se intenta en orden hasta encontrar uno con cuota disponible.
# Verificado activo en Groq a abril 2026 — actualizar si alguno es deprecado.
GROQ_MODEL_CHAIN = [
    "llama-3.3-70b-versatile",                    # principal (100k tokens/día)
    "meta-llama/llama-4-scout-17b-16e-instruct",  # fallback 1 — Llama 4 Scout (MoE 17B×16)
    "qwen/qwen3-32b",                             # fallback 2 — Qwen 3 32B
]
GEMINI_MODEL = "gemini-2.5-flash"  # reservado, no se usa como fallback


# ─── Utilidades de JSON ───────────────────────────────────────────────────────

def _fix_json_escapes(raw: str) -> str:
    """
    Corrige backslashes inválidos en JSON producidos por LaTeX en la respuesta del LLM.

    Parsea carácter por carácter rastreando si estamos dentro de un string JSON.
    Dentro de strings, solo son válidos: \" \\\\ / \\b \\f \\n \\r \\t \\uXXXX
    Cualquier otro \\X (incluyendo \\frac, \\alpha, \\nabla, \\upsilon, etc.)
    se dobla a \\\\X para que sea JSON válido.

    Args:
        raw: texto JSON crudo con posibles escapes de LaTeX inválidos
    Returns:
        JSON con backslashes correctamente escapados
    """
    _HEX = set("0123456789abcdefABCDEF")
    result = []
    in_string = False
    i = 0
    n = len(raw)

    while i < n:
        ch = raw[i]

        if not in_string:
            result.append(ch)
            if ch == '"':
                in_string = True
            i += 1
            continue

        if ch == '"':
            in_string = False
            result.append(ch)
            i += 1
        elif ch != '\\':
            result.append(ch)
            i += 1
        else:
            if i + 1 >= n:
                result.append('\\\\')
                i += 1
                continue

            nxt = raw[i + 1]

            if nxt in '"\\/ ':
                result.append(ch)
                result.append(nxt)
                i += 2
            elif nxt in 'bfnrt':
                after = raw[i + 2] if i + 2 < n else ''
                if after.isalpha() or after == '{':
                    result.append('\\\\')
                    i += 1
                else:
                    result.append(ch)
                    result.append(nxt)
                    i += 2
            elif nxt == 'u':
                if (i + 5 < n and
                        all(raw[i + 2 + j] in _HEX for j in range(4))):
                    result.append(raw[i:i + 6])
                    i += 6
                else:
                    result.append('\\\\')
                    i += 1
            else:
                result.append('\\\\')
                i += 1

    return ''.join(result)


def _parse_json_response(raw: str) -> dict:
    """
    Parsea la respuesta JSON del LLM, limpiando markdown y corrigiendo escapes LaTeX.

    El LLM suele emitir backslashes simples en comandos LaTeX (\rho, \frac, \text...)
    que colisionan con escape sequences JSON (\r → CR, \f → FF, \t → TAB, etc.).
    Se aplica _fix_json_escapes SIEMPRE antes de parsear para evitar que json.loads
    convierta silenciosamente \rho → chr(13)+'ho', \frac → chr(12)+'rac', etc.

    Args:
        raw: texto crudo de la respuesta
    Returns:
        diccionario parseado
    """
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    # Siempre corregir escapes LaTeX primero — json.loads los convertiría en
    # caracteres de control sin emitir error, corrompiendo las fórmulas
    try:
        return json.loads(_fix_json_escapes(raw))
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"No se pudo parsear JSON: {e}", e.doc, e.pos)


# ─── Proveedor Groq ───────────────────────────────────────────────────────────

def _configure_groq(api_key: str) -> Groq:
    """Crea y retorna un cliente de Groq."""
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurado.")
    return Groq(api_key=api_key)


def _is_quota_exhausted(err_str: str) -> bool:
    """Detecta si el error de Groq indica cuota agotada (diaria o de tokens)."""
    if "429" not in err_str:
        return False
    low = err_str.lower()
    return "day" in low or "per_day" in low or "tokens" in low


def _strip_thinking_tags(raw: str) -> str:
    """
    Elimina bloques <think>...</think> que DeepSeek R1 emite antes del JSON.

    Args:
        raw: respuesta cruda del modelo
    Returns:
        texto sin bloques de razonamiento
    """
    import re
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    return raw.strip()


def _call_one_groq_model(
    client: Groq,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_retries: int = 5,
) -> str:
    """
    Intenta llamar a un modelo Groq específico con reintentos ante errores transitorios.

    Lanza QuotaExhausted (RuntimeError marcado) si la cuota está agotada,
    para que _call_llm pueda pasar al siguiente modelo de la cadena.

    Args:
        client: cliente Groq
        model: nombre del modelo
        system_prompt: instrucciones del sistema
        user_prompt: mensaje del usuario
        temperature: temperatura
        max_retries: reintentos ante errores transitorios (503/500/429-minuto)
    Returns:
        texto JSON crudo de la respuesta
    """
    delay = 5
    max_delay = 60
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=8192,
            )
            raw = response.choices[0].message.content.strip()
            # DeepSeek R1 emite <think>...</think> antes del JSON
            return _strip_thinking_tags(raw)
        except Exception as e:
            err_str = str(e)
            if _is_quota_exhausted(err_str):
                raise _QuotaError(model, err_str) from e
            is_unavailable = (
                "decommissioned" in err_str.lower()
                or "not found" in err_str.lower()
                or ("400" in err_str and "model" in err_str.lower())
            )
            if is_unavailable:
                raise _QuotaError(model, f"Modelo no disponible: {err_str[:120]}") from e
            is_retryable = "503" in err_str or "500" in err_str or (
                "429" in err_str and "minute" in err_str.lower()
            )
            if attempt < max_retries - 1 and is_retryable:
                print(f"  {model} — error transitorio (intento {attempt + 1}/{max_retries}), reintentando en {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                raise


class _QuotaError(RuntimeError):
    """Error interno: cuota del modelo agotada, intentar el siguiente."""
    def __init__(self, model: str, detail: str):
        self.model = model
        super().__init__(detail)


# ─── Lógica de selección de proveedor ────────────────────────────────────────

def _call_llm(
    system_prompt: str,
    groq_key: str,
    temperature: float = 0.5,
    label: str = "",
) -> tuple:
    """
    Llama al LLM disponible recorriendo la cadena de modelos Groq.

    Orden: llama-3.3-70b → llama-3.1-70b → deepseek-r1-distill-llama-70b.
    Si todos tienen la cuota agotada, lanza RuntimeError con mensaje claro.

    Args:
        system_prompt: instrucciones completas del sistema
        groq_key: API key de Groq
        temperature: temperatura del modelo
        label: etiqueta para logs
    Returns:
        (raw_text, model_used) — texto JSON crudo y nombre del modelo que respondió
    """
    if not groq_key:
        raise RuntimeError(
            "GROQ_API_KEY no está configurado.\n"
            "Obtén tu clave gratuita en: console.groq.com"
        )

    client = _configure_groq(groq_key)
    user_prompt = "Genera el JSON solicitado siguiendo exactamente las instrucciones y el schema del sistema."
    exhausted = []

    last_error = None
    for model in GROQ_MODEL_CHAIN:
        print(f"{label} con Groq ({model})...")
        try:
            raw = _call_one_groq_model(client, model, system_prompt, user_prompt, temperature)
            return raw, model
        except _QuotaError as e:
            exhausted.append(model)
            last_error = str(e)
            print(f"  Cuota/modelo no disponible para {model}: {last_error[:80]}")
        except Exception as e:
            exhausted.append(model)
            last_error = str(e)
            print(f"  Error en {model}: {last_error[:120]}, probando siguiente modelo...")

    raise RuntimeError(
        f"Todos los modelos de Groq fallaron ({', '.join(exhausted)}).\n"
        f"Último error: {last_error or 'desconocido'}\n"
        "Si es cuota agotada, las cuotas se restablecen a medianoche UTC (7pm Colombia)."
    )


# ─── Construcción de prompts ──────────────────────────────────────────────────

def _get_level_key(level: str) -> str:
    """Compatibilidad: delega en la función canónica de subject_knowledge."""
    return normalize_level_key(level)


def _build_type_instructions(question_types: list) -> str:
    """Construye el bloque de instrucciones por tipo de pregunta."""
    return "\n".join(
        TYPE_INSTRUCTIONS[qt]
        for qt in question_types
        if qt in TYPE_INSTRUCTIONS
    )


def _format_bullet_list(items, empty_text: str = "(ninguno)") -> str:
    """Formatea una lista de strings como bullets para inyectar al prompt."""
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return f"  {empty_text}"
    return "\n".join(f"  • {it}" for it in items)


def _select_level_contexts(area: str, level_key: str, avoid: list, sample_size: int = 8) -> list:
    """
    Devuelve hasta `sample_size` contextos curados + expandidos para (area, level_key),
    excluyendo los que aparezcan en `avoid` (case-insensitive).

    Si los curados se agotan tras filtrar por historial reciente, se intenta
    rellenar con contextos expandidos por LLM (cache lazy).

    Args:
        area: clave de área ("math"/"science"/...)
        level_key: nivel canónico
        avoid: lista de strings a excluir
        sample_size: cantidad objetivo de contextos
    Returns:
        lista de strings (puede ser más corta que sample_size si la cantera es chica)
    """
    avoid_lower = {a.strip().lower() for a in (avoid or []) if a}

    def _ok(s: str) -> bool:
        sl = s.strip().lower()
        if not sl:
            return False
        # Filtro robusto: excluir si CUALQUIER fragmento "avoid" está contenido
        # en el contexto candidato o viceversa (matching parcial)
        for av in avoid_lower:
            if av and (av in sl or sl in av):
                return False
        return True

    curated = [c for c in get_contexts_for(area, level_key) if _ok(c)]

    # Si tras filtrar quedan suficientes, mezclar y devolver
    if len(curated) >= sample_size:
        random.shuffle(curated)
        return curated[:sample_size]

    # Si la cantera curada se queda corta, intentar expandir con LLM
    expanded = _load_expanded_cache(area, level_key)
    expanded_filtered = [c for c in expanded if _ok(c)]

    pool = curated + [c for c in expanded_filtered if c not in curated]
    random.shuffle(pool)
    return pool[:sample_size] if pool else curated  # peor caso: devolver lo que haya


# ─── Expansor de contextos con LLM (cache lazy) ──────────────────────────────

_CACHE_PATH = os.path.join(os.path.expanduser("~"), "Sapiens", ".context_cache.json")


def _load_full_cache() -> dict:
    """Carga el cache completo de contextos expandidos. Vacío si no existe."""
    if not os.path.exists(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_full_cache(cache: dict) -> None:
    """Persiste el cache de contextos expandidos."""
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[ai_agent] No se pudo escribir el cache de contextos: {e}")


def _cache_key(area: str, level_key: str) -> str:
    return f"{area}|{level_key}"


def _load_expanded_cache(area: str, level_key: str) -> list:
    """Devuelve la lista de contextos expandidos cacheados para (area, level_key)."""
    cache = _load_full_cache()
    return list(cache.get(_cache_key(area, level_key), []))


def expand_contexts_with_llm(
    area: str,
    level_key: str,
    groq_key: str,
    target_count: int = 20,
) -> list:
    """
    Genera contextos novedosos para (area, level_key) y los persiste en cache.

    Solo se invoca cuando la cantera curada se ha agotado tras filtrar por
    historial reciente. Usa los contextos curados como ejemplos few-shot y las
    guías de lenguaje del nivel para garantizar coherencia.

    Args:
        area: clave de área
        level_key: nivel canónico
        groq_key: API key de Groq
        target_count: cantidad de contextos a pedir al LLM
    Returns:
        lista total de contextos cacheados para esa combinación tras la expansión
    """
    if not groq_key:
        return _load_expanded_cache(area, level_key)

    seed_contexts = get_contexts_for(area, level_key)[:6]
    guidelines = build_language_guidelines(level_key)

    expander_prompt = (
        f"Eres un experto en diseño curricular para el área {area} a nivel {level_key}.\n"
        f"Genera {target_count} contextos del mundo real, NUEVOS y DISTINTOS de los siguientes ejemplos:\n"
        + "\n".join(f"  • {c}" for c in seed_contexts)
        + "\n\n"
        + guidelines
        + "\n\nReglas:\n"
        "- Cada contexto debe ser una frase corta (10-25 palabras) con nombre concreto y datos verosímiles.\n"
        "- Apropiado al nivel educativo indicado: NO uses tecnicismos avanzados en niveles bajos.\n"
        "- Variedad temática: cubre subáreas distintas dentro del área.\n\n"
        "SALIDA: JSON estricto con esta estructura, sin texto adicional:\n"
        '{"contexts": ["contexto 1", "contexto 2", ...]}'
    )

    try:
        raw, _model = _call_llm(
            expander_prompt,
            groq_key,
            temperature=0.8,
            label=f"Expandiendo contextos ({area}/{level_key})",
        )
        parsed = _parse_json_response(raw)
        new_items = parsed.get("contexts") or []
        new_items = [str(x).strip() for x in new_items if str(x).strip()]
    except Exception as e:
        print(f"[ai_agent] Falló expansión de contextos para {area}/{level_key}: {e}")
        return _load_expanded_cache(area, level_key)

    cache = _load_full_cache()
    key = _cache_key(area, level_key)
    existing = cache.get(key, [])
    seen = {x.lower() for x in existing}
    for item in new_items:
        if item.lower() not in seen:
            existing.append(item)
            seen.add(item.lower())
    # Tope para no inflar el JSON indefinidamente
    cache[key] = existing[-200:]
    _save_full_cache(cache)
    return list(cache[key])


def detect_and_prepare_prompt(
    topic: str,
    level: str,
    time_estimate: str,
    context: str,
    comments: str = "",
    subject_area_override: str = "",
    recent_topics: list = None,
) -> tuple:
    """
    Prepara el prompt completo de generación.

    Args:
        topic: tema de la tarea
        level: nivel educativo (texto libre o clave canónica)
        time_estimate: tiempo estimado
        context: contexto académico/web/curado combinado
        comments: comentarios del profesor
        subject_area_override: área forzada ("" = auto-detectar)
        recent_topics: contextos recientes a evitar (de history_manager)
    Returns:
        (prompt_completo, subject_area, question_count, question_types, level_key)
    """
    if subject_area_override and subject_area_override != "auto":
        area = subject_area_override
    else:
        area = detect_subject_area(topic)

    area_instr = AREA_INSTRUCTIONS.get(area, AREA_INSTRUCTIONS["default"])

    level_key = _get_level_key(level)
    question_types = LEVEL_QUESTION_TYPES.get(level_key, LEVEL_QUESTION_TYPES["default"])
    type_instr = _build_type_instructions(question_types)

    question_count = estimate_question_count(time_estimate)
    teacher_instr = comments if comments else "Ninguna condición adicional."

    avoid = list(recent_topics or [])
    level_contexts = _select_level_contexts(area, level_key, avoid)

    area_names = {
        "math": "Matemáticas",
        "science": "Ciencias Naturales",
        "engineering": "Ingeniería",
        "cs": "Ciencias de la Computación",
        "humanities": "Humanidades y Ciencias Sociales",
        "default": "Educación General",
    }

    prompt = GENERATION_SYSTEM_PROMPT.format(
        subject_area=area_names.get(area, "Educación General"),
        question_count=question_count,
        topic=topic,
        level=level,
        context=context,
        level_specific_contexts=_format_bullet_list(
            level_contexts,
            empty_text="(sin lista — usa el contexto académico general respetando el nivel)",
        ),
        recent_topics_to_avoid=_format_bullet_list(
            avoid, empty_text="(no hay temas recientes)"
        ),
        teacher_instructions=teacher_instr,
        language_guidelines=build_language_guidelines(level_key),
        area_instructions=area_instr,
        anti_pattern_rules=build_anti_pattern_rules(level_key),
        type_instructions=type_instr,
    )

    return prompt, area, question_count, question_types, level_key


# ─── Pasos del pipeline ───────────────────────────────────────────────────────

def generate_questions(
    prompt: str,
    groq_key: str,
    temperature: float = 0.5,
) -> tuple:
    """
    Primer paso: genera las preguntas con el LLM disponible.

    Args:
        prompt: prompt completo del sistema
        groq_key: API key de Groq
        temperature: temperatura del modelo
    Returns:
        (dict_preguntas, model_used)
    """
    raw, model = _call_llm(prompt, groq_key, temperature, label="Generando preguntas")
    return _parse_json_response(raw), model


def validate_and_review(
    questions_data: dict,
    topic: str,
    level: str,
    subject_area: str,
    groq_key: str,
) -> tuple:
    """
    Segundo paso: revisa y corrige la evaluación generada.

    Args:
        questions_data: diccionario con las preguntas generadas
        topic: tema original
        level: nivel educativo
        subject_area: área detectada
        groq_key: API key de Groq
    Returns:
        (dict_revisado, model_used)
    """
    review_prompt = REVIEW_SYSTEM_PROMPT.format(
        questions_json=json.dumps(questions_data, ensure_ascii=False, indent=2),
        topic=topic,
        level=level,
        subject_area=subject_area,
    )
    raw, model = _call_llm(review_prompt, groq_key, 0.3, label="Validando calidad pedagógica")
    return _parse_json_response(raw), model


# ─── Orquestador principal ────────────────────────────────────────────────────

def generate_stem_task(
    topic: str,
    level: str,
    time_estimate: str,
    groq_api_key: str = "",
    comments: str = "",
    subject_area_override: str = "",
    status_callback=None,
) -> dict:
    """
    Orquestador principal: genera una tarea STEM completa con validación.

    Usa Groq recorriendo la cadena de modelos hasta encontrar uno con cuota disponible:
    llama-3.3-70b → llama-3.1-70b → deepseek-r1-distill-llama-70b.

    Args:
        topic: tema de la tarea
        level: nivel educativo
        time_estimate: tiempo estimado
        groq_api_key: clave de API de Groq (también acepta GROQ_API_KEY del env)
        comments: comentarios/condiciones del profesor
        subject_area_override: área forzada ("" o "auto" = auto-detectar)
        status_callback: función opcional para reportar progreso al UI
    Returns:
        diccionario con title, introduction, subject_area, questions[]
    """
    start_time = time.time()

    groq_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")

    def report(msg):
        if status_callback:
            status_callback(msg)
        print(msg)

    try:
        # Pre-cálculo: área y nivel — necesarios antes del prompt para consultar
        # el historial y evitar contextos repetidos.
        if subject_area_override and subject_area_override != "auto":
            area_pre = subject_area_override
        else:
            area_pre = detect_subject_area(topic)
        level_key_pre = _get_level_key(level)

        # Paso 0: Consultar historial de generaciones recientes
        recent = history_manager.get_recent_topics(area_pre, level_key_pre, n=10)
        if recent:
            report(f"Evitando {len(recent)} contextos recientes de generaciones anteriores...")

        # Paso 1: Obtener contexto académico (web + curado)
        report("Buscando contexto académico y del mundo real...")
        context = get_context(topic, level)

        # Paso 2: Preparar prompt con contextos filtrados por nivel
        report("Preparando prompt especializado...")
        prompt, area, q_count, q_types, level_key = detect_and_prepare_prompt(
            topic, level, time_estimate, context, comments,
            subject_area_override, recent_topics=recent,
        )

        # Paso 3: Generar preguntas
        report(f"Generando {q_count} preguntas con Groq (nivel: {level_key})...")
        questions_data, model_gen = generate_questions(prompt, groq_key)

        # Paso 4: Validar y revisar
        report("Validando calidad pedagógica...")
        reviewed_data, model_rev = validate_and_review(
            questions_data, topic, level, area, groq_key
        )

        # El modelo real puede diferir entre pasos si hubo fallback
        active_model = model_gen if model_gen == model_rev else f"{model_gen} / {model_rev}"

        # Paso 5: Persistir en historial para futuras generaciones
        try:
            extracted = history_manager.extract_contexts_from_questions(reviewed_data)
            history_manager.append_generation(area, level_key, topic, extracted[:6])
        except Exception as hist_err:
            # El historial es best-effort; no debe abortar la generación
            print(f"[ai_agent] Aviso: no se pudo actualizar el historial: {hist_err}")

        # Agregar metadatos
        reviewed_data["subject_area"] = area
        reviewed_data["metadata"] = {
            "provider": "Groq",
            "model": active_model,
            "temperature_gen": 0.5,
            "temperature_review": 0.3,
            "generation_time_s": round(time.time() - start_time, 1),
            "question_count": len(reviewed_data.get("questions", [])),
            "question_types": q_types,
            "level_key": level_key,
            "recent_topics_avoided": len(recent),
        }

        report(f"Generación completada exitosamente ({active_model}).")
        return reviewed_data

    except json.JSONDecodeError as e:
        err_msg = f"El modelo devolvió JSON malformado: {e}"
        print(err_msg)
        report(f"Error: {err_msg[:80]}")
        raise RuntimeError(err_msg) from e
    except RuntimeError:
        # Cuota agotada u error crítico — propagar para que la UI lo muestre
        raise
    except Exception as e:
        err_msg = str(e)
        print(f"Error en generación: {err_msg}")
        report(f"Error: {err_msg[:80]}")
        raise RuntimeError(f"Error inesperado durante la generación:\n{err_msg}") from e


def _fallback_response(topic: str, error_msg: str) -> dict:
    """Respuesta de contingencia si todo falla."""
    return {
        "title": f"Tarea STEM: {topic}",
        "introduction": "Hubo un error al generar el contenido con IA. "
                        "Por favor intenta de nuevo o verifica tu conexión.",
        "subject_area": "default",
        "questions": [
            {
                "question_type": "short_answer",
                "order_index": 1,
                "bloom_level": "understand",
                "points": 10.0,
                "content": {
                    "stem": f"Investiga y describe las aplicaciones reales de {topic} "
                            "en la industria o la vida cotidiana.",
                    "expected_length": "3-5 oraciones",
                },
                "answer_key": {
                    "reference_answer": "Respuesta abierta.",
                    "key_points": ["Aplicaciones reales", "Contexto industrial o cotidiano"],
                },
                "rubric": {
                    "criteria": [
                        {
                            "name": "Relevancia",
                            "description": "La respuesta aborda aplicaciones reales del tema.",
                            "levels": [
                                {"score": 10, "description": "Excelente — ejemplos específicos y detallados"},
                                {"score": 5, "description": "Aceptable — ejemplos generales"},
                                {"score": 0, "description": "Insuficiente — no aborda el tema"},
                            ],
                        }
                    ],
                    "total_points": 10.0,
                },
            }
        ],
        "metadata": {"error": error_msg},
    }
