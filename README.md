# YakuTraza

**Trazabilidad verificable de trámites y recursos de inversión de las EPS.** Prototipo para la Hackathon
Sunass «Lideresas por el Agua», Desafío 3 (gestión financiera de las EPS).

YakuTraza convierte cada expediente regulatorio en una ruta verificable, como el rastreo de un paquete:
una línea de tiempo con tres relojes (plazo normativo, meta interna y plazo del oficio), evidencia
por hito, la ruta del dinero y vistas por rol. El diseño completo está en
[`docs/YakuTraza_Documento_tecnico.pdf`](docs/YakuTraza_Documento_tecnico.pdf).

> **Ninguna salida de YakuTraza es una decisión regulatoria.** El sistema informa y alerta; las decisiones
> son de Sunass.

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Ingesta de DS01–DS09 y control de calidad con reporte HTML | Lista |
| 2 | Calendario de días hábiles y motor de tres relojes | Lista |
| 3 | Expediente vivo (timeline, evidencia, bitácora, pre-chequeo art. 93/94) | Pendiente |
| 4 | Ruta del dinero | Pendiente |
| 5 | Interfaz por rol (React) | Pendiente |
| 6 | Extracción asistida de documentos (IA con cita) | Pendiente |
| 7 | Demo, pruebas de interfaz y entrega | Pendiente |

## Arquitectura

```
CSV DS01–DS09 (DATA_DIR, solo lectura)
        │
        ▼
backend/app/ingesta     lee todo como texto, convierte a los tipos del diccionario, no corrige nada
        │
        ├──► backend/app/calidad   reglas de rules/calidad.yaml → hallazgos con dataset, fila y fuente
        │
        ▼
PostgreSQL 16           tablas por dataset + carga_lotes + calidad_hallazgos (Alembic)
        │
        ▼
FastAPI (/docs)         /datasets, /calidad/*, /calendario/*, /reglas/plazos,
                        /expedientes/{id}/relojes, /alertas
```

- **Base de datos:** PostgreSQL 16. Llaves del diccionario (`cod_eps`, `ubigeo` como texto de 6 dígitos,
  `id_expediente`, `cod_proyecto`, `cui`, `cod_meta`). Cada fila guarda `fila_origen` (línea del CSV; el
  encabezado es la línea 1) y `valores_originales` (el texto tal como llegó).
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 y Alembic. La API documentada con OpenAPI
  (`/docs`, `/openapi.json`) sirve como esquema de intercambio para integrarse luego al SIA.
- **Reglas:** catálogo YAML versionado en [`rules/`](rules/). Cada regla declara su fuente (hoja del
  diccionario o norma), su severidad y su estado de validación, y cada umbral dice si es **diccionario**,
  **derivado** (sale de un cálculo documentado) o **supuesto** (por validar con la DRE).
- **Frontend:** React con TypeScript y Vite (Fase 5).

## Datos

**Los datos no se versionan.** El diccionario indica que la muestra es de «uso exclusivo de los equipos
inscritos», y este repositorio es público. El código los lee desde la carpeta indicada en `DATA_DIR`, que
debe contener:

- `ds01_catalogo_eps.csv`, `ds01_localidades_eps.csv`, `ds02_procedimientos.csv`,
  `ds02_hitos_procedimientos.csv`, `ds03_programa_inversiones.csv`, `ds04_ejecucion_inversiones.csv`,
  `ds05_fondo_inversiones_reservas.csv`, `ds06_estados_financieros.csv`, `ds07_metas_gestion.csv`,
  `ds08_inversiones_mef.csv`, `ds09_ipm.csv`
- `diccionario_variables.xlsx` (con él se verifica que la especificación de columnas, tipos y unidades
  coincida con el diccionario)
- `casos_reales/` (PDF de Tacna, EPSSMU y EMAPA Pasco; se usan desde la Fase 6)

Cada dato se rotula según su naturaleza:

| Rótulo | Qué incluye |
|---|---|
| **real** | DS09 (IPM del INEI, serie PN01286PM de BCRPData) y la geografía INEI (ubigeo, departamento, provincia, distrito, localidad) |
| **sintético** | EPS, montos, expedientes, proyectos, CUI y documentos de DS01–DS08 |
| **estimado** | Población servida y población beneficiaria; fecha de publicación del IPM |
| **supuesto** | Umbrales y criterios del equipo marcados así en `rules/` |

Fecha de corte de la muestra: **2026-09-30** (hoja Léame). Es el «hoy» de la demo y se cambia con `FECHA_CORTE`.

## Cómo correrlo

### Con Docker (recomendado)

1. Copia `.env.example` como `.env` y ajusta `DATA_DIR` a la carpeta de los datos.
2. Levanta la base y la API, carga los datos y genera el reporte:

```bash
make seed
```

En Windows sin `make`:

```powershell
.\scripts\tareas.ps1 docker-seed
```

- API y documentación: <http://localhost:8000/docs>
- Reporte de calidad: <http://localhost:8000/calidad/reporte.html> (agrega `?descargar=true` para bajarlo).
  También queda en `reportes/calidad.html`.
- PostgreSQL queda publicado en el puerto **5433** del host (para no chocar con un PostgreSQL local en
  5432); se cambia con `POSTGRES_PORT`.

### Sin Docker (desarrollo y pruebas)

```powershell
.\scripts\tareas.ps1 instalar   # crea backend\.venv
.\scripts\tareas.ps1 test       # pytest
.\scripts\tareas.ps1 cobertura  # pytest con cobertura de calidad e ingesta
.\scripts\tareas.ps1 seed       # carga en la base de DATABASE_URL (SQLite si no hay .env)
.\scripts\tareas.ps1 calidad    # vuelve a evaluar las reglas tras editar rules/calidad.yaml
.\scripts\tareas.ps1 api        # API en http://localhost:8000
```

SQLite solo se usa para desarrollo y pruebas; el prototipo apunta a PostgreSQL 16.

## Control de calidad (Fase 1)

La muestra trae errores a propósito. El módulo de calidad **los señala y no los corrige**. Cada hallazgo
se guarda en `calidad_hallazgos` con dataset, fila, llave, regla, severidad (alta, media, baja o
informativa), explicación, valor observado y esperado, fuente de la regla y estado de validación.

| Tipo | Reglas | Qué detecta |
|---|---|---|
| Duplicados | CAL-DUP-01/02 | Filas idénticas; llaves repetidas con valores distintos |
| Montos en otra unidad | CAL-UNI-01 | Montos unas 1000 veces fuera de la escala de su serie |
| Códigos que no cruzan | CAL-LLV-01/02/03/04 | Relaciones de la hoja Relaciones, formatos de código, proyectos sin ejecución, entidad del MEF |
| CUI sin MEF | CAL-CUI-01 | CUI de DS03 que no figura en DS08 |
| Reportes faltantes | CAL-FAL-01/02/03/04 | Trimestres (DS04), meses (DS05), estados financieros (DS06) y metas (DS07) sin reporte |
| Fechas inconsistentes | CAL-FEC-01/02/03/04 | Fin antes del inicio, hitos que no encadenan, fechas posteriores al corte, reportes antes del cierre |
| Diferencias con el MEF | CAL-MEF-01/02 | Avance físico y ejecución acumulada de DS04 frente a DS08 |
| Coherencia aritmética | CAL-ARI-01 a 06 | Fórmulas del diccionario (saldo del fondo, depósito programado, acumulados, indicadores DS06, sumas de DS01) |
| Dato no registrado | CAL-FAL-05 | Inversiones de DS08 sin avance físico (permitido, pero impide conciliar) |
| Formato | CAL-FMT-01 | Valores o columnas que no coinciden con el diccionario |

Las diferencias que caben en la tolerancia de redondeo no se ocultan: se informan agrupadas, con
severidad informativa, su conteo y su distribución por rangos.

## Motor de plazos (Fase 2)

Cada expediente de DS02 tiene **tres relojes**:

| Reloj | Qué mide | De dónde sale |
|---|---|---|
| Normativo | Plazo máximo del procedimiento y de cada etapa de la revisión periódica | RGT (arts. 45.1, 46.3, 47.6, 49.3, 89.7 y 93.8), hoja Hitos, DS02 |
| Interno | Metas de gestión por hito | Hoja Hitos (principal). Si el flujograma del expediente dice otra cosa, se muestra al lado como «discrepancia». |
| Del oficio | Plazo que se le da a la EP en un oficio o prórroga | RGT (arts. 34.2, 45.2, 89.6 y 93.7), TUO de la Ley 27444 (arts. 136.1 y 147), hoja Hitos. Si hay un documento registrado, prima el plazo que fija. |

- **Cómputo:** días hábiles contados desde el día hábil siguiente (TUO de la Ley 27444, arts. 142.1, 144.1 y 145.1; RGT art. 45.1).
  `fecha_limite = inicio + plazo + días de suspensión a cargo de la EP` (hoja Léame).
- **Calendario:** librería `holidays` (versión fija) más los feriados con vigencia de la hoja Supuestos. Las dos fuentes coinciden; si difirieran, la diferencia se registraría como hallazgo.
- **Alertas explicables:** «vence en N DH», «vencido hace N DH» o «no puedo calcular: falta X». Cada alerta trae su regla, su fuente, su estado de validación y el documento que inició el conteo. Si DS02 no trae el documento, la alerta dice «declarado, no verificado».
- **Validación contra DS02:**
  - `fecha_limite` y `dias_habiles_sunass` coinciden en 64 de 65 expedientes. El restante, RP-2026-0002, queda en «no puedo calcular» porque tiene una fecha inconsistente.
  - Los 360 vencimientos de reporte trimestral coinciden.
  - De los reajustes por IPM, coinciden los 35 que tienen base conocida.
  - Los resultados aparecen en el reporte de calidad (reglas CAL-PLZ).
- **Procedimientos sin flujograma** (reporte periódico, reajuste por IPM y verificación de incrementos): sus reglas vienen de la hoja Supuestos y se rotulan «supuesto de simulación». La excepción es el plazo de 90 días calendario para aplicar el reajuste, que sale del RGT, art. 82.3.
- **Versiones por vigencia:** cuando una norma cambia un plazo, la versión anterior se conserva con su `vigente_hasta` y la nueva entra con su `vigente_desde`. El motor aplica la versión vigente cuando empezó cada etapa o hito. Por ejemplo, desde la RCD 124-2025 (27-10-2025) la audiencia tiene un máximo de 30 DH y los comentarios, 15 DH. Si el dato no permite comparar con la versión que regía entonces, el motor dice «no puedo comparar».
- **Catálogo:** [`rules/plazos.yaml`](rules/plazos.yaml). Cada regla trae `tipo_reloj`, plazo, `vigente_desde` y `vigente_hasta`, sus fuentes con cita textual, su `respaldo` y su `estado_validacion`. **Todas están «por validar»**, porque la DRE aún no valida ninguna.
- **Preguntas pendientes:** [`docs/preguntas_para_la_DRE.md`](docs/preguntas_para_la_DRE.md) reúne cada discrepancia, subplazo que no suma y plazo sin norma citada, con la pregunta concreta y lo que cambia en el motor según la respuesta.

Endpoints: `/calendario/feriados?anio=`, `/calendario/diferencias`, `/reglas/plazos`,
`/expedientes/{id}/relojes?fecha_corte=` y `/alertas?fecha_corte=&cod_eps=&reloj=`. Las alertas se ordenan por
plazo restante, con las vencidas primero, y nunca por el tamaño de la EPS.

## Supuestos

Todos están en [`rules/calidad.yaml`](rules/calidad.yaml), con su sustento:

- **Umbral de escala** para montos en otra unidad: factor 100.
- **Conciliación con el MEF en un corte común:** umbrales de 10 puntos de avance físico y 20 % de
  ejecución financiera. DS04 llega a 2026-T2 y DS08 es una foto de agosto a septiembre de 2026. La
  ejecución se compara al cierre de 2025-T4, con el devengado del MEF calculado como
  `devengado_acumulado − devengado_2026`. Solo es «diferencia real» si persiste en ese corte. Las que
  explica el desfase se informan aparte, como informativas (tipo `desfase_mef`). DS08 no trae historia del
  avance físico, así que esas diferencias se informan como no verificables, salvo que el MEF posterior sea
  menor que la EPS. Si un proyecto concluyó antes del corte, se usa su acumulado final (supuesto: un
  proyecto concluido no ejecuta más).
- **Identidades del estado de resultados en DS06:** `resultado_operativo = ingresos − costos y gastos` y
  `resultado_neto = resultado_operativo + ingresos financieros − gastos financieros − impuesto`. No están
  escritas en el diccionario, pero se cumplen en las 99 filas presentadas. Un margen negativo que cuadra
  es una pérdida real y no se marca.
- **Porcentaje de depósito redondeado:** DS05 publica `porcentaje_ingresos` con 2 decimales. Se supone
  que es el redondeo del porcentaje con el que se calculó el depósito. De ahí sale una tolerancia
  relativa a los ingresos del mes: `ingresos_base_mes × 0,00005 + 0,005`.

## Limitaciones

- La muestra es sintética (salvo DS09). Los hallazgos describen la muestra, no a EPS reales.
- Las reglas marcadas «por validar» deben revisarse con la DRE.
- Fuera del alcance: integración real con el SIA o el trámite documentario, firma digital, envío real de
  mensajes y datos personales.

## Fuentes

- Sunass (2021). Reglamento General de Tarifas, RCD 028-2021-SUNASS-CD. Se leyó el compendio oficial de Sunass, que incluye las modificatorias hasta la RCD 004-2023: <https://cdn.www.gob.pe/uploads/document/file/4388328/>.
- Sunass (2025). RCD 124-2025-SUNASS-CD, que modifica el RGT (El Peruano, 26-10-2025): `docs/normas/RCD-124-2025-SUNASS-CD.pdf`.
- Sunass (2026). RCD 028-2026-SUNASS-CD, que modifica el art. 90 del RGT (El Peruano, 31-07-2026): `docs/normas/RCD-028-2026-SUNASS-CD_El-Peruano-2026-07-31.pdf`.
- TUO de la Ley 27444, Ley del Procedimiento Administrativo General, DS 004-2019-JUS: <https://cdn.www.gob.pe/uploads/document/file/5320370/>. El DS 006-2026-JUS aprobó un TUO nuevo, que no se leyó.
- Sunass (2026). Expediente General del Desafío 3, v1.0.
- Sunass (2026). Diccionario de variables y datasets DS01–DS09, Desafío 3 (hojas Léame, Relaciones, Hitos,
  Supuestos y una por dataset).

## Declaración de uso de IA

El código de este prototipo se escribió con asistencia de Claude (Anthropic) en Claude Code. El equipo
revisa cada fase y valida los datos contra el diccionario y las normas citadas. En la Fase 6, la extracción
de documentos usará por defecto un modelo abierto local; la API de Anthropic solo se usará, como opción,
con textos públicos o sintéticos y después de anonimizar los nombres de personas.

## Licencia

[MIT](LICENSE).
