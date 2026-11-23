"""Servidor MCP de datos públicos (CONAPO + SEP) — lo consume el Evaluador.

Cualquier cliente MCP (el Evaluador de ADK, Claude Desktop, VS Code…) puede usarlo.
No reescribimos las herramientas: se importan de mexico_vivo/tools/datos_publicos.py.

Prueba:  python probar_servidor.py
Ojo:     un servidor stdio habla por la salida estándar; un print() rompe la conexión.
         Para depurar, impriman en sys.stderr.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mexico_vivo.tools.datos_publicos import (  # noqa: E402
    escuelas_municipio,
    municipios_prioritarios,
    perfil_municipio,
)

try:  # SDK de MCP 2.x
    from mcp.server import MCPServer as _Server
except ImportError:  # SDK de MCP 1.x
    from mcp.server.fastmcp import FastMCP as _Server

servidor = _Server(
    name="datos-publicos-mx",
    instructions=(
        "Datos públicos de México para priorizar intervenciones de salud sexual y reproductiva "
        "adolescente: tasa específica de fecundidad adolescente por municipio (CONAPO 2023), "
        "índice de marginación municipal (CONAPO) y catálogo de escuelas SEP con conectividad. "
        "Los municipios se identifican con la clave INEGI de 5 dígitos (cve_mun). "
        "Sólo lectura. Cita la fuente (CONAPO/SEP) al usar una cifra."
    ),
)

servidor.add_tool(municipios_prioritarios)
servidor.add_tool(perfil_municipio)
servidor.add_tool(escuelas_municipio)
# TODO (Meyer): registrar aquí nuevas herramientas de datos públicos.

if __name__ == "__main__":
    servidor.run()  # stdio
