# Prompt para Claude Code · Prototipo YakuTraza (Hackathon Sunass "Lideresas por el Agua", Desafío 3)

---

## 0. Rol y forma de trabajar

Eres el equipo técnico que construye el prototipo funcional de **YakuTraza** para el sprint presencial de la Hackathon Sunass "Lideresas por el Agua", Desafío 3 (gestión financiera de las EPS). Somos un equipo de 4 ingenieros y este prototipo debe coincidir exactamente con nuestro documento técnico (`./docs/YakuTraza_Documento_tecnico.pdf`). Léelo completo antes de empezar, junto con el expediente del desafío y el diccionario de variables (todas sus hojas: Léame, Relaciones, Hitos, Supuestos y una por dataset).

Reglas de trabajo:

1. **Primero planifica.** Antes de escribir código, muéstrame un plan por fases con los archivos que vas a crear y espera mi aprobación. Al cerrar cada fase, ejecuta las pruebas, resume lo hecho y espera mi visto bueno.
2. **No inventes datos, reglas ni fechas.** Todo dato sale de `./data`, del diccionario o de una norma citada. Si algo no está, déjalo vacío y márcalo "por validar". Nunca rellenes huecos con valores plausibles.
3. **Todo lo que se muestre debe tener fuente.** Cada alerta, monto, plazo y vínculo indica su fuente (dataset y fila, hoja del diccionario, artículo del RGT o documento).
4. **La muestra es sintética.** Las EPS, montos, expedientes y documentos de DS01–DS08 son ficticios (solo DS09, el IPM, es real). La interfaz debe rotular cada dato como **real**, **sintético**, **estimado** o **supuesto**.
5. **La muestra trae errores a propósito** (duplicados, montos en otra unidad, códigos que no cruzan, reportes faltantes, fechas inconsistentes, diferencias con el MEF). Detectarlos y mostrarlos es parte del reto: nunca los corrijas en silencio.
6. **Ninguna salida es una decisión regulatoria.** El sistema informa y alerta; las decisiones son de Sunass.
7. **Fecha de corte de la muestra: 2026-09-30.** Úsala como "hoy" en la demo, configurable.

## 1. Qué es YakuTraza (resumen del documento técnico)

Convierte cada expediente regulatorio en una ruta verificable, como el rastreo de un paquete. Tiene tres funciones centrales conectadas:

1. **Línea de tiempo con tres relojes, evidencia y control de calidad.** Separa el plazo normativo, la meta interna y el plazo fijado en cada oficio o prórroga. Cada hito exige su documento; un hito sin documento se muestra como "declarado, no verificado". Si falta una fecha, el sistema muestra "no puedo calcular" en lugar de estimar.
2. **Ruta del dinero.** Muestra lo solicitado, lo autorizado (y de qué fondo o reserva), lo usado y lo verificado, junto con el avance físico y financiero de los proyectos. Nunca confunde aprobado con ejecutado.
3. **Vistas por rol:** especialista, dirección, otras áreas (solo lectura), EPS y ciudadanía.

Usuaria principal: la especialista del Equipo SRT (Subdirección de Regulación Tarifaria) de la Dirección de Regulación Económica (DRE). Beneficiaria final de referencia: una jefa de hogar en una localidad con poca continuidad del servicio, que quiere saber si las obras avanzan y cuándo puede opinar sobre la tarifa.

## 2. Arquitectura y stack (coherente con el documento técnico)

- **Base de datos:** PostgreSQL 16. Usa las llaves del diccionario (`cod_eps`, `ubigeo` como texto de 6 dígitos, `id_expediente`, `cod_proyecto`, `cui`, `cod_meta`). No uses el número de documento como identificador del caso.
- **Backend:** Python 3.12 con FastAPI, SQLAlchemy y Pydantic. Expón una API REST documentada con OpenAPI, que sirva como esquema de intercambio para integrarse luego al SIA.
- **Frontend:** React con TypeScript y Vite.
- **Orquestación:** `docker-compose` con los servicios `db`, `api` y `web`, más un comando `make seed` que cargue los datos.
- **Reglas:** catálogo en archivos YAML versionados (`./rules/`), editable sin programar. Cada regla lleva `id`, `procedimiento`, `hito`, `tipo_reloj` (normativo, interno u oficio), `plazo_dh`, `cuenta_plazo`, `vigente_desde`, `vigente_hasta`, `fuente` (artículo o hoja del diccionario) y `estado_validacion` (validada o por validar).
- **Código abierto:** licencia MIT para nuestro código, README claro y repositorio público en GitHub (las bases lo exigen).
- **IA:** una interfaz `ExtractionProvider` con dos implementaciones. Por defecto, un modelo abierto local (por ejemplo vía Ollama). Como opción, la API de Anthropic, que solo puede usarse con textos públicos o sintéticos y después de anonimizar los nombres de personas.

## 3. Fase 1 · Ingesta y control de calidad de datos

- Carga DS01 a DS09 (incluidas las dos tablas de DS02) según el diccionario, respetando tipos y unidades (montos en soles con 2 decimales; DS06 en soles enteros; porcentajes de 0 a 100).
- Implementa un **módulo de calidad** con una regla por tipo de problema:
  - duplicados;
  - montos con unidad sospechosa (por ejemplo, miles en lugar de soles);
  - llaves que no cruzan entre datasets (usa la hoja Relaciones);
  - trimestres o meses sin reporte;
  - fechas inconsistentes (fin antes del inicio, hitos fuera de orden);
  - diferencias entre el avance reportado por la EPS (DS04) y el MEF (DS08);
  - CUI declarado en DS03 que no aparece en DS08.
- Cada hallazgo se guarda en una tabla `calidad_hallazgos` con dataset, fila, regla, severidad y explicación. Genera un reporte HTML descargable con todos los hallazgos.
- Prueba: el reporte debe encontrar al menos un caso de cada tipo que el diccionario anuncia. Si algún tipo no aparece, dilo, no lo fuerces.

## 4. Fase 2 · Calendario y motor de plazos (tres relojes)

- **Días hábiles:** de lunes a viernes, sin feriados nacionales. Usa la librería `holidays` para Perú y añade lo que indica la hoja Supuestos del diccionario (6 de agosto y 9 de diciembre desde 2022, 23 de julio desde 2023 y 7 de junio desde 2024, según su vigencia). Si la librería y el diccionario difieren, registra la diferencia y márcala "validar con el calendario oficial".
- **Regla del diccionario:** `fecha_limite = fecha_inicio + plazo_maximo_dh + dias_suspension_dh`, en días hábiles. Los hitos con `cuenta_plazo = False` están a cargo de la EPS y suspenden el plazo de Sunass.
- **Reloj normativo:** el plazo máximo del procedimiento (DS02 `plazo_maximo_dh`). Son 30 DH en cambio al programa de inversiones y en uso excepcional del fondo. En la revisión periódica son 195 DH en cuatro etapas (30, 60, 45 y 60).
- **Reloj interno:** los plazos referenciales de la hoja Hitos y de los flujogramas del expediente. Por ejemplo, la derivación tiene 1 DH; en la revisión periódica, la audiencia pública tiene un máximo de 30 DH y los comentarios hasta 15 DH después de la audiencia.
- **Reloj del oficio:** el plazo fijado en cada oficio o prórroga. Por ejemplo, la subsanación tiene un máximo de 2 DH en cambio al programa de inversiones y en uso del fondo, y de 10 DH en la revisión periódica; la información adicional, hasta 10 DH.
- **Alertas explicables:** "vence en N DH", "vencido" o "no puedo calcular: falta X". Cada alerta muestra la regla, su fuente y el documento que inició el conteo.
- **Validación:** recalcula `fecha_limite` y `dias_habiles_sunass` y compáralos con DS02. Lista las discrepancias en el reporte de calidad.
- **Pruebas unitarias:** feriados, fines de semana, suspensiones, prórrogas y casos sin fecha.
- Reproduce también los otros tres procedimientos de la muestra (reajuste por IPM, reporte periódico y verificación de incrementos) con las reglas de la hoja Supuestos, marcadas como "supuesto de simulación".

## 5. Fase 3 · Expediente vivo (timeline y pasaporte de evidencia)

- Por `id_expediente`, muestra una línea de tiempo vertical con cada hito: responsable, fechas, plazo referencial, documento (con su tipo: OF, INF, MEM, RD o RCD), si cuenta para el plazo y su estado.
- Un hito sin documento se muestra como **"declarado, no verificado"**.
- Registro de documentos que llegan por canales informales. En los casos reales, Tacna envió información por correo electrónico y EPSSMU por un enlace de Drive: debe poder registrarse ese canal.
- **Bitácora de cambios:** quién cambió qué y cuándo (append-only).
- **Pre-chequeo art. 93 / art. 94** para cambios al programa de inversiones, como reglas configurables marcadas "por validar con la DRE":
  - Art. 94.1, numeral 1: el cambio va solo con comunicación si los incrementos acumulados del periodo no superan el 10% del monto total del programa de inversiones.
  - Art. 94, numeral 6 (incorporado por la RCD 085-2022): en sustituciones de los numerales 3 y 4 del párrafo 93.1, el costo individual no debe superar el menor valor entre el 10% del programa y S/ 5 000 000, y la suma de sustituciones del periodo no debe superar el 10%.
  - En los demás casos, el cambio va por el art. 93, con aprobación del Consejo Directivo.
  - Si el proyecto tiene `meta_asociada` (DS03 → DS07), muestra una advertencia: el art. 92 exige que el cambio no modifique las metas de gestión.
  - Muestra siempre la regla aplicada y el texto citado.

## 6. Fase 4 · Ruta del dinero

- **Por expediente:** monto solicitado y aprobado (DS02), tipo de fondo o reserva (DS05 `tipo_fondo`), uso excepcional registrado (DS05 `uso_excepcional` + `id_expediente_uso_excepcional`) y estado de verificación posterior. No hay dato de verificación en la muestra: muestra "pendiente" y no lo inventes.
- **Por proyecto:** programado original y vigente (DS03), la modificación que lo cambió (`id_expediente_modificacion`), ejecución trimestral y acumulada y avance físico (DS04), y conciliación con el MEF (DS08).
- **Escalera de estados:** programado → aprobado → financiado → en ejecución (o paralizado) → concluido → beneficio verificado. El último peldaño queda siempre "no verificado" en la muestra.
- **Señal para revisión** (nunca "problema"): una diferencia entre avance financiero y físico mayor a un umbral configurable. Por defecto, 25 puntos porcentuales, marcado como supuesto.
- **Contexto financiero (DS06):** liquidez, endeudamiento, relación de trabajo, morosidad y eficiencia de cobranza, con las fórmulas de la hoja Supuestos. Se muestra como contexto, nunca como nota ni diagnóstico.
- **Fondos (DS05):** compara el depósito programado con el efectuado y muestra el saldo final mensual.

## 7. Fase 5 · Vistas e interfaz

**Roles y permisos** (RBAC, con una matriz configurable en YAML):

- **Especialista SRT:** bandeja "mi siguiente acción" ordenada por plazo restante (no por tamaño de la EPS), expediente vivo y ruta del dinero.
- **Coordinación SRT y Dirección DRE:** tablero con el porcentaje de expedientes que superan el plazo máximo (línea base de la muestra), demoras por hito y por responsable, embudo de firmas y carga por especialista. Como DS02 registra unidades y no personas, crea especialistas ficticios rotulados como tales. Incluye una propuesta de asignación por carga y un simulador de escenarios que nunca modifica los datos reales.
- **Otras áreas de Sunass:** solo lectura.
- **EPS:** solo ve su `cod_eps`. Ve sus trámites, qué le falta y hasta cuándo, y su fondo y usos autorizados. No ve documentos internos (INF y MEM en borrador). Una acción por pantalla.
- **Vista ciudadana pública:** búsqueda por localidad o ubigeo (DS01); proyectos con su etapa real, la población beneficiaria (rotulada "estimada") y la decisión de Sunass vinculada; avisos de audiencias públicas y plazos de comentarios. Solo información agregada y no reservada.

**La prueba memorable** (es el criterio de éxito del sprint): desde la bandeja, en menos de un minuto, la especialista debe poder responder qué expediente requiere su acción, qué evidencia falta y por qué importa darle seguimiento.

**Inclusión:**

- Lenguaje claro.
- Alertas con ícono y texto, sin depender solo del color.
- Diseño móvil primero en las vistas EPS y ciudadana.
- Avisos simulados por correo o mensajería: solo vista previa, sin envío real.
- Campo para un resumen en quechua que una persona debe validar. No generes traducciones automáticas sin revisión humana.

## 8. Fase 6 · Extracción asistida de documentos (IA)

- **Entrada:** un PDF (oficio, carta o resolución). Primero se extrae el texto (con OCR si es necesario). Los PDF reales traen marcas de agua y texto ruidoso: límpialo antes.
- **Salida:** solo estos campos: número de documento, fecha, remitente, plazo otorgado o solicitado (en DH) y requerimientos. Cada campo lleva la **cita textual exacta y la página**. Si no hay cita, el campo queda vacío.
- **Validación automática:** la cita debe existir literalmente en el texto extraído. Si no existe, se descarta el campo.
- **Interfaz:** cada dato se marca "propuesto por IA" con los botones Confirmar o Corregir, y solo entra al expediente cuando una persona lo confirma.
- **Demo:** usa los PDF de `./data/casos_reales/`. Primero anonimiza los nombres de personas que aparecen en firmas. Si usas un proveedor externo, envía solo texto anonimizado.
- **Evaluación:** calcula la precisión de los campos extraídos contra un pequeño conjunto anotado a mano (5 documentos) e infórmala.

## 9. Diseño visual (paleta tomada de los documentos oficiales del hackathon)

No hay un manual público de identidad de Sunass con códigos de color, así que la paleta se extrajo de los PDF oficiales: el Expediente del Desafío 3 para la línea institucional y la Guía de la Fase 2 para la línea de campaña. Debe confirmarse con el manual de marca de Sunass en la mentoría. No reproduzcas el logo de Sunass salvo que tengamos el archivo oficial autorizado.

Define estos tokens CSS:

```css
:root {
  /* Línea institucional (Expediente Desafío 3) */
  --yt-navy-900: #182C3E;   /* texto principal, encabezados */
  --yt-navy-800: #17324D;
  --yt-navy-700: #173A66;
  --yt-blue-600: #245B85;   /* acciones primarias, enlaces */
  --yt-blue-500: #087EA1;
  --yt-teal-500: #008C95;   /* acento institucional */
  --yt-slate-600: #526575;  /* texto secundario */
  --yt-slate-500: #5F7180;
  --yt-ice-100:  #EAF5F8;   /* fondos suaves */
  --yt-ice-50:   #F2F7FA;
  /* Línea de campaña "Lideresas por el Agua" (Guía Fase 2), uso puntual */
  --yt-violet-600: #713BCE;
  --yt-lilac-300:  #D09EFF;
}
```

Reglas de uso:

- Contraste WCAG AA verificado. `#008C95` sobre blanco da 4,05:1: úsalo solo en texto grande, íconos, bordes o fondos con texto oscuro, nunca en texto normal. Para texto, usa `--yt-navy-900` (14,3:1) o `--yt-blue-600` (7,2:1).
- Los estados (vencido, por vencer, en plazo, no calculable) se distinguen por ícono, etiqueta y patrón además del color.
- Tipografía: **Noto Sans** (abierta, y es la que usa el expediente oficial), con respaldo `Arial, sans-serif`.
- Estilo: sobrio, institucional, mucho espacio en blanco, tablas legibles y sin animaciones innecesarias.

## 10. Fase 7 · Demo, pruebas y entrega

- **Guion de demo reproducible** (`make demo`):
  1. Abrir la bandeja con la fecha de corte.
  2. Abrir un expediente de cambio al programa de inversiones de DS02 con prórroga.
  3. Ver los tres relojes y una alerta explicada.
  4. Ver los proyectos afectados y su ruta del dinero.
  5. Cambiar a la vista EPS.
  6. Cambiar a la vista ciudadana de esa localidad.
  7. Mostrar el reporte de calidad.
  8. Mostrar la extracción con cita de un oficio real anonimizado (Tacna).
- **Contraste con los casos reales** (como texto informativo en la demo, con su fuente):
  - Tacna: solicitud recibida el 17 de julio de 2026 y RCD 032-2026 del 28 de agosto de 2026.
  - EPSSMU: solicitud recibida el 12 de septiembre de 2025 y RCD 126-2025 del 27 de octubre de 2025. Se autorizaron S/ 217 313,20 desde una reserva (PCC/PAS), no desde el fondo, con exoneración de devolución.
  - EMAPA Pasco: resolución de inicio publicada el 15 de septiembre de 2024, audiencia pública el 8 de noviembre de 2024 y RCD 076-2024 del 13 de diciembre de 2024.
- **Pruebas:** pytest para backend y reglas (cobertura mínima del 80% en el motor de plazos y en calidad), y pruebas de interfaz de los flujos de la demo.
- **README:** propósito, arquitectura, cómo correrlo, fuentes de datos, supuestos, limitaciones y declaración de uso de IA.
- **Despliegue:** un enlace público operativo para el jurado (las bases lo exigen). Propón opciones y espera mi elección antes de desplegar; no crees cuentas ni uses credenciales sin preguntarme.
- **Entregable final:** también un `docs/indicadores.md` con la línea base calculada de la muestra. Incluye el porcentaje de expedientes que superan el plazo máximo (comparando `dias_habiles_sunass` con `plazo_maximo_dh`) por tipo y por EPS, rotulado "muestra simulada".

## 11. Fuera del alcance

Integración real con el SIA o el trámite documentario, firma digital, envío real de mensajes, datos personales y cualquier dato no autorizado por el comité.

Cuando termines el plan de la Fase 1, detente y muéstramelo.
