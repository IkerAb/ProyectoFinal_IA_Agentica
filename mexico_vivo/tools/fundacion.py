"""Herramientas del EXPERTO DE LA FUNDACIÓN (dueño: Iker) sobre datos internos de México Vivo.

Fuente: datos/fundacion.db (SINTÉTICA, generada por scripts/generar_datos_sinteticos.py).
El catálogo detallado de programas (objetivos, requisitos) va por RAG: colección "programas".
"""

from ..config import FECHA_HOY
from ..db import consultar


def listar_programas() -> dict:
    """Catálogo resumido de programas de México Vivo con requisitos y capacidad.

    Úsala para saber qué programas existen antes de recomendar uno.

    Returns:
        dict con 'programas': programa_id, nombre, enfoque, modalidad, requiere_internet,
        requiere_computadoras, costo_por_escuela, personal_por_escuela, capacidad_mensual.
    """
    return {"status": "ok", "programas": consultar(
        """SELECT programa_id, nombre, enfoque, poblacion_objetivo, modalidad, requiere_internet,
                  requiere_computadoras, costo_por_escuela, personal_por_escuela, capacidad_mensual
           FROM programas WHERE activo = 1""")}


def recursos_disponibles(programa_id: str, estado: str = "") -> dict:
    """Presupuesto restante, personal disponible e inventario para un programa.

    Úsala para verificar que una intervención es viable ANTES de aprobarla.

    Args:
        programa_id: Clave del programa, p. ej. "P01".
        estado: Estado donde sería la intervención (filtra personal por base). Vacío = todos.

    Returns:
        dict con presupuesto (asignado, ejercido, restante), personal disponible e inventario.
    """
    prog = consultar("SELECT * FROM programas WHERE programa_id = ?", (programa_id,))
    if not prog:
        return {"status": "error", "mensaje": f"No existe el programa {programa_id!r}."}
    presupuesto = consultar(
        "SELECT periodo, asignado, ejercido, asignado - ejercido AS restante "
        "FROM presupuesto WHERE programa_id = ? ORDER BY periodo DESC LIMIT 1", (programa_id,))
    personal = consultar(
        """SELECT persona_id, nombre, rol, estado_base FROM personal
           WHERE programas LIKE ? AND disponible_desde <= ? AND (? = '' OR estado_base LIKE ?)
           LIMIT 15""",
        (f"%{programa_id}%", FECHA_HOY, estado, f"%{estado}%"))
    inventario = consultar(
        "SELECT material, cantidad, almacen FROM inventario WHERE programa_id = ?", (programa_id,))
    return {"status": "ok", "programa": prog[0]["nombre"],
            "presupuesto": presupuesto[0] if presupuesto else None,
            "personal_disponible": personal, "inventario": inventario}


def historial_intervenciones(cve_mun: str = "", programa_id: str = "") -> dict:
    """Intervenciones pasadas de la fundación (para no duplicar y aprender de resultados).

    Args:
        cve_mun: Clave del municipio (vacío = todos).
        programa_id: Clave del programa (vacío = todos).

    Returns:
        dict con las últimas 20 intervenciones que coinciden.
    """
    filas = consultar(
        """SELECT intervencion_id, cve_mun, municipio, estado, programa_id, fecha_inicio,
                  escuelas_atendidas, jovenes_alcanzados, resultado
           FROM intervenciones
           WHERE (? = '' OR cve_mun = ?) AND (? = '' OR programa_id = ?)
           ORDER BY fecha_inicio DESC LIMIT 20""",
        (cve_mun, cve_mun, programa_id, programa_id))
    return {"status": "ok" if filas else "vacio", "intervenciones": filas}


# TODO (Iker): ¿una herramienta que calcule el costo de un plan (escuelas × costo + viáticos)?
