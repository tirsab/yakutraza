# Preguntas para la DRE (mentoría)

YakuTraza · Hackathon Sunass «Lideresas por el Agua» · Desafío 3
Versión de trabajo tras la Fase 2. Fecha de corte de la muestra: 2026-09-30.

Todas las reglas de plazo del prototipo están **«por validar»**. Este documento reúne cada
discrepancia entre fuentes, cada subplazo que no suma y cada plazo sin norma citada que encontramos,
además de las preguntas de producto y datos. Para cada punto indicamos la pregunta concreta, las
fuentes que se contradicen y qué cambia en el motor según la respuesta.

Los identificadores (DRE-02, E-1…) son los que aparecen en `rules/plazos.yaml`, en el campo
`pregunta_dre`. Las abreviaturas de las fuentes están en el [anexo](#anexo-fuentes).

---

## Prioridad para la mentoría

Si solo hay tiempo para cinco preguntas, estas son, en orden:

1. **[DRE-02](#dre-02--suspensión-o-reinicio-del-plazo)**: cuando la EP subsana o entrega información, ¿el plazo de Sunass se suspende o se reinicia? Esto cambia la fecha límite de todos los expedientes con subsanación.
2. **[DRE-15](#dre-15--cómo-informar-que-un-procedimiento-superó-el-plazo)**: ¿cómo prefieren que la interfaz informe que un procedimiento superó el plazo, considerando que el RGT lo sujeta a silencio administrativo positivo?
3. **[DRE-20](#dre-20--canales-informales-y-fecha-de-inicio-del-cómputo)**: si la EP envía información por correo o por un enlace externo, ¿desde cuándo corre el plazo?
4. **[DRE-08](#dre-08--etapa-de-inicio-de-la-revisión-periódica)**: en la etapa de inicio de la revisión periódica, las metas internas suman 36 DH frente a una etapa de 30 DH. ¿Cuáles corren en paralelo?
5. **[E-1](#e-1--datos-reales-para-la-línea-base)**: ¿hay datos reales de tiempos de atención o un registro histórico de expedientes de la DRE para medir la línea base? Reemplaza a DRE-10, que ya resolvió la RCD 124-2025 (ver [Resueltas](#resueltas)).

---

## A. Normas que no pudimos leer o verificar

### DRE-14 · Confirmar la RCD que incorporó el numeral 6 del art. 94
- **Pregunta.** ¿Confirman que el numeral 6 del art. 94 lo incorporó la RCD 108-2022-SUNASS-CD (publicada el 17-11-2022)?
- **Fuentes.**
  - El compendio oficial del RGT anota: «Numeral incorporado por la Resolución De Consejo Directivo N.º 108-2022-SUNASS-CD, publicada el 17 de noviembre del 2022».
  - La RCD 085-2022 solo publicó el proyecto para comentarios.
  - La RCD 028-2026 modifica el art. 90, no los arts. 93 ni 94.
- **Qué cambia en el motor.** Es la fuente y la vigencia de la regla del pre-chequeo art. 93/94 de la Fase 3. Si no hay respuesta, citaremos la RCD 108-2022 con la marca «por validar».

### DRE-16 · Nuevo TUO de la Ley 27444 (DS 006-2026-JUS)
- **Pregunta.** En el TUO aprobado por el DS 006-2026-JUS (publicado el 30-04-2026), ¿siguen numerados igual los arts. 136.1, 142.1, 143, 144.1, 145.1, 145.2 y 147? ¿Cambió algún plazo?
- **Fuentes.**
  - Leímos y citamos el TUO del DS 004-2019-JUS.
  - Según fuentes secundarias, el DS 006-2026-JUS lo derogó, rige desde el 01-05-2026 y no renumeró.
- **Qué cambia en el motor.** Solo las citas del catálogo, salvo que algún plazo haya cambiado.

### DRE-22 · Art. 90 entre la RCD 037-2024 y la RCD 028-2026
- **Pregunta.**
  1. ¿Qué decía el art. 90 tras la RCD 037-2024 y desde qué fecha rigió?
  2. ¿Qué plazo tenía la EP para informar el uso del fondo por emergencia antes del 01-08-2026?
- **Fuentes.**
  - Texto original del art. 90.2 (compendio): informar «dentro de los siete días hábiles de utilizados los recursos».
  - La RCD 028-2026 cita que la RCD 037-2024 modificó el art. 90, pero no leímos esa resolución.
  - Desde el 01-08-2026 rige el art. 90.3: informe mensual dentro de 10 DH.
- **Qué cambia en el motor.**
  - Hoy la versión original del plazo (PLZ-N-FONDO-EMERGENCIA-V2021) está desactivada, porque no sabemos cuándo dejó de regir.
  - Con la respuesta se activaría esa versión y se agregaría la intermedia.

### DRE-05 · Etapa de evaluación (art. 46) y consulta pública
- **Pregunta.**
  1. ¿Desde qué fecha rige el art. 46 modificado por la RCD 033-2022?
  2. ¿Cómo sabremos si una revisión periódica usó mecanismos de consulta pública? En ese caso el plazo de la etapa es de 120 DH, no 60 (art. 46.4).
- **Fuentes.**
  - Compendio del RGT, art. 46.3 y 46.4. La RCD 124-2025 no modificó el art. 46.
  - DS02 no registra si hubo consulta pública.
- **Qué cambia en el motor.** Habría que agregar un dato al expediente («con consulta pública: sí/no») y una regla de 120 DH.

---

## B. Fuentes que se contradicen

### DRE-09 · Etapa de evaluación: ¿a qué corresponden los 10 DH?
- **Pregunta.** ¿Los 10 DH son para que el equipo SRT culmine el estudio y elabore el informe (hoja Hitos), o para el memo a la GG, la elevación y la RCD que dispone la difusión (flujograma)?
- **Fuentes.**
  - Hitos: `informe_difusion` = 10 DH.
  - Flujograma RP (pág. 10): el informe está dentro del bloque de 50 dh, y los 10 dh («un solo hito o actividad que dura 10 dh») cubren memo, elevación y aprobación.
- **Qué cambia en el motor.** Cambia qué hitos mide la meta de 10 DH (PLZ-I-RP-INFORME-DIFUSION frente a PLZ-I-RP-BLOQUE-DIFUSION). Hoy manda la hoja Hitos y el flujograma se muestra como «discrepancia».

### DRE-11 · Cambio al programa de inversiones: ¿quién firma el memo a la GG?
- **Pregunta.** En el cambio al programa de inversiones, ¿firma el memorándum a la GG la SRT o la DRE?
- **Fuentes.**
  - Hitos: «SRT revisa y firma el memorándum a la GG».
  - Flujograma CPI (pág. 11): la DRE «Revisa y firma Memo a GG».
  - En uso excepcional del FI y en revisión periódica, la hoja Hitos sí pone a la DRE.
- **Qué cambia en el motor.** Cambia el responsable del hito y, con él, la bandeja de quién debe actuar y la carga por unidad. Los plazos no cambian.

### DRE-12 · Uso excepcional del FI: bloques de 24 y 5 DH
- **Pregunta.**
  1. ¿En qué bloque de tiempo está la asignación al equipo SRT?
  2. ¿La firma del informe por la DRE va dentro de los 24 DH o de los 5 DH?
- **Fuentes.**
  - Flujograma UFI (pág. 9): la asignación queda fuera de los dos bloques (1 + 24 + 5 = 30), y la firma del informe por la DRE aparece en el bloque verde.
  - Nota del flujograma: «El Informe es único: SRT visa, DRE firma y OAJ firma».
  - RGT art. 89.3: el informe técnico legal lo elaboran la DRT y la OAJ.
- **Qué cambia en el motor.** Cambian los hitos de PLZ-I-UFI-BLOQUE-24 y PLZ-I-UFI-BLOQUE-5, que hoy se muestran como «solo flujograma».

### DRE-07 · Derivación: ¿1 DH o el mismo día?
- **Pregunta.** ¿La derivación de la DRE a la SRT tiene 1 DH como meta interna, o rige el «mismo día» del TUO?
- **Fuentes.**
  - Hitos y los tres flujogramas: 1 DH.
  - TUO 27444, art. 143.1: a falta de plazo expreso, «dentro del mismo día de su presentación».
- **Qué cambia en el motor.** PLZ-I-DERIVACION pasaría a 0 DH y la alerta se activaría el mismo día.

### DRE-01 · Feriados regionales y días no laborables
- **Pregunta.** ¿El cómputo debe excluir los feriados regionales del ámbito de la EPS y los días no laborables decretados?
- **Fuentes.**
  - TUO 27444, art. 145.1: excluye «los feriados no laborables de orden nacional o regional».
  - Léame: «sin feriados nacionales».
  - Supuestos: «No incluye días no laborables decretados».
- **Qué cambia en el motor.** Habría que llevar un calendario por región (ubigeo de la sede, DS01) y uno de días no laborables decretados.

---

## C. Subplazos que no suman o cuyo cómputo no está claro

### DRE-02 · Suspensión o reinicio del plazo
- **Pregunta.** Cuando la EP subsana o entrega información adicional, ¿el plazo de Sunass se suspende y se reanuda, o empieza a contarse desde la subsanación? ¿La información adicional del CPI y el UFI también suspende el plazo?
- **Fuentes.**
  - Léame: los hitos de la EP «suspenden el plazo de la Sunass».
  - RGT art. 45.2 (no lo modificó la RCD 124-2025): «se suspende el plazo», pero solo para la revisión periódica.
  - TUO art. 142.1: los plazos «se contabilizan una vez efectuada» la subsanación.
  - RGT arts. 89.6 y 93.7: no dicen si la información adicional suspende el plazo.
- **Qué cambia en el motor.** Si es reinicio, la fórmula `inicio + plazo + suspensión` no sirve para la subsanación: el plazo se recalcularía desde la fecha de subsanación. Esto cambia la fecha límite de los expedientes con subsanación.

### DRE-08 · Etapa de inicio de la revisión periódica
- **Pregunta.** Las metas internas de la etapa de inicio suman 1 + 1 + 7 + 10 + 17 = 36 DH, más que los 30 DH de la etapa. ¿Los 10 DH del oficio de subsanación corren en paralelo con la evaluación de requisitos, es decir, dentro de los «diez primeros días hábiles» del art. 45.2? ¿Qué significa la marca de «2 DH» del flujograma?
- **Fuentes.**
  - Hitos: derivación 1, asignación 1, evaluación de requisitos 7, oficio de subsanación 10, informe de inicio 17.
  - Flujograma RP: bloque verde de 7 dh, la nota «el plazo para elaborar el oficio es 10dh», la marca «2 DH» y el bloque rojo de 17 dh.
  - RGT art. 45.2: las observaciones se formulan «dentro de los diez primeros días hábiles del plazo».
- **Qué cambia en el motor.** Si los 10 DH son un tope dentro de la etapa, el oficio de subsanación se mediría desde la solicitud y no desde el fin de la evaluación de requisitos. También cambiarían las metas de PLZ-I-RP-REQUISITOS y PLZ-I-RP-OFICIO-SUB.

### DRE-03 · Inicio de cada etapa de la revisión periódica
- **Pregunta.** ¿Cada etapa cuenta desde el hecho que fija el RGT, o desde el fin de la etapa anterior como en DS02? En particular, ¿la etapa de aprobación empieza al vencer los 45 DH de difusión aunque los comentarios terminen antes?
- **Fuentes.**
  - RGT vigente:
    - etapa 2: desde la resolución de inicio (art. 46.3);
    - etapa 3: desde el día siguiente de la publicación (art. 47.5, RCD 124-2025);
    - etapa 4: desde que transcurre «el plazo señalado en el párrafo 47.5» (art. 49.3). Con la RCD 124-2025, el 47.5 pasó a ser la etapa de difusión de 45 DH; antes era el plazo de comentarios.
  - RGT art. 32.1: la publicación ocurre dentro de los 5 DH siguientes a la emisión.
  - DS02 y Hitos: cada etapa empieza al terminar la anterior.
- **Qué cambia en el motor.** Hoy cada etapa cuenta los días de sus propios hitos, como DS02. Con el criterio literal del RGT, la etapa 4 empezaría al vencer los 45 DH de difusión.

### DRE-21 · Versión de la norma para los procedimientos en trámite
- **Pregunta.**
  1. Para una revisión periódica en trámite el 27-10-2025, ¿se aplica la versión de la norma vigente cuando empezó cada etapa o hito (criterio del motor), o la vigente cuando empezó el procedimiento?
  2. ¿Confirman que la RCD 124-2025 rige desde el 27-10-2025?
- **Fuentes.**
  - La RCD 124-2025 no fija fecha de vigencia. Usamos la regla general: el día siguiente de su publicación (26-10-2025).
  - Sus disposiciones complementarias finales solo regulan los procedimientos suspendidos por la RCD 074-2024, que «continúan considerando el plazo que restaba».
  - El expediente pide «leer los casos con las reglas vigentes en su fecha».
- **Qué cambia en el motor.** Si la respuesta es «la vigente al inicio del procedimiento», el motor elegiría la versión de cada regla con la fecha de inicio del expediente en lugar de la fecha de cada etapa o hito.

### DRE-13 · Base de los 2 DH de subsanación en CPI y UFI
- **Pregunta.** ¿Los 2 DH de subsanación de requisitos TUPA salen del art. 136.1 del TUO o del TUPA de Sunass? ¿Aplican también cuando el equipo SRT observa los requisitos después de la recepción?
- **Fuentes.**
  - Hitos y Flujogramas CPI y UFI: «máx. 2 DH».
  - TUO art. 136.1: 2 DH para observaciones de la unidad de recepción «al momento de su presentación».
  - El RGT no fija este plazo para CPI ni UFI.
- **Qué cambia en el motor.** Cambia la fuente citada y quizá el plazo por defecto de PLZ-O-SUBSANACION-2.

### DRE-06 · Vencimiento del reporte mensual de fondos en día no hábil
- **Pregunta.** Si el día 15 cae en día no hábil, ¿el reporte mensual del fondo vence el siguiente día hábil, como el trimestral?
- **Fuentes.**
  - Supuestos: el trimestral se corre al siguiente hábil; el mensual «vence a los 15 días calendario».
  - TUO art. 145.2: el vencimiento en día inhábil se prorroga al siguiente día hábil.
- **Qué cambia en el motor.** Cambiaría la regla PLZ-N-FONDO-MES y las alertas de reportes mensuales atrasados.

---

## D. Plazos sin norma citada o decisiones de presentación

### DRE-15 · Cómo informar que un procedimiento superó el plazo
- **Pregunta.** ¿Cómo prefieren que la interfaz informe que un procedimiento superó el plazo, considerando que el RGT lo sujeta a silencio administrativo positivo?
- **Fuentes.**
  - RGT arts. 89.8 y 93.9: «El procedimiento administrativo está sujeto a silencio administrativo positivo».
  - En la muestra, CPI-2026-0004 está vencido hace 7 DH al corte.
- **Qué cambia en el motor.** Solo el texto y el tono de la alerta de vencimiento: por ejemplo, si se menciona el silencio positivo, a quién se muestra (especialista, dirección, EPS) y con qué advertencia. **El sistema no declara el silencio:** esa es una decisión de Sunass.

### DRE-17 · Reajuste por IPM: base del primer reajuste
- **Pregunta.** ¿Cómo se fija la base del primer reajuste de un periodo cuando el anterior no está registrado? ¿Sunass sigue el plazo de 90 días calendario para que la EP aplique el reajuste?
- **Fuentes.**
  - RGT art. 82.3: 90 días calendario. La RCD 124-2025 mantuvo ese plazo y agregó el 82.6: la inaplicación «no acarrea su pérdida ni genera recuperos».
  - Supuestos: base en el último reajuste aplicado o en el inicio del periodo.
  - Con DS09 reproducimos 35 de 35 reajustes con base conocida; otros 21 no tienen base en la muestra.
- **Qué cambia en el motor.** Se activaría el reloj PLZ-N-RTI, a cargo de la EP, para los reajustes sin base conocida.

### DRE-18 · Verificación de incrementos: alcance y plazo tras la RCD 124-2025
- **Pregunta.**
  1. Desde el 27-10-2025, ¿Sunass sigue verificando el cumplimiento de metas para aplicar el incremento **base**, o solo verifica las condiciones del incremento **condicionado**?
  2. ¿Qué plazo tiene esa verificación?
- **Fuentes.**
  - Supuestos (la regla que simula DS02): «Se verifica en los años 2 y 3 del periodo con las metas condicionantes del año anterior» y «Plazo supuesto: 30 DH».
  - RGT art. 19.1, en el texto de la RCD 124-2025: «El incremento tarifario base se aplica a partir del primer ciclo de facturación inmediatamente posterior al inicio del año regulatorio correspondiente». Ya no menciona la verificación de metas.
  - RGT art. 19.2, mismo texto: el incremento condicionado se aplica cuando Sunass verifica la culminación del expediente técnico (costos de ejecución) o la entrada en operación de la inversión (operación y mantenimiento).
  - Ningún texto leído fija un plazo para esa verificación.
  - DS02 registra verificaciones por metas también en 2026 (por ejemplo, VCI-2026-0001 y VCI-2026-0002).
- **Qué cambia en el motor.**
  - PLZ-N-VCI tendría dos versiones. Hasta el 26-10-2025 rige la verificación por metas (supuesto de simulación). Desde el 27-10-2025, solo la verificación del incremento condicionado.
  - Las verificaciones por metas de 2026 se rotularían como «regla anterior».

### DRE-23 · Monto total del programa para el 10 % del art. 94
- **Pregunta.** Para los topes del art. 94 (numerales 1 y 6), ¿el «monto total del Programa de Inversiones» es el programado original del estudio tarifario o el vigente tras las modificaciones aprobadas?
- **Fuentes.**
  - RGT art. 94, numerales 1 y 6: «el 10% del monto total del Programa de Inversiones». No precisa si es el original o el vigente.
  - DS03 trae los dos montos (`monto_programado_original` y `monto_programado_vigente`).
- **Qué cambia en el motor.**
  - Hoy el pre-chequeo usa el **original** del periodo vigente, marcado como supuesto en `rules/prechequeo_pi.yaml`, con el parámetro `base_monto_total`.
  - Si es el vigente, cambian los topes de 10 % y S/ 5 000 000 y, con ellos, algunas vías.

### DRE-24 · Causal de los cambios al programa de inversiones
- **Pregunta.**
  1. ¿Dónde registra la DRE la causal del párrafo 93.1, o el 93.2, de cada solicitud de cambio al programa de inversiones?
  2. ¿Por qué un cambio que cabría en el art. 94 llega por el art. 93?
- **Fuentes.**
  - DS02 no registra la causal; solo el proyecto y el «nuevo monto pendiente».
  - Al leer los 9 cambios al programa de inversiones de la muestra como incrementos de monto, todos quedan por debajo del 10 % del art. 94.1 (solo comunicación), aunque DS02 los tramitó por el art. 93.
  - El caso real de Tacna se tramitó por el art. 93.2 (recursos liberados), que según la RCD 032-2026 no exige causal del 93.1.
- **Qué cambia en el motor.**
  - Con la causal registrada, el pre-chequeo dejaría de suponer «incremento de monto» y aplicaría la rama correcta.
  - Hoy, para los expedientes de DS02, se muestra solo como contraste informativo.

### DRE-25 · Qué evidencia confirma que un proyecto está financiado
- **Pregunta.** En la escalera del proyecto, ¿qué documento o registro confirma que un proyecto está «financiado»? Por ejemplo: el estudio tarifario, un convenio de transferencia, un contrato de endeudamiento o el PIM del MEF.
- **Fuentes.**
  - DS03 solo trae `fuente_financiamiento` (fondo de inversiones, transferencia del gobierno nacional, endeudamiento o cooperación), declarada por la EPS.
  - DS08 trae el PIM 2026 del MEF, pero solo para los proyectos con CUI.
- **Qué cambia en el motor.**
  - Hoy el peldaño «financiado» figura como «declarado» (supuesto en `rules/ruta_dinero.yaml`, parámetro `financiado`).
  - Con la evidencia definida, pasaría a «cumplido» solo cuando exista ese registro.

### DRE-26 · Cómo mide la DRE la carga de cada especialista
- **Pregunta.**
  1. ¿Cómo mide hoy la DRE la carga de trabajo de cada especialista?
  2. ¿Pesa igual una revisión periódica que un reporte periódico?
- **Fuentes.**
  - DS02 registra unidades (DRE, SRT, Equipo SRT), no personas: el prototipo usa especialistas ficticios.
  - La hoja Hitos del diccionario muestra que la revisión periódica tiene cuatro etapas y audiencia pública, y que
    el cambio al programa y el uso excepcional exigen informe, memorándum y resolución del Consejo Directivo.
- **Qué cambia en el motor.**
  - Hoy la carga usa pesos por tipo de trámite (supuesto, `rules/tablero.yaml`): revisión periódica 5; cambio al
    programa y uso excepcional 3; verificación de incrementos 2; reporte periódico y reajuste por IPM 1.
  - Con la respuesta cambian la carga por especialista y la propuesta de asignación del tablero.

### DRE-27 · Requisitos del TUPA para cambios al programa de inversiones
- **Pregunta.** ¿Qué documentos exige el TUPA de Sunass para pedir un cambio al programa de inversiones (art. 93) o para comunicarlo (art. 94)?
- **Fuentes.**
  - El RGT solo menciona, en el art. 94, el «oficio dirigido al Gerente General de la Sunass», y en el art. 93.1, que la solicitud es previa a la ejecución.
  - La hoja Hitos del diccionario tiene el hito «verificación de requisitos del TUPA», pero no lista los requisitos.
- **Qué cambia en el motor.**
  - Hoy el portal EPS («¿Qué vía te corresponde?») muestra solo los documentos que menciona la norma citada; los requisitos del TUPA figuran «por validar».
  - Con la lista oficial, la EPS vería todos los documentos con sus casillas antes de presentar.

### DRE-19 · Umbral de alerta «por vencer»
- **Pregunta.** ¿Desde cuántos días hábiles restantes conviene avisar «por vencer»? Hoy usamos 5 DH, como supuesto.
- **Fuentes.** Ninguna. Es un supuesto del equipo (`umbral_por_vencer_dh`).
- **Qué cambia en el motor.** Solo ese parámetro.

### DRE-20 · Canales informales y fecha de inicio del cómputo
- **Pregunta.** Si la EP envía información por correo electrónico o por un enlace externo, como ocurrió en los casos de Tacna y EPSSMU, ¿desde cuándo corre el plazo: desde el envío o desde su ingreso por mesa de partes?
- **Fuentes.**
  - Casos reales del expediente (Tacna, EPSSMU).
  - TUO art. 144.1: el cómputo empieza desde la notificación o publicación del acto.
  - No encontramos una regla para la recepción por canales informales.
- **Qué cambia en el motor.** Define qué fecha toma el registro de documentos de la Fase 3 como inicio del conteo cuando el canal no es la mesa de partes.

---

## E. Producto y datos

### E-1 · Datos reales para la línea base
- **Pregunta.** ¿Existen datos reales de tiempos de atención, o un registro histórico de expedientes de la DRE, que podamos usar para la línea base?
- **Contexto.** El indicador «% de expedientes que superan el plazo máximo» hoy se calcula solo con la muestra simulada (DS02).
- **Qué cambia.** La línea base de `docs/indicadores.md` (Fase 7) pasaría de «muestra simulada» a datos reales, con su fuente.

### E-2 · Qué puede mostrarse en la vista ciudadana
- **Pregunta.** ¿Qué información de fondos e inversiones puede mostrarse en la vista ciudadana? Por ejemplo: saldos del fondo, montos por proyecto, avance físico y usos excepcionales autorizados.
- **Contexto.** La vista ciudadana debe mostrar solo información agregada y no reservada.
- **Qué cambia.** Los permisos de la vista ciudadana (Fase 5) y los campos que expone la API pública.

### E-3 · Lo que ya hace el equipo CIÓN con IA
- **Pregunta.** ¿Qué hace hoy el equipo CIÓN con IA en las modificaciones del programa de inversiones, para no duplicarlo?
- **Contexto.**
  - La Memoria anual 2025 de Sunass menciona IA en modificaciones de programas de inversión.
  - Nuestra Fase 6 propone extraer, con cita textual, la fecha, el plazo y los requerimientos de los oficios.
- **Qué cambia.** El alcance de la Fase 6: complementar lo que ya existe o integrarse a ello.

### E-4 · Verificación posterior del uso del fondo por emergencia (RCD 028-2026)
- **Pregunta.** ¿Qué evidencia y qué área verifican después el uso del fondo de emergencia según la RCD 028-2026?
- **Contexto.** Desde el 01-08-2026, el art. 90 permite usar el fondo sin solicitud ni expediente ante una declaratoria de emergencia por desastres o por peligro inminente.
  - En el caso de peligro inminente, el uso se limita a la reducción del riesgo y la preparación.
  - Solo cubre «costos excedentes e inesperados».
  - La EP remite un informe mensual dentro de los 10 DH siguientes al cierre de cada mes y al término de la declaratoria.
  - La muestra no registra declaratorias, y los dos usos excepcionales de DS05 tienen expediente UFI (art. 89).
- **Qué cambia.**
  - En la ruta del dinero (Fase 4), un uso excepcional sin expediente se mostraría como «uso por emergencia (art. 90): requiere informe mensual», no como error.
  - Se activaría el reloj PLZ-N-FONDO-EMERGENCIA-V2026, siempre que tengamos la fecha y el ámbito de la declaratoria.
  - El último peldaño, «beneficio verificado», necesita saber quién verifica y con qué evidencia.

### E-5 · Intercambio con el SIA, roles y permisos
- **Pregunta.**
  1. ¿Qué formato de intercambio usa hoy el SIA (archivos, servicios, estructura de datos)?
  2. ¿Qué roles y permisos tiene hoy la DRE para ver y editar expedientes?
- **Contexto.** La API de YakuTraza se documenta con OpenAPI para integrarse luego al SIA. La Fase 5 define la matriz de permisos por rol en YAML.
- **Qué cambia.** El esquema de intercambio de la API y la matriz de permisos (`rules/`).

---

## Resueltas

Preguntas que respondieron las normas que el equipo descargó de gob.pe (`docs/normas/`).

### DRE-10 · Etapa de difusión: comentarios y audiencia (resuelta)
- **Qué dice la norma.** RCD 124-2025-SUNASS-CD, que modifica el RGT:
  - **Art. 47.2:** «La audiencia pública debe celebrarse en un plazo máximo de treinta días hábiles contados desde el inicio de la etapa de difusión». El máximo de 30 DH es norma, no solo una meta interna.
  - **Art. 47.4:** «Los interesados y la empresa prestadora pueden formular comentarios hasta el decimoquinto día hábil siguiente a la realización de la audiencia pública». Hay un solo plazo de 15 DH para todos, y desaparecen los 40 DH propios de la EP.
  - **Art. 47.5:** la etapa de difusión dura como máximo 45 DH, contados desde el día siguiente de la publicación.
- **Cómo quedó en el motor.**
  - Nuevas reglas normativas PLZ-N-RP-AUDIENCIA-V2025 y PLZ-N-RP-COMENTARIOS-V2025, vigentes desde el 27-10-2025.
  - La versión anterior se conserva como PLZ-N-RP-COMENTARIOS-V2021, vigente hasta el 26-10-2025. DS02 registra a la EP y a los interesados en un solo hito, que entonces tenían plazos distintos (5 DH y 40 DH). Por eso, para esos casos el motor dice «no puedo comparar» en lugar de calificar.
  - La hoja Hitos y el flujograma coinciden con el texto vigente.

### DRE-04 · Texto vigente de los arts. 45, 47, 48 y 49 (resuelta)
- **Qué dice la norma.** La RCD 124-2025 se emitió el 23-10-2025 y se publicó en El Peruano el 26-10-2025.
  - **Art. 45:** solo cambió el párrafo 45.4 (procedencia). Los plazos del 45.1 (30 DH) y del 45.2 (subsanación de 10 DH, con suspensión) siguen igual.
  - **Arts. 47 y 48:** reescritos (ver DRE-10). El aviso de la audiencia debe publicarse al menos 10 días calendario antes (art. 48.2).
  - **Art. 49.3:** la aprobación sigue en 60 DH, pero ahora cuenta desde que transcurre el plazo del nuevo 47.5, es decir, la etapa de difusión (ver DRE-03).
- **Cómo quedó en el motor.**
  - Cada regla afectada tiene dos versiones: hasta el 26-10-2025 y desde el 27-10-2025.
  - La pregunta que sigue abierta es cuál versión aplica a los procedimientos en trámite (DRE-21).

### DRE-14 (parte resuelta) · Alcance de la RCD 028-2026
- **Qué dice la norma.** La RCD 028-2026-SUNASS-CD (publicada el 31-07-2026, vigente desde el 01-08-2026) **modifica solo el art. 90**: el uso excepcional por declaratoria de emergencia. No toca los arts. 89, 93 ni 94.
  - **Art. 90.1:** el uso procede sin solicitud ante emergencias por desastres o por peligro inminente.
  - **Art. 90.2:** solo cubre «costos excedentes e inesperados». En peligro inminente, se limita a reducción del riesgo y preparación.
  - **Art. 90.3:** la EP remite un informe mensual dentro de 10 DH.
- **Cómo quedó en el motor.**
  - El motor del uso excepcional con expediente (art. 89, 30 DH) no cambia.
  - Se agregó el reloj PLZ-N-FONDO-EMERGENCIA-V2026, que no puede activarse sin datos de la declaratoria (E-4).
  - Lo pendiente de DRE-14 quedó reducido a confirmar la RCD 108-2022.

---

## Anexo: fuentes

| Abreviatura | Documento | Cómo lo leímos |
|---|---|---|
| RGT | Reglamento General de Tarifas, RCD 028-2021-SUNASS-CD (publicado el 27-07-2021; rige desde el día siguiente, art. 3) | Compendio oficial de Sunass, con modificatorias hasta la RCD 004-2023 |
| RCD 124-2025 | Modifica, entre otros, los arts. 31, 32, 37 a 41, 43, 45, 47, 48, 49 y 82 del RGT | `docs/normas/RCD-124-2025-SUNASS-CD.pdf` (El Peruano, 26-10-2025) |
| RCD 028-2026 | Modifica el art. 90 del RGT | `docs/normas/RCD-028-2026-SUNASS-CD_El-Peruano-2026-07-31.pdf` |
| TUO 27444 | TUO de la Ley del Procedimiento Administrativo General, DS 004-2019-JUS | PDF oficial en el CDN de gob.pe (archivo 5320370) |
| RCD 108-2022 | Incorpora el numeral 6 del art. 94 | Nota de modificación del compendio del RGT |
| Hitos, Léame, Supuestos | Hojas del diccionario de variables | Archivo `diccionario_variables.xlsx` |
| Flujograma UFI, RP y CPI | Expediente General del Desafío 3, págs. 9, 10 y 11 | PDF del expediente |

**Lo que no pudimos leer.**
- **RCD 037-2024:** la versión intermedia del art. 90.
- **RCD 033-2022 completa:** usamos la nota del compendio.
- **TUO del DS 006-2026-JUS.**
