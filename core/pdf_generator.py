"""
Generador de PDF con identidad visual Sapiens completa.

Soporta:
- Renderizado de LaTeX (inline y bloque) via matplotlib mathtext
- Múltiples tipos de pregunta (selección múltiple, numérico, ensayo, etc.)
- Fuentes Outfit (títulos) e Instrument Sans (cuerpo) bundleadas
- Paleta de marca Sapiens (teal, warm white, deep teal)
- Clave de respuestas opcional en página separada
- Compatibilidad con formato legacy (title, intuition_questions, etc.)
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from core.brand import COLORS, PDF_COLORS, hex_to_rgb
from core.latex_parser import parse_mixed_content, has_latex
from core.latex_renderer import render_latex_to_image, render_latex_block, get_image_dimensions


# ---------------------------------------------------------------------------
# Normalización de caracteres Unicode no soportados por las fuentes bundleadas
# ---------------------------------------------------------------------------

_UNICODE_REPLACEMENTS = str.maketrans({
    "\u00b2": "^2",   # ²
    "\u00b3": "^3",   # ³
    "\u00b9": "^1",   # ¹
    "\u2070": "^0",   # ⁰
    "\u2074": "^4",   # ⁴
    "\u2075": "^5",   # ⁵
    "\u2076": "^6",   # ⁶
    "\u2077": "^7",   # ⁷
    "\u2078": "^8",   # ⁸
    "\u2079": "^9",   # ⁹
    "\u00b1": "+/-",  # ±
    "\u00d7": "x",    # ×
    "\u00f7": "/",    # ÷
    "\u2212": "-",    # − (guión matemático)
    "\u2013": "-",    # – (guión en)
    "\u2014": "--",   # — (guión em)
    "\u2019": "'",    # ' (comilla tipográfica)
    "\u201c": '"',    # " (comilla apertura)
    "\u201d": '"',    # " (comilla cierre)
    "\u2026": "...",  # … (puntos suspensivos)
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma",
    "\u03b4": "delta", "\u03b5": "epsilon", "\u03b8": "theta",
    "\u03bb": "lambda", "\u03bc": "mu", "\u03bd": "nu",
    "\u03c0": "pi", "\u03c1": "rho", "\u03c3": "sigma",
    "\u03c4": "tau", "\u03c6": "phi", "\u03c9": "omega",
    "\u0394": "Delta", "\u03a3": "Sigma", "\u03a9": "Omega",
    "\u221e": "inf",  # ∞
    "\u2248": "~=",   # ≈
    "\u2260": "!=",   # ≠
    "\u2264": "<=",   # ≤
    "\u2265": ">=",   # ≥
})


def _safe_text(text: str) -> str:
    """
    Reemplaza caracteres Unicode fuera del rango de las fuentes bundleadas
    por equivalentes ASCII seguros antes de enviar a FPDF2.
    """
    return str(text).translate(_UNICODE_REPLACEMENTS)


# ---------------------------------------------------------------------------
# Rutas de fuentes
# ---------------------------------------------------------------------------

_RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
_FONTS_DIR = os.path.join(_RESOURCES_DIR, "fonts")


def _load_fonts(pdf: FPDF) -> tuple:
    """
    Carga fuentes para el PDF en orden de prioridad:
    1. Outfit + Instrument Sans bundleadas en resources/fonts/ (TTF válidos)
    2. Segoe UI del sistema Windows
    3. Helvetica (built-in FPDF2, siempre disponible)

    Returns:
        (heading_font, body_font) — nombres de familia registrados
    """
    heading_font = "helvetica"
    body_font = "helvetica"

    def _try_add(family: str, style: str, path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            pdf.add_font(family, style=style, fname=path)
            return True
        except Exception:
            return False

    # 1. Fuentes bundleadas en resources/fonts/
    outfit_bold = os.path.join(_FONTS_DIR, "Outfit-Bold.ttf")
    outfit_semi = os.path.join(_FONTS_DIR, "Outfit-SemiBold.ttf")
    instrument_reg = os.path.join(_FONTS_DIR, "InstrumentSans-Regular.ttf")
    instrument_med = os.path.join(_FONTS_DIR, "InstrumentSans-Medium.ttf")

    if _try_add("Outfit", "B", outfit_bold):
        _try_add("Outfit", "", outfit_semi if os.path.exists(outfit_semi) else outfit_bold)
        heading_font = "Outfit"

    if _try_add("InstrumentSans", "", instrument_reg):
        _try_add("InstrumentSans", "B", instrument_med if os.path.exists(instrument_med) else instrument_reg)
        body_font = "InstrumentSans"

    # 2. Fallback: Segoe UI (Windows — tipografía limpia y bien soportada)
    if heading_font == "helvetica":
        segoe_b = r"C:\Windows\Fonts\segoeuib.ttf"
        segoe_r = r"C:\Windows\Fonts\segoeui.ttf"
        if _try_add("SegoeUI", "", segoe_r) and _try_add("SegoeUI", "B", segoe_b):
            heading_font = "SegoeUI"
            body_font = "SegoeUI"

    return heading_font, body_font


# ---------------------------------------------------------------------------
# Clase PDF principal
# ---------------------------------------------------------------------------

class SapiensPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.heading_font = "helvetica"
        self.body_font = "helvetica"

    def footer(self):
        self.set_y(-15)
        self.set_font(self.body_font, "", 8)
        r, g, b = PDF_COLORS["footer_text"]
        self.set_text_color(r, g, b)
        self.cell(0, 10, f"Sapiens by Shift  |  Pagina {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Renderizado de contenido mixto (texto + LaTeX) — inline real
# ---------------------------------------------------------------------------

def _write_words_inline(pdf: SapiensPDF, text: str, font_family: str,
                        font_size: int, line_height: float):
    """
    Escribe `text` palabra por palabra en la línea actual con salto automático.

    Permite que el texto y las imágenes LaTeX compartan la misma línea física.
    """
    pdf.set_font(font_family, "", font_size)
    r_margin = pdf.w - pdf.r_margin
    words = _safe_text(text).split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else " " + word
        if not token:
            continue
        tw = pdf.get_string_width(token)
        if pdf.get_x() + tw > r_margin and pdf.get_x() > pdf.l_margin:
            pdf.ln(line_height)
            pdf.set_x(pdf.l_margin)
            token = word
            tw = pdf.get_string_width(token)
        pdf.cell(tw, line_height, token)


def _write_mixed_content(pdf: SapiensPDF, text: str, font_family: str,
                         font_size: int, line_height: float = 6.0):
    """
    Escribe texto con LaTeX embebido en el PDF.

    Renderizado verdaderamente inline: texto e imágenes LaTeX comparten la misma
    línea física. Los bloques ($$...$$) se centran en línea propia.
    """
    pdf.set_x(pdf.l_margin)

    if not has_latex(text):
        pdf.set_font(font_family, "", font_size)
        pdf.multi_cell(0, line_height, _safe_text(text), align="L")
        return

    segments = parse_mixed_content(text)
    r_margin = pdf.w - pdf.r_margin
    max_w    = r_margin - pdf.l_margin
    _DPI     = 150

    for seg in segments:
        stype   = seg["type"]
        content = seg["content"]

        if stype == "text":
            if content.strip() or content:
                _write_words_inline(pdf, content, font_family, font_size, line_height)

        elif stype == "latex_inline":
            img_path = render_latex_to_image(content, fontsize=font_size)
            if img_path and os.path.exists(img_path):
                w_px, h_px = get_image_dimensions(img_path)
                if w_px > 0 and h_px > 0:
                    img_w = (w_px / _DPI) * 25.4
                    img_h = (h_px / _DPI) * 25.4
                    if img_w > max_w:
                        img_h *= max_w / img_w
                        img_w  = max_w
                    # Saltar línea si no cabe
                    if pdf.get_x() + img_w > r_margin and pdf.get_x() > pdf.l_margin:
                        pdf.ln(line_height)
                        pdf.set_x(pdf.l_margin)
                    # Alinear verticalmente al centro de la línea
                    y_img = pdf.get_y() + max(0.0, (line_height - img_h) / 2.0)
                    x_img = pdf.get_x()
                    pdf.image(img_path, x=x_img, y=y_img, w=img_w, h=img_h)
                    # Avanzar x tras la imagen; mantener y
                    pdf.set_xy(x_img + img_w, pdf.get_y())
                else:
                    _write_words_inline(pdf, content, font_family, font_size, line_height)
            else:
                _write_words_inline(pdf, content, font_family, font_size, line_height)

        elif stype == "latex_block":
            # Terminar línea actual y centrar bloque
            if pdf.get_x() > pdf.l_margin:
                pdf.ln(line_height)
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            img_path = render_latex_block(content, fontsize=font_size + 2)
            if img_path and os.path.exists(img_path):
                w_px, h_px = get_image_dimensions(img_path)
                if w_px > 0 and h_px > 0:
                    img_w = (w_px / _DPI) * 25.4
                    img_h = (h_px / _DPI) * 25.4
                    if img_w > max_w:
                        img_h *= max_w / img_w
                        img_w  = max_w
                    x_c = pdf.l_margin + (max_w - img_w) / 2
                    pdf.image(img_path, x=x_c, y=pdf.get_y(), w=img_w, h=img_h)
                    pdf.set_y(pdf.get_y() + img_h + 2)
                    pdf.set_x(pdf.l_margin)
                else:
                    pdf.multi_cell(0, line_height, content, align="L")
            else:
                pdf.multi_cell(0, line_height, content, align="L")
            pdf.ln(2)

    # Asegurar nueva línea al final si el cursor no está al margen
    if pdf.get_x() > pdf.l_margin:
        pdf.ln(line_height)


# ---------------------------------------------------------------------------
# Renderizadores por tipo de pregunta
# ---------------------------------------------------------------------------

def _render_multiple_choice(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza una pregunta de selección múltiple."""
    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)
    pdf.ln(2)

    options = content.get("options", [])
    original_l_margin = pdf.l_margin
    opt_indent = original_l_margin + 8

    for opt in options:
        opt_id = opt.get("id", "?")
        opt_text = opt.get("text", "")
        pdf.set_x(original_l_margin)
        y_current = pdf.get_y()
        # Círculo indicador
        pdf.set_draw_color(*PDF_COLORS["border"])
        pdf.ellipse(original_l_margin + 2, y_current + 1, 4, 4)
        # Texto con soporte LaTeX, indentado para no solapar el círculo
        pdf.set_left_margin(opt_indent)
        _write_mixed_content(pdf, f"{opt_id}) {opt_text}", body_font, 11, lh)
        pdf.set_left_margin(original_l_margin)
        pdf.ln(1)

    pdf.ln(3)


def _render_numeric(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza un problema numérico."""
    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)

    # Datos contextuales si los hay
    context_data = content.get("context_data", {})
    if context_data:
        pdf.ln(2)
        pdf.set_x(pdf.l_margin)
        pdf.set_font(body_font, "B", 10)
        pdf.set_text_color(*PDF_COLORS["secondary_text"])
        pdf.multi_cell(0, 5, "Datos:", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(body_font, "", 10)
        for key, val in context_data.items():
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, _safe_text(f"  \u2022 {key}: {val}"), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*PDF_COLORS["body_text"])

    # Espacio para respuesta
    pdf.ln(3)
    pdf.set_x(pdf.l_margin)
    pdf.set_draw_color(*PDF_COLORS["border"])
    pdf.set_font(body_font, "", 10)
    pdf.set_text_color(*PDF_COLORS["secondary_text"])
    pdf.cell(0, 5, "Respuesta: _______________", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PDF_COLORS["body_text"])
    pdf.ln(4)


def _render_essay(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza una pregunta de ensayo."""
    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)

    min_w = content.get("min_words", 200)
    max_w = content.get("max_words", 800)
    pdf.ln(2)
    pdf.set_font(body_font, "", 9)
    pdf.set_text_color(*PDF_COLORS["secondary_text"])
    pdf.cell(0, 4, f"Extension esperada: {min_w}-{max_w} palabras", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PDF_COLORS["body_text"])

    # Líneas para escritura
    pdf.ln(2)
    pdf.set_draw_color(*hex_to_rgb(COLORS["border_subtle"]))
    for _ in range(8):
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(7)
    pdf.ln(3)


def _render_problem_solving(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza un problema de resolución por pasos."""
    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)

    context_data = content.get("context_data", {})
    if context_data:
        pdf.ln(2)
        pdf.set_x(pdf.l_margin)
        pdf.set_font(body_font, "B", 10)
        pdf.set_text_color(*PDF_COLORS["secondary_text"])
        pdf.multi_cell(0, 5, "Datos del problema:", align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(body_font, "", 10)
        for key, val in context_data.items():
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, _safe_text(f"  \u2022 {key}: {val}"), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*PDF_COLORS["body_text"])

    # Espacio para desarrollo
    pdf.ln(3)
    pdf.set_font(body_font, "", 9)
    pdf.set_text_color(*PDF_COLORS["secondary_text"])
    pdf.cell(0, 4, "Desarrollo (muestra cada paso):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PDF_COLORS["body_text"])

    pdf.set_draw_color(*hex_to_rgb(COLORS["border_subtle"]))
    for _ in range(6):
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(7)
    pdf.ln(3)


def _render_true_false(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza una pregunta de verdadero/falso."""
    # Instrucción explícita antes del enunciado
    pdf.set_font(body_font, "", 9)
    pdf.set_text_color(*PDF_COLORS["secondary_text"])
    pdf.cell(0, 4, "Indica si la siguiente afirmacion es Verdadera (V) o Falsa (F):",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*PDF_COLORS["body_text"])
    pdf.ln(1)

    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)
    pdf.ln(2)

    pdf.set_x(pdf.l_margin)
    pdf.set_font(body_font, "", 11)
    pdf.set_draw_color(*PDF_COLORS["border"])
    y = pdf.get_y()
    # Checkbox Verdadero
    x_v = pdf.l_margin + 5
    pdf.rect(x_v, y + 0.5, 4, 4)
    pdf.set_xy(x_v + 6, y)
    pdf.cell(30, 5, "Verdadero")
    # Checkbox Falso
    x_f = pdf.l_margin + 50
    pdf.rect(x_f, y + 0.5, 4, 4)
    pdf.set_xy(x_f + 6, y)
    pdf.cell(20, 5, "Falso", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)


def _render_short_answer(pdf: SapiensPDF, idx: int, content: dict, body_font: str, lh: float):
    """Renderiza una pregunta de respuesta corta."""
    stem = content.get("stem", "")
    _write_mixed_content(pdf, f"{idx}. {stem}", body_font, 11, lh)
    pdf.ln(2)

    pdf.set_draw_color(*hex_to_rgb(COLORS["border_subtle"]))
    for _ in range(3):
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(7)
    pdf.ln(3)


# Mapa tipo → renderizador
_QUESTION_RENDERERS = {
    "multiple_choice": _render_multiple_choice,
    "numeric": _render_numeric,
    "essay": _render_essay,
    "problem_solving": _render_problem_solving,
    "true_false": _render_true_false,
    "short_answer": _render_short_answer,
}

# Alias para tipos que el LLM devuelve en español o con variantes
_TYPE_ALIASES: dict[str, str] = {
    "selección múltiple": "multiple_choice",
    "seleccion multiple": "multiple_choice",
    "seleccion_multiple": "multiple_choice",
    "opción múltiple": "multiple_choice",
    "opcion multiple": "multiple_choice",
    "múltiple opción": "multiple_choice",
    "multiple opcion": "multiple_choice",
    "numérico": "numeric",
    "numerico": "numeric",
    "cálculo numérico": "numeric",
    "calculo numerico": "numeric",
    "problema de cálculo numérico": "numeric",
    "problema de calculo numerico": "numeric",
    "problema numérico": "numeric",
    "problema numerico": "numeric",
    "ensayo": "essay",
    "argumentación": "essay",
    "argumentacion": "essay",
    "ensayo/argumentación": "essay",
    "ensayo/argumentacion": "essay",
    "resolución de problemas": "problem_solving",
    "resolucion de problemas": "problem_solving",
    "problema de resolución con pasos": "problem_solving",
    "problema de resolucion con pasos": "problem_solving",
    "resolución por pasos": "problem_solving",
    "resolucion por pasos": "problem_solving",
    "problem solving": "problem_solving",
    "verdadero/falso": "true_false",
    "verdadero falso": "true_false",
    "verdadero o falso": "true_false",
    "v/f": "true_false",
    "respuesta corta": "short_answer",
    "short answer": "short_answer",
    "respuesta_corta": "short_answer",
}


def _normalize_q_type(raw: str) -> str:
    """
    Convierte el question_type devuelto por el LLM al key canónico esperado por
    _QUESTION_RENDERERS. Soporta nombres en español, con/sin tilde, y con espacios
    o guiones bajos como separadores.
    """
    if raw in _QUESTION_RENDERERS:
        return raw
    normalized = _TYPE_ALIASES.get(raw.lower().strip())
    if normalized:
        return normalized
    # Último recurso: reemplazar espacios por _ y pasar a minúsculas
    slug = raw.lower().strip().replace(" ", "_").replace("/", "_")
    return slug if slug in _QUESTION_RENDERERS else "short_answer"


# ---------------------------------------------------------------------------
# Renderizador de clave de respuestas
# ---------------------------------------------------------------------------

def _render_answer_key(pdf: SapiensPDF, questions: list, heading_font: str, body_font: str):
    """Genera la página de clave de respuestas con rúbricas."""
    pdf.add_page()

    # Título
    pdf.set_font(heading_font, "B", 16)
    pdf.set_text_color(*PDF_COLORS["title"])
    pdf.cell(0, 10, "Clave de Respuestas y Rubricas", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Línea decorativa
    pdf.set_draw_color(*PDF_COLORS["accent_line"])
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(8)

    for q in questions:
        idx = q.get("order_index", 0)
        q_type = _normalize_q_type(q.get("question_type", "unknown"))
        bloom = q.get("bloom_level", "")
        points = q.get("points", 0)
        answer_key = q.get("answer_key", {})
        rubric = q.get("rubric", {})

        # Encabezado de pregunta
        pdf.set_font(heading_font, "B", 11)
        pdf.set_text_color(*PDF_COLORS["section_header"])
        type_names = {
            "multiple_choice": "Seleccion multiple",
            "numeric": "Numerico",
            "essay": "Ensayo",
            "problem_solving": "Resolucion de problemas",
            "true_false": "Verdadero/Falso",
            "short_answer": "Respuesta corta",
        }
        type_display = type_names.get(q_type, q_type)
        pdf.cell(0, 6, f"Pregunta {idx} ({type_display}) - {points} pts - Bloom: {bloom}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Respuesta correcta
        pdf.set_font(body_font, "", 10)
        pdf.set_text_color(*PDF_COLORS["body_text"])

        if q_type == "multiple_choice":
            correct = answer_key.get("correct", "?")
            pdf.cell(0, 5, f"  Respuesta correcta: {correct}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            explanation = q.get("content", {}).get("explanation", "")
            if explanation:
                pdf.set_font(body_font, "", 9)
                pdf.set_text_color(*PDF_COLORS["secondary_text"])
                _write_mixed_content(pdf, f"  Explicacion: {explanation}", body_font, 9, 5)
                pdf.set_text_color(*PDF_COLORS["body_text"])

        elif q_type == "numeric":
            value = answer_key.get("value", "?")
            unit = answer_key.get("unit", "")
            tol = answer_key.get("tolerance", 0.05)
            pdf.cell(0, 5, f"  Valor esperado: {value} {unit} (tolerancia: +/-{tol*100:.0f}%)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        elif q_type == "true_false":
            is_true = answer_key.get("is_true", None)
            ans = "Verdadero" if is_true else "Falso"
            pdf.cell(0, 5, f"  Respuesta: {ans}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        elif q_type in ("essay", "short_answer"):
            ref = answer_key.get("reference_answer", "")
            if ref:
                pdf.set_font(body_font, "", 9)
                _write_mixed_content(pdf, f"  Referencia: {ref}", body_font, 9, 5)

        elif q_type == "problem_solving":
            steps = answer_key.get("steps", [])
            final = answer_key.get("final_answer", "")
            for i, step in enumerate(steps, 1):
                step_text = step if isinstance(step, str) else str(step)
                _write_mixed_content(pdf, f"  Paso {i}: {step_text}", body_font, 9, 5)
            if final:
                _write_mixed_content(pdf, f"  Respuesta final: {final}", body_font, 9, 5)

        # Rúbrica
        criteria = rubric.get("criteria", [])
        if criteria:
            pdf.ln(2)
            pdf.set_font(body_font, "B", 9)
            pdf.set_text_color(*PDF_COLORS["secondary_text"])
            pdf.cell(0, 5, "  Rubrica:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font(body_font, "", 8)
            for crit in criteria:
                crit_name = crit.get("name", "")
                pdf.cell(0, 4, f"    • {crit_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                for lvl in crit.get("levels", []):
                    score = lvl.get("score", 0)
                    desc = lvl.get("description", "")
                    pdf.cell(0, 4, f"      [{score} pts] {desc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_text_color(*PDF_COLORS["body_text"])
        pdf.ln(5)


# ---------------------------------------------------------------------------
# Función principal: crear PDF
# ---------------------------------------------------------------------------

def create_stem_pdf(task_data: dict, logo_path: str, output_path: str, include_answer_key: bool = False):
    """
    Crea un PDF con identidad visual Sapiens completa.

    Soporta formato nuevo (questions[]) y formato legacy (intuition_questions, etc.)

    Args:
        task_data: diccionario con la tarea generada
        logo_path: ruta al logo Sapiens
        output_path: ruta de salida del PDF
        include_answer_key: si True, agrega página con clave de respuestas
    """
    pdf = SapiensPDF()
    heading_font, body_font = _load_fonts(pdf)
    pdf.heading_font = heading_font
    pdf.body_font = body_font

    pdf.add_page()
    pdf.set_margins(25, 20, 25)
    pdf.set_auto_page_break(auto=True, margin=25)

    body_lh = 5.5  # Line height para cuerpo

    # --- Header: Logo + Título ---
    logo_w = 45
    logo_x = 210 - 25 - logo_w
    has_logo = logo_path and os.path.exists(logo_path)

    if has_logo:
        try:
            pdf.image(logo_path, x=logo_x, y=15, w=logo_w)
        except Exception as e:
            print(f"Error colocando logo: {e}")
            has_logo = False

    # Título
    pdf.set_font(heading_font, "B", 15)
    pdf.set_text_color(*PDF_COLORS["title"])
    title = task_data.get("title", "Evaluacion STEM Sapiens")
    title_max_w = (logo_x - 25 - 5) if has_logo else 0
    pdf.multi_cell(title_max_w, 8, title, align="L")

    # Asegurar que el cursor esté debajo del logo
    if has_logo and pdf.get_y() < 48:
        pdf.set_y(48)
    else:
        pdf.ln(4)

    # Línea decorativa teal
    pdf.set_draw_color(*PDF_COLORS["accent_line"])
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # --- Introducción ---
    intro = task_data.get("introduction", "")
    if intro:
        pdf.set_font(body_font, "", 11)
        pdf.set_text_color(*PDF_COLORS["body_text"])
        _write_mixed_content(pdf, intro, body_font, 11, body_lh)
        pdf.ln(8)

    # --- Detectar formato: nuevo (questions[]) vs legacy ---
    questions = task_data.get("questions", [])

    if questions:
        _render_new_format(pdf, questions, heading_font, body_font, body_lh)

        if include_answer_key:
            _render_answer_key(pdf, questions, heading_font, body_font)
    else:
        _render_legacy_format(pdf, task_data, heading_font, body_font, body_lh)

    # --- Guardar ---
    pdf.output(output_path)
    print(f"PDF generado exitosamente en: {output_path}")


def _render_new_format(pdf: SapiensPDF, questions: list, heading_font: str, body_font: str, lh: float):
    """Renderiza preguntas en el formato nuevo con tipos variados."""
    # Agrupar por bloom level para secciones
    bloom_sections = {
        "remember": "Fase 1: Comprension",
        "understand": "Fase 1: Comprension",
        "apply": "Fase 2: Aplicacion",
        "analyze": "Fase 2: Aplicacion",
        "evaluate": "Fase 3: Sintesis y Evaluacion",
        "create": "Fase 3: Sintesis y Evaluacion",
    }

    current_section = ""
    for q in sorted(questions, key=lambda x: x.get("order_index", 0)):
        bloom = q.get("bloom_level", "understand")
        section = bloom_sections.get(bloom, "Preguntas")

        # Nuevo encabezado de sección si cambió
        if section != current_section:
            current_section = section
            pdf.ln(4)
            pdf.set_font(heading_font, "B", 13)
            pdf.set_text_color(*PDF_COLORS["section_header"])
            pdf.cell(0, 8, current_section, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            # Sub-línea teal
            pdf.set_draw_color(*PDF_COLORS["accent_line"])
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
            pdf.ln(4)
            pdf.set_text_color(*PDF_COLORS["body_text"])

        # Renderizar según tipo
        q_type = _normalize_q_type(q.get("question_type", "short_answer"))
        content = q.get("content", {})
        idx = q.get("order_index", 0)
        points = q.get("points", 0)

        # Badge de puntos + tipo de pregunta
        type_labels = {
            "multiple_choice": "Seleccion multiple",
            "numeric": "Numerico",
            "essay": "Ensayo",
            "problem_solving": "Resolucion de problemas",
            "true_false": "Verdadero / Falso",
            "short_answer": "Respuesta corta",
        }
        type_label = type_labels.get(q_type, q_type)
        pdf.set_font(body_font, "", 8)
        pdf.set_text_color(*PDF_COLORS["secondary_text"])
        pdf.cell(0, 4, f"[{type_label}  •  {points} puntos]", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*PDF_COLORS["body_text"])

        renderer = _QUESTION_RENDERERS.get(q_type, _render_short_answer)
        renderer(pdf, idx, content, body_font, lh)


def _render_legacy_format(pdf: SapiensPDF, task_data: dict, heading_font: str, body_font: str, lh: float):
    """Renderiza el formato legacy (intuition_questions, development_problems, deep_dive_challenge)."""

    # Fase 1: Intuición
    intuition = task_data.get("intuition_questions", [])
    if intuition:
        pdf.set_font(heading_font, "B", 13)
        pdf.set_text_color(*PDF_COLORS["section_header"])
        pdf.cell(0, 8, "Fase 1: Activacion de la Intuicion", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*PDF_COLORS["accent_line"])
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(*PDF_COLORS["body_text"])

        for idx, q in enumerate(intuition, 1):
            _write_mixed_content(pdf, f"{idx}. {q}", body_font, 11, lh)
            pdf.ln(4)
        pdf.ln(4)

    # Fase 2: Desarrollo
    development = task_data.get("development_problems", [])
    if development:
        pdf.set_font(heading_font, "B", 13)
        pdf.set_text_color(*PDF_COLORS["section_header"])
        pdf.cell(0, 8, "Fase 2: Desarrollo Formal", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*PDF_COLORS["accent_line"])
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(*PDF_COLORS["body_text"])

        for idx, q in enumerate(development, 1):
            _write_mixed_content(pdf, f"{idx}. {q}", body_font, 11, lh)
            pdf.ln(4)
        pdf.ln(4)

    # Fase 3: Reto
    deep_dive = task_data.get("deep_dive_challenge", "")
    if deep_dive:
        pdf.set_font(heading_font, "B", 13)
        pdf.set_text_color(*PDF_COLORS["section_header"])
        pdf.cell(0, 8, "Fase 3: Reto de Profundizacion", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*PDF_COLORS["accent_line"])
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(*PDF_COLORS["body_text"])

        if isinstance(deep_dive, list):
            deep_dive = " ".join(deep_dive)
        _write_mixed_content(pdf, deep_dive, body_font, 11, lh)
