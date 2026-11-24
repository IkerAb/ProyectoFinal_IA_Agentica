# Changelog

Formato: una entrada por cambio relevante, con autor. El **cambio entre corrida 1 y corrida 2 de
los evals** debe quedar aquí explícito (qué se cambió, en qué agente, por qué).

## [Sin publicar]

### Experto de la Fundación v1 (Iker)
- Datos verificados de México Vivo en `datos/fundacion/` (6 programas, cifras 2023, fuentes
  externas), indexados en la colección RAG `programas` (`scripts/ingest.py` ahora lee `.jsonl`).
- Base operativa rehecha: catálogo con los `program_id` reales y escenario `SIMULADO` sólo para
  Generación Viva, PARESS y Hablemos de sexo y amor; los demás responden INFORMACIÓN NO DISPONIBLE.
  Se eliminaron los programas inventados P01–P05.
- 7 herramientas: `search_programs`, `get_program_details`, `get_available_resources`,
  `calculate_intervention_cost`, `check_feasibility` (con `max_escuelas_viables`),
  `get_intervention_history`, `audit_proposal` (veredicto APROBABLE / NO_VIABLE / DUPLICADO /
  REQUIERE_INFORMACION).
- Instrucciones con proceso de 5 etapas, reglas de datos y tres decisiones (APROBADO, RECHAZADO,
  REQUIERE INFORMACIÓN); `crear_experto()` y paquete `solo_experto/` para probarlo aislado.

### Agregado
- Estructura inicial del repositorio: paquete `mexico_vivo/` con tres agentes (Evaluador,
  Experto de la Fundación, Contactador) orquestados como `SequentialAgent[LoopAgent(evaluador,
  experto), contactador]`.
- Herramientas por dueño (`mexico_vivo/tools/`), servidor MCP de datos públicos, RAG con ChromaDB.
- Aprobación humana (`require_confirmation=True`) en `enviar_correo` y `registrar_seguimiento`.
- Generador de datos sintéticos (`scripts/generar_datos_sinteticos.py`, semilla fija) y
  preparación de datos públicos (`scripts/preparar_datos_publicos.py`, con modo `--demo`).
- Esqueleto de 15 casos de evaluación y script `evals/correr_evals.py`.
- Google ADK fijado en `2.15.0`.
