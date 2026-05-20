import os
import sys
import ctypes
import threading
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from core.ai_agent import generate_stem_task
from core.pdf_generator import create_stem_pdf
from core.brand import COLORS, RADIUS

# ---------------------------------------------------------------------------
# Cargar fuentes Sapiens en Windows (para la UI)
# ---------------------------------------------------------------------------

_RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
_FONTS_DIR = os.path.join(_RESOURCES_DIR, "fonts")

def _load_system_fonts():
    """Registra fuentes TTF en GDI (sesión actual, sin instalación permanente)."""
    if sys.platform != "win32":
        return
    try:
        gdi32 = ctypes.windll.gdi32
        for font_file in os.listdir(_FONTS_DIR):
            if font_file.endswith(".ttf"):
                gdi32.AddFontResourceW(os.path.join(_FONTS_DIR, font_file))
    except Exception as e:
        print(f"Error registrando fuentes: {e}")

_load_system_fonts()

# Tema claro (Sapiens es light-first)
ctk.set_appearance_mode("Light")


# ---------------------------------------------------------------------------
# Constantes UI
# ---------------------------------------------------------------------------

HEADING_FONT = "Outfit"
BODY_FONT    = "Instrument Sans"

BG_BASE       = COLORS["bg_base"]
BG_SURFACE    = COLORS["bg_surface"]
BORDER        = COLORS["border"]
PRIMARY       = COLORS["primary"]
PRIMARY_DARK  = COLORS["primary_dark"]
PRIMARY_LIGHT = COLORS["primary_light"]
TEXT_PRIMARY  = COLORS["text_primary"]
TEXT_SECONDARY = COLORS["text_secondary"]
SUCCESS = COLORS["success"]
ERROR   = COLORS["error"]
INFO    = COLORS["info"]

AREA_OPTIONS = {
    "Automatico":  "auto",
    "Matematicas": "math",
    "Ciencias":    "science",
    "Ingenieria":  "engineering",
    "Humanidades": "humanities",
    "Computacion": "cs",
}


# ---------------------------------------------------------------------------
# Helper: calcular tamaño de logo preservando aspect ratio
# ---------------------------------------------------------------------------

def _logo_size(path: str, target_w: int) -> tuple:
    """Devuelve (w, h) para CTkImage preservando la proporción de la imagen."""
    try:
        with Image.open(path) as img:
            w, h = img.size
        ratio = h / w
        return target_w, max(1, int(target_w * ratio))
    except Exception:
        return target_w, int(target_w * 0.22)  # fallback seguro


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sapiens - Generador de Tareas STEM")
        self.geometry("640x800")
        self.minsize(560, 600)          # mínimo útil
        self.resizable(True, True)      # pantalla completa y redimensionable

        self.configure(fg_color=BG_BASE)

        # Icono de ventana
        icon_path = os.path.join(_RESOURCES_DIR, "sapiens_icon.png")
        if os.path.exists(icon_path):
            try:
                icon_img = Image.open(icon_path)
                self.iconphoto(False,
                    ctk.CTkImage(light_image=icon_img, size=(32, 32))._light_image)
            except Exception:
                pass

        # Permitir que la columna principal se expanda
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # fila del scroll

        # ── Header ──────────────────────────────────────────────────────────
        self.header_frame = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(15, 5))
        self.header_frame.grid_columnconfigure(0, weight=1)

        logo_path = os.path.join(_RESOURCES_DIR, "sapiens_logo.png")
        if os.path.exists(logo_path):
            lw, lh = _logo_size(logo_path, 150)
            logo_img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                size=(lw, lh),
            )
            ctk.CTkLabel(self.header_frame, image=logo_img, text="").grid(
                row=0, column=0, sticky="w")

        ctk.CTkLabel(
            self.header_frame,
            text="Generador de Tareas STEM",
            font=ctk.CTkFont(family=HEADING_FONT, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ctk.CTkLabel(
            self.header_frame,
            text="Aprende a tu medida",
            font=ctk.CTkFont(family=BODY_FONT, size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, sticky="w")

        # ── Área scrollable ──────────────────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_BASE,
            scrollbar_button_color=COLORS["border_strong"],
            scrollbar_button_hover_color=PRIMARY,
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── Formulario (dentro del scroll) ──────────────────────────────────
        self.form = ctk.CTkFrame(
            self.scroll,
            fg_color=BG_SURFACE,
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=BORDER,
        )
        self.form.grid(row=0, column=0, sticky="ew", padx=25, pady=(5, 10))
        self.form.grid_columnconfigure(0, weight=1)

        hf = ctk.CTkFont(family=HEADING_FONT, weight="bold", size=13)
        bf = ctk.CTkFont(family=BODY_FONT, size=13)
        sf = ctk.CTkFont(family=BODY_FONT, size=11)

        row = 0

        # Tema
        self._label("Tema (ej. Termodinamica, Algebra lineal):", hf, row); row += 1
        self.topic_entry = self._entry(bf, row); row += 1

        # Nivel — dropdown estricto para garantizar calibración correcta de dificultad
        self._label("Nivel educativo:", hf, row); row += 1
        self.level_var = ctk.StringVar(value="Universitario")
        self.level_menu = ctk.CTkOptionMenu(
            self.form,
            variable=self.level_var,
            values=["Primaria", "Secundaria", "Preparatoria", "Universitario", "Avanzado"],
            height=36,
            corner_radius=RADIUS["sm"],
            fg_color=BG_SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_DARK,
            dropdown_fg_color=BG_SURFACE,
            dropdown_hover_color=PRIMARY_LIGHT,
            dropdown_text_color=TEXT_PRIMARY,
            text_color=TEXT_PRIMARY,
            font=bf,
        )
        self.level_menu.grid(row=row, column=0, sticky="ew", padx=20, pady=5); row += 1

        # Área temática
        self._label("Area tematica:", hf, row); row += 1
        self.area_var = ctk.StringVar(value="Automatico")
        self.area_menu = ctk.CTkOptionMenu(
            self.form,
            variable=self.area_var,
            values=list(AREA_OPTIONS.keys()),
            height=36,
            corner_radius=RADIUS["sm"],
            fg_color=BG_SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_DARK,
            dropdown_fg_color=BG_SURFACE,
            dropdown_hover_color=PRIMARY_LIGHT,
            dropdown_text_color=TEXT_PRIMARY,
            text_color=TEXT_PRIMARY,
            font=bf,
        )
        self.area_menu.grid(row=row, column=0, sticky="ew", padx=20, pady=5); row += 1

        # Tiempo estimado
        self._label("Tiempo estimado (ej. 45 min):", hf, row); row += 1
        self.time_entry = self._entry(bf, row); row += 1

        # Comentarios
        self._label("Comentarios o condiciones extra (opcional):", hf, row); row += 1
        self.comment_entry = ctk.CTkTextbox(
            self.form,
            height=80,
            border_width=1,
            border_color=BORDER,
            fg_color=BG_SURFACE,
            text_color=TEXT_PRIMARY,
            font=bf,
            corner_radius=RADIUS["sm"],
        )
        self.comment_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5); row += 1

        # Switch: incluir clave de respuestas
        self.answer_key_var = ctk.BooleanVar(value=False)
        self.answer_key_switch = ctk.CTkSwitch(
            self.form,
            text="Incluir clave de respuestas en el PDF",
            variable=self.answer_key_var,
            font=sf,
            text_color=TEXT_SECONDARY,
            progress_color=PRIMARY,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_DARK,
        )
        self.answer_key_switch.grid(row=row, column=0, sticky="w",
                                    padx=20, pady=(12, 15)); row += 1

        # ── Botón + progreso + status (fuera del scroll) ─────────────────────
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=0)

        self.generate_btn = ctk.CTkButton(
            self,
            text="Generar Evaluacion STEM",
            command=self.start_generation,
            height=48,
            corner_radius=RADIUS["xl"],
            font=ctk.CTkFont(family=HEADING_FONT, size=15, weight="bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_DARK,
            text_color="white",
        )
        self.generate_btn.grid(row=2, column=0, sticky="ew",
                               padx=25, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(
            self,
            mode="indeterminate",
            progress_color=PRIMARY,
            fg_color=BORDER,
            height=4,
            corner_radius=2,
        )
        # Se muestra dinámicamente durante la generación

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family=BODY_FONT, size=12),
        )
        self.status_label.grid(row=4, column=0, pady=(0, 12))

    # ── Helpers de UI ────────────────────────────────────────────────────────

    def _label(self, text: str, font, row: int):
        ctk.CTkLabel(
            self.form,
            text=text,
            text_color=TEXT_PRIMARY,
            font=font,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=20, pady=(12, 0))

    def _entry(self, font, row: int, placeholder: str = "") -> ctk.CTkEntry:
        entry = ctk.CTkEntry(
            self.form,
            height=36,
            border_color=BORDER,
            fg_color=BG_SURFACE,
            text_color=TEXT_PRIMARY,
            font=font,
            corner_radius=RADIUS["sm"],
            placeholder_text=placeholder,
            placeholder_text_color=COLORS["text_tertiary"],
        )
        entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)
        return entry

    def _update_status(self, text: str, color: str = TEXT_SECONDARY):
        self.status_label.configure(text=text, text_color=color)

    # ── Lógica de generación ──────────────────────────────────────────────────

    def start_generation(self):
        topic    = self.topic_entry.get().strip()
        level    = self.level_var.get().strip()
        time_est = self.time_entry.get().strip()
        comments = self.comment_entry.get("1.0", "end-1c").strip()
        area     = AREA_OPTIONS.get(self.area_var.get(), "auto")
        include_answers = self.answer_key_var.get()

        # Leer GROQ_API_KEY desde variable de entorno o .env local
        groq_key = os.environ.get("GROQ_API_KEY", "")
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    key, _, val = line.strip().partition("=")
                    if key == "GROQ_API_KEY" and not groq_key:
                        groq_key = val.strip().strip('"').strip("'")

        if not groq_key:
            messagebox.showerror(
                "API Key requerida",
                "Configura GROQ_API_KEY en el archivo .env\n\n"
                "Obtén tu clave gratuita en: console.groq.com",
            )
            return

        if not topic or not level:
            messagebox.showerror("Error", "Tema y Nivel son obligatorios.")
            return

        logo = os.path.join(_RESOURCES_DIR, "sapiens_logo.png")
        self.generate_btn.configure(state="disabled", text="Generando...")
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=25, pady=2)
        self.progress_bar.start()
        self._update_status("Iniciando generacion...", INFO)

        threading.Thread(
            target=self.run_generation,
            args=(topic, level, time_est, groq_key, logo, comments, area, include_answers),
            daemon=True,
        ).start()

    def run_generation(self, topic, level, time_est, groq_key, logo, comments, area, include_answers):
        try:
            task_data = generate_stem_task(
                topic=topic,
                level=level,
                time_estimate=time_est,
                groq_api_key=groq_key,
                comments=comments,
                subject_area_override=area,
                status_callback=lambda msg: self._update_status(msg, INFO),
            )

            self._update_status("Creando PDF con identidad Sapiens...", INFO)

            safe_topic = "".join(c for c in topic if c.isalnum() or c == " ").rstrip()
            safe_topic = safe_topic.replace(" ", "_")[:30]
            output_filename = f"Tarea_{safe_topic}.pdf"

            target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
            os.makedirs(target_dir, exist_ok=True)
            output_path = os.path.join(target_dir, output_filename)

            create_stem_pdf(task_data, logo, output_path, include_answer_key=include_answers)

            self._update_status("PDF generado exitosamente", SUCCESS)
            messagebox.showinfo(
                "Completado",
                f"El PDF se ha generado correctamente en:\n{output_path}",
            )

        except RuntimeError as e:
            # Errores críticos con mensaje amigable (ej. cuota diaria agotada)
            self._update_status("Error al generar.", ERROR)
            messagebox.showerror("Error de API", str(e))
            print(f"Error crítico: {e}")
        except Exception as e:
            self._update_status("Error durante la generacion.", ERROR)
            messagebox.showerror("Error", f"Ocurrio un error: {e}")
            print(f"Error: {e}")
        finally:
            self.generate_btn.configure(state="normal", text="Generar Evaluacion STEM")
            self.progress_bar.stop()
            self.progress_bar.grid_forget()


if __name__ == "__main__":
    app = App()
    app.mainloop()
