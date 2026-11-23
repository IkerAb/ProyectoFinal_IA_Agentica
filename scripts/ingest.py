"""Indexa PDFs en ChromaDB para el RAG.

Uso:
  python scripts/ingest.py centros_amigables datos/documentos/centros_amigables/
  python scripts/ingest.py programas         datos/documentos/programas/

Cada fragmento guarda metadatos: archivo, pagina (y 'estado' si lo pueden detectar, para filtrar).
Pueden reemplazarlo por el ingest.py de su Lab 6 manteniendo los nombres de colección.

TODO (Meyer): para el Directorio de Centros Amigables, detectar el estado de cada página y
guardarlo en el metadato 'estado' (permite filtrar en buscar_centros_amigables).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from mexico_vivo.tools.rag import _cliente, embed  # noqa: E402

TAM, SOLAPE = 1200, 200  # caracteres


def trocear(texto: str) -> list[str]:
    return [texto[i:i + TAM] for i in range(0, max(len(texto), 1), TAM - SOLAPE) if texto[i:i + TAM].strip()]


def main(coleccion: str, carpeta: Path) -> None:
    import pymupdf4llm

    col = _cliente().get_or_create_collection(coleccion, metadata={"hnsw:space": "cosine"})
    for pdf in sorted(carpeta.glob("*.pdf")):
        paginas = pymupdf4llm.to_markdown(str(pdf), page_chunks=True)
        ids, docs, metas = [], [], []
        for p in paginas:
            num = p["metadata"]["page"] if "page" in p["metadata"] else p["metadata"].get("page_number")
            for j, trozo in enumerate(trocear(p["text"])):
                ids.append(f"{pdf.stem}-p{num}-{j}")
                docs.append(trozo)
                metas.append({"archivo": pdf.name, "pagina": num})
        for i in range(0, len(docs), 64):
            col.upsert(ids=ids[i:i + 64], documents=docs[i:i + 64], metadatas=metas[i:i + 64],
                       embeddings=embed(docs[i:i + 64], es_consulta=False))
        print(f"  {pdf.name}: {len(docs)} fragmentos")
    print(f"✅ colección '{coleccion}': {col.count()} fragmentos")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
