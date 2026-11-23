"""Herramientas del EVALUADOR (dueño: Meyer) sobre datos públicos.

Fuente: datos/publicos.db, construida por scripts/preparar_datos_publicos.py a partir de
  - CONAPO: tasa específica de fecundidad adolescente por municipio 2023
  - CONAPO: índice de marginación municipal
  - SEP: catálogo de centros de trabajo (escuelas, con internet/computadoras)

Estas funciones se registran en servidor_mcp.py y el Evaluador las consume por MCP.
Reglas: herramientas específicas (no SQL libre), regresar poco (top N, columnas útiles).
"""

from ..db import consultar


def municipios_prioritarios(estado: str = "", top_n: int = 10) -> dict:
    """Lista los municipios con mayor tasa de fecundidad adolescente, con su marginación.

    Úsala para encontrar candidatos de intervención. Filtra por estado si el usuario lo pide.

    Args:
        estado: Nombre del estado (p. ej. "Chiapas"). Vacío = todo el país.
        top_n: Cuántos municipios regresar (máximo 25).

    Returns:
        dict con 'municipios': cve_mun, municipio, estado, tef_adolescente, grado_marginacion.
    """
    top_n = max(1, min(int(top_n), 25))
    sql = """SELECT cve_mun, municipio, estado, poblacion_15_19, tef_adolescente,
                    indice_marginacion, grado_marginacion
             FROM municipios
             WHERE (? = '' OR estado LIKE ?)
             ORDER BY tef_adolescente DESC LIMIT ?"""
    filas = consultar(sql, (estado, f"%{estado}%", top_n), base="publicos")
    if not filas:
        return {"status": "vacio", "mensaje": f"No hay municipios para estado={estado!r}."}
    return {"status": "ok", "municipios": filas}


def perfil_municipio(cve_mun: str) -> dict:
    """Ficha de un municipio: fecundidad adolescente, marginación y resumen de sus escuelas.

    Args:
        cve_mun: Clave INEGI de 5 dígitos (entidad + municipio), p. ej. "07089".

    Returns:
        dict con los indicadores del municipio y conteos de escuelas por nivel y conectividad.
    """
    mun = consultar("SELECT * FROM municipios WHERE cve_mun = ?", (cve_mun,), base="publicos")
    if not mun:
        return {"status": "error", "mensaje": f"No existe el municipio {cve_mun!r}."}
    escuelas = consultar(
        """SELECT nivel, COUNT(*) AS escuelas, SUM(alumnos) AS alumnos,
                  SUM(tiene_internet) AS con_internet, SUM(tiene_computadoras) AS con_computadoras
           FROM escuelas WHERE cve_mun = ? GROUP BY nivel""",
        (cve_mun,), base="publicos",
    )
    return {"status": "ok", "municipio": mun[0], "escuelas_por_nivel": escuelas}


def escuelas_municipio(cve_mun: str, nivel: str = "secundaria", limite: int = 15) -> dict:
    """Escuelas de un municipio con sus características (para decidir programa y canal de contacto).

    Args:
        cve_mun: Clave INEGI de 5 dígitos.
        nivel: "secundaria", "bachillerato" o "" para todos.
        limite: Máximo de escuelas a regresar (máximo 30).

    Returns:
        dict con 'escuelas': cct, nombre, nivel, sostenimiento, alumnos, tiene_internet,
        tiene_computadoras, email, telefono.
    """
    limite = max(1, min(int(limite), 30))
    filas = consultar(
        """SELECT cct, nombre, nivel, sostenimiento, localidad, alumnos,
                  tiene_internet, tiene_computadoras, email, telefono
           FROM escuelas WHERE cve_mun = ? AND (? = '' OR nivel = ?)
           ORDER BY alumnos DESC LIMIT ?""",
        (cve_mun, nivel, nivel, limite), base="publicos",
    )
    return {"status": "ok" if filas else "vacio", "escuelas": filas}


# TODO (Meyer): ¿más herramientas? p. ej. comparar_municipios(cves), municipios_sin_cobertura(...)
