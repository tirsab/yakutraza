"""Procedimientos sin flujograma: reporte trimestral, reporte de fondos y reajuste por IPM.

- Reporte trimestral y de fondos: supuestos de simulación (hoja Supuestos).
- Reajuste por IPM: disparo al 3 % acumulado (RGT art. 80; hoja Supuestos) y
  plazo de 90 días calendario para aplicarlo (RGT art. 82.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.calidad.reglas._util import fin_mes, fin_trimestre
from app.plazos.calendario import Calendario

UMBRAL_IPM = Decimal("3")


def limite_reporte_trimestral(trimestre: str, cal: Calendario, dias: int = 30) -> date:
    """30 días calendario después del cierre; si cae en día no hábil, el siguiente hábil (hoja Supuestos)."""
    return cal.siguiente_habil(fin_trimestre(trimestre) + timedelta(days=dias))


def limite_reporte_fondos(anio_mes: str, dias: int = 15) -> date:
    """15 días calendario después del cierre del mes (hoja Supuestos; no se corre al día hábil siguiente)."""
    return fin_mes(anio_mes) + timedelta(days=dias)


def limite_aplicacion_reajuste(mes_disparo: str, dias: int = 90) -> date:
    """90 días calendario posteriores al vencimiento del mes en que se acumuló el 3 % (RGT art. 82.3)."""
    return fin_mes(mes_disparo) + timedelta(days=dias)


def variacion_acumulada(indices: dict[str, Decimal], base: str, hasta: str) -> Decimal | None:
    """Variación porcentual del IPM entre el índice de `base` y el de `hasta` (DS09, índice base dic. 2020)."""
    if base not in indices or hasta not in indices:
        return None
    return (indices[hasta] / indices[base] - 1) * 100


def mes_de_disparo(indices: dict[str, Decimal], base: str, umbral: Decimal = UMBRAL_IPM) -> str | None:
    """Primer mes posterior a `base` en que la variación acumulada llega al umbral."""
    for mes in sorted(indices):
        if mes > base:
            v = variacion_acumulada(indices, base, mes)
            if v is not None and v >= umbral:
                return mes
    return None


@dataclass
class ReproduccionReajuste:
    expediente: str
    cod_eps: str
    base: str | None
    motivo_base: str
    mes_ds02: str | None
    mes_calculado: str | None
    variacion_ds02: Decimal | None
    variacion_calculada: Decimal | None
    reproduce: bool | None  # None = no puedo calcular
    fila: int | None
    limite_aplicacion: date | None


def reproducir_reajustes(rti: list[dict], ipm: list[dict], inicio_periodo: dict[str, int]) -> list[ReproduccionReajuste]:
    """Recalcula el disparo y la variación de cada reajuste de DS02 desde DS09.

    Base (hoja Supuestos): el último reajuste aplicado o, si es posterior, el
    inicio del periodo regulatorio vigente. El primer reajuste de cada EPS en
    la muestra no tiene base conocida (el reajuste anterior es previo a 2021):
    «no puedo calcular».
    """
    indices = {r["anio_mes"]: Decimal(str(r["indice_base_dic2020"])) for r in ipm}
    indices.setdefault("2020-12", Decimal(100))  # base del índice encadenado (hoja ds09)
    publicado = {r["fecha_publicacion"]: r["anio_mes"] for r in ipm}
    res = []
    por_eps: dict[str, list[dict]] = {}
    for r in sorted(rti, key=lambda r: (r["cod_eps"], r["fecha_inicio"])):
        por_eps.setdefault(r["cod_eps"], []).append(r)
    for eps, lista in por_eps.items():
        ultimo_aplicado: str | None = None
        for r in lista:
            mes_ds02 = publicado.get(r["fecha_inicio"])
            ini = inicio_periodo.get(eps)
            base_periodo = f"{ini - 1}-12" if ini else None
            if ultimo_aplicado and base_periodo and base_periodo > ultimo_aplicado and mes_ds02 and mes_ds02 > base_periodo:
                base, motivo = base_periodo, f"inicio del periodo regulatorio {ini}"
            elif ultimo_aplicado:
                base, motivo = ultimo_aplicado, "último reajuste aplicado"
            else:
                base, motivo = None, "falta el último reajuste anterior a la muestra"
            calc = mes_de_disparo(indices, base) if base else None
            var = variacion_acumulada(indices, base, mes_ds02) if base and mes_ds02 else None
            var_ds02 = Decimal(str(r["porcentaje_previsto"])) if r.get("porcentaje_previsto") is not None else None
            if base is None:
                reproduce = None
            elif r.get("resultado") == "no_aplicado_por_la_ep" and ultimo_aplicado is None:
                reproduce = None
            else:
                reproduce = (calc == mes_ds02 and var is not None and var_ds02 is not None
                             and abs(var - var_ds02) < Decimal("0.006"))
            res.append(ReproduccionReajuste(
                r["id_expediente"], eps, base, motivo, mes_ds02, calc, var_ds02,
                None if var is None else var.quantize(Decimal("0.001")), reproduce, r.get("_fila"),
                limite_aplicacion_reajuste(mes_ds02) if mes_ds02 else None,
            ))
            if r.get("resultado") == "reajuste_aplicado" and mes_ds02:
                ultimo_aplicado = mes_ds02
    return res




def limites_informe_emergencia(inicio: date, termino: date | None, cal: Calendario, dias_dh: int = 10) -> list[date]:
    """Vencimientos de los informes mensuales por uso del fondo durante una emergencia (RGT art. 90.3,
    RCD 028-2026, vigente desde el 01.08.2026): 10 DH desde el último día de cada mes calendario de la
    declaratoria y desde su término. Sin la declaratoria (inicio y término), no se puede calcular.
    """
    limites = []
    mes = date(inicio.year, inicio.month, 1)
    while True:
        fin = fin_mes(f"{mes.year}-{mes.month:02d}")
        if termino is not None and fin >= termino:
            break
        limites.append(cal.sumar_dias_habiles(fin, dias_dh))
        mes = (fin + timedelta(days=1))
        if termino is None and len(limites) >= 1:
            break  # declaratoria vigente: solo el informe del mes en curso
    if termino is not None:
        limites.append(cal.sumar_dias_habiles(termino, dias_dh))
    return limites
