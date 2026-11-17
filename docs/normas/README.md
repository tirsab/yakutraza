# Normas leídas

Los PDF de las normas **no se versionan** (`docs/normas/*.pdf` está en `.gitignore`).
Son publicaciones oficiales; para citarlas basta el número, la fecha de publicación y el
enlace oficial. El SHA-256 identifica la copia exacta que leímos: quien descargue el mismo
archivo puede comprobar que es idéntico.

Las citas textuales de cada plazo están en [`rules/plazos.yaml`](../../rules/plazos.yaml)
(sección `fuentes_documentales` y campo `fuentes` de cada regla) y en
[`rules/prechequeo_pi.yaml`](../../rules/prechequeo_pi.yaml).

| Norma | Publicación | Enlace oficial | Copia leída (nombre local) | SHA-256 de la copia leída |
|---|---|---|---|---|
| **RCD N.° 028-2021-SUNASS-CD**, Reglamento General de Tarifas (RGT). Se leyó el compendio de Sunass, que incluye las modificatorias hasta la RCD 004-2023. | 27-07-2021, El Peruano (rige desde el día siguiente, art. 3) | Norma: <https://www.gob.pe/institucion/sunass/normas-legales/2040084-028-2021-cd> · Compendio: <https://cdn.www.gob.pe/uploads/document/file/4388328/> | `compendio_rgt.pdf` | `e03fdd4c7a2905770e621b6743bda38ae4c7b99a30b294d64d302be7c83a73b6` |
| **RCD N.° 028-2021-SUNASS-CD**, texto original del RGT, sin modificatorias | 27-07-2021, El Peruano (separata especial). Rige desde el 28-07-2021 (art. 3). | <https://www.gob.pe/institucion/sunass/normas-legales/2040084-028-2021-cd> (el equipo la descargó de esa página) | `4097674-resolucion-de-consejo-directivo-n-028-2021-sunass-cd.pdf` | `1119b24467d4f125f0d700d747dcac56590ad31e0454759905b1b692d416ec08` |
| **RCD N.° 033-2022-SUNASS-CD**, que modifica, entre otros, los arts. 41 a 44 y 46 del RGT | 16-05-2022, El Peruano, págs. 15-18 y anexos. Rige desde el 17-05-2022 (art. 3). | Sin enlace registrado: copia entregada por el equipo | `RESOLUCION Nº 033-2022-SUNASS-CD.pdf.pdf.pdf` | `a35429c1cb22b94ddfeaecf768e2981b3bd92b9cee0bccd6c0321bb174b04f53` |
| **RCD N.° 037-2024-SUNASS-CD**, que modifica, entre otros, los arts. 19, 51 y 90 del RGT | 05-07-2024, El Peruano, págs. 30-34. Rige desde el 06-07-2024 (art. 5). | Descargada de gob.pe por el equipo (el nombre del archivo corresponde al documento 5730324 del CDN de gob.pe) | `5730324-res-037-2024-sunass-cd.pdf` | `53e2172261c8b941a936f7af867615e250a5f2c28fdcc00dee33d5c66af5212a` |
| **RCD N.° 124-2025-SUNASS-CD**, que modifica, entre otros, los arts. 19, 31, 32, 45, 47, 48, 49 y 82 del RGT | 26-10-2025, El Peruano (separata especial). No fija fecha de vigencia: se usa el día siguiente, 27-10-2025 (por validar). | <https://www.gob.pe/institucion/sunass/normas-legales/7325221-124-2025-sunass-cd> | `RCD-124-2025-SUNASS-CD.pdf` | `a0906460660ed8079ee032d2b625fbe77be0b3cb9c7dce2552c1a400e51da9c9` |
| **RCD N.° 028-2026-SUNASS-CD**, que modifica el art. 90 del RGT (uso excepcional del fondo por declaratoria de emergencia) | 31-07-2026, El Peruano, págs. 9-10. Rige desde el 01-08-2026 (art. 2). | <https://busquedas.elperuano.pe/dispositivo/NL/2538837-1> (código del dispositivo impreso en la publicación: 2538837-1) | `RCD-028-2026-SUNASS-CD_El-Peruano-2026-07-31.pdf` | `8fec72730ef97bddbecf805ad2c7c04721a33ca82ca4c9acf3e1f9dcc9a0dd19` |
| **Decreto Supremo N.° 006-2026-JUS**, nuevo TUO de la Ley 27444. Deroga el DS 004-2019-JUS y renumera sus artículos sin cambiar el texto. | 30-04-2026, El Peruano (separata especial). No fija vigencia: se usa el día siguiente, 01-05-2026 (por validar). | Copia de un **sitio secundario**, LP Derecho: <https://img.lpderecho.pe/wp-content/uploads/2026/04/DECRETO-SUPREMO-006-2026-JUS-LPDerecho.pdf>. Su contenido corresponde a la separata oficial de El Peruano del 30-04-2026. | `DECRETO-SUPREMO-006-2026-JUS-LPDerecho.pdf` | `2cf6fcce04b87dd5a7a6b7581e44ccccb84cb7e47d04e6ad233f056d6fba249d` |
| **Decreto Supremo N.° 004-2019-JUS**, TUO de la Ley 27444, Ley del Procedimiento Administrativo General (derogado desde el 01-05-2026) | 25-01-2019, El Peruano | <https://cdn.www.gob.pe/uploads/document/file/5320370/4770872-decreto-supremo-n-004-2019-jus.pdf> | `tuo_27444_ds004_2019.pdf` | `01224f0288f9ad47e4f8def4e89aa2b1eb1ba7dd7b11a2c7a660ce08b09fe6ba` |

**Notas**
- La copia de la RCD 028-2026 es la página completa de El Peruano. Incluye otras normas de esa edición que no se usan en el proyecto.
- La copia del nuevo TUO (DS 006-2026-JUS) viene de un sitio secundario, LP Derecho. Su contenido corresponde a la separata oficial de El Peruano del 30-04-2026 (portada, fecha y numeración de páginas de El Peruano). La correspondencia entre la numeración anterior y la nueva está en `docs/preguntas_para_la_DRE.md` (DRE-16, resuelta).
- La página de gob.pe de la RCD 028-2021 lista «Modificado por: RCD 037-2024», pero esa lista no está completa (también la modificaron, entre otras, las RCD 033-2022, 108-2022, 004-2023, 124-2025 y 028-2026). El historial de modificaciones se toma de cada resolución y del compendio, no de esa lista.
- La RCD 108-2022-SUNASS-CD, que incorporó el numeral 6 del art. 94, se cita por la nota de modificación del compendio del RGT. No se leyó la resolución misma.
- Los PDF de las RCD 124-2025 y 028-2026 estuvieron versionados en el commit `3ccf67a` y siguen en ese historial, porque se decidió no reescribirlo. Desde la Fase 3 ya no se versionan.

**Para trabajar con las normas en local:** copie los PDF a esta carpeta con los nombres de la columna «Copia leída» y compruebe el SHA-256:

```bash
sha256sum docs/normas/*.pdf
```
