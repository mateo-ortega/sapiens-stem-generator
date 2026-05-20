"""
Recuperación de contexto académico y del mundo real para generación de tareas STEM.

Combina búsquedas en ArXiv, web (DuckDuckGo) y la base de datos curada local
para proveer al LLM con datos reales y verificados.
"""

import arxiv
from ddgs import DDGS
from core.subject_knowledge import get_subject_knowledge, normalize_level_key
from core.prompts import detect_subject_area

# Timeout global para búsquedas web (segundos)
_WEB_TIMEOUT = 10


def search_arxiv(query: str, max_results: int = 2) -> str:
    """
    Busca papers académicos en ArXiv relacionados con el query.

    Args:
        query: término de búsqueda
        max_results: máximo de resultados
    Returns:
        texto con títulos y resúmenes de papers encontrados
    """
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = ""
        for result in client.results(search):
            results += f"Title: {result.title}\nSummary: {result.summary}\n\n"

        return results if results else "No se encontraron papers académicos."
    except Exception as e:
        print(f"Error buscando en ArXiv: {e}")
        return "Error obteniendo contexto académico."


def search_web(query: str, max_results: int = 3) -> str:
    """
    Busca en la web usando DuckDuckGo con timeout.

    Args:
        query: término de búsqueda
        max_results: máximo de resultados
    Returns:
        texto con títulos y snippets de resultados web
    """
    try:
        results = ""
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(query, max_results=max_results)
            for r in ddgs_gen:
                results += f"Fuente: {r['title']}\nContenido: {r['body']}\n\n"
        return results if results else "No se encontraron resultados web."
    except Exception as e:
        print(f"Error buscando en web: {e}")
        return "Error obteniendo contexto web."


def get_context(topic: str, level: str) -> str:
    """
    Combina ArXiv, búsqueda web bilingüe y conocimiento curado local
    para proveer contexto pedagógico completo.

    Args:
        topic: tema de la tarea (ej. "Termodinámica")
        level: nivel educativo (ej. "Universitario", "Secundaria")
    Returns:
        texto combinado con todo el contexto disponible
    """
    print(f"Obteniendo contexto para '{topic}' nivel '{level}'...")

    sections = []

    # 1. Detectar área y normalizar nivel para conocimiento curado
    area = detect_subject_area(topic)
    level_key = normalize_level_key(level)

    # 2. Conocimiento curado local filtrado por nivel (no requiere internet)
    local_knowledge = get_subject_knowledge(area, level_key)
    if local_knowledge:
        sections.append(f"BASE DE CONOCIMIENTO CURADO:\n{local_knowledge}")

    # 3. ArXiv — para niveles intermedios y avanzados (no solo universitario)
    advanced_keywords = [
        "universi", "avanzado", "superior", "college", "preparatoria",
        "bachillerato", "pregrado", "posgrado", "graduate",
    ]
    if any(word in level.lower() for word in advanced_keywords):
        academic = search_arxiv(topic)
        if academic and "Error" not in academic:
            sections.append(f"CONTEXTO ACADÉMICO (ArXiv):\n{academic}")

    # 4. Búsqueda web bilingüe — español e inglés para mayor cobertura
    web_queries = [
        f"aplicaciones reales de {topic}",
        f"real world application of {topic}",
    ]

    web_results = []
    for query in web_queries:
        result = search_web(query, max_results=2)
        if result and "Error" not in result:
            web_results.append(result)

    if web_results:
        sections.append(f"CONTEXTO DEL MUNDO REAL:\n{''.join(web_results)}")

    # 5. Búsqueda de datos experimentales (para áreas cuantitativas)
    if area in ("science", "engineering", "math"):
        data_query = f"{topic} datos experimentales unidades SI"
        data_result = search_web(data_query, max_results=2)
        if data_result and "Error" not in data_result:
            sections.append(f"DATOS EXPERIMENTALES:\n{data_result}")

    combined = "\n\n".join(sections)
    return combined if combined else "No se pudo obtener contexto externo."


if __name__ == "__main__":
    print(get_context("Termodinámica", "Universitario"))
