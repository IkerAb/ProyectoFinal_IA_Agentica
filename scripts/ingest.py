"""Indexa documentos en ChromaDB para el RAG.

Uso:
  python scripts/ingest.py programas         datos/fundacion/                  # catálogo verificado (.jsonl)
  python scripts/ingest.py centros_amigables datos/documentos/centros_amigables/  # PDFs

Soporta:
  - *.pdf   → fragmentos por página; metadatos: archivo, pagina
  - *.jsonl → un fragmento por registro (catálogo de programas); metadatos: archivo, program_id, fuente

TODO (Meyer): para el Directorio de Centros Amigables, detectar el estado de cada página y
guardarlo en el metadato 'estado' (permite filtrar en buscar_centros_amigables).
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from mexico_vivo.tools.rag import _cliente, embed  # noqa: E402

TAM, SOLAPE = 1200, 200  # caracteres


def trocear(texto: str) -> list[str]:
    return [texto[i:i + TAM] for i in range(0, max(len(texto), 1), TAM - SOLAPE) if texto[i:i + TAM].strip()]


def _lista(v) -> str:
    return ", ".join(v) if v else "no documentado"


def desde_jsonl(ruta: Path):
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        p = json.loads(linea)
        texto = (f"Programa: {p['name']}\nDescripción: {p['description']}\n"
                 f"Objetivos: {_lista(p.get('objectives'))}\n"
                 f"Población objetivo: {_lista(p.get('target_population'))}\n"
                 f"Canales: {_lista(p.get('delivery_channels'))}\n"
                 f"Participan: {_lista(p.get('documented_participation'))}\n"
                 f"Detalle de fuentes: {' | '.join(s['support'] for s in p.get('sources', []))}")
        meta = {"archivo": ruta.name, "program_id": p["program_id"],
                "fuente": p["sources"][0]["url"] if p.get("sources") else ""}
        yield f"{ruta.stem}-{p['program_id']}", texto, meta


def desde_pdf(ruta: Path):
    import pymupdf4llm

    for p in pymupdf4llm.to_markdown(str(ruta), page_chunks=True):
        num = p["metadata"].get("page") or p["metadata"].get("page_number")
        for j, trozo in enumerate(trocear(p["text"])):
            yield f"{ruta.stem}-p{num}-{j}", trozo, {"archivo": ruta.name, "pagina": num}


def main(coleccion: str, carpeta: Path) -> None:
    col = _cliente().get_or_create_collection(coleccion, metadata={"hnsw:space": "cosine"})
    archivos = sorted(carpeta.glob("*.pdf")) + sorted(carpeta.glob("*.jsonl"))
    if not archivos:
        sys.exit(f"No hay .pdf ni .jsonl en {carpeta}")
    for archivo in archivos:
        fragmentos = list(desde_pdf(archivo) if archivo.suffix == ".pdf" else desde_jsonl(archivo))
        for i in range(0, len(fragmentos), 64):
            lote = fragmentos[i:i + 64]
            ids, docs, metas = zip(*lote)
            col.upsert(ids=list(ids), documents=list(docs), metadatas=list(metas),
                       embeddings=embed(list(docs), es_consulta=False))
        print(f"  {archivo.name}: {len(fragmentos)} fragmentos")
    print(f"✅ colección '{coleccion}': {col.count()} fragmentos")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
