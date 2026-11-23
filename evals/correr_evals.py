"""Corre los 15 casos de evals/casos.json contra root_agent y guarda tokens, latencia y agentes.

Uso:
  python evals/correr_evals.py --corrida 1
  python evals/correr_evals.py --corrida 2      # después de UN cambio (anotarlo en CHANGELOG)
  python evals/correr_evals.py --corrida 1 --casos C01 C13

Salida: evals/resultados/corrida_<n>.csv y corrida_<n>_respuestas.json.
La columna 'acerto' se llena A MANO (o con un juez) comparando con respuesta_esperada.

Las herramientas con require_confirmation pausan la ejecución: aquí sólo se registra que se pidió
la aprobación (pidio_aprobacion=True); no se aprueba automáticamente.
"""

import argparse
import asyncio
import csv
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from mexico_vivo.agent import root_agent  # noqa: E402

RESULTADOS = RAIZ / "evals" / "resultados"


async def correr_caso(runner: InMemoryRunner, caso: dict) -> dict:
    sesion = await runner.session_service.create_session(app_name=runner.app_name, user_id="eval")
    msg = types.Content(role="user", parts=[types.Part(text=caso["tarea"])])
    t0 = time.perf_counter()
    tokens_in = tokens_out = 0
    agentes, herramientas, texto_final = [], [], ""
    pidio_aprobacion = False
    async for ev in runner.run_async(user_id="eval", session_id=sesion.id, new_message=msg):
        if ev.author and ev.author != "user" and ev.author not in agentes:
            agentes.append(ev.author)
        if ev.usage_metadata:
            tokens_in += ev.usage_metadata.prompt_token_count or 0
            tokens_out += ev.usage_metadata.candidates_token_count or 0
        for fc in ev.get_function_calls():
            herramientas.append(fc.name)
            if fc.name == "adk_request_confirmation":
                pidio_aprobacion = True
        if ev.content and ev.content.parts:
            texto = "".join(p.text or "" for p in ev.content.parts)
            if texto.strip():
                texto_final = texto
    return {
        "id": caso["id"], "dificil": caso["dificil"], "categoria": caso["categoria"],
        "latencia_s": round(time.perf_counter() - t0, 2),
        "tokens_entrada": tokens_in, "tokens_salida": tokens_out,
        "agentes": "|".join(agentes), "herramientas": "|".join(herramientas),
        "pidio_aprobacion": pidio_aprobacion,
        "agentes_esperados_ok": set(caso["agentes_esperados"]) <= set(agentes),
        "acerto": "",  # llenar a mano
        "respuesta": texto_final,
    }


async def main(corrida: int, ids: list[str] | None) -> None:
    casos = json.loads((RAIZ / "evals" / "casos.json").read_text())
    if ids:
        casos = [c for c in casos if c["id"] in ids]
    runner = InMemoryRunner(agent=root_agent, app_name="mexico_vivo")
    filas = []
    for caso in casos:
        print(f"▶ {caso['id']} …", flush=True)
        try:
            filas.append(await correr_caso(runner, caso))
        except Exception as e:  # un caso que truena no detiene la corrida
            filas.append({"id": caso["id"], "error": repr(e)})
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / f"corrida_{corrida}_respuestas.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=2))
    columnas = sorted({k for f in filas for k in f if k != "respuesta"})
    with open(RESULTADOS / f"corrida_{corrida}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"✅ evals/resultados/corrida_{corrida}.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--corrida", type=int, required=True)
    ap.add_argument("--casos", nargs="*")
    a = ap.parse_args()
    asyncio.run(main(a.corrida, a.casos))
