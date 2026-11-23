"""Construye datos/publicos.db a partir de los archivos públicos descargados en datos/crudos/.

Fuentes (descárguenlas a mano a datos/crudos/; ver README):
  1. CONAPO — Tasa específica de fecundidad adolescente por municipio 2023 (Excel, ~57 MB)
  2. CONAPO — Índice de marginación municipal (CSV, datos.gob.mx)
  3. SEP    — Catálogo de centros de trabajo (CSV, datos.gob.mx)

Esquema destino (lo que esperan las herramientas del Evaluador):
  municipios(cve_mun, municipio, cve_ent, estado, poblacion_15_19, tef_adolescente,
             indice_marginacion, grado_marginacion)
  escuelas(cct, nombre, nivel, sostenimiento, cve_mun, localidad, alumnos,
           tiene_internet, tiene_computadoras, email, telefono)

Uso:
  python scripts/preparar_datos_publicos.py          # con los archivos reales
  python scripts/preparar_datos_publicos.py --demo   # base mínima FALSA para desarrollar ya

TODO (Meyer): completar cargar_reales() con los nombres de columnas reales de cada archivo.
"""

import argparse
import random
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CRUDOS = RAIZ / "datos" / "crudos"
DESTINO = RAIZ / "datos" / "publicos.db"

ESQUEMA = """
CREATE TABLE municipios (cve_mun TEXT PRIMARY KEY, municipio TEXT, cve_ent TEXT, estado TEXT,
  poblacion_15_19 INT, tef_adolescente REAL, indice_marginacion REAL, grado_marginacion TEXT);
CREATE TABLE escuelas (cct TEXT PRIMARY KEY, nombre TEXT, nivel TEXT, sostenimiento TEXT,
  cve_mun TEXT, localidad TEXT, alumnos INT, tiene_internet INT, tiene_computadoras INT,
  email TEXT, telefono TEXT);
CREATE INDEX idx_esc_mun ON escuelas(cve_mun);
"""


def crear_base() -> sqlite3.Connection:
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.unlink(missing_ok=True)
    con = sqlite3.connect(DESTINO)
    con.executescript(ESQUEMA)
    return con


def cargar_reales(con: sqlite3.Connection) -> None:
    import pandas as pd  # noqa: F401

    # TODO (Meyer): ajustar nombres de archivo y columnas.
    # fec = pd.read_excel(CRUDOS / "tef_adolescente_municipal_2023.xlsx", ...)
    # mar = pd.read_csv(CRUDOS / "imm_2020.csv", encoding="latin-1")
    # sep = pd.read_csv(CRUDOS / "catalogo_ct_sep.csv", encoding="latin-1", low_memory=False)
    #   → filtrar a secundaria/bachillerato y activos para no cargar millones de filas.
    # municipios = fec.merge(mar, on="cve_mun")  → municipios.to_sql("municipios", con, if_exists="append", index=False)
    raise NotImplementedError("Completen cargar_reales() o usen --demo mientras tanto.")


def cargar_demo(con: sqlite3.Connection, semilla: int = 7) -> None:
    """Datos FALSOS (claves y cifras inventadas) sólo para que el pipeline corra end-to-end."""
    rnd = random.Random(semilla)
    estados = {"07": "Chiapas", "12": "Guerrero", "20": "Oaxaca"}
    grados = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
    for ent, edo in estados.items():
        for m in range(1, 9):
            cve = f"{ent}{m:03d}"
            idx = round(rnd.uniform(-1.5, 2.5), 3)
            con.execute("INSERT INTO municipios VALUES (?,?,?,?,?,?,?,?)",
                        (cve, f"DEMO {edo} {m}", ent, edo, rnd.randint(800, 25_000),
                         round(rnd.uniform(40, 130), 1), idx,
                         grados[min(4, int((idx + 1.5) / 0.8))]))
            for e in range(rnd.randint(0, 6)):
                nivel = rnd.choice(["secundaria", "bachillerato"])
                inet = int(rnd.random() < 0.5)
                con.execute("INSERT INTO escuelas VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (f"DEMO{cve}{e}", f"Escuela demo {cve}-{e}", nivel,
                             rnd.choice(["publico", "privado"]), cve, f"Localidad {e}",
                             rnd.randint(60, 900), inet, int(inet and rnd.random() < 0.7),
                             f"escuela{cve}{e}@demo.example", "000-000-0000"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="base mínima falsa para desarrollo")
    args = ap.parse_args()
    con = crear_base()
    (cargar_demo if args.demo else cargar_reales)(con)
    con.commit()
    n_m = con.execute("SELECT COUNT(*) FROM municipios").fetchone()[0]
    n_e = con.execute("SELECT COUNT(*) FROM escuelas").fetchone()[0]
    con.close()
    print(f"✅ {DESTINO.relative_to(RAIZ)}: {n_m} municipios, {n_e} escuelas"
          + ("  (DEMO: datos falsos)" if args.demo else ""))
