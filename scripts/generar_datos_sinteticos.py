"""Genera datos/fundacion.db: catálogo VERIFICADO + escenario operativo SIMULADO de México Vivo.

Por qué hay datos simulados
---------------------------
El paquete verificado (datos/fundacion/README.md) documenta que NO existe información pública de
presupuesto, personal, inventario, costos, capacidad ni historial de intervenciones. La propuesta
del equipo (Entrega 1) acordó usar un escenario sintético para esas variables. Este script lo
genera con reglas explícitas y semilla fija, y marca CADA fila con origen = 'SIMULADO'.

Qué es verificado y qué es simulado
-----------------------------------
- programas            → VERIFICADO (se copia de datos/fundacion/programas.json)
- parametros_operativos, presupuesto, personal, inventario, intervenciones → SIMULADO
- contactos            → vacía (la llena el Contactador)

Cobertura deliberadamente incompleta: sólo hay escenario operativo para PROGRAMAS_CON_ESCENARIO.
ASSI Vivo, Empresa Viva e Incidencias se quedan sin datos operativos para que el Experto practique
responder "INFORMACIÓN NO DISPONIBLE" en lugar de inventar.

Uso:  python scripts/generar_datos_sinteticos.py [--semilla 42]
"""

import argparse
import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "datos" / "fundacion.db"
CATALOGO = RAIZ / "datos" / "fundacion" / "programas.json"
HOY = date(2026, 11, 23)
SIM = "SIMULADO"

# ------------------------------------------------------------------ reglas del escenario simulado
# modalidad y requiere_internet se DERIVAN de delivery_channels documentados (no son dato oficial).
# Los rangos numéricos son supuestos del equipo; cámbienlos aquí y anótenlo en CHANGELOG.md.
PROGRAMAS_CON_ESCENARIO = {
    "generacion_viva": dict(
        modalidad="presencial_escolar", requiere_internet=0,
        costo_por_escuela=(15_000, 30_000), costo_por_alumno=(40, 90), viaticos_por_escuela=(3_000, 8_000),
        escuelas_por_facilitador_mes=(2, 4), capacidad_escuelas_mes=(6, 12),
        materiales={"manual_docente": 2, "kit_taller": 1, "folletos_familias": 120},
    ),
    "paress": dict(
        modalidad="mixta_formacion_y_digital", requiere_internet=1,
        costo_por_escuela=(20_000, 40_000), costo_por_alumno=(60, 120), viaticos_por_escuela=(2_000, 6_000),
        escuelas_por_facilitador_mes=(1, 3), capacidad_escuelas_mes=(3, 6),
        materiales={"guia_agente_de_cambio": 25, "licencias_curso_digital": 40},
    ),
    "hablemos_de_sexo_y_amor": dict(
        modalidad="digital", requiere_internet=1,
        costo_por_escuela=(3_000, 7_000), costo_por_alumno=(5, 15), viaticos_por_escuela=(0, 0),
        escuelas_por_facilitador_mes=(6, 10), capacidad_escuelas_mes=(15, 30),
        materiales={"carteles_qr": 10},
    ),
}
ESTADOS = ["Chiapas", "Guerrero", "Oaxaca", "Puebla", "Veracruz", "Estado de México",
           "Ciudad de México", "Jalisco", "Michoacán", "Coahuila"]
ROLES = ["facilitador", "psicologo", "pedagogo", "coordinador_regional"]
RESULTADOS = ["concluida", "parcial", "cancelada"]

ESQUEMA = """
CREATE TABLE programas (program_id TEXT PRIMARY KEY, nombre TEXT, descripcion TEXT,
  poblacion_objetivo TEXT, canales TEXT, origen TEXT);
CREATE TABLE parametros_operativos (program_id TEXT PRIMARY KEY, modalidad TEXT,
  requiere_internet INT, costo_por_escuela REAL, costo_por_alumno REAL, viaticos_por_escuela REAL,
  escuelas_por_facilitador_mes INT, capacidad_escuelas_mes INT, origen TEXT);
CREATE TABLE presupuesto (program_id TEXT, periodo TEXT, asignado REAL, ejercido REAL, origen TEXT);
CREATE TABLE personal (persona_id TEXT PRIMARY KEY, rol TEXT, estado_base TEXT,
  disponible_desde TEXT, programas TEXT, origen TEXT);
CREATE TABLE inventario (program_id TEXT, material TEXT, cantidad INT, minimo_por_escuela INT,
  almacen TEXT, origen TEXT);
CREATE TABLE intervenciones (intervencion_id TEXT PRIMARY KEY, cve_mun TEXT, municipio TEXT,
  estado TEXT, program_id TEXT, fecha_inicio TEXT, escuelas_atendidas INT,
  jovenes_alcanzados INT, resultado TEXT, origen TEXT);
CREATE TABLE contactos (contacto_id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT,
  destinatario TEXT, tipo_destinatario TEXT, cve_mun TEXT, programa_id TEXT, asunto TEXT,
  cuerpo TEXT, estatus TEXT, archivo TEXT, nota TEXT);
"""


def municipios_disponibles() -> list[tuple[str, str, str]]:
    """Usa municipios de publicos.db si ya existe, para que el historial cuadre con el Evaluador."""
    pub = RAIZ / "datos" / "publicos.db"
    if pub.exists():
        con = sqlite3.connect(pub)
        filas = con.execute("SELECT cve_mun, municipio, estado FROM municipios").fetchall()
        con.close()
        if filas:
            return filas
    return [("00000", "Municipio demo", "Demo")]


def generar(semilla: int) -> None:
    rnd = random.Random(semilla)
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.unlink(missing_ok=True)
    con = sqlite3.connect(DESTINO)
    con.executescript(ESQUEMA)

    for p in catalogo:
        con.execute("INSERT INTO programas VALUES (?,?,?,?,?,'VERIFICADO')",
                    (p["program_id"], p["name"], p["description"],
                     json.dumps(p.get("target_population"), ensure_ascii=False),
                     json.dumps(p.get("delivery_channels"), ensure_ascii=False)))

    ids_catalogo = {p["program_id"] for p in catalogo}
    for pid, r in PROGRAMAS_CON_ESCENARIO.items():
        assert pid in ids_catalogo, f"{pid} no está en el catálogo verificado"
        u = lambda rango: round(rnd.uniform(*rango), -1)  # noqa: E731
        con.execute("INSERT INTO parametros_operativos VALUES (?,?,?,?,?,?,?,?,?)",
                    (pid, r["modalidad"], r["requiere_internet"], u(r["costo_por_escuela"]),
                     u(r["costo_por_alumno"]), u(r["viaticos_por_escuela"]),
                     rnd.randint(*r["escuelas_por_facilitador_mes"]),
                     rnd.randint(*r["capacidad_escuelas_mes"]), SIM))
        asignado = round(rnd.uniform(250_000, 1_200_000), -3)
        con.execute("INSERT INTO presupuesto VALUES (?,?,?,?,?)",
                    (pid, "2026-S2", asignado, round(asignado * rnd.uniform(0.4, 0.97), -2), SIM))
        for material, minimo in r["materiales"].items():
            # alcanza para 3-20 escuelas: intervenciones chicas pasan, las grandes pueden fallar
            con.execute("INSERT INTO inventario VALUES (?,?,?,?,?,?)",
                        (pid, material, rnd.randint(minimo * 3, minimo * 20), minimo,
                         rnd.choice(["CDMX", "Oaxaca", "Tuxtla"]), SIM))

    con_escenario = list(PROGRAMAS_CON_ESCENARIO)
    for i in range(1, 31):
        progs = ",".join(sorted(rnd.sample(con_escenario, rnd.randint(1, 2))))
        con.execute("INSERT INTO personal VALUES (?,?,?,?,?,?)",
                    (f"E{i:03d}", rnd.choice(ROLES), rnd.choice(ESTADOS),
                     (HOY + timedelta(days=rnd.randint(-90, 60))).isoformat(), progs, SIM))

    municipios = municipios_disponibles()
    for i in range(1, 41):
        cve, mun, edo = rnd.choice(municipios)
        con.execute("INSERT INTO intervenciones VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (f"I{i:04d}", cve, mun, edo, rnd.choice(con_escenario),
                     (HOY - timedelta(days=rnd.randint(20, 900))).isoformat(),
                     rnd.randint(1, 10), rnd.randint(40, 1200), rnd.choice(RESULTADOS), SIM))
    con.commit()
    con.close()
    print(f"✅ {DESTINO.relative_to(RAIZ)} (semilla={semilla}): {len(catalogo)} programas verificados, "
          f"escenario SIMULADO para {', '.join(con_escenario)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=42)
    generar(ap.parse_args().semilla)
