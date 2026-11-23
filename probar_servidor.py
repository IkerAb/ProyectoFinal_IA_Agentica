"""Se conecta a servidor_mcp.py como cualquier cliente MCP, muestra el menú y prueba una herramienta.

Uso:  python probar_servidor.py [estado]
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVIDOR = Path(__file__).resolve().parent / "servidor_mcp.py"


async def main(estado: str):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)])
    async with stdio_client(params) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            info = await sesion.initialize()
            srv = getattr(info, "server_info", None) or getattr(info, "serverInfo", None)
            print(f"✅ Conectado a '{srv.name}'\n")
            print("Menú de herramientas (lo único que ve el modelo):")
            for t in (await sesion.list_tools()).tools:
                linea = (t.description or "(sin descripción)").strip().splitlines()[0]
                esquema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None) or {}
                print(f"  • {t.name}({', '.join(esquema.get('properties', {}))})\n      {linea}")
            print(f"\nPrueba: municipios_prioritarios(estado={estado!r}, top_n=3)")
            r = await sesion.call_tool("municipios_prioritarios", {"estado": estado, "top_n": 3})
            print(r.content[0].text[:1000])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else ""))
