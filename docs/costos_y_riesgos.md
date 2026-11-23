# Costos y riesgos

## Costo por consulta (medido con las trazas de los evals)
| Corrida | Tokens entrada prom. | Tokens salida prom. | Costo prom. / consulta | Latencia prom. |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

Proyección a 100 / 10,000 / 1,000,000 consultas — escenario conservador y optimista (precio del
modelo, vueltas del LoopAgent, tamaño de contexto RAG). TODO

## Riesgos y mitigaciones
| Riesgo concreto | Mitigación |
|---|---|
| El Contactador escribe a un correo inventado | Validar que el destinatario venga de `escuelas`; aprobación humana |
| Prompt injection en el PDF de Centros Amigables | Regla de PRIORIDAD en instrucciones; red teaming |
| Loop Evaluador↔Experto sin converger (costo) | `max_iterations=3` |
| Datos sintéticos interpretados como reales | Documentado en generador y reporte |
| TODO | |
