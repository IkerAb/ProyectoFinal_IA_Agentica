"""RAG compartido. Colecciones (ver scripts/ingest.py):

- "centros_amigables" → Directorio de Centros Amigables (PDF 172 p.)  → lo usa el EVALUADOR
- "programas"         → documentos de programas de México Vivo / reporte anual → lo usa el EXPERTO

Pueden reemplazar este archivo con su rag_core.py del Lab 6; sólo mantengan las firmas de
buscar_centros_amigables y buscar_programas para no romper los agentes.
Los imports pesados (chromadb, sentence-transformers) son perezosos para que `adk web`
cargue aunque todavía no hayan indexado nada.
"""

import os
from functools import lru_cache

from ..config import CHROMA_DIR

MODELO_EMB_LOCAL = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def _cliente():
    import chromadb
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


@lru_cache(maxsize=1)
def _embedder():
    if os.getenv("EMBEDDINGS", "local") != "local":
        raise NotImplementedError("TODO: embeddings de Gemini (ver Lab 6)")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_EMB_LOCAL)


def embed(textos: list[str], es_consulta: bool) -> list[list[float]]:
    pref = "query: " if es_consulta else "passage: "   # convención de e5
    return _embedder().encode([pref + t for t in textos], normalize_embeddings=True).tolist()


def _buscar(coleccion: str, consulta: str, k: int, filtro: dict | None = None) -> dict:
    try:
        col = _cliente().get_collection(coleccion)
    except ImportError:
        return {"status": "error", "mensaje": "Falta chromadb/sentence-transformers: uv pip install -r requirements.txt"}
    except Exception:
        return {"status": "error", "mensaje": f"La colección {coleccion!r} no existe. Corran scripts/ingest.py."}
    k = max(1, min(int(k), 8))
    r = col.query(query_embeddings=embed([consulta], True), n_results=k, where=filtro or None)
    resultados = [
        {"texto": doc, "archivo": meta.get("archivo"), "pagina": meta.get("pagina")}
        for doc, meta in zip(r["documents"][0], r["metadatas"][0])
    ]
    return {"status": "ok", "resultados": resultados}


def buscar_centros_amigables(consulta: str, estado: str = "", k: int = 5) -> dict:
    """Busca en el Directorio de Centros Amigables (servicios de salud para adolescentes del gobierno).

    Úsala para saber si un municipio YA tiene cobertura del gobierno y no duplicar esfuerzos.

    Args:
        consulta: Qué buscar, p. ej. "centro amigable en Ocosingo".
        estado: Estado para filtrar (si se indexó con metadato 'estado'). Vacío = sin filtro.
        k: Número de fragmentos (máximo 8).

    Returns:
        dict con 'resultados': texto, archivo y página. Cita como [archivo, p. N].
    """
    filtro = {"estado": estado} if estado else None
    return _buscar("centros_amigables", consulta, k, filtro)


def buscar_programas(consulta: str, k: int = 5) -> dict:
    """Busca en los documentos de programas de México Vivo (objetivos, requisitos, población).

    Args:
        consulta: Qué buscar, p. ej. "requisitos del programa de educadores pares".
        k: Número de fragmentos (máximo 8).

    Returns:
        dict con 'resultados': texto, archivo y página. Cita como [archivo, p. N].
    """
    return _buscar("programas", consulta, k)
