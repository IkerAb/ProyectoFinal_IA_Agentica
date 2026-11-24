# México Vivo · Sistema multi-agente (ODS 3.7)

**COM-11310 IA Agéntica — Proyecto Final · Equipo Iker Goat**
Elías Penhos Abadi · Meyer Hemlinson Rosenthal · Iker Aboitiz Jaimes

Sistema en **Google ADK** que ayuda a la Fundación México Vivo a canalizar sus recursos contra el
embarazo adolescente: decide **a qué municipio** ir, **qué programa** ofrecer con **qué recursos**,
y genera el **primer contacto** institucional, que un humano aprueba antes de enviarse.

## Arquitectura

```
SequentialAgent "mexico_vivo"
├── LoopAgent "revision_evaluador_experto"  (máx. 3 vueltas)
│   ├── evaluador          (Meyer)  MCP datos públicos + RAG Centros Amigables  → state["candidatos"]
│   └── experto_fundacion  (Iker)   funciones BD fundación + RAG programas      → state["revision_experto"]
│                                    aprueba → exit_loop · rechaza → otra vuelta
└── contactador            (Elías)  historial + enviar_correo 👤 + registrar_seguimiento 👤
```

👤 = `FunctionTool(..., require_confirmation=True)`: ADK pausa y un humano aprueba o rechaza.

| Agente | Dueño | Archivo | Herramientas | Tipo |
|---|---|---|---|---|
| Evaluador | Meyer | `mexico_vivo/agentes/evaluador.py` | `municipios_prioritarios`, `perfil_municipio`, `escuelas_municipio` · `buscar_centros_amigables` | MCP · RAG |
| Experto de la Fundación | Iker | `mexico_vivo/agentes/experto.py` | `search_programs`, `get_program_details` · `get_available_resources`, `calculate_intervention_cost`, `check_feasibility`, `get_intervention_history`, `audit_proposal` · `exit_loop` | RAG · Funciones (SQL) |
| Contactador | Elías | `mexico_vivo/agentes/contactador.py` | `historial_contactos`, `enviar_correo` 👤, `registrar_seguimiento` 👤 | Funciones |

**Por qué varios agentes:** contextos grandes y separados (datos nacionales vs. conocimiento interno
de la ONG), un agente que audita a otro (Experto ↔ Evaluador) y permisos distintos (sólo el
Contactador escribe). El contexto pasa por el estado de la sesión (`output_key`).

## Estructura

```
├── mexico_vivo/              ← paquete del agente (lo que carga `adk web`)
│   ├── agent.py              ← orquestación (root_agent)
│   ├── config.py             ← rutas, modelos por rol, fecha "hoy"
│   ├── db.py                 ← consultar() / ejecutar() sobre las dos bases
│   ├── agentes/              ← un archivo por agente (cada dueño edita el suyo)
│   └── tools/                ← un archivo de herramientas por dueño + rag.py compartido
├── servidor_mcp.py           ← servidor MCP de datos públicos (lo usa el Evaluador)
├── probar_servidor.py        ← cliente MCP de prueba
├── scripts/
│   ├── generar_datos_sinteticos.py  ← datos/fundacion.db (semilla fija, reproducible)
│   ├── preparar_datos_publicos.py   ← datos/publicos.db (CONAPO + SEP; --demo para desarrollar)
│   └── ingest.py                    ← indexa PDFs en chroma_db/
├── datos/crudos/             ← archivos públicos descargados (no se suben)
├── datos/documentos/         ← PDFs para RAG (no se suben)
├── evals/                    ← casos.json (15) + correr_evals.py + resultados/
├── trazas/                   ← trazas exportadas de adk web (SÍ se suben)
└── docs/                     ← secciones individuales, red teaming, costos y riesgos
```

## Instalación

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
cp mexico_vivo/.env.example mexico_vivo/.env      # pongan SU propia GOOGLE_API_KEY
```

## Datos

```bash
python scripts/preparar_datos_publicos.py --demo   # mientras no estén los datos reales
python scripts/generar_datos_sinteticos.py         # después de publicos.db (usa sus municipios)
```

Datos reales (descargar a `datos/crudos/` y completar `cargar_reales()`):

| Conjunto | Fuente | Tipo |
|---|---|---|
| Tasa de fecundidad adolescente por municipio 2023 (~57 MB) | [CONAPO](https://www.gob.mx/conapo/documentos/tasa-especifica-de-fecundidad-adolescente-por-municipio-2023) | Público |
| Índice de marginación municipal | [datos.gob.mx](https://www.datos.gob.mx/dataset/indices_marginacion) | Público |
| Catálogo de centros de trabajo SEP | [datos.gob.mx](https://www.datos.gob.mx/dataset/catalogo_centros_trabajo_sep) | Público |
| Directorio de Centros Amigables (PDF 172 p.) → RAG | Secretaría de Salud | Público |
| Catálogo de programas de México Vivo + cifras 2023 → RAG del Experto | `datos/fundacion/` (sitio oficial, consultado 2026-11-23; ver su README) | Público, verificado |
| Presupuesto, personal, inventario, costos, capacidad, historial | `scripts/generar_datos_sinteticos.py` (cada fila con `origen = 'SIMULADO'`) | Sintético |

> No hay datos públicos de recursos operativos de México Vivo. El escenario simulado sólo cubre
> Generación Viva, PARESS y Hablemos de sexo y amor; para ASSI Vivo, Empresa Viva e Incidencias el
> Experto debe responder `INFORMACIÓN NO DISPONIBLE`.

RAG:

```bash
python scripts/ingest.py programas datos/fundacion/
python scripts/ingest.py centros_amigables datos/documentos/centros_amigables/
```

## Correr

```bash
python verificar_entorno.py      # todo en ✅
python probar_servidor.py Chiapas
adk web                          # http://localhost:8000 → elegir "mexico_vivo"
```

Para probar un agente solo, sin los demás: en `adk web` elijan `solo_experto` y peguen una
propuesta como la que mandaría el Evaluador (ver `solo_experto/agent.py`).

Los correos son **simulados**: se guardan en `salida/*.eml` y en la tabla `contactos`.

## Evals

```bash
python evals/correr_evals.py --corrida 1
# diagnóstico con trazas → UN cambio (anotarlo en CHANGELOG.md)
python evals/correr_evals.py --corrida 2
```

## Reglas del repo

- Cada quien trabaja en **su** agente y **sus** herramientas; cambios a `agent.py`/`config.py` se avisan.
- Commits de todos los integrantes. Ramas por persona/feature y PR a `main`.
- **Nunca** subir `.env`, llaves de API ni bases `.db`.
- Exportar trazas relevantes de `adk web` a `trazas/` (evals y red teaming).
