"""RAG compartido sobre ChromaDB. Colecciones (ver scripts/ingest.py):

- "centros_amigables" → Directorio de Centros Amigables (PDF 172 p.)        → EVALUADOR
- "programas"         → catálogo verificado datos/fundacion/programas.jsonl  → EXPERTO
                        (la herramienta del Experto es search_programs, en tools/fundacion.py)

Los imports pesados (chromadb, sentence-transformers) son perezosos para que `adk web`
cargue aunque todavía no hayan indexado nada.
"""

import os
from functools import lru_cache

from ..config import CHROMA_DIR

MODELO_EMB_LOCAL = "intfloat/multilingual-e5-small"


class RagNoDisponible(Exception):
    """Faltan dependencias o la colección no está indexada."""


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


def buscar(coleccion: str, consulta: str, k: int = 5, filtro: dict | None = None) -> list[dict]:
    """Regresa [{texto, distancia, **metadatos}]. Lanza RagNoDisponible si no se puede buscar."""
    try:
        col = _cliente().get_collection(coleccion)
    except ImportError as e:
        raise RagNoDisponible("faltan chromadb/sentence-transformers (uv pip install -r requirements.txt)") from e
    except Exception as e:
        raise RagNoDisponible(f"la colección {coleccion!r} no existe; corran scripts/ingest.py") from e
    k = max(1, min(int(k), 8))
    r = col.query(query_embeddings=embed([consulta], True), n_results=k, where=filtro or None)
    return [{"texto": doc, "distancia": round(dist, 3), **meta}
            for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])]


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
    try:
        res = buscar("centros_amigables", consulta, k, {"estado": estado} if estado else None)
    except RagNoDisponible as e:
        return {"status": "error", "mensaje": str(e)}
    return {"status": "ok", "resultados": res}
