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
| **RCD N.° 124-2025-SUNASS-CD**, que modifica, entre otros, los arts. 19, 31, 32, 45, 47, 48, 49 y 82 del RGT | 26-10-2025, El Peruano (separata especial). No fija fecha de vigencia: se usa el día siguiente, 27-10-2025 (por validar). | <https://www.gob.pe/institucion/sunass/normas-legales/7325221-124-2025-sunass-cd> | `RCD-124-2025-SUNASS-CD.pdf` | `a0906460660ed8079ee032d2b625fbe77be0b3cb9c7dce2552c1a400e51da9c9` |
| **RCD N.° 028-2026-SUNASS-CD**, que modifica el art. 90 del RGT (uso excepcional del fondo por declaratoria de emergencia) | 31-07-2026, El Peruano, págs. 9-10. Rige desde el 01-08-2026 (art. 2). | <https://busquedas.elperuano.pe/dispositivo/NL/2538837-1> (código del dispositivo impreso en la publicación: 2538837-1) | `RCD-028-2026-SUNASS-CD_El-Peruano-2026-07-31.pdf` | `8fec72730ef97bddbecf805ad2c7c04721a33ca82ca4c9acf3e1f9dcc9a0dd19` |
| **Decreto Supremo N.° 004-2019-JUS**, TUO de la Ley 27444, Ley del Procedimiento Administrativo General | 25-01-2019, El Peruano | <https://cdn.www.gob.pe/uploads/document/file/5320370/4770872-decreto-supremo-n-004-2019-jus.pdf> | `tuo_27444_ds004_2019.pdf` | `01224f0288f9ad47e4f8def4e89aa2b1eb1ba7dd7b11a2c7a660ce08b09fe6ba` |

**Notas**
- La copia de la RCD 028-2026 es la página completa de El Peruano. Incluye otras normas de esa edición que no se usan en el proyecto.
- El DS 006-2026-JUS aprobó un TUO nuevo de la Ley 27444, que no se leyó (ver `docs/preguntas_para_la_DRE.md`, DRE-16).
- La RCD 108-2022-SUNASS-CD, que incorporó el numeral 6 del art. 94, se cita por la nota de modificación del compendio del RGT. No se leyó la resolución misma.
- Los PDF de las RCD 124-2025 y 028-2026 estuvieron versionados en el commit `3ccf67a` y siguen en ese historial, porque se decidió no reescribirlo. Desde la Fase 3 ya no se versionan.

**Para trabajar con las normas en local:** copie los PDF a esta carpeta con los nombres de la columna «Copia leída» y compruebe el SHA-256:

```bash
sha256sum docs/normas/*.pdf
```
