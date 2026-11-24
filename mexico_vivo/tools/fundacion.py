"""Herramientas del EXPERTO DE LA FUNDACIÓN (dueño: Iker).

Dos fuentes, con papeles distintos:
  - Conocimiento DOCUMENTAL (RAG + catálogo verificado en datos/fundacion/): qué es cada programa,
    a quién atiende, por qué canales. Fuente oficial, con URL.
  - Información OPERATIVA (SQL sobre datos/fundacion.db): presupuesto, personal, inventario,
    capacidad, costos e historial. Hoy es un escenario SIMULADO (no hay datos públicos); cada
    respuesta lo etiqueta con 'origen'.

Regla dura (también en código): si un dato no existe, se responde INFORMACIÓN NO DISPONIBLE.
Los cálculos (costos, personal, capacidad) se hacen aquí en Python, no los estima el LLM.
"""

import json
import math
import re
import unicodedata
from datetime import date, timedelta
from functools import lru_cache

from ..config import FECHA_HOY, FUNDACION_DOCS
from ..db import consultar
from .rag import RagNoDisponible, buscar

NO_DISP = "INFORMACIÓN NO DISPONIBLE"
ORIGEN_SIM = "SIMULADO (escenario sintético acordado en la propuesta; no son datos reales de México Vivo)"
POBLACION_JUVENIL = ("juventud", "jovenes", "adolescentes")
CAMPOS_NO_DOCUMENTADOS = ("requirements", "resource_needs", "coverage_capacity", "costs",
                          "geographic_coverage")


# ================================================================ utilidades internas
@lru_cache(maxsize=1)
def _catalogo() -> dict[str, dict]:
    datos = json.loads((FUNDACION_DOCS / "programas.json").read_text(encoding="utf-8"))
    return {p["program_id"]: p for p in datos}


@lru_cache(maxsize=1)
def _hechos() -> list[dict]:
    return json.loads((FUNDACION_DOCS / "hechos_institucionales_2023.json").read_text(encoding="utf-8"))


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _programa_o_error(program_id: str) -> tuple[dict | None, dict | None]:
    prog = _catalogo().get(program_id)
    if prog is None:
        return None, {"status": "error",
                      "mensaje": f"No existe el programa {program_id!r} en el catálogo verificado.",
                      "programas_validos": sorted(_catalogo())}
    return prog, None


def _parametros(program_id: str) -> dict | None:
    filas = consultar("SELECT * FROM parametros_operativos WHERE program_id = ?", (program_id,))
    return filas[0] if filas else None


def _presupuesto(program_id: str) -> dict | None:
    filas = consultar(
        "SELECT periodo, asignado, ejercido, asignado - ejercido AS restante FROM presupuesto "
        "WHERE program_id = ? ORDER BY periodo DESC LIMIT 1", (program_id,))
    return filas[0] if filas else None


def _personal(program_id: str, estado: str) -> list[dict]:
    return consultar(
        """SELECT persona_id, rol, estado_base, disponible_desde FROM personal
           WHERE (',' || programas || ',') LIKE ? AND disponible_desde <= ?
             AND (? = '' OR estado_base = ?)""",
        (f"%,{program_id},%", FECHA_HOY, estado, estado))


def _inventario(program_id: str) -> list[dict]:
    return consultar("SELECT material, cantidad, minimo_por_escuela, almacen FROM inventario "
                     "WHERE program_id = ?", (program_id,))


def _costo(par: dict, n_escuelas: int, n_alumnos: int) -> dict:
    por_escuelas = n_escuelas * (par["costo_por_escuela"] + par["viaticos_por_escuela"])
    por_alumnos = n_alumnos * par["costo_por_alumno"]
    meses = math.ceil(n_escuelas / par["capacidad_escuelas_mes"])
    facilitadores = math.ceil(n_escuelas / (par["escuelas_por_facilitador_mes"] * meses))
    return {"total_mxn": round(por_escuelas + por_alumnos, 2),
            "desglose": {"escuelas_mxn": round(n_escuelas * par["costo_por_escuela"], 2),
                         "viaticos_mxn": round(n_escuelas * par["viaticos_por_escuela"], 2),
                         "alumnos_mxn": round(por_alumnos, 2)},
            "meses_necesarios": meses, "facilitadores_necesarios": facilitadores}


def _evaluar(program_id: str, n_escuelas: int, n_alumnos: int, escuelas_con_internet: int,
             estado: str, plazo_meses: int) -> dict:
    """Corre todos los chequeos para un tamaño de intervención. Sin LLM: reglas explícitas."""
    checks: list[dict] = []
    add = lambda recurso, resultado, detalle: checks.append(  # noqa: E731
        {"recurso": recurso, "resultado": resultado, "detalle": detalle})

    par = _parametros(program_id)
    if par is None:
        for r in ("presupuesto", "personal", "capacidad", "materiales", "infraestructura"):
            add(r, NO_DISP, "El programa no tiene parámetros operativos registrados.")
        return {"viable": "INDETERMINADO", "checks": checks, "costo": None}

    costo = _costo(par, n_escuelas, n_alumnos)

    pres = _presupuesto(program_id)
    if pres is None:
        add("presupuesto", NO_DISP, "Sin presupuesto registrado.")
    else:
        ok = pres["restante"] >= costo["total_mxn"]
        add("presupuesto", "OK" if ok else "FALLA",
            f"Costo {costo['total_mxn']:,.0f} vs restante {pres['restante']:,.0f} MXN ({pres['periodo']}).")

    gente = _personal(program_id, estado)
    total = len(_personal(program_id, "")) if estado else len(gente)
    ok = len(gente) >= costo["facilitadores_necesarios"]
    nota = f" (hay {total} en todo el país)" if estado and not ok and total else ""
    add("personal", "OK" if ok else "FALLA",
        f"Necesarios {costo['facilitadores_necesarios']}, disponibles {len(gente)}"
        f"{' en ' + estado if estado else ''}{nota}.")

    ok = costo["meses_necesarios"] <= plazo_meses
    add("capacidad", "OK" if ok else "FALLA",
        f"{n_escuelas} escuelas a {par['capacidad_escuelas_mes']}/mes = {costo['meses_necesarios']} "
        f"mes(es); plazo {plazo_meses}.")

    inv = _inventario(program_id)
    if not inv:
        add("materiales", NO_DISP, "Sin inventario registrado.")
    else:
        faltan = [f"{i['material']} (hay {i['cantidad']}, se necesitan {i['minimo_por_escuela'] * n_escuelas})"
                  for i in inv if i["cantidad"] < i["minimo_por_escuela"] * n_escuelas]
        add("materiales", "FALLA" if faltan else "OK",
            "Faltan: " + "; ".join(faltan) if faltan else "Inventario suficiente.")

    if not par["requiere_internet"]:
        add("infraestructura", "OK", "El programa no requiere internet en la escuela.")
    elif escuelas_con_internet < 0:
        add("infraestructura", "PENDIENTE", "Requiere internet y no se informó cuántas escuelas lo tienen.")
    else:
        ok = escuelas_con_internet >= n_escuelas
        add("infraestructura", "OK" if ok else "FALLA",
            f"Requiere internet: {escuelas_con_internet} de {n_escuelas} escuelas lo tienen.")

    resultados = {c["resultado"] for c in checks}
    viable = "NO" if "FALLA" in resultados else (
        "INDETERMINADO" if resultados & {NO_DISP, "PENDIENTE"} else "SI")
    return {"viable": viable, "checks": checks, "costo": costo}


# ================================================================ herramientas
def search_programs(necesidad: str, k: int = 3) -> dict:
    """Busca en la documentación oficial (RAG) los programas de México Vivo que atienden una necesidad.

    Úsala al inicio para identificar programas candidatos. Regresa descripciones documentales,
    NO información de recursos.

    Args:
        necesidad: La necesidad de la comunidad en lenguaje natural, p. ej.
            "educación sexual en secundarias con participación de docentes".
        k: Cuántos programas regresar (máximo 6).

    Returns:
        dict con 'programas': program_id, nombre, fragmento relevante y fuente (URL).
    """
    k = max(1, min(int(k), 6))
    try:
        hits = buscar("programas", necesidad, k=8)
        modo = "rag_embeddings"
        vistos, programas = set(), []
        for h in hits:
            pid = h.get("program_id")
            if pid in vistos or pid not in _catalogo():
                continue
            vistos.add(pid)
            programas.append({"program_id": pid, "nombre": _catalogo()[pid]["name"],
                              "fragmento": h["texto"][:500], "distancia": h["distancia"]})
    except RagNoDisponible as e:
        # Respaldo léxico para que el agente funcione antes de indexar (se reporta en 'modo').
        modo = f"respaldo_lexico ({e})"
        palabras = {w for w in re.findall(r"\w{4,}", _norm(necesidad))}
        puntaje = []
        for pid, p in _catalogo().items():
            texto = _norm(" ".join([p["name"], p["description"], *(p.get("objectives") or []),
                                    *(p.get("target_population") or []), *(p.get("delivery_channels") or [])]))
            puntaje.append((sum(w in texto for w in palabras), pid))
        programas = [{"program_id": pid, "nombre": _catalogo()[pid]["name"],
                      "fragmento": _catalogo()[pid]["description"], "coincidencias": s}
                     for s, pid in sorted(puntaje, reverse=True) if s > 0]
    for p in programas:
        p["fuente"] = _catalogo()[p["program_id"]]["sources"][0]["url"]
    return {"status": "ok" if programas else "vacio", "modo": modo, "programas": programas[:k]}


def get_program_details(program_id: str) -> dict:
    """Ficha documental completa de un programa: descripción, objetivos, población, canales y fuentes.

    Los campos que la fuente oficial no documenta (requisitos, costos, capacidad, cobertura)
    vienen como INFORMACIÓN NO DISPONIBLE. También incluye cifras institucionales 2023 atribuidas
    a ese programa (sólo como evidencia histórica, no como disponibilidad actual).

    Args:
        program_id: p. ej. "generacion_viva", "paress", "assi_vivo", "hablemos_de_sexo_y_amor",
            "empresa_viva", "incidencias".
    """
    prog, err = _programa_o_error(program_id)
    if err:
        return err
    ficha = {k: v for k, v in prog.items() if k not in CAMPOS_NO_DOCUMENTADOS}
    for campo in CAMPOS_NO_DOCUMENTADOS:
        ficha[campo] = prog.get(campo) if prog.get(campo) not in (None, [], "") else NO_DISP
    if not prog.get("objectives"):
        ficha["objectives"] = NO_DISP
    if not prog.get("target_population"):
        ficha["target_population"] = NO_DISP
    ficha["hechos_2023"] = [h["statement"] for h in _hechos()
                            if _norm(prog["name"]) in _norm(h.get("scope", ""))] or NO_DISP
    par = _parametros(program_id)
    ficha["parametros_operativos"] = ({**par, "origen": ORIGEN_SIM} if par else NO_DISP)
    return {"status": "ok", "programa": ficha}


def get_available_resources(program_id: str, estado: str = "") -> dict:
    """Recursos operativos de un programa: presupuesto restante, personal disponible e inventario.

    Úsala SIEMPRE antes de aprobar. Los datos son un escenario SIMULADO (ver 'origen').

    Args:
        program_id: Clave del programa.
        estado: Estado de la intervención para filtrar personal por base (vacío = todo el país).
    """
    prog, err = _programa_o_error(program_id)
    if err:
        return err
    pres = _presupuesto(program_id)
    gente = _personal(program_id, estado)
    inv = _inventario(program_id)
    return {"status": "ok", "programa": prog["name"], "origen": ORIGEN_SIM,
            "presupuesto": pres or NO_DISP,
            "personal_disponible": {"total": len(gente), "personas": gente[:15]} if gente else NO_DISP,
            "inventario": inv or NO_DISP}


def calculate_intervention_cost(program_id: str, n_escuelas: int, n_alumnos: int) -> dict:
    """Calcula el costo de una intervención con los parámetros operativos registrados.

    Fórmula: escuelas × (costo_por_escuela + viáticos) + alumnos × costo_por_alumno.
    También estima meses y facilitadores necesarios. NUNCA estimes costos sin esta herramienta.

    Args:
        program_id: Clave del programa.
        n_escuelas: Número de escuelas a atender.
        n_alumnos: Número total de alumnos de esas escuelas.
    """
    prog, err = _programa_o_error(program_id)
    if err:
        return err
    if n_escuelas < 1 or n_alumnos < 0:
        return {"status": "error", "mensaje": "n_escuelas debe ser ≥ 1 y n_alumnos ≥ 0."}
    par = _parametros(program_id)
    if par is None:
        return {"status": "no_disponible", "programa": prog["name"],
                "mensaje": f"{NO_DISP}: el programa no tiene costos registrados; solicitarlos a la fundación."}
    return {"status": "ok", "programa": prog["name"], "origen": ORIGEN_SIM,
            "parametros": {k: par[k] for k in ("costo_por_escuela", "costo_por_alumno",
                                               "viaticos_por_escuela", "capacidad_escuelas_mes",
                                               "escuelas_por_facilitador_mes")},
            **_costo(par, n_escuelas, n_alumnos)}


def check_feasibility(program_id: str, n_escuelas: int, n_alumnos: int,
                      escuelas_con_internet: int = -1, estado: str = "", plazo_meses: int = 3) -> dict:
    """Verifica si una intervención se puede ejecutar: presupuesto, personal, capacidad, materiales
    e infraestructura. Si no es viable, calcula el máximo de escuelas que SÍ se podría atender.

    Args:
        program_id: Clave del programa.
        n_escuelas: Escuelas propuestas.
        n_alumnos: Alumnos totales de esas escuelas.
        escuelas_con_internet: Cuántas de esas escuelas tienen internet (-1 = desconocido).
        estado: Estado de la intervención (para personal disponible).
        plazo_meses: Plazo máximo para ejecutarla (default 3).

    Returns:
        dict con viable ("SI" | "NO" | "INDETERMINADO"), checks por recurso y costo.
    """
    prog, err = _programa_o_error(program_id)
    if err:
        return err
    if n_escuelas < 1 or n_alumnos < 0:
        return {"status": "error", "mensaje": "n_escuelas debe ser ≥ 1 y n_alumnos ≥ 0."}
    res = _evaluar(program_id, n_escuelas, n_alumnos, escuelas_con_internet, estado, plazo_meses)
    out = {"status": "ok", "programa": prog["name"], "origen": ORIGEN_SIM, **res}
    if res["viable"] == "NO":
        alumnos_x_escuela = n_alumnos / n_escuelas
        out["max_escuelas_viables"] = next(
            (n for n in range(n_escuelas - 1, 0, -1)
             if _evaluar(program_id, n, round(alumnos_x_escuela * n),
                         min(escuelas_con_internet, n) if escuelas_con_internet >= 0 else -1,
                         estado, plazo_meses)["viable"] == "SI"), 0)
    return out


def get_intervention_history(cve_mun: str = "", program_id: str = "", meses: int = 24) -> dict:
    """Intervenciones anteriores de la fundación (para no duplicar y aprender de resultados).

    Args:
        cve_mun: Clave INEGI del municipio (vacío = todos).
        program_id: Clave del programa (vacío = todos).
        meses: Ventana hacia atrás desde hoy (default 24).
    """
    desde = (date.fromisoformat(FECHA_HOY) - timedelta(days=30 * int(meses))).isoformat()
    filas = consultar(
        """SELECT intervencion_id, cve_mun, municipio, estado, program_id, fecha_inicio,
                  escuelas_atendidas, jovenes_alcanzados, resultado
           FROM intervenciones WHERE fecha_inicio >= ?
             AND (? = '' OR cve_mun = ?) AND (? = '' OR program_id = ?)
           ORDER BY fecha_inicio DESC LIMIT 20""",
        (desde, cve_mun, cve_mun, program_id, program_id))
    return {"status": "ok" if filas else "vacio", "origen": ORIGEN_SIM,
            "intervenciones": filas or NO_DISP}


def audit_proposal(cve_mun: str, municipio: str, estado: str, program_id: str, n_escuelas: int,
                   n_alumnos: int, escuelas_con_internet: int = -1,
                   programas_gobierno: str = "") -> dict:
    """Auditoría completa de una propuesta (municipio + programa): combina ficha del programa,
    ajuste de población, historial en el municipio, duplicidad con gobierno y viabilidad.

    Úsala cuando ya tengas un programa candidato para un municipio. Si el veredicto no es
    APROBABLE, busca otro programa o reduce el alcance y vuelve a auditar.

    Args:
        cve_mun: Clave INEGI de 5 dígitos.
        municipio: Nombre del municipio.
        estado: Estado.
        program_id: Programa a auditar.
        n_escuelas: Escuelas propuestas.
        n_alumnos: Alumnos totales.
        escuelas_con_internet: Escuelas con internet (-1 = desconocido).
        programas_gobierno: Programas del gobierno ya presentes en el municipio, tal como los
            reportó el Evaluador (vacío si no reportó).

    Returns:
        dict con hallazgos, viabilidad y veredicto_preliminar:
        APROBABLE | NO_VIABLE | DUPLICADO (mismo programa en el municipio en 12 meses) |
        REQUIERE_INFORMACION.
    """
    prog, err = _programa_o_error(program_id)
    if err:
        return err
    hallazgos: list[str] = []
    duplicado = False

    poblacion = prog.get("target_population") or []
    juvenil = any(any(p in _norm(x) for p in POBLACION_JUVENIL) for x in poblacion)
    if not poblacion:
        hallazgos.append(f"Población objetivo del programa: {NO_DISP}.")
    elif not juvenil:
        hallazgos.append(f"BLOQUEANTE: {prog['name']} atiende a {poblacion}, no a adolescentes.")

    recientes = get_intervention_history(cve_mun=cve_mun, meses=12)["intervenciones"]
    if isinstance(recientes, list):
        mismas = [i for i in recientes if i["program_id"] == program_id]
        if mismas:
            duplicado = True
            hallazgos.append(f"ALERTA de duplicidad: {len(mismas)} intervención(es) de este programa "
                             f"en {municipio} en los últimos 12 meses ({mismas[0]['fecha_inicio']}).")
        canceladas = [i for i in recientes if i["resultado"] == "cancelada"]
        if canceladas:
            hallazgos.append(f"Antecedente: {len(canceladas)} intervención(es) cancelada(s) en el municipio.")

    if programas_gobierno.strip():
        hallazgos.append(f"REVISAR posible duplicidad con gobierno: {programas_gobierno.strip()}.")
    else:
        hallazgos.append("El Evaluador no reportó programas de gobierno; la duplicidad no está verificada.")

    viab = check_feasibility(program_id, n_escuelas, n_alumnos, escuelas_con_internet, estado)

    if any(h.startswith("BLOQUEANTE") for h in hallazgos) or viab["viable"] == "NO":
        veredicto = "NO_VIABLE"
    elif duplicado:
        veredicto = "DUPLICADO"
    elif viab["viable"] == "INDETERMINADO":
        veredicto = "REQUIERE_INFORMACION"
    else:
        veredicto = "APROBABLE"

    return {"status": "ok", "municipio": f"{municipio} ({cve_mun}), {estado}",
            "programa": f"{prog['name']} ({program_id})", "fuente_programa": prog["sources"][0]["url"],
            "hallazgos": hallazgos, "viabilidad": viab, "veredicto_preliminar": veredicto}
