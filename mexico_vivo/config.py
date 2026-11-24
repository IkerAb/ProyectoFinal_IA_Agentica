"""Configuración compartida: rutas, modelos y fábrica de modelos Gemini.

Todos los agentes importan de aquí para no repetir configuración.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models.google_llm import Gemini
from google.genai import types

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
load_dotenv(AGENT_DIR / ".env")


def _ruta(var: str, default: str) -> Path:
    p = Path(os.getenv(var, default))
    return p if p.is_absolute() else PROJECT_DIR / p


FUNDACION_DB = _ruta("FUNDACION_DB", "datos/fundacion.db")
PUBLICOS_DB = _ruta("PUBLICOS_DB", "datos/publicos.db")
CHROMA_DIR = _ruta("CHROMA_DIR", "chroma_db")
FUNDACION_DOCS = PROJECT_DIR / "datos" / "fundacion"   # catálogo VERIFICADO de programas (RAG)
SALIDA_DIR = PROJECT_DIR / "salida"          # correos "enviados" (simulados)

# "Hoy" del sistema: fíjenlo para que los evals sean reproducibles.
FECHA_HOY = os.getenv("FECHA_HOY", "2026-11-23")

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-3.5-flash-lite")


def modelo(rol: str) -> Gemini:
    """Modelo para un rol (evaluador, experto, contactador). Se puede sobreescribir con MODEL_<ROL>."""
    return Gemini(
        model=os.getenv(f"MODEL_{rol.upper()}", DEFAULT_MODEL),
        # 429 = cuota por minuto, 503 = saturado → esperar y reintentar
        retry_options=types.HttpRetryOptions(
            attempts=4, initial_delay=10, max_delay=60, http_status_codes=[429, 503]
        ),
    )


CONFIG_GENERACION = types.GenerateContentConfig(temperature=0.2)
