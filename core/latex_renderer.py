"""
Renderizador de expresiones LaTeX a imágenes PNG usando matplotlib.

Usa el motor mathtext de matplotlib que NO requiere instalación de LaTeX
en el sistema, haciéndolo ideal para distribución como app de escritorio.
"""

import os
import tempfile
import hashlib
import matplotlib
matplotlib.use("Agg")  # Backend sin GUI
import matplotlib.pyplot as plt
from matplotlib import mathtext


# Directorio de cache para imágenes renderizadas (por sesión)
_CACHE_DIR = None


def _get_cache_dir() -> str:
    """Obtiene o crea el directorio de cache temporal."""
    global _CACHE_DIR
    if _CACHE_DIR is None or not os.path.exists(_CACHE_DIR):
        _CACHE_DIR = tempfile.mkdtemp(prefix="sapiens_latex_")
    return _CACHE_DIR


def _hash_latex(latex_str: str, fontsize: int, dpi: int) -> str:
    """Genera un hash único para cachear imágenes renderizadas."""
    key = f"{latex_str}_{fontsize}_{dpi}"
    return hashlib.md5(key.encode()).hexdigest()


def render_latex_to_image(
    latex_str: str,
    fontsize: int = 14,
    dpi: int = 150,
    text_color: str = "#1A1C23",
) -> str:
    """
    Renderiza una expresión LaTeX a un archivo PNG temporal.

    Args:
        latex_str: expresión LaTeX (sin delimitadores $)
        fontsize: tamaño de fuente en puntos
        dpi: resolución de la imagen
        text_color: color del texto en hex
    Returns:
        ruta absoluta al archivo PNG, o cadena vacía si falla
    """
    if not latex_str or not latex_str.strip():
        return ""

    cache_dir = _get_cache_dir()
    img_hash = _hash_latex(latex_str, fontsize, dpi)
    cached_path = os.path.join(cache_dir, f"{img_hash}.png")

    # Retornar cache si existe
    if os.path.exists(cached_path):
        return cached_path

    try:
        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        ax.axis("off")
        fig.patch.set_alpha(0)

        # Renderizar con mathtext (no requiere LaTeX del sistema)
        text_obj = ax.text(
            0, 0,
            f"${latex_str}$",
            fontsize=fontsize,
            color=text_color,
            transform=ax.transAxes,
            ha="left",
            va="baseline",
        )

        # Ajustar tamaño de la figura al contenido
        fig.savefig(
            cached_path,
            dpi=dpi,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.02,
        )
        plt.close(fig)

        return cached_path

    except Exception as e:
        print(f"Error renderizando LaTeX '{latex_str[:50]}...': {e}")
        plt.close("all")
        return ""


def render_latex_block(
    latex_str: str,
    fontsize: int = 16,
    dpi: int = 150,
    text_color: str = "#1A1C23",
) -> str:
    """
    Renderiza una ecuación LaTeX en bloque (más grande, centrada).

    Args:
        latex_str: expresión LaTeX (sin delimitadores $$)
        fontsize: tamaño de fuente
        dpi: resolución
        text_color: color del texto
    Returns:
        ruta al PNG o cadena vacía si falla
    """
    return render_latex_to_image(latex_str, fontsize=fontsize, dpi=dpi, text_color=text_color)


def cleanup_cache():
    """Limpia el directorio de cache de imágenes LaTeX."""
    global _CACHE_DIR
    if _CACHE_DIR and os.path.exists(_CACHE_DIR):
        import shutil
        try:
            shutil.rmtree(_CACHE_DIR)
        except Exception as e:
            print(f"Error limpiando cache LaTeX: {e}")
        _CACHE_DIR = None


def get_image_dimensions(image_path: str) -> tuple:
    """
    Obtiene las dimensiones de una imagen en píxeles.

    Args:
        image_path: ruta al archivo de imagen
    Returns:
        (ancho, alto) en píxeles, o (0, 0) si falla
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return (0, 0)
