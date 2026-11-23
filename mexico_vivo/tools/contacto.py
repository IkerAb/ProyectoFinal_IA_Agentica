"""Herramientas del CONTACTADOR (dueño: Elías).

Las acciones que ESCRIBEN (enviar_correo, registrar_seguimiento) se registran en el agente con
FunctionTool(..., require_confirmation=True): ADK pausa y un humano aprueba o rechaza.

El envío de correo es SIMULADO: se guarda un .eml en salida/ y una fila en fundacion.db/contactos.
Si algún día se conecta un SMTP real, sólo cambia _entregar().
"""

from datetime import datetime
from email.message import EmailMessage

from ..config import SALIDA_DIR
from ..db import consultar, ejecutar

TIPOS_DESTINATARIO = {"escuela", "gobierno_municipal", "gobierno_estatal", "universidad", "centro_salud"}


def historial_contactos(cve_mun: str = "", destinatario: str = "") -> dict:
    """Contactos previos (para no escribir dos veces a la misma institución).

    Args:
        cve_mun: Clave del municipio (vacío = todos).
        destinatario: Correo del destinatario (vacío = todos).

    Returns:
        dict con los últimos 20 contactos que coinciden.
    """
    filas = consultar(
        """SELECT contacto_id, fecha, destinatario, tipo_destinatario, cve_mun, asunto, estatus
           FROM contactos WHERE (? = '' OR cve_mun = ?) AND (? = '' OR destinatario = ?)
           ORDER BY fecha DESC LIMIT 20""",
        (cve_mun, cve_mun, destinatario, destinatario))
    return {"status": "ok" if filas else "vacio", "contactos": filas}


def _entregar(msg: EmailMessage) -> str:
    SALIDA_DIR.mkdir(exist_ok=True)
    ruta = SALIDA_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{msg['To'].replace('@', '_at_')}.eml"
    ruta.write_bytes(bytes(msg))
    return str(ruta.name)


def enviar_correo(destinatario: str, tipo_destinatario: str, cve_mun: str,
                  asunto: str, cuerpo: str, programa_id: str) -> dict:
    """Envía el correo de primer contacto y lo registra. REQUIERE APROBACIÓN HUMANA.

    Args:
        destinatario: Correo electrónico del destinatario.
        tipo_destinatario: escuela | gobierno_municipal | gobierno_estatal | universidad | centro_salud.
        cve_mun: Clave del municipio al que corresponde el contacto.
        asunto: Asunto del correo.
        cuerpo: Texto completo del correo.
        programa_id: Programa que se ofrece, p. ej. "P01".

    Returns:
        dict con status y contacto_id.
    """
    if tipo_destinatario not in TIPOS_DESTINATARIO:
        return {"status": "error", "mensaje": f"tipo_destinatario inválido; usa uno de {sorted(TIPOS_DESTINATARIO)}"}
    if "@" not in destinatario:
        return {"status": "error", "mensaje": "destinatario no es un correo válido"}
    # TODO (Elías): validar que el destinatario venga de los datos (escuelas/directorio), no inventado.

    msg = EmailMessage()
    msg["From"] = "contacto@mexicovivo.example"   # dominio de ejemplo: el envío es simulado
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.set_content(cuerpo)
    archivo = _entregar(msg)

    contacto_id = ejecutar(
        """INSERT INTO contactos (fecha, destinatario, tipo_destinatario, cve_mun, programa_id,
                                  asunto, cuerpo, estatus, archivo)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'enviado', ?)""",
        (datetime.now().isoformat(timespec="seconds"), destinatario, tipo_destinatario, cve_mun,
         programa_id, asunto, cuerpo, archivo))
    return {"status": "ok", "contacto_id": contacto_id, "archivo": archivo}


def registrar_seguimiento(contacto_id: int, estatus: str, nota: str) -> dict:
    """Actualiza el estatus de un contacto (respondió, sin respuesta, rechazó). REQUIERE APROBACIÓN.

    Args:
        contacto_id: Id del contacto.
        estatus: "respondio" | "sin_respuesta" | "rechazo" | "agendado".
        nota: Nota breve del seguimiento.
    """
    if estatus not in {"respondio", "sin_respuesta", "rechazo", "agendado"}:
        return {"status": "error", "mensaje": "estatus inválido"}
    n = ejecutar("UPDATE contactos SET estatus = ?, nota = ? WHERE contacto_id = ?",
                 (estatus, nota, contacto_id))
    return {"status": "ok" if n else "error", "filas": n}
