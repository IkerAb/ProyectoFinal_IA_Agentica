# Changelog

Formato: una entrada por cambio relevante, con autor. El **cambio entre corrida 1 y corrida 2 de
los evals** debe quedar aquí explícito (qué se cambió, en qué agente, por qué).

## [Sin publicar]

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
