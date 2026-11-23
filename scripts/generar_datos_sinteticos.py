"""Genera datos/fundacion.db: datos SINTÉTICOS internos de México Vivo.

Reproducible: misma semilla → misma base. Documenten aquí cualquier cambio de rangos
(la propuesta se compromete a documentar el procedimiento).

Tablas: programas, personal, presupuesto, inventario, intervenciones, contactos (vacía; la llena
el Contactador).

Uso:  python scripts/generar_datos_sinteticos.py [--semilla 42]

NOTA: los nombres/enfoques de programas están inspirados en las líneas de trabajo descritas en la
propuesta (educación sexual en escuelas, pláticas, planificación familiar, educadores pares,
apoyo en línea). TODO (Iker): ajustarlos con el reporte anual de la fundación.
"""

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "datos" / "fundacion.db"

# (id, nombre, enfoque, población, modalidad, req_internet, req_compus, costo_rango, personal, capacidad_rango)
PROGRAMAS = [
    ("P01", "Educación Sexual Integral en Escuelas", "Talleres curriculares en aula",
     "secundaria y bachillerato", "presencial", 0, 0, (18_000, 35_000), 2, (6, 12)),
    ("P02", "Pláticas para Jóvenes", "Pláticas abiertas de 2 h sobre sexualidad y prevención",
     "12 a 19 años", "presencial", 0, 0, (4_000, 9_000), 1, (15, 30)),
    ("P03", "Acceso a Planificación Familiar", "Vinculación con servicios de salud y métodos",
     "15 a 19 años", "presencial", 0, 0, (25_000, 50_000), 2, (3, 6)),
    ("P04", "Educadores Pares", "Capacitar jóvenes para que orienten a sus compañeros",
     "bachillerato", "mixta", 1, 0, (30_000, 60_000), 2, (2, 5)),
    ("P05", "Orientación en Línea", "Acompañamiento y resolución de dudas por chat/plataforma",
     "12 a 19 años", "en_linea", 1, 1, (6_000, 12_000), 1, (20, 40)),
]

ESTADOS = ["Chiapas", "Guerrero", "Oaxaca", "Puebla", "Veracruz", "Estado de México",
           "Ciudad de México", "Jalisco", "Michoacán", "Coahuila"]
ROLES = ["facilitador", "coordinador_regional", "psicologo", "trabajador_social"]
MATERIALES = ["manual_facilitador", "kit_anatomico", "folletos", "condones_demostracion",
              "tablets", "proyector"]
RESULTADOS = ["exitosa", "parcial", "cancelada"]

ESQUEMA = """
CREATE TABLE programas (programa_id TEXT PRIMARY KEY, nombre TEXT, enfoque TEXT,
  poblacion_objetivo TEXT, modalidad TEXT, requiere_internet INT, requiere_computadoras INT,
  costo_por_escuela REAL, personal_por_escuela INT, capacidad_mensual INT, activo INT);
CREATE TABLE personal (persona_id TEXT PRIMARY KEY, nombre TEXT, rol TEXT, estado_base TEXT,
  disponible_desde TEXT, programas TEXT);
CREATE TABLE presupuesto (programa_id TEXT, periodo TEXT, asignado REAL, ejercido REAL);
CREATE TABLE inventario (programa_id TEXT, material TEXT, cantidad INT, almacen TEXT);
CREATE TABLE intervenciones (intervencion_id TEXT PRIMARY KEY, cve_mun TEXT, municipio TEXT,
  estado TEXT, programa_id TEXT, fecha_inicio TEXT, escuelas_atendidas INT,
  jovenes_alcanzados INT, resultado TEXT);
CREATE TABLE contactos (contacto_id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT,
  destinatario TEXT, tipo_destinatario TEXT, cve_mun TEXT, programa_id TEXT, asunto TEXT,
  cuerpo TEXT, estatus TEXT, archivo TEXT, nota TEXT);
"""


def generar(semilla: int, municipios: list[tuple[str, str, str]]) -> None:
    rnd = random.Random(semilla)
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.unlink(missing_ok=True)
    con = sqlite3.connect(DESTINO)
    con.executescript(ESQUEMA)

    for pid, nom, enf, pob, mod, inet, comp, costo, pers, cap in PROGRAMAS:
        con.execute("INSERT INTO programas VALUES (?,?,?,?,?,?,?,?,?,?,1)",
                    (pid, nom, enf, pob, mod, inet, comp, round(rnd.uniform(*costo), -2), pers,
                     rnd.randint(*cap)))
        asignado = round(rnd.uniform(300_000, 1_500_000), -3)
        con.execute("INSERT INTO presupuesto VALUES (?,?,?,?)",
                    (pid, "2026-S2", asignado, round(asignado * rnd.uniform(0.3, 0.98), -2)))
        for mat in rnd.sample(MATERIALES, 3):
            con.execute("INSERT INTO inventario VALUES (?,?,?,?)",
                        (pid, mat, rnd.randint(0, 400), rnd.choice(["CDMX", "Oaxaca", "Tuxtla"])))

    hoy = date(2026, 11, 23)
    for i in range(1, 41):
        progs = ",".join(sorted(rnd.sample([p[0] for p in PROGRAMAS], rnd.randint(1, 3))))
        con.execute("INSERT INTO personal VALUES (?,?,?,?,?,?)",
                    (f"E{i:03d}", f"Persona {i:03d}", rnd.choice(ROLES), rnd.choice(ESTADOS),
                     (hoy + timedelta(days=rnd.randint(-60, 45))).isoformat(), progs))

    for i in range(1, 61):
        cve, mun, edo = rnd.choice(municipios)
        con.execute("INSERT INTO intervenciones VALUES (?,?,?,?,?,?,?,?,?)",
                    (f"I{i:04d}", cve, mun, edo, rnd.choice(PROGRAMAS)[0],
                     (hoy - timedelta(days=rnd.randint(30, 900))).isoformat(),
                     rnd.randint(1, 12), rnd.randint(40, 1500), rnd.choice(RESULTADOS)))
    con.commit()
    con.close()
    print(f"✅ {DESTINO.relative_to(RAIZ)} generada (semilla={semilla})")


def municipios_disponibles() -> list[tuple[str, str, str]]:
    """Usa municipios reales de publicos.db si ya existe, para que el historial cuadre."""
    pub = RAIZ / "datos" / "publicos.db"
    if pub.exists():
        con = sqlite3.connect(pub)
        filas = con.execute("SELECT cve_mun, municipio, estado FROM municipios").fetchall()
        con.close()
        if filas:
            return filas
    return [("00000", "Municipio demo", "Demo")]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=42)
    generar(ap.parse_args().semilla, municipios_disponibles())
