# Preguntas para la DRE (mentoría)

YakuTraza · Hackathon Sunass «Lideresas por el Agua» · Desafío 3
Versión de trabajo de la Fase 2 (motor de plazos). Fecha de corte de la muestra: 2026-09-30.

Todas las reglas de plazo del prototipo están **«por validar»**. Este documento reúne cada
discrepancia entre fuentes, cada subplazo que no suma y cada plazo sin norma citada que encontramos.
Para cada punto indicamos la pregunta concreta, las fuentes que se contradicen y qué cambia en el
motor según la respuesta. Los identificadores (DRE-01, DRE-02…) son los que aparecen en
`rules/plazos.yaml`, en el campo `pregunta_dre`.

**Fuentes citadas.** Las abreviaturas (Hitos, Léame, Supuestos, Flujograma, DS02) y las copias de las
normas que leímos están en el [anexo](#anexo-fuentes-y-lo-que-no-pudimos-leer).

---

## A. Normas que no pudimos leer o verificar

### DRE-04 · Texto vigente de los arts. 45, 47, 48 y 49 (RCD 124-2025-SUNASS-CD)
- **Pregunta.**
  1. ¿Cuál es el texto vigente de los arts. 45, 47, 48 y 49 del RGT tras la RCD 124-2025 y desde qué fecha rige?
  2. ¿Qué regla se aplica a las revisiones periódicas que empezaron antes de esa fecha?
- **Fuentes.**
  - El expediente (Anexo) dice que la RCD 124-2025 modificó esos artículos y que «los casos anteriores deben leerse con las reglas vigentes en su fecha».
  - Solo leímos la versión anterior: el compendio oficial, actualizado a la RCD 004-2023.
  - No obtuvimos el texto de la 124-2025, porque gob.pe bloquea el acceso automatizado.
- **Qué cambia en el motor.** Se llenan `vigente_desde` y `vigente_hasta` de las reglas PLZ-N-RP-1, -3 y -4. Si los plazos cambiaron, se agrega una versión nueva de cada regla. El motor elegiría la versión según la fecha de inicio del expediente.

### DRE-14 · ¿Qué RCD incorporó el numeral 6 del art. 94?
- **Pregunta.** ¿Confirman que el numeral 6 del art. 94 lo incorporó la RCD 108-2022-SUNASS-CD (publicada el 17-11-2022) y no la RCD 085-2022? ¿Hay modificaciones posteriores de los arts. 93 y 94, por ejemplo la «RCD 028-2026» que cita nuestro documento técnico?
- **Fuentes.**
  - El compendio oficial del RGT anota en el art. 94: «Numeral incorporado por la Resolución De Consejo Directivo N.º 108-2022-SUNASS-CD, publicada el 17 de noviembre del 2022».
  - La matriz de comentarios de la RCD 085-2022 indica que esa resolución solo dispuso publicar el **proyecto** para comentarios (19-09-2022).
  - Nuestro documento técnico y el encargo del pre-chequeo citan la «RCD 085-2022».
- **Qué cambia en el motor.** Es la fuente y la vigencia de la regla del pre-chequeo art. 93/94 de la Fase 3. Si no hay respuesta, citaremos la RCD 108-2022 (según el compendio) con la marca «por validar».

### DRE-16 · Nuevo TUO de la Ley 27444 (DS 006-2026-JUS)
- **Pregunta.** En el TUO aprobado por el DS 006-2026-JUS (publicado el 30-04-2026), ¿siguen numerados igual los arts. 136.1, 142.1, 143, 144.1, 145.1, 145.2 y 147? ¿Cambió algún plazo?
- **Fuentes.**
  - Leímos y citamos el TUO del DS 004-2019-JUS.
  - Según fuentes secundarias, el DS 006-2026-JUS lo derogó, entró en vigencia el 01-05-2026 y no renumeró.
- **Qué cambia en el motor.** Solo las citas del catálogo, salvo que algún plazo haya cambiado.

### DRE-05 · Etapa de evaluación (art. 46) y consulta pública
- **Pregunta.**
  1. ¿Desde qué fecha rige el art. 46 modificado por la RCD 033-2022?
  2. ¿Cómo sabremos si una revisión periódica usó mecanismos de consulta pública? En ese caso el plazo de la etapa es de 120 DH, no 60 (art. 46.4).
- **Fuentes.**
  - Compendio del RGT, art. 46.3 y 46.4.
  - DS02 no registra si hubo consulta pública.
- **Qué cambia en el motor.** Habría que agregar un dato al expediente («con consulta pública: sí/no») y una regla de 120 DH. Mientras tanto, la etapa 2 usa 60 DH.

---

## B. Fuentes que se contradicen

### DRE-10 · Etapa de difusión: comentarios y audiencia
- **Pregunta.**
  1. ¿Cuál es hoy el plazo de comentarios: 15 DH después de la audiencia, o hasta el 5.º DH (interesados)?
  2. ¿La EP tiene un plazo propio de 40 DH improrrogables?
  3. ¿El máximo de 30 DH para la audiencia es una norma o una meta interna?
- **Fuentes.**
  - Hitos y Flujograma RP (pág. 10): comentarios «hasta 15 DH tras la audiencia»; audiencia «máx. 30 DH».
  - RGT, versión anterior a la RCD 124-2025:
    - art. 47.5: interesados «hasta el quinto día hábil siguiente a la realización de la audiencia pública»;
    - art. 47.4: la EP tiene «un plazo improrrogable de cuarenta días hábiles», contado desde la notificación del proyecto;
    - art. 48.3: al menos 10 días calendario entre el aviso de convocatoria y la audiencia, sin máximo.
- **Qué cambia en el motor.**
  - Comentarios: si rige el RGT, PLZ-I-RP-COMENTARIOS pasaría a 5 DH y a reloj normativo.
  - Comentarios de la EP: se activaría la regla PLZ-O-RP-COMENTARIOS-EP-40, que hoy está desactivada porque DS02 no tiene ese hito.
  - Audiencia: si el máximo de 30 DH es meta interna, se queda en el reloj interno.

### DRE-09 · Etapa de evaluación: ¿a qué corresponden los 10 DH?
- **Pregunta.** ¿Los 10 DH son para que el equipo SRT culmine el estudio y elabore el informe (hoja Hitos), o para el memo a la GG, la elevación y la RCD que dispone la difusión (flujograma)?
- **Fuentes.**
  - Hitos: `informe_difusion` = 10 DH.
  - Flujograma RP: el informe está dentro del bloque de 50 dh, y los 10 dh («un solo hito o actividad que dura 10 dh») cubren memo, elevación y aprobación.
- **Qué cambia en el motor.** Cambia qué hitos mide la meta de 10 DH (PLZ-I-RP-INFORME-DIFUSION frente a PLZ-I-RP-BLOQUE-DIFUSION) y el bloque de 50 DH (PLZ-I-RP-PROYECTO). Hoy manda la hoja Hitos y el flujograma se muestra como «discrepancia».

### DRE-11 · Cambio al programa de inversiones: ¿quién firma el memo a la GG?
- **Pregunta.** En el cambio al programa de inversiones, ¿firma el memorándum a la GG la SRT o la DRE?
- **Fuentes.**
  - Hitos: `memo_gg` = «SRT revisa y firma el memorándum a la GG» (responsable SRT).
  - Flujograma CPI (pág. 11): la DRE «Revisa y firma Memo a GG».
  - En uso excepcional del FI y en revisión periódica, Hitos sí pone a la DRE.
- **Qué cambia en el motor.** Cambia el responsable del hito y, con él, la bandeja de quién debe actuar y la carga por unidad del tablero (Fase 5). Los plazos no cambian.

### DRE-12 · Uso excepcional del FI: bloques de 24 y 5 DH
- **Pregunta.**
  1. ¿En qué bloque de tiempo está la asignación al equipo SRT?
  2. ¿La firma del informe por la DRE va dentro de los 24 DH o de los 5 DH?
- **Fuentes.**
  - Flujograma UFI (pág. 9): el bloque rojo de 24 dh empieza en «Verifica requisitos del TUPA» y termina en la firma de la OAJ; el bloque verde de 5 dh incluye la firma del memo y la del informe por la DRE, la elevación y el CD. La asignación queda fuera de ambos (1 + 24 + 5 = 30).
  - La nota del flujograma dice: «El Informe es único: SRT visa, DRE firma y OAJ firma».
  - RGT art. 89.3: el informe técnico legal lo elaboran la DRT y la OAJ.
- **Qué cambia en el motor.** Cambian los hitos de PLZ-I-UFI-BLOQUE-24 y PLZ-I-UFI-BLOQUE-5. La hoja Hitos no da plazo a estos hitos, así que hoy se muestran como «solo flujograma».

### DRE-07 · Derivación: ¿1 DH o el mismo día?
- **Pregunta.** ¿La derivación de la DRE a la SRT tiene 1 DH como meta interna, o rige el «mismo día» del TUO?
- **Fuentes.**
  - Hitos y los tres flujogramas: 1 DH.
  - TUO 27444, art. 143.1: a falta de plazo expreso, la recepción y derivación se hacen «dentro del mismo día de su presentación».
- **Qué cambia en el motor.** PLZ-I-DERIVACION pasaría a 0 DH y la alerta se activaría el mismo día.

### DRE-01 · Feriados regionales y días no laborables
- **Pregunta.** ¿El cómputo debe excluir los feriados regionales del ámbito de la EPS y los días no laborables decretados?
- **Fuentes.**
  - TUO 27444, art. 145.1: excluye «los feriados no laborables de orden nacional o regional» y los días no laborables del servicio.
  - Léame: «sin feriados nacionales».
  - Supuestos: «No incluye días no laborables decretados».
- **Qué cambia en el motor.** Habría que llevar un calendario por región (ubigeo de la sede, DS01) y uno de días no laborables decretados. Hoy solo se usan los feriados nacionales.

---

## C. Subplazos que no suman o cuyo cómputo no está claro

### DRE-08 · Etapa de inicio de la revisión periódica
- **Pregunta.** Las metas internas de la etapa de inicio suman 1 + 1 + 7 + 10 + 17 = 36 DH, más que los 30 DH de la etapa. ¿Los 10 DH del oficio de subsanación corren en paralelo con la evaluación de requisitos, es decir, dentro de los «diez primeros días hábiles» del art. 45.2? ¿Y qué significa la marca de «2 DH» junto a la firma del oficio en el flujograma?
- **Fuentes.**
  - Hitos: derivación 1, asignación 1, evaluación de requisitos 7, oficio de subsanación 10, informe de inicio 17.
  - Flujograma RP: bloque verde de 7 dh (que incluye asignación y proyecto de oficio), la nota «el plazo para elaborar el oficio es 10dh», la marca «2 DH» y el bloque rojo de 17 dh.
  - RGT art. 45.2: las observaciones se formulan «dentro de los diez primeros días hábiles del plazo».
- **Qué cambia en el motor.** Si los 10 DH son un tope dentro de la etapa, el oficio de subsanación se mediría desde la solicitud y no desde el fin de la evaluación de requisitos. También cambiarían las metas de PLZ-I-RP-REQUISITOS y PLZ-I-RP-OFICIO-SUB.

### DRE-03 · Inicio de cada etapa de la revisión periódica
- **Pregunta.** ¿Cada etapa cuenta desde el hito que fija el RGT, o desde el fin de la etapa anterior como en DS02?
- **Fuentes.**
  - RGT: la etapa 2 cuenta desde el día siguiente de la resolución de inicio (art. 46.3); la 3, desde la publicación en El Peruano (art. 47.6, y la nota del flujograma); la 4, desde que vence el plazo de comentarios (art. 49.3).
  - RGT art. 32.1: la publicación ocurre «dentro de los cinco días hábiles siguientes» a la emisión.
  - DS02 y Hitos: la etapa 3 incluye el hito `publicacion` y el total suma 195 DH.
- **Qué cambia en el motor.** Hoy cada etapa cuenta los días de sus propios hitos, como DS02. Con el criterio del RGT, la etapa 3 empezaría al día siguiente de la publicación, y ese hito podría tener una meta propia de 5 DH (art. 32.1).

### DRE-02 · Suspensión o reinicio del plazo
- **Pregunta.** Cuando la EP subsana o entrega información adicional, ¿el plazo de Sunass se suspende y se reanuda, o empieza a contarse desde la subsanación? ¿La información adicional del CPI y el UFI también suspende el plazo?
- **Fuentes.**
  - Léame: los hitos de la EP «suspenden el plazo de la Sunass».
  - RGT art. 45.2: «se suspende el plazo», pero solo para la revisión periódica.
  - TUO art. 142.1: los plazos «se contabilizan una vez efectuada» la subsanación.
  - RGT arts. 89.6 y 93.7 (CPI y UFI): no dicen si la información adicional suspende el plazo.
- **Qué cambia en el motor.** Si es reinicio, la fórmula `inicio + plazo + suspensión` no sirve para la subsanación: el plazo se recalcularía desde la fecha de subsanación. Esto cambia la fecha límite de los expedientes con subsanación.

### DRE-13 · Base de los 2 DH de subsanación en CPI y UFI
- **Pregunta.** ¿Los 2 DH de subsanación de requisitos TUPA salen del art. 136.1 del TUO o de otra norma (el TUPA de Sunass)? ¿Aplican también cuando el equipo SRT observa los requisitos después de la recepción?
- **Fuentes.**
  - Hitos y Flujogramas CPI y UFI: «EP subsana, máx. 2 DH».
  - TUO art. 136.1: 2 DH para las observaciones que hace la unidad de recepción «al momento de su presentación».
  - El RGT leído no fija este plazo para CPI ni UFI.
- **Qué cambia en el motor.** Cambia la fuente citada y quizá el plazo por defecto de PLZ-O-SUBSANACION-2.

### DRE-06 · Vencimiento del reporte mensual de fondos en día no hábil
- **Pregunta.** Si el día 15 cae en día no hábil, ¿el reporte mensual del fondo vence el siguiente día hábil, como el trimestral?
- **Fuentes.**
  - Supuestos: el trimestral se corre al siguiente hábil; del mensual solo dice «vence a los 15 días calendario».
  - TUO art. 145.2: el vencimiento en día inhábil se prorroga al siguiente día hábil.
- **Qué cambia en el motor.** Cambiaría la regla PLZ-N-FONDO-MES y, con ella, las alertas de reportes mensuales atrasados.

---

## D. Plazos sin norma citada o que la muestra no trae

### DRE-17 · Plazo para aplicar el reajuste por IPM
- **Pregunta.** ¿Sunass sigue el plazo del art. 82.3 del RGT (90 días calendario para que la EP aplique el reajuste)? ¿Cómo se fija la base del primer reajuste de un periodo cuando el anterior no está registrado?
- **Fuentes.**
  - RGT arts. 80 y 82.3.
  - Supuestos: base en el último reajuste aplicado o en el inicio del periodo.
  - DS02 no trae plazo para el reajuste.
  - Con DS09 reproducimos 35 de 35 reajustes con base conocida; otros 21 no tienen base en la muestra.
- **Qué cambia en el motor.** Se activaría un reloj normativo a cargo de la EP (PLZ-N-RTI) y la alerta «reajuste no aplicado a tiempo».

### DRE-18 · Plazo de la verificación de incrementos
- **Pregunta.** ¿Qué plazo tiene la verificación de condiciones para los incrementos tarifarios?
- **Fuentes.**
  - Supuestos: «Plazo supuesto: 30 DH».
  - RGT arts. 19.2 y 19.3: regulan la verificación pero no le fijan plazo.
- **Qué cambia en el motor.** Cambia PLZ-N-VCI, que hoy está rotulada «supuesto de simulación».

### DRE-15 · Silencio administrativo positivo
- **Pregunta.** Cuando un CPI o un UFI supera los 30 DH sin resolución, ¿la interfaz debe advertir que el procedimiento está sujeto a silencio administrativo positivo? Por ejemplo, CPI-2026-0004 de la muestra está vencido hace 7 DH al corte.
- **Fuentes.**
  - RGT arts. 89.8 y 93.9: «El procedimiento administrativo está sujeto a silencio administrativo positivo».
- **Qué cambia en el motor.** Solo cambiaría el texto informativo de la alerta de vencimiento. **El sistema no declararía el silencio:** esa es una decisión de Sunass.

### DRE-19 · Umbral de alerta «por vencer»
- **Pregunta.** ¿Desde cuántos días hábiles restantes conviene avisar «por vencer»? Hoy usamos 5 DH, como supuesto.
- **Fuentes.** Ninguna. Es un supuesto del equipo (`rules/plazos.yaml`, `umbral_por_vencer_dh`).
- **Qué cambia en el motor.** Solo ese parámetro.

### DRE-20 · Canales informales y fecha de inicio del cómputo
- **Pregunta.** Si la EP envía información por correo electrónico o por un enlace externo, como ocurrió en los casos de Tacna y EPSSMU, ¿desde cuándo corre el plazo: desde el envío o desde su ingreso por mesa de partes?
- **Fuentes.**
  - Casos reales del expediente (Tacna, EPSSMU).
  - TUO art. 144.1: el cómputo empieza desde la notificación o publicación del acto.
  - No encontramos una regla para la recepción por canales informales.
- **Qué cambia en el motor.** Define qué fecha toma el registro de documentos de la Fase 3 como inicio del conteo cuando el canal no es la mesa de partes.

---

## Anexo: fuentes y lo que no pudimos leer

| Abreviatura | Documento | Cómo lo leímos |
|---|---|---|
| RGT | Reglamento General de Tarifas, RCD 028-2021-SUNASS-CD (publicado el 27-07-2021; rige desde el día siguiente, art. 3) | Compendio oficial de Sunass en el CDN de gob.pe (archivo 4388328), con modificatorias hasta la RCD 004-2023 (20-01-2023) |
| TUO 27444 | TUO de la Ley del Procedimiento Administrativo General, DS 004-2019-JUS | PDF oficial en el CDN de gob.pe (archivo 5320370) |
| RCD 108-2022 | Incorpora el numeral 6 del art. 94 | Nota de modificación del compendio del RGT |
| RCD 085-2022 | Publica el proyecto de modificación de los arts. 93 y 94 para comentarios | Matriz de comentarios (CDN de gob.pe, archivo 3847948) |
| Hitos, Léame, Supuestos | Hojas del diccionario de variables | Archivo `diccionario_variables.xlsx` |
| Flujograma UFI, RP y CPI | Expediente General del Desafío 3, págs. 9, 10 y 11 | PDF del expediente |

**Lo que no pudimos leer.**
- **RCD 124-2025-SUNASS-CD:** gob.pe devuelve «Acceso restringido» y no ubicamos el dispositivo en El Peruano.
- **El nuevo TUO (DS 006-2026-JUS).**
- **Las RCD 033-2022 y 108-2022 completas.** Usamos sus notas en el compendio.

Si la DRE nos comparte esos PDF, los citamos directamente.
