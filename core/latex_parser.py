"""
Parser de contenido mixto texto + LaTeX.

Segmenta texto que contiene expresiones LaTeX en bloques tipados
para que el generador de PDF pueda renderizar cada segmento apropiadamente.
"""

import re


def parse_mixed_content(text: str) -> list:
    """
    Divide texto con LaTeX embebido en segmentos tipados.

    Detecta:
    - $$...$$ → latex_block (ecuaciones centradas)
    - $...$   → latex_inline (expresiones en línea)
    - texto   → text (prosa normal)

    Args:
        text: texto con posibles expresiones LaTeX
    Returns:
        lista de dicts: [{"type": "text"|"latex_inline"|"latex_block", "content": "..."}]
    """
    if not text or not isinstance(text, str):
        return [{"type": "text", "content": str(text) if text else ""}]

    segments = []

    # Regex que captura $$...$$ (block) y $...$ (inline) en orden
    # $$...$$ se procesa primero porque es más largo
    pattern = re.compile(
        r'(\$\$.*?\$\$)'   # bloque: $$...$$
        r'|'
        r'(\$[^$]+?\$)',    # inline: $...$
        re.DOTALL
    )

    last_end = 0
    for match in pattern.finditer(text):
        start = match.start()

        # Texto antes del match
        if start > last_end:
            plain = text[last_end:start]
            if plain.strip():
                segments.append({"type": "text", "content": plain})
            elif plain:
                segments.append({"type": "text", "content": plain})

        # Determinar tipo y extraer contenido sin delimitadores
        if match.group(1):
            # Bloque $$...$$
            latex_content = match.group(1)[2:-2].strip()
            if latex_content:
                segments.append({"type": "latex_block", "content": latex_content})
        elif match.group(2):
            # Inline $...$
            latex_content = match.group(2)[1:-1].strip()
            if latex_content:
                segments.append({"type": "latex_inline", "content": latex_content})

        last_end = match.end()

    # Texto restante después del último match
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append({"type": "text", "content": remaining})

    # Si no se encontró ningún patrón LaTeX, devolver todo como texto
    if not segments:
        segments.append({"type": "text", "content": text})

    return segments


def has_latex(text: str) -> bool:
    """Verifica rápidamente si un texto contiene expresiones LaTeX."""
    if not text:
        return False
    return "$" in text


def strip_latex(text: str) -> str:
    """
    Elimina delimitadores LaTeX y devuelve solo el contenido.
    Útil como fallback cuando no se puede renderizar.
    """
    result = text
    result = re.sub(r'\$\$(.*?)\$\$', r'\1', result, flags=re.DOTALL)
    result = re.sub(r'\$([^$]+?)\$', r'\1', result)
    return result
