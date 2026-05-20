"""
Tokens de marca Sapiens centralizados.

Fuente autoritativa: Sapiens_Brand_Kit/tokens/sapiens_tokens_light.json
Sapiens es light-first. Usa teal #2B9E8F como color primario.
"""


# --- Colores (hex para CustomTkinter, RGB tuples para FPDF2) ---

COLORS = {
    "primary":       "#2B9E8F",
    "primary_dark":  "#1E7A6D",
    "primary_light": "#E6F5F2",
    "secondary":     "#E8A838",
    "secondary_dark": "#B07A10",
    "secondary_light": "#FFF5E0",
    "bg_base":       "#FAFAF7",
    "bg_surface":    "#FFFFFF",
    "bg_alt":        "#F5F0EB",
    "border":        "#E0DCD6",
    "border_subtle": "#EDEBE7",
    "border_strong": "#C8C4BE",
    "text_primary":  "#1A1C23",
    "text_secondary": "#6B6B6B",
    "text_tertiary": "#9A9A9A",
    "text_disabled": "#BEBEBE",
    "success":       "#34A853",
    "success_bg":    "#E8F5E9",
    "error":         "#E85D5D",
    "error_bg":      "#FDECEC",
    "warning":       "#E8A838",
    "warning_bg":    "#FFF5E0",
    "info":          "#4A9FD9",
    "info_bg":       "#E8F2FA",
}


def hex_to_rgb(hex_color: str) -> tuple:
    """Convierte '#RRGGBB' a (R, G, B)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# Tuplas RGB para uso directo en FPDF2
RGB = {k: hex_to_rgb(v) for k, v in COLORS.items()}


# --- Tipografía ---

FONTS = {
    "heading":  "Outfit",
    "body":     "Instrument Sans",
    "mono":     "Geist Mono",
    "label":    "Jura",
}

FONT_SIZE = {
    "display": 52,
    "h1":      40,
    "h2":      30,
    "h3":      22,
    "body_lg": 18,
    "body":    16,
    "body_sm": 14,
    "caption": 12,
    "label":   11,
}

FONT_WEIGHT = {
    "regular":  400,
    "medium":   500,
    "semibold": 600,
    "bold":     700,
}


# --- Espaciado y radios ---

SPACING = {
    "xs":  4,
    "sm":  8,
    "md":  16,
    "lg":  24,
    "xl":  32,
    "2xl": 48,
    "3xl": 64,
    "4xl": 96,
}

RADIUS = {
    "sm":   6,
    "md":   10,
    "lg":   14,
    "xl":   20,
    "full": 9999,
}


# --- PDF específicos ---

PDF_COLORS = {
    "title":          RGB["primary"],
    "section_header": RGB["primary_dark"],
    "body_text":      RGB["text_primary"],
    "secondary_text": RGB["text_secondary"],
    "footer_text":    RGB["text_secondary"],
    "accent_line":    RGB["primary"],
    "border":         RGB["border"],
}
