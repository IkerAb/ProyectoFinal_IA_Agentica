"""Orquestación del sistema de México Vivo (root_agent para `adk web`).

Patrón: SequentialAgent [ LoopAgent(evaluador → experto) , contactador ]

    usuario ─▶ ┌─────────── revision (LoopAgent, máx 3) ───────────┐ ─▶ contactador ─▶ 👤 aprueba envío
               │ evaluador ──state["candidatos"]──▶ experto        │
               │     ▲                                  │          │
               │     └──state["revision_experto"]───────┘          │
               │        (rechazo → otra vuelta; aprobado → exit_loop)
               └───────────────────────────────────────────────────┘

Por qué este patrón (justificarlo en el reporte):
  - Contextos separados: datos nacionales (Evaluador) vs. conocimiento interno de la ONG (Experto).
  - Un agente verifica a otro: el Experto audita y puede rechazar → LoopAgent.
  - Permisos distintos: sólo el Contactador tiene herramientas que escriben, y piden aprobación.
  - El contexto pasa por el estado de la sesión (output_key), visible en las trazas de adk web.

TODO (equipo): si el prompt en vivo no siempre pide una intervención completa (p. ej. una
pregunta suelta), considerar un coordinador LlmAgent con estos agentes como sub_agents.
"""

from google.adk.agents import LoopAgent, SequentialAgent

from .agentes.contactador import contactador
from .agentes.evaluador import evaluador
from .agentes.experto import experto

revision = LoopAgent(
    name="revision_evaluador_experto",
    description="El Evaluador propone municipios y el Experto los audita hasta aprobar un plan.",
    sub_agents=[evaluador, experto],
    max_iterations=3,
)

root_agent = SequentialAgent(
    name="mexico_vivo",
    description="Canaliza los recursos de México Vivo al mejor programa por municipio y genera el contacto.",
    sub_agents=[revision, contactador],
)
