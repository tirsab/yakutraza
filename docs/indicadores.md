# Indicadores de línea base · muestra simulada

> **Muestra simulada.** Datos sintéticos de la muestra del Hackathon Sunass «Lideresas por el Agua». No describen a ninguna EPS real ni el desempeño real de la Sunass.

Generado con `python -m app.cli indicadores`, con la misma función que alimenta el tablero gerencial (`app/vistas/tablero.py`, `supera_plazo`). Fecha de corte de la muestra: 30-09-2026.

## Expedientes que superan el plazo máximo

- **Fórmula:** días hábiles atribuibles a la Sunass (DS02 dias_habiles_sunass) > plazo máximo (DS02 plazo_maximo_dh).
- **Resultado:** 12 de 65 expedientes con datos (18,5 %); 3 de ellos siguen en trámite.
- **No calculables:** 416 expedientes. DS02 no trae los días atribuibles a la Sunass o el plazo máximo (por ejemplo, reportes periódicos y reajustes por IPM). No se estiman.
- **Nota:** Valores de DS02 a la fecha de corte de la muestra: el selector de fecha no cambia esta línea base. Incluye expedientes en trámite que ya superan el plazo. Si DS02 no trae los días o el plazo, el expediente cuenta como «no calculable»: no se estima.

### Por tipo de trámite

| Tipo de trámite | Superan el plazo | Con datos | % | No calculables |
|---|---:|---:|---:|---:|
| Cambio al programa de inversiones | 1 | 9 | 11,1 % | 0 |
| Reajuste por IPM | 0 | 0 | no calculable | 56 |
| Reporte periódico | 0 | 0 | no calculable | 360 |
| Revisión periódica de tarifas | 10 | 20 | 50,0 % | 0 |
| Uso excepcional del fondo | 1 | 4 | 25,0 % | 0 |
| Verificación de incrementos tarifarios | 0 | 32 | 0,0 % | 0 |

### Por EPS

| EPS | Superan el plazo | Con datos | % | No calculables |
|---|---:|---:|---:|---:|
| EPS01 | 0 | 3 | 0,0 % | 20 |
| EPS02 | 1 | 3 | 33,3 % | 20 |
| EPS03 | 0 | 3 | 0,0 % | 21 |
| EPS04 | 0 | 4 | 0,0 % | 20 |
| EPS05 | 1 | 2 | 50,0 % | 21 |
| EPS06 | 1 | 4 | 25,0 % | 20 |
| EPS07 | 1 | 4 | 25,0 % | 22 |
| EPS08 | 0 | 4 | 0,0 % | 21 |
| EPS09 | 1 | 4 | 25,0 % | 20 |
| EPS10 | 0 | 4 | 0,0 % | 21 |
| EPS11 | 1 | 2 | 50,0 % | 22 |
| EPS12 | 1 | 2 | 50,0 % | 21 |
| EPS13 | 0 | 4 | 0,0 % | 21 |
| EPS14 | 1 | 4 | 25,0 % | 21 |
| EPS15 | 1 | 4 | 25,0 % | 20 |
| EPS16 | 2 | 4 | 50,0 % | 21 |
| EPS17 | 0 | 3 | 0,0 % | 21 |
| EPS18 | 1 | 2 | 50,0 % | 21 |
| EPS19 | 0 | 3 | 0,0 % | 21 |
| EPS20 | 0 | 2 | 0,0 % | 21 |

## Expedientes que superan el plazo

`CPI-2026-0004`, `RP-2022-0002`, `RP-2022-0003`, `RP-2023-0003`, `RP-2024-0002`, `RP-2024-0003`, `RP-2024-0005`, `RP-2025-0001`, `RP-2025-0002`, `RP-2025-0003`, `RP-2025-0004`, `UFI-2025-0001`

Fuente: DS02 ds02_procedimientos (sintético).
