"""
Arquitectura de prompts para generación de tareas STEM.

Portado y adaptado desde cognia/apps/api/app/ai/prompts/generation.py
para la aplicación de escritorio Sapiens STEM Generator.

Incluye:
- Detección automática de área temática
- Instrucciones específicas por área (math, science, engineering, humanities, cs)
- Instrucciones por tipo de pregunta
- Reglas anti-patrón para evitar escenarios genéricos/irreales
- Schema JSON de salida estructurada
"""

import re

# ---------------------------------------------------------------------------
# Detección automática de área temática
# ---------------------------------------------------------------------------

_AREA_KEYWORDS = {
    "math": [
        "matemática", "matemáticas", "math", "cálculo", "calculo", "álgebra",
        "algebra", "geometría", "geometria", "trigonometría", "trigonometria",
        "estadística", "estadistica", "probabilidad", "probability", "statistics",
        "ecuaciones diferenciales", "álgebra lineal", "series", "integrales",
        "derivadas", "funciones", "logaritmos", "matrices", "vectores",
        "combinatoria", "aritmética", "aritmetica", "números complejos",
    ],
    "science": [
        "física", "fisica", "physics", "química", "quimica", "chemistry",
        "biología", "biologia", "biology", "termodinámica", "termodinamica",
        "thermodynamics", "mecánica", "mecanica", "óptica", "optica",
        "electromagnetismo", "ondas", "cinemática", "cinematica", "dinámica",
        "dinamica", "estequiometría", "estequiometria", "reacciones químicas",
        "enlace químico", "tabla periódica", "genética", "genetica",
        "ecología", "ecologia", "célula", "celula", "evolución", "evolucion",
        "transferencia de calor", "mecánica de fluidos", "electroquímica",
        "cinética química", "cinetica quimica", "operaciones unitarias",
    ],
    "engineering": [
        "ingeniería", "ingenieria", "engineering", "diseño", "circuitos",
        "materiales", "procesos", "reactores", "intercambiadores",
        "destilación", "destilacion", "control", "automatización",
        "automatizacion", "mecatrónica", "mecatronica", "estructuras",
        "resistencia de materiales", "manufactura", "robótica", "robotica",
        "instrumentación", "instrumentacion", "simulación", "simulacion",
        "balance de materia", "balance de energía", "columnas", "bombas",
        "tuberías", "CAD", "PLC", "SCADA",
    ],
    "cs": [
        "programación", "programacion", "programming", "algoritmo",
        "algoritmos", "datos", "software", "computación", "computacion",
        "computer science", "redes", "base de datos", "database",
        "inteligencia artificial", "machine learning", "python", "java",
        "javascript", "html", "css", "sql", "estructuras de datos",
        "complejidad", "recursión", "recursion", "grafos", "árboles",
        "ciberseguridad", "sistemas operativos", "compiladores",
    ],
    "humanities": [
        "historia", "history", "filosofía", "filosofia", "philosophy",
        "literatura", "literature", "sociología", "sociologia",
        "economía", "economia", "economics", "psicología", "psicologia",
        "geografía", "geografia", "política", "politica", "derecho",
        "ética", "etica", "arte", "música", "musica", "antropología",
        "antropologia", "lingüística", "linguistica", "educación",
    ],
}


def detect_subject_area(topic: str) -> str:
    """
    Detecta el área temática a partir del texto del tema.

    Args:
        topic: texto libre del tema (ej. "Termodinámica", "Álgebra lineal")
    Returns:
        clave del área: "math", "science", "engineering", "cs", "humanities", "default"
    """
    topic_lower = topic.lower().strip()

    scores = {area: 0 for area in _AREA_KEYWORDS}
    for area, keywords in _AREA_KEYWORDS.items():
        for kw in keywords:
            if kw in topic_lower:
                # Puntaje proporcional a la longitud del keyword (más específico = más peso)
                scores[area] += len(kw)

    best_area = max(scores, key=scores.get)
    if scores[best_area] > 0:
        return best_area
    return "default"


# ---------------------------------------------------------------------------
# Instrucciones específicas por área temática
# ---------------------------------------------------------------------------

MATH_INSTRUCTIONS = """
INSTRUCCIONES PARA MATEMÁTICAS:
- Usa notación LaTeX para TODAS las expresiones matemáticas (inline: $...$, bloque: $$...$$).
- Los problemas numéricos deben incluir todos los datos con unidades explícitas.
- Proporciona la solución paso a paso para problemas de cálculo.
- Indica tolerancia para respuestas numéricas (±5% por defecto, ajusta si aplica).
- Distingue entre preguntas conceptuales (definiciones, propiedades) y procedimentales (cálculo).
- Para álgebra lineal, cálculo o estadística: contextualiza en aplicaciones reales del área.
- Incluye casos límite o condiciones de validez cuando sean relevantes.
- Usa notación estándar: $\\int$, $\\sum$, $\\lim$, $\\frac{a}{b}$, $\\sqrt{x}$, etc.
"""

SCIENCE_INSTRUCTIONS = """
INSTRUCCIONES PARA CIENCIAS:
- Usa datos experimentales reales o verosímiles con unidades del SI.
- Incluye análisis de error y propagación de incertidumbre donde aplique.
- Las preguntas deben reflejar metodología científica: hipótesis, experimentación, análisis.
- Para química: incluye balanceo de ecuaciones, estequiometría, condiciones de reacción.
- Para física: incluye diagramas de cuerpo libre, análisis vectorial, leyes de conservación.
- Para biología: contextualiza en procesos celulares, ecosistemas o genética según el tema.
- Diferencia entre observación, inferencia e interpretación en preguntas de análisis.
- Usa LaTeX para fórmulas: $PV = nRT$, $F = ma$, $\\Delta G = \\Delta H - T\\Delta S$, etc.
"""

ENGINEERING_INSTRUCTIONS = """
INSTRUCCIONES PARA INGENIERÍA:
- Incluye balances de materia y/o energía cuando el tema lo requiera.
- Especifica condiciones de operación (temperatura, presión, caudal) con unidades del SI.
- Los problemas de diseño deben tener criterios de aceptación cuantificables.
- Para dimensionamiento: proporciona correlaciones o ecuaciones de diseño relevantes.
- Contextualiza en procesos industriales reales (reactores, columnas, intercambiadores, etc.).
- Incluye consideraciones de seguridad o eficiencia cuando aplique.
- Para ingeniería de software: incluye complejidad computacional, arquitectura y patrones.
- Usa LaTeX para ecuaciones: $Q = UA\\Delta T_{lm}$, $\\dot{m} = \\rho v A$, etc.
"""

HUMANITIES_INSTRUCTIONS = """
INSTRUCCIONES PARA HUMANIDADES Y CIENCIAS SOCIALES:
- Las preguntas de análisis deben requerir argumentación con evidencia textual o histórica.
- Incluye citas textuales o referencias a fuentes primarias cuando el material lo permita.
- Fomenta el pensamiento crítico: no hay respuestas de memoria, sino construcción de tesis.
- Para filosofía: incluye identificación de premisas, falacias y argumentos válidos.
- Para historia: relaciona causas, consecuencias y contexto sociopolítico.
- Para literatura: analiza estilo, estructura narrativa y contexto del autor.
- Las rúbricas deben evaluar coherencia argumentativa, uso de evidencia y originalidad.
"""

CS_INSTRUCTIONS = """
INSTRUCCIONES PARA CIENCIAS DE LA COMPUTACIÓN:
- Usa pseudocódigo claro y legible para algoritmos (independiente del lenguaje).
- Incluye análisis de complejidad temporal y espacial (notación Big-O).
- Los problemas deben incluir casos borde y ejemplos de input/output explícitos.
- Para estructuras de datos: analiza operaciones CRUD y sus complejidades.
- Para bases de datos: incluye consultas SQL o modelos entidad-relación.
- Para redes: referencia modelos OSI/TCP-IP con protocolos específicos.
- Contextualiza los problemas en aplicaciones reales (sistemas web, IA, videojuegos, etc.).
"""

DEFAULT_INSTRUCTIONS = """
INSTRUCCIONES GENERALES:
- Contextualiza las preguntas en situaciones reales y relevantes para el nivel del estudiante.
- Varía los formatos de pregunta para evaluar distintas dimensiones del conocimiento.
- Las rúbricas deben ser claras y medibles, con criterios diferenciados por nivel de desempeño.
- Evita preguntas ambiguas o con más de una interpretación válida.
- Asegura que cada pregunta sea independiente y no revele respuestas de otras preguntas.
- Si hay fórmulas matemáticas, usa notación LaTeX: $E = mc^2$.
"""

AREA_INSTRUCTIONS = {
    "math": MATH_INSTRUCTIONS,
    "science": SCIENCE_INSTRUCTIONS,
    "engineering": ENGINEERING_INSTRUCTIONS,
    "humanities": HUMANITIES_INSTRUCTIONS,
    "cs": CS_INSTRUCTIONS,
    "default": DEFAULT_INSTRUCTIONS,
}

# ---------------------------------------------------------------------------
# Reglas anti-patrón parametrizadas por nivel educativo
#
# La regla original era una constante única que forzaba contextos
# industriales/científicos en TODOS los niveles. Eso producía problemas de
# primaria con menciones a ITER o TSP. Ahora las reglas se calibran por nivel.
# ---------------------------------------------------------------------------

_ANTI_PATTERN_PRIMARIA = """
REGLAS DE CONTEXTUALIZACIÓN (nivel PRIMARIA, 6-12 años):
- USA escenarios cotidianos comprensibles para un niño: la tienda escolar, el recreo,
  los deportes, las mascotas, los juegos, la familia, recetas de cocina, fiestas,
  el clima, los animales del zoológico, las plantas, los planetas en general.
- ESTÁ PERMITIDO y se ANIMA usar nombres propios y situaciones del estilo:
  "Juan repartió 12 dulces entre 4 amigos", "María tenía 5 mascotas",
  "En el recreo Carlos saltó la cuerda 30 veces". Estos NO son anti-patrones aquí.
- PROHIBIDO TERMINANTEMENTE mencionar: ITER, James Webb, CERN, TSP, RSA, Haber-Bosch,
  Navier-Stokes, transformer, Ecopetrol, reactor CSTR, columnas de destilación,
  blockchain, machine learning, ósmosis inversa, ni cualquier tecnología industrial,
  algoritmo teórico avanzado o concepto universitario.
- Los números deben ser ENTEROS PEQUEÑOS o porcentajes simples (10%, 20%, 25%, 50%, 75%).
  Sin notación científica, sin unidades del SI exóticas (kg, cm, m, litros y pesos
  colombianos están bien; J, Pa, mol, S/m no).
- Los problemas deben sentirse como situaciones del día a día de un niño en Colombia.
"""

_ANTI_PATTERN_SECUNDARIA = """
REGLAS DE CONTEXTUALIZACIÓN (nivel SECUNDARIA, 12-15 años):
- USA escenarios cotidianos avanzados o de ciencia escolar: presupuesto familiar,
  deportes con datos reales, geometría del barrio, experimentos de laboratorio escolar,
  reciclaje, redes sociales, videojuegos, clima local.
- Está permitido nombrar personas con nombres propios (Juan, María) si la situación
  es real y el problema tiene datos verosímiles. Evita "una empresa produce X" sin contexto.
- EVITA tecnologías industriales avanzadas, algoritmos teóricos, contextos de investigación
  de frontera. No uses ITER, James Webb, TSP, RSA, transformer, Ecopetrol, ni similares.
- Los números pueden incluir decimales y unidades comunes (kg, m, km/h, °C, %).
- Los problemas deben sentirse familiares para un adolescente colombiano.
"""

_ANTI_PATTERN_PREPARATORIA = """
REGLAS DE CONTEXTUALIZACIÓN (nivel PREPARATORIA / BACHILLERATO ALTO):
- USA contextos de ciencia y tecnología accesibles: experimentos de laboratorio,
  proyectos de feria de ciencias, programación introductoria, deportes con física,
  finanzas personales, energía renovable a escala doméstica.
- EVITA escenarios genéricos de "Juan compró X" sin datos reales. Prefiere contextos
  con números verosímiles y referencias a tecnologías que un estudiante de bachillerato
  pueda haber visto (Arduino, paneles solares, drones, impresión 3D).
- Datos numéricos con unidades del SI cuando aplique. No abuses de tecnicismos
  industriales pesados (refinerías, plantas de 1000 MW) — eso es para universitario.
"""

_ANTI_PATTERN_UNIVERSITARIO = """
REGLAS ANTI-PATRÓN (nivel UNIVERSITARIO — CUMPLIMIENTO ESTRICTO):
- NUNCA uses escenarios genéricos tipo "Juan compró 5 manzanas", "María viaja en tren",
  "una empresa produce X unidades", o "un estudiante mide Y".
- USA contextos industriales, científicos o profesionales REALES y ESPECÍFICOS.
  Ejemplo bueno: "En la planta petroquímica de Ecopetrol en Barrancabermeja..."
  Ejemplo bueno: "Un reactor CSTR de 2 m³ opera a 350 K y 5 atm procesando..."
- Todos los datos numéricos DEBEN ser verosímiles y con unidades del SI.
- Referencia fenómenos, procesos, experimentos o tecnologías que realmente existen.
- Los problemas deben sentirse como situaciones que un profesional del área enfrentaría.
"""

_ANTI_PATTERN_AVANZADO = """
REGLAS ANTI-PATRÓN (nivel AVANZADO / POSGRADO — CUMPLIMIENTO ESTRICTO):
- USA casos de estudio de investigación de frontera, papers recientes (últimos 5 años
  cuando sea posible), proyectos industriales de gran escala, o problemas abiertos del área.
- Datos numéricos rigurosos con unidades del SI, citando órdenes de magnitud reales.
- Los problemas deben requerir integración de conceptos avanzados, no aplicación directa
  de fórmulas. Evalúa razonamiento de nivel doctoral o profesional senior.
- NO uses escenarios cotidianos ni ejemplos de bachillerato.
"""

_ANTI_PATTERN_BY_LEVEL = {
    "primaria": _ANTI_PATTERN_PRIMARIA,
    "secundaria": _ANTI_PATTERN_SECUNDARIA,
    "preparatoria": _ANTI_PATTERN_PREPARATORIA,
    "universitario": _ANTI_PATTERN_UNIVERSITARIO,
    "avanzado": _ANTI_PATTERN_AVANZADO,
}


def build_anti_pattern_rules(level_key: str) -> str:
    """
    Construye las reglas anti-patrón apropiadas al nivel educativo.

    Args:
        level_key: clave normalizada del nivel (primaria/secundaria/preparatoria/
                   universitario/avanzado). Cualquier valor desconocido cae a 'universitario'.
    Returns:
        bloque de texto con las reglas listas para inyectar en el prompt
    """
    return _ANTI_PATTERN_BY_LEVEL.get(level_key, _ANTI_PATTERN_UNIVERSITARIO)


# ---------------------------------------------------------------------------
# Guías de lenguaje y dificultad numérica por nivel
#
# Indica al LLM cómo escribir (longitud de oraciones, vocabulario)
# y qué tipo de operaciones numéricas son apropiadas.
# ---------------------------------------------------------------------------

_LANGUAGE_GUIDELINES_BY_LEVEL = {
    "primaria": """
GUÍAS DE LENGUAJE Y DIFICULTAD (PRIMARIA):
- Oraciones cortas (máximo 15 palabras). Vocabulario sencillo, frecuente en niños de 6-12 años.
- Define cualquier palabra nueva inmediatamente con un sinónimo entre paréntesis.
- Operaciones permitidas: suma, resta, multiplicación y división con números enteros pequeños
  (típicamente <100), fracciones simples (1/2, 1/4, 3/4) y porcentajes redondos (10/25/50/75/100%).
- NO uses notación científica, exponentes, raíces, logaritmos, ni LaTeX complejo.
- LaTeX permitido solo para fracciones muy simples si ayuda a la claridad: $\\tfrac{1}{2}$.
""",
    "secundaria": """
GUÍAS DE LENGUAJE Y DIFICULTAD (SECUNDARIA):
- Oraciones de longitud media. Vocabulario adolescente, técnicismos solo cuando se introducen
  con definición clara.
- Operaciones permitidas: aritmética con decimales, álgebra básica (ecuaciones lineales,
  sistemas 2x2), geometría euclidiana, porcentajes y proporciones, estadística descriptiva
  básica (media, mediana, moda).
- Notación científica permitida con moderación. LaTeX para fórmulas cortas.
""",
    "preparatoria": """
GUÍAS DE LENGUAJE Y DIFICULTAD (PREPARATORIA):
- Vocabulario académico pero accesible. Tecnicismos del área permitidos.
- Operaciones permitidas: álgebra avanzada, trigonometría, funciones, cálculo introductorio
  (límites, derivadas y antiderivadas básicas), probabilidad y estadística, química con
  mol y unidades SI básicas.
- LaTeX completo. Notación científica habitual.
""",
    "universitario": """
GUÍAS DE LENGUAJE Y DIFICULTAD (UNIVERSITARIO):
- Lenguaje técnico del área, sin definir cada término. Se asume manejo del vocabulario disciplinar.
- Operaciones permitidas: todo el aparato matemático del pregrado (cálculo multivariable,
  ecuaciones diferenciales, álgebra lineal, mecánica clásica, termodinámica, química
  cuantitativa con unidades SI, programación, etc.).
- LaTeX riguroso. Tablas de datos cuando aplique.
""",
    "avanzado": """
GUÍAS DE LENGUAJE Y DIFICULTAD (AVANZADO / POSGRADO):
- Lenguaje técnico de frontera. Referencias a literatura científica reciente cuando aporten.
- Se espera integración de conceptos: no aplicación directa de fórmulas sino razonamiento.
- LaTeX y notación matemática rigurosa. Símbolos especializados del área permitidos.
""",
}


def build_language_guidelines(level_key: str) -> str:
    """Devuelve las guías de lenguaje y dificultad numérica para el nivel dado."""
    return _LANGUAGE_GUIDELINES_BY_LEVEL.get(
        level_key, _LANGUAGE_GUIDELINES_BY_LEVEL["universitario"]
    )

# ---------------------------------------------------------------------------
# Instrucciones por tipo de pregunta
# ---------------------------------------------------------------------------

TYPE_INSTRUCTIONS = {
    "multiple_choice": """
Genera preguntas de selección múltiple:
- Exactamente 4 opciones (a, b, c, d).
- Solo 1 opción correcta.
- Los distractores deben ser errores conceptuales comunes, NO absurdos.
- Incluye una explicación de por qué la respuesta correcta es correcta.
- content JSON: {"stem": "...", "options": [{"id": "a", "text": "...", "is_correct": false}, ...], "explanation": "..."}
- answer_key JSON: {"correct": "a"}
""",
    "numeric": """
Genera problemas de cálculo numérico:
- Todos los datos necesarios con unidades SI.
- Proporciona la solución paso a paso.
- Indica el valor esperado, unidad y tolerancia (±5% por defecto).
- content JSON: {"stem": "...", "context_data": {}, "expected_value": 0, "unit": "...", "tolerance": 0.05, "solution_steps": []}
- answer_key JSON: {"value": 0, "unit": "...", "tolerance": 0.05}
""",
    "essay": """
Genera preguntas de ensayo/argumentación:
- Requiere análisis crítico, no solo descripción.
- Incluye los conceptos clave que debe abordar la respuesta.
- content JSON: {"stem": "...", "key_concepts": [], "min_words": 200, "max_words": 800, "reference_answer": "..."}
- answer_key JSON: {"key_concepts": [], "reference_answer": "..."}
""",
    "problem_solving": """
Genera problemas de resolución con pasos:
- Datos contextuales claros con unidades.
- Los pasos deben ser evaluables parcialmente (crédito parcial).
- content JSON: {"stem": "...", "context_data": {}, "expected_steps": [], "final_answer": "...", "partial_credit": true}
- answer_key JSON: {"steps": [], "final_answer": "..."}
""",
    "true_false": """
Genera preguntas de verdadero/falso:
- Afirmaciones claras y sin ambigüedad.
- Incluye justificación de la respuesta correcta.
- content JSON: {"stem": "...", "explanation": "..."}
- answer_key JSON: {"is_true": true}
""",
    "short_answer": """
Genera preguntas de respuesta corta:
- Respuesta esperada en 1-3 oraciones.
- content JSON: {"stem": "...", "expected_length": "1-3 sentences"}
- answer_key JSON: {"reference_answer": "...", "key_points": []}
""",
}

# ---------------------------------------------------------------------------
# Mapeo de nivel a tipos de pregunta por defecto
# ---------------------------------------------------------------------------

LEVEL_QUESTION_TYPES = {
    "primaria": ["multiple_choice", "true_false", "short_answer"],
    "secundaria": ["multiple_choice", "short_answer", "problem_solving", "true_false"],
    "preparatoria": ["multiple_choice", "numeric", "problem_solving", "short_answer"],
    "universitario": ["multiple_choice", "numeric", "problem_solving", "essay", "short_answer"],
    "avanzado": ["numeric", "problem_solving", "essay"],
    "default": ["multiple_choice", "problem_solving", "short_answer"],
}

# ---------------------------------------------------------------------------
# Mapeo de tiempo estimado a número de preguntas
# ---------------------------------------------------------------------------

def estimate_question_count(time_estimate: str) -> int:
    """
    Estima el número de preguntas basado en el tiempo.

    Args:
        time_estimate: texto como "45 min", "1 hora", "90 minutos"
    Returns:
        número de preguntas sugerido (3-8)
    """
    if not time_estimate:
        return 5

    time_lower = time_estimate.lower().strip()

    # Extraer número
    numbers = re.findall(r"(\d+)", time_lower)
    if not numbers:
        return 5

    minutes = int(numbers[0])

    # Convertir horas a minutos
    if "hora" in time_lower or "hour" in time_lower or "hr" in time_lower:
        minutes *= 60

    # ~10 min por pregunta como referencia
    count = max(3, min(8, minutes // 10))
    return count


# ---------------------------------------------------------------------------
# Prompt del sistema — se formatea con parámetros de cada solicitud
# ---------------------------------------------------------------------------

GENERATION_SYSTEM_PROMPT = """Eres un diseñador instruccional experto en {subject_area}.
Tu tarea es crear {question_count} preguntas de evaluación sobre "{topic}" para nivel "{level}".

CONTEXTO ACADÉMICO Y DEL MUNDO REAL (Úsalo obligatoriamente):
{context}

CONTEXTOS APROPIADOS AL NIVEL "{level}" (USA preferentemente uno de estos):
{level_specific_contexts}

CONTEXTOS RECIENTES A EVITAR (NO repitas estos contextos ya usados en generaciones anteriores):
{recent_topics_to_avoid}

INSTRUCCIONES DEL DOCENTE:
{teacher_instructions}

{language_guidelines}

{area_instructions}

{anti_pattern_rules}

REGLAS PEDAGÓGICAS:
1. Las preguntas DEBEN estar contextualizadas usando los CONTEXTOS APROPIADOS AL NIVEL listados arriba.
   Si la lista está vacía, recurre al CONTEXTO ACADÉMICO general manteniendo el nivel pedido.
2. NO uses contextos de la lista "CONTEXTOS RECIENTES A EVITAR" — busca variedad temática.
3. Progresión de dificultad según taxonomía de Bloom (ajustada al nivel):
   - Primeras preguntas: Recordar/Comprender (definiciones, identificación)
   - Intermedias: Aplicar/Analizar (cálculos, comparaciones, relaciones causa-efecto)
   - Finales: Evaluar/Crear (diseño, argumentación, síntesis)
4. Para cada pregunta genera una rúbrica de evaluación detallada.
5. Los distractores en selección múltiple deben ser errores conceptuales comunes, NO opciones absurdas.
6. Si hay fórmulas matemáticas, usa notación LaTeX: inline $...$ y bloque $$...$$.
   En primaria, limita LaTeX a fracciones simples si las necesitas.
7. Cada pregunta debe ser independiente (no revelar respuestas de otras).

TIPOS DE PREGUNTA A GENERAR:
{type_instructions}

SALIDA:
Genera un JSON estrictamente con esta estructura (sin formato markdown como ```json):
{{
  "title": "Título descriptivo y profesional de la evaluación",
  "introduction": "Párrafo motivacional que conecte al estudiante con aplicaciones reales del tema",
  "questions": [
    {{
      "question_type": "tipo_de_pregunta",
      "order_index": 1,
      "bloom_level": "remember|understand|apply|analyze|evaluate|create",
      "points": 10.0,
      "content": {{}},
      "answer_key": {{}},
      "rubric": {{
        "criteria": [
          {{
            "name": "Nombre del criterio",
            "description": "Qué se evalúa",
            "levels": [
              {{"score": 10, "description": "Excelente"}},
              {{"score": 7, "description": "Bueno"}},
              {{"score": 4, "description": "Regular"}},
              {{"score": 0, "description": "Insuficiente"}}
            ]
          }}
        ],
        "total_points": 10.0
      }}
    }}
  ]
}}
"""

# ---------------------------------------------------------------------------
# Prompt de validación/revisión (segundo paso)
# ---------------------------------------------------------------------------

REVIEW_SYSTEM_PROMPT = """Eres un revisor pedagógico experto. Tu tarea es revisar y corregir una evaluación
generada por IA para asegurar máxima calidad.

EVALUACIÓN A REVISAR:
{questions_json}

TEMA: {topic}
NIVEL: {level}
ÁREA: {subject_area}

CRITERIOS DE REVISIÓN (verifica cada uno):

1. PROGRESIÓN DE BLOOM: ¿Las preguntas siguen una progresión lógica desde recordar hasta evaluar/crear?
   Si no, reordena o ajusta los bloom_level.

2. FORMATO LATEX: ¿Todas las expresiones matemáticas usan $...$ (inline) o $$...$$ (bloque)?
   Corrige cualquier fórmula que esté en texto plano. Usa notación estándar.

3. REALISMO: ¿Los escenarios son situaciones reales, no genéricas?
   Rechaza "Juan compró manzanas" y reemplaza con contextos profesionales/científicos.

4. DATOS NUMÉRICOS: ¿Todos los valores son verosímiles con unidades SI correctas?
   Verifica órdenes de magnitud. Un río no fluye a 500 m/s. Una persona no pesa 500 kg.

5. DISTRACTORES: ¿Las opciones incorrectas en selección múltiple son errores conceptuales
   plausibles, no opciones absurdas o evidentemente falsas?

6. RÚBRICAS: ¿Cada pregunta tiene una rúbrica con criterios medibles y diferenciados?

7. INDEPENDENCIA: ¿Cada pregunta es independiente y no revela respuestas de otras?

8. COMPLETITUD: ¿Los problemas numéricos incluyen TODOS los datos necesarios para resolverlos?

SALIDA:
Devuelve el JSON corregido con la MISMA estructura. Si todo está bien, devuelve el JSON sin cambios.
NO añadas comentarios fuera del JSON. Solo el JSON corregido.
"""
