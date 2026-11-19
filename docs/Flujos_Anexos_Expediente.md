# Flujos de los anexos del Expediente del Desafío 3 (verificados contra los diagramas)

> Para Claude Code. Guarda este archivo en `docs/Flujos_Anexos_Expediente.md`. Es la descripción textual de los tres flujogramas del Expediente General del Desafío 3 (págs. 9 a 11), revisada contra las imágenes. Úsala como referencia para `rules/plazos.yaml`, `rules/pasos_procedimiento.yaml` y la barra de pasos de la interfaz.
>
> **Regla general del expediente:** los flujogramas son propuestas de secuencia y metas internas de tiempo. No reemplazan el RGT ni crean plazos legales. La solución debe separar: (a) el plazo normativo vigente, (b) la meta interna de gestión y (c) el plazo fijado en cada oficio o prórroga.
>
> **Carriles (responsables):** EP (empresa prestadora), DRE (Dirección de Regulación Económica), SRT (Subdirección de Regulación Tarifaria), Equipo SRT, OAJ (Oficina de Asesoría Jurídica, solo en el Anexo 2), DU (Dirección de Usuarios, solo en el Anexo D), GG (Gerencia General) y CD (Consejo Directivo).

---

## Anexo 2 · Uso excepcional del Fondo de Inversiones (art. 89 RGT)

**Plazo máximo del procedimiento:** 30 DH.

**Metas por bloque:**
- **Derivación:** 1 DH (DRE → SRT). Queda **fuera** de los dos bloques.
- **Asignación al Equipo SRT:** también queda **fuera** de los dos bloques en el diagrama (1 + 24 + 5 = 30).
- **Bloque rojo, 24 dh:** desde «Verifica requisitos del TUPA» hasta la firma del informe por la OAJ. Incluye la subsanación, la información adicional, el informe con el proyecto de resolución, el visado de la SRT y la firma de la OAJ.
- **Bloque verde, 5 dh:** la firma del memo a la GG y del informe por la DRE, la elevación de la GG y la aprobación del CD.

**Regla del informe único:** el informe técnico-legal es un solo documento: la SRT lo visa, la DRE lo firma y la OAJ lo firma.

**Secuencia:**
1. **EP** presenta la solicitud por Mesa de Partes.
2. **DRE** deriva a la SRT (meta: 1 DH).
3. **SRT** asigna al Equipo SRT.
4. **Equipo SRT** verifica los requisitos del TUPA. **¿Cumple?**
   - **No:**
     - el Equipo SRT elabora el proyecto de oficio de subsanación;
     - la SRT revisa y firma el oficio;
     - la EP subsana en un **máximo de 2 DH**. **¿Subsana?**
       - **No:** la DRE dispone que **se archive el procedimiento**. Fin.
       - **Sí:** la subsanación reingresa por Mesa de Partes → DRE → SRT → Equipo SRT. En el diagrama la flecha vuelve a la **verificación de requisitos** (ver la diferencia 2).
   - **Sí:** el Equipo SRT evalúa la información.
5. **¿Requiere información adicional?**
   - **Sí:**
     - el Equipo SRT elabora el proyecto de oficio;
     - la SRT revisa y firma el oficio;
     - la EP remite la información en **hasta 10 DH**;
     - la información retorna por DRE → SRT → Equipo.
   - **No:** continúa.
6. **Equipo SRT** evalúa la información y elabora el informe y el proyecto de resolución.
7. **SRT** revisa y **visa** el informe.
8. **OAJ** revisa y **firma** el informe. Aquí cierra el bloque de 24 dh.
9. **DRE** firma el memo a la GG y revisa y **firma** el informe. Aquí empieza el bloque de 5 dh.
10. **GG** eleva al Consejo Directivo.
11. **CD** aprueba la resolución. Fin.

---

## Anexo E · Cambio al programa de inversiones (art. 93 RGT)

**Plazo máximo del procedimiento:** 30 DH.

**Metas por bloque:**
- **Derivación:** 1 DH (DRE → SRT), fuera de los bloques.
- **Bloque amarillo, 24 dh:** desde la **asignación** al Equipo SRT hasta la revisión y firma del informe por la SRT. Incluye la verificación del TUPA, la subsanación, la información adicional y el informe con el proyecto de resolución.
- **Bloque verde, 5 dh:** la firma del memo a la GG por la DRE, la elevación de la GG y la aprobación del CD.

Este flujo **no tiene carril de OAJ**.

**Secuencia:**
1. **EP** presenta la solicitud por Mesa de Partes.
2. **DRE** deriva a la SRT (meta: 1 DH).
3. **SRT** asigna al Equipo SRT. Aquí empieza el bloque de 24 dh.
4. **Equipo SRT** verifica los requisitos del TUPA. **¿Cumple?**
   - **No:**
     - el Equipo SRT elabora el proyecto de oficio de subsanación;
     - la SRT revisa y firma el oficio;
     - la EP subsana en un **máximo de 2 DH**. **¿Subsana?**
       - **No:** **se cierra el procedimiento** (carril de la DRE). Fin.
       - **Sí:** reingresa por Mesa de Partes → DRE → SRT → Equipo SRT.
   - **Sí:** el Equipo SRT evalúa la información.
5. **¿Requiere información adicional?**
   - **Sí:**
     - el Equipo SRT elabora el proyecto de oficio;
     - la SRT revisa y firma el oficio;
     - la EP remite la información en **hasta 10 DH**;
     - la información retorna por DRE → SRT → Equipo.
   - **No:** continúa.
6. **Equipo SRT** evalúa la información y elabora el informe y el proyecto de resolución.
7. **SRT** revisa y **firma el informe**. Aquí cierra el bloque de 24 dh.
8. **DRE** revisa y **firma el memo a la GG**. Aquí empieza el bloque de 5 dh. En el diagrama, la DRE **no** firma el informe en este flujo (ver la diferencia 1).
9. **GG** eleva al Consejo Directivo.
10. **CD** aprueba la resolución. Fin.

---

## Anexo D · Revisión periódica (arts. 45 a 49 RGT)

Son cuatro etapas, con su plazo máximo cada una.

**Leyenda del diagrama:**
- rectángulo blanco: actividad;
- rombo amarillo: decisión;
- rectángulo celeste: hito o resolución;
- recuadros punteados: metas de tiempo.

### Etapa 1 · Inicio (máximo 30 DH)
1. **EP o interesados** presentan la solicitud, o el oficio subsanando, por Mesa de Partes.
2. **DRE** deriva a la SRT. Marca de **1 DH**.
3. **SRT** asigna al Equipo SRT. Marca de **1 DH**.
4. **Equipo SRT** evalúa los requisitos. **¿Cumple?**
   - **No:**
     - el Equipo SRT elabora el proyecto de oficio;
     - la SRT revisa el proyecto de oficio;
     - la **DRE firma el oficio**. Marca de **2 DH** y nota del diagrama: «el plazo para elaborar el oficio es 10dh» (ver la diferencia 3);
     - la EP subsana en un **máximo de 10 DH** y reingresa por Mesa de Partes.
   - **Sí:** continúa.
5. **Equipo SRT** elabora el informe y el proyecto de resolución.
6. **SRT** revisa y firma el informe.
7. **DRE** emite la **resolución de inicio, inadmisibilidad o improcedencia** (hito).

**Recuadros de la etapa 1:**
- **verde claro, 7 dh:** asignación, evaluación de requisitos, y proyecto y revisión del oficio;
- **rojo, 17 dh:** informe, firma de la SRT y resolución de la DRE.

### Etapa 2 · Evaluación (máximo 60 DH)
1. **Equipo SRT** elabora el proyecto de estudio tarifario y el proyecto de resolución tarifaria.
2. **¿Requiere información de la EP?**
   - **Sí:**
     - el Equipo SRT elabora el proyecto de oficio;
     - la SRT revisa el oficio;
     - la DRE firma el oficio;
     - la EP remite la información en un **máximo de 10 DH**.
   - **No:** continúa.
3. **Equipo SRT** culmina el estudio tarifario y el proyecto de resolución tarifaria, y elabora el informe y el memo.
4. **SRT** revisa los documentos y firma el informe.
5. **DRE** revisa y firma el memo a la GG.
6. **GG** eleva al CD.
7. **CD** aprueba la difusión.

**Recuadros de la etapa 2:**
- **amarillo, 50 dh:** pasos 1 a 4;
- **celeste, 10 dh:** pasos 5 a 7, que el diagrama trata como «un solo hito o actividad que dura 10 dh».

### Etapa 3 · Difusión (máximo 45 DH, contados desde el día siguiente de la publicación en El Peruano)
1. **CD:** resolución que dispone la difusión (hito).
2. **DU** fija el día, la hora y el lugar, y realiza la audiencia, en un **máximo de 30 dh**.
3. **EP e interesados** formulan comentarios **hasta 15 DH después de la audiencia**.

Estos plazos coinciden con el texto vigente del RGT tras la RCD 124-2025 (arts. 47.2, 47.4 y 47.5).

### Etapa 4 · Aprobación (máximo 60 DH)
1. **EP o interesados:** vence el plazo para comentarios. Es el fin de la etapa 3.
2. **Equipo SRT** evalúa los comentarios y elabora el informe, el estudio tarifario final y el proyecto de resolución tarifaria final.
3. **SRT** revisa los documentos y firma el informe.
4. **DRE** revisa y firma el memo a la GG.
5. **GG** eleva al CD.
6. **CD** aprueba la resolución tarifaria. Fin del procedimiento.

**Recuadros de la etapa 4:**
- **naranja, 50 dh:** pasos 2 y 3;
- **verde oscuro, 10 dh:** pasos 4 a 6, tratados como «un solo hito que dura 10 dh».

---

## Diferencias entre el texto de trabajo y los diagramas

Al comparar la descripción textual que preparó el equipo con las imágenes, encontramos tres puntos en los que manda el diagrama:

1. **Anexo E: la DRE no firma el informe.** El texto de trabajo decía «DRE: revisa y firma el Informe y el Memo». En el diagrama, la DRE solo **revisa y firma el memo a la GG**, y quien firma el informe es la SRT. A diferencia del Anexo 2, aquí no hay regla de informe único con firma de la DRE ni de la OAJ.
2. **Anexo 2: tras la subsanación, se vuelve a verificar.** El texto de trabajo decía que, si la EP subsana, «pasa directamente a la evaluación de información». En el diagrama, la flecha del «Sí» vuelve a entrar por Mesa de Partes → DRE → SRT → Equipo SRT y llega a la **verificación de requisitos**. Es razonable: lo subsanado se vuelve a revisar.
3. **Anexo 2: la asignación queda fuera del bloque de 24 dh.** El texto de trabajo decía que el bloque rojo «abarca desde la asignación al Equipo SRT». En el diagrama, el recuadro rojo empieza en «Verifica requisitos del TUPA», y la asignación queda fuera. En cambio, en el **Anexo E** el recuadro amarillo **sí** incluye la asignación.

Hay además un matiz de redacción en el **Anexo D**: la nota dice «el plazo para elaborar el oficio es 10dh», no «el plazo legal». Junto a la marca de 2 DH, es justamente la pregunta DRE-08 para la mentoría.

## Relación con las preguntas para la DRE

- **DRE-11:** en el Anexo E, la hoja Hitos del diccionario dice que la SRT firma el memo a la GG, y el diagrama dice la DRE.
- **DRE-12:** en el Anexo 2, la asignación queda fuera de los bloques, y la DRE firma el informe dentro del bloque de 5 dh.
- **DRE-08:** en la etapa de inicio del Anexo D, las metas suman 36 DH frente a los 30 DH de la etapa.
- **DRE-09:** en la etapa 2 del Anexo D, el bloque de 10 dh corresponde al memo, la elevación y la aprobación, mientras que la hoja Hitos asigna esos 10 DH al informe.

## Qué debe revisar Claude Code con este archivo

1. Que `rules/plazos.yaml` y `rules/pasos_procedimiento.yaml` reflejen exactamente estos pasos, responsables y bloques, citando «Flujograma, Anexo 2 / D / E, pág. 9 / 10 / 11».
2. Que la barra de pasos y la línea de tiempo usen los mismos nombres de pasos y responsables.
3. Que en el Anexo E ningún hito diga que la DRE firma el informe.
4. Que, tras una subsanación del Anexo 2, el expediente vuelva a la verificación de requisitos.
5. Que la asignación quede fuera del bloque de 24 dh en el Anexo 2 y dentro en el Anexo E.
