"""Conexión a las dos bases SQLite del proyecto.

- publicos.db  → datos públicos (CONAPO fecundidad, marginación, escuelas SEP). Sólo lectura.
- fundacion.db → datos SINTÉTICOS de México Vivo (programas, personal, presupuesto, inventario,
                 intervenciones) + la tabla `contactos` donde el Contactador registra.

Siempre usen parámetros (?) en lugar de pegar texto del usuario dentro del SQL.
"""

import sqlite3
from pathlib import Path

from .config import FUNDACION_DB, PUBLICOS_DB


def _abrir(ruta: Path, solo_lectura: bool) -> sqlite3.Connection:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No encuentro la base {ruta}. Corran `python scripts/generar_datos_sinteticos.py` "
            f"y `python scripts/preparar_datos_publicos.py` (ver README)."
        )
    uri = f"file:{ruta}?mode=ro" if solo_lectura else f"file:{ruta}"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def consultar(sql: str, params: tuple = (), base: str = "fundacion") -> list[dict]:
    """SELECT de sólo lectura. base = "fundacion" | "publicos"."""
    ruta = FUNDACION_DB if base == "fundacion" else PUBLICOS_DB
    con = _abrir(ruta, solo_lectura=True)
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def ejecutar(sql: str, params: tuple = ()) -> int:
    """INSERT/UPDATE sobre fundacion.db (la única base donde el sistema escribe)."""
    con = _abrir(FUNDACION_DB, solo_lectura=False)
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid or cur.rowcount
    finally:
        con.close()
