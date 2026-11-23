"""Revisa que el entorno esté listo. Uso: python verificar_entorno.py [--sin-gemini]"""

import importlib
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
ok = True


def check(nombre: str, cond: bool, ayuda: str = "") -> None:
    global ok
    print(("✅ " if cond else "❌ ") + nombre + ("" if cond else f"  → {ayuda}"))
    ok &= cond


check("Python ≥ 3.10", sys.version_info >= (3, 10), "instalen Python 3.10+")
for mod in ["google.adk", "mcp", "dotenv", "chromadb", "sentence_transformers", "pymupdf4llm", "pandas"]:
    try:
        importlib.import_module(mod)
        check(f"import {mod}", True)
    except ImportError:
        check(f"import {mod}", False, "uv pip install -r requirements.txt")

env = RAIZ / "mexico_vivo" / ".env"
check("mexico_vivo/.env existe", env.exists(), "cp mexico_vivo/.env.example mexico_vivo/.env")

from mexico_vivo.config import CHROMA_DIR, FUNDACION_DB, PUBLICOS_DB  # noqa: E402

check("datos/fundacion.db", FUNDACION_DB.exists(), "python scripts/generar_datos_sinteticos.py")
check("datos/publicos.db", PUBLICOS_DB.exists(), "python scripts/preparar_datos_publicos.py [--demo]")
check("chroma_db/ (RAG)", CHROMA_DIR.exists(), "python scripts/ingest.py <coleccion> <carpeta>")

try:
    from mexico_vivo.agent import root_agent  # noqa: E402
    check(f"root_agent carga ({root_agent.name})", True)
except Exception as e:
    check("root_agent carga", False, repr(e))

if "--sin-gemini" not in sys.argv:
    try:
        from google import genai

        from mexico_vivo.config import DEFAULT_MODEL
        r = genai.Client().models.generate_content(model=DEFAULT_MODEL, contents="Responde sólo: ok")
        check(f"Gemini responde ({DEFAULT_MODEL})", bool(r.text))
    except Exception as e:
        check("Gemini responde", False, f"revisen GOOGLE_API_KEY: {e!r}"[:200])

print("\nTodo listo 🎉" if ok else "\nHay pendientes ↑")
sys.exit(0 if ok else 1)
