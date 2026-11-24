# Experto de la Fundación — dueño: Iker Aboitiz Jaimes

> Sección individual del reporte (13 pts). Llenar con la plantilla oficial del curso; esto es un borrador (v1).

## Rol y alcance
Recibe la propuesta del Evaluador, investiga si es viable y determina cómo aprovechar los recursos
de México Vivo. Es el agente que conoce a la fundación y audita que las recomendaciones de los demás
tengan sentido. No elige municipios ni contacta a nadie.

Responde cuatro preguntas: ¿qué necesita la comunidad?, ¿qué programa la atiende?, ¿tenemos los
recursos?, ¿la intervención es viable y tiene sentido?

## Proceso
```
Propuesta del Evaluador → necesidad → search_programs / get_program_details (RAG)
  → get_available_resources / calculate_intervention_cost (SQL) → audit_proposal
  → ¿viable? ── sí → auditoría + DECISIÓN: APROBADO (exit_loop)
            └─ no → otro programa o menor alcance (máx. 3 intentos)
                    → RECHAZADO (vuelve al Evaluador) o REQUIERE INFORMACIÓN (exit_loop)
```

## Herramientas
| Herramienta | Tipo | ¿Escribe? | Para qué |
|---|---|---|---|
| `search_programs` | RAG (ChromaDB, e5-small) | No | Programas candidatos para una necesidad |
| `get_program_details` | Catálogo verificado | No | Ficha documental; campos sin fuente → INFORMACIÓN NO DISPONIBLE |
| `get_available_resources` | SQL | No | Presupuesto, personal, inventario |
| `calculate_intervention_cost` | SQL + cálculo | No | Costo, meses y facilitadores (el LLM no estima) |
| `check_feasibility` | SQL + reglas | No | Viabilidad por recurso y `max_escuelas_viables` |
| `get_intervention_history` | SQL | No | Evitar duplicar intervenciones |
| `audit_proposal` | Compuesta | No | Población, duplicidad, gobierno y viabilidad en un veredicto |
| `exit_loop` | Control de ADK | No | Termina el ciclo con el Evaluador |

## Datos
- **Documental, verificado:** `datos/fundacion/` (sitio oficial de México Vivo, consultado 2026-11-23).
- **Operativo, SIMULADO:** `datos/fundacion.db`; no existen datos públicos de recursos. Cada
  respuesta lo etiqueta con `origen`.

## Qué recibe y qué entrega
Lee `state["candidatos"]`; escribe `state["revision_experto"]` con la auditoría y la decisión.

## Pendiente
- Contrato con el Evaluador: acordar con Meyer que reporte `cve_mun`, escuelas (n, alumnos, con
  internet) y programas de gobierno, que son los argumentos de `audit_proposal`.
- Probar con Gemini en `solo_experto` y guardar trazas en `trazas/`.

## Fallos encontrados en evals (con traza)
TODO

## Red teaming
- **Me ataca:** Meyer (según la rotación en `docs/red_teaming.md`).
- **Defendí:** TODO
