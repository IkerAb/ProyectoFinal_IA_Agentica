# Datos verificados para el Agente Experto de México Vivo

## Principio de integridad
Este paquete contiene únicamente información encontrada en fuentes oficiales consultadas el 2026-11-23. **No se generaron datos sintéticos ni se rellenaron campos desconocidos.** Los valores `null`, listas vacías y campos ausentes significan que la fuente consultada no documenta ese dato; no significan cero.

## Archivos
- `programas.json`: descripciones institucionales estructuradas de los programas/servicios que aparecen en el sitio oficial. Incluye referencias por registro.
- `programas.jsonl`: la misma información, un objeto JSON por línea, útil para ingestión registro a registro.
- `hechos_institucionales_2023.json`: cifras históricas que la página oficial muestra para 2023. No se atribuyen a programas cuando la fuente no lo hace.
- `fuentes_externas.json`: catálogo de datasets públicos recomendados para el contexto municipal y gubernamental, con URL, cobertura y uso previsto.
- `README.md`: instrucciones, límites y trazabilidad.

## Importante: datos que NO están incluidos
No se encontró evidencia pública suficiente en las fuentes consultadas para completar:
- presupuesto disponible de México Vivo por municipio o programa;
- personal disponible, perfiles, horas y costos;
- inventario de materiales;
- costos unitarios de intervención;
- capacidad máxima operativa por programa;
- historial municipal de intervenciones de la fundación;
- requisitos formales de elegibilidad de escuelas/municipios.

No deben inferirse ni fabricarse. Para usar esas variables, soliciten datos a la fundación o acuerden explícitamente un escenario sintético con el profesor/equipo, claramente etiquetado como simulado.

## Programas/servicios incluidos
El sitio oficial presenta Generación Viva, PARESS, ASSI Vivo, Hablemos de sexo y amor, Empresa Viva e Incidencias. Los Términos y Condiciones describen con mayor detalle cuatro programas (Generación Viva, PARESS, ASSI Vivo y Hablemos de sexo y amor). Este paquete conserva esa diferencia y no inventa fichas operativas.

## Fuentes externas a descargar por separado
1. CONAPO - TEFA municipal 2023: https://www.gob.mx/conapo/documentos/tasa-especifica-de-fecundidad-adolescente-por-municipio-2023
2. CONAPO - Índice de marginación municipal 2020 (CSV): https://www.datos.gob.mx/dataset/indices_marginacion/resource/d65dbd44-2fad-4344-bfc2-45152067a14d
3. SEP - Catálogo de Centros de Trabajo (CSV; hay ediciones 2025 y 2024): https://www.datos.gob.mx/dataset/catalogo_centros_trabajo_sep
4. ENAPEA - Sistema de Indicadores para Monitoreo y Seguimiento: https://unidaddegenero.segob.gob.mx/es/ENAPEA/Que_es_la_ENAPEA

Revisen los diccionarios y metadatos de cada descarga antes de mapear columnas. No asuman que todos los indicadores tienen nivel municipal o el mismo año.

## Uso recomendado por el agente
- Usar `programas.json` como catálogo documental de programas.
- Usar `hechos_institucionales_2023.json` solo como evidencia histórica, no como disponibilidad actual.
- Usar `fuentes_externas.json` como registro de fuentes para el Evaluador y para auditoría.
- Cuando falten presupuesto, personal, inventario o capacidad, responder `INFORMACIÓN NO DISPONIBLE` y solicitarla; nunca completar con valores estimados sin autorización explícita.

## Nota metodológica
La TEFA de CONAPO es un indicador territorial de fecundidad adolescente; por sí sola no prueba que una intervención concreta sea necesaria o eficaz. La marginación es contexto socioeconómico y el catálogo SEP describe centros de trabajo, pero se requiere revisar variables y vigencia para definir qué es relevante para cada programa.
