"""Experto de la Fundación SOLO, para probarlo en `adk web` sin el Evaluador.

En adk web elijan "solo_experto" y peguen una propuesta como la que mandaría el Evaluador, p. ej.:

  Municipio candidato: DEMO Chiapas 8 (07008), Chiapas. TEFA 90.1, marginación Muy alto.
  Escuelas: 3 secundarias, 1,200 alumnos, 1 con internet. Programas de gobierno: ninguno reportado.

No usa LoopAgent: si el agente llama exit_loop aquí, no pasa nada.
"""

from mexico_vivo.agentes.experto import crear_experto

root_agent = crear_experto("experto_solo")
