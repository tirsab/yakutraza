"""Pre-chequeo de un cambio al programa de inversiones: art. 94 (comunicación) o art. 93 (Consejo Directivo).

Orienta; no decide. Cada resultado dice la regla aplicada, el texto citado, los
cálculos con su fuente (DS03 fila por fila) y lo que falta para determinar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

SOLO_COMUNICACION = "solo_comunicacion_art_94"
CONSEJO_DIRECTIVO = "aprobacion_cd_art_93"
NO_DETERMINABLE = "no_determinable"


@dataclass
class Entrada:
    cod_eps: str
    tipo_cambio: str
    anio_solicitud: int
    cod_proyecto: str | None = None
    monto_nuevo_pendiente: Decimal | None = None  # incremento de monto: nuevo monto pendiente del proyecto
    costo_proyecto_sustituto: Decimal | None = None  # sustituciones 93.1.3 / 93.1.4
    suma_sustituciones_previas: Decimal | None = None  # sustituciones ya hechas en el periodo (la EP la declara)
    id_expediente: str | None = None  # si es un expediente de DS02, para excluir su propia modificación


@dataclass
class Resultado:
    ruta: str
    titulo: str
    regla_aplicada: str
    texto_citado: list[dict[str, str]]
    explicacion: str
    calculos: dict[str, Any] = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    supuestos: list[str] = field(default_factory=list)
    estado_validacion: str = "por validar"
    aviso: str = "Pre-chequeo orientativo: no es una decisión regulatoria. Las decisiones son de Sunass."


@lru_cache
def catalogo_desde(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def _d(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal(0)


def _soles(x: Decimal) -> str:
    entero, _, dec = f"{x.quantize(Decimal('0.01')):,.2f}".partition(".")
    return f"S/ {entero.replace(',', ' ')},{dec}"


def _pct(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01"))).replace(".", ",")


def datos_programa(ds03: pd.DataFrame, e: Entrada) -> dict[str, Any]:
    """Montos del programa vigente de la EPS (DS03) que usa el pre-chequeo, con sus filas de origen."""
    vig = ds03[(ds03["cod_eps"] == e.cod_eps) & (ds03["tipo_periodo"] == "vigente")]
    res: dict[str, Any] = {"periodo": None, "total_programa": None, "filas_programa": [], "incrementos_previos": Decimal(0),
                           "filas_incrementos": [], "pendiente_proyecto": None, "filas_proyecto": [],
                           "meta_asociada": None, "nombre_proyecto": None}
    if vig.empty:
        return res
    res["periodo"] = vig["periodo_regulatorio"].iloc[0]
    res["total_programa"] = sum((_d(v) for v in vig["monto_programado_original"]), Decimal(0))
    res["filas_programa"] = [int(f) for f in vig["_fila"]]
    for _, r in vig.iterrows():
        mod = r["id_expediente_modificacion"]
        if mod and mod != e.id_expediente:
            dif = _d(r["monto_programado_vigente"]) - _d(r["monto_programado_original"])
            if dif > 0:
                res["incrementos_previos"] += dif
                res["filas_incrementos"].append(int(r["_fila"]))
    if e.cod_proyecto:
        p = vig[vig["cod_proyecto"] == e.cod_proyecto]
        if not p.empty:
            res["nombre_proyecto"] = p["nombre_proyecto"].iloc[0]
            res["meta_asociada"] = p["meta_asociada"].iloc[0] or None
            pend = Decimal(0)
            for _, r in p.iterrows():
                if r["anio"] is not None and int(r["anio"]) >= e.anio_solicitud:
                    # Si este mismo expediente modificó la fila, se toma el monto anterior al cambio.
                    col = "monto_programado_original" if r["id_expediente_modificacion"] == e.id_expediente \
                        and e.id_expediente else "monto_programado_vigente"
                    pend += _d(r[col])
                    res["filas_proyecto"].append(int(r["_fila"]))
            res["pendiente_proyecto"] = pend
    return res


def prechequear(ds03: pd.DataFrame, e: Entrada, cat: dict[str, Any]) -> Resultado:
    t = cat["textos"]
    par = cat["parametros"]
    umbral = Decimal(par["umbral_incrementos_pct"]["valor"]) / 100
    tope_pct = Decimal(par["tope_sustitucion_pct"]["valor"]) / 100
    tope_soles = Decimal(par["tope_sustitucion_soles"]["valor"])
    if e.tipo_cambio not in cat["tipos_cambio"]:
        raise ValueError(f"Tipo de cambio no reconocido: {e.tipo_cambio}")
    dp = datos_programa(ds03, e)
    supuestos = [par["base_monto_total"]["sustento"].strip()]
    calc: dict[str, Any] = {
        "periodo_regulatorio": dp["periodo"],
        "monto_total_programa": None if dp["total_programa"] is None else str(dp["total_programa"]),
        "fuente_monto_total": f"DS03, monto_programado_original del periodo vigente ({len(dp['filas_programa'])} filas)",
        "incrementos_previos_periodo": str(dp["incrementos_previos"]),
        "filas_incrementos_previos": dp["filas_incrementos"],
    }
    adv = []
    if dp["meta_asociada"]:
        adv.append(f"El proyecto {e.cod_proyecto} impulsa la meta de gestión {dp['meta_asociada']} (DS03 → DS07): "
                   f"el art. 92 exige que el cambio no modifique las metas de gestión. Texto: «{t['art_92']}».")

    def res(ruta, titulo, regla, textos, expl, faltan=None):
        return Resultado(ruta=ruta, titulo=titulo, regla_aplicada=regla, texto_citado=textos, explicacion=expl,
                         calculos=calc, advertencias=adv, faltantes=faltan or [], supuestos=supuestos)

    if dp["total_programa"] is None:
        return res(NO_DETERMINABLE, "No puedo determinar la vía", "—", [],
                   f"No puedo determinar: falta el programa de inversiones vigente de {e.cod_eps} en DS03.",
                   ["programa de inversiones vigente (DS03)"])
    total = dp["total_programa"]
    cita = lambda clave, ubic: {"ubicacion": ubic, "texto": t[clave]}  # noqa: E731

    if e.tipo_cambio == "recursos_liberados_93_2":
        return res(CONSEJO_DIRECTIVO, "Requiere autorización previa de Sunass (art. 93.2)", "RGT art. 93.2",
                   [cita("art_93_2", "RGT art. 93.2"),
                    cita("rcd_032_2026_3_10", "RCD 032-2026-SUNASS-CD, considerando 3.10 (caso Tacna)")],
                   "El destino de recursos liberados por donación o transferencia necesita autorización previa de "
                   "Sunass; según la RCD 032-2026, no se exige además una causal del párrafo 93.1.")

    if e.tipo_cambio in ("adelanto_94_2", "reprogramacion_94_4", "cambio_nombre_94_5"):
        num = e.tipo_cambio.split("_")[-1]
        clave = {"2": "art_94_2", "4": "art_94_4", "5": "art_94_5"}[num]
        verificar = {"2": "que se trate de un adelanto de inversiones ya previstas",
                     "4": "que no cambien los montos anuales programados del periodo",
                     "5": "la aprobación del nuevo nombre en el SNPMGI"}[num]
        return res(SOLO_COMUNICACION, f"Solo comunicación (art. 94, numeral {num})", f"RGT art. 94, numeral {num}",
                   [cita("art_94_encabezado", "RGT art. 94"), cita(clave, f"RGT art. 94, numeral {num}")],
                   f"La EP declara este supuesto. El sistema no puede verificarlo con los datos de la muestra: "
                   f"falta comprobar {verificar}.", [verificar])

    if e.tipo_cambio in ("sustitucion_93_1_3", "sustitucion_93_1_4"):
        num = e.tipo_cambio[-1]
        textos = [cita(f"art_93_1_{num}", f"RGT art. 93.1, numeral {num}"), cita("art_94_6", "RGT art. 94, numeral 6")]
        if e.costo_proyecto_sustituto is None:
            return res(NO_DETERMINABLE, "No puedo determinar la vía", "RGT art. 94, numeral 6", textos,
                       "No puedo determinar: falta el costo individual del proyecto previsto que se sustituye.",
                       ["costo individual del proyecto sustituido"])
        tope_ind = min(total * tope_pct, tope_soles)
        calc.update(costo_proyecto_sustituto=str(e.costo_proyecto_sustituto), tope_individual=str(tope_ind))
        if e.costo_proyecto_sustituto > tope_ind:
            return res(CONSEJO_DIRECTIVO, "Requiere aprobación del Consejo Directivo (art. 93)", "RGT art. 94, numeral 6",
                       textos + [cita("art_93_6", "RGT art. 93.6")],
                       f"El costo del proyecto sustituido ({_soles(e.costo_proyecto_sustituto)}) supera el menor valor "
                       f"entre el 10 % del programa ({_soles(total * tope_pct)}) y S/ 5 000 000: "
                       f"tope {_soles(tope_ind)}. Va por el art. 93.")
        if e.suma_sustituciones_previas is None:
            return res(NO_DETERMINABLE, "No puedo determinar la vía", "RGT art. 94, numeral 6", textos,
                       f"El costo individual cumple el tope ({_soles(e.costo_proyecto_sustituto)} ≤ {_soles(tope_ind)}), "
                       "pero no puedo comprobar que la suma de sustituciones del periodo no supere el 10 %: DS03 no "
                       "registra sustituciones. La EP debe declarar las sustituciones previas del periodo.",
                       ["suma de sustituciones previas del periodo"])
        suma = e.suma_sustituciones_previas + e.costo_proyecto_sustituto
        calc.update(suma_sustituciones=str(suma), tope_suma=str(total * tope_pct))
        if suma <= total * tope_pct:
            return res(SOLO_COMUNICACION, "Solo comunicación (art. 94, numeral 6)", "RGT art. 94, numeral 6", textos,
                       f"Costo individual {_soles(e.costo_proyecto_sustituto)} ≤ {_soles(tope_ind)} y suma de "
                       f"sustituciones del periodo {_soles(suma)} ≤ 10 % del programa ({_soles(total * tope_pct)}).")
        return res(CONSEJO_DIRECTIVO, "Requiere aprobación del Consejo Directivo (art. 93)", "RGT art. 94, numeral 6",
                   textos + [cita("art_93_6", "RGT art. 93.6")],
                   f"La suma de sustituciones del periodo ({_soles(suma)}) supera el 10 % del programa "
                   f"({_soles(total * tope_pct)}). Va por el art. 93.")

    if e.tipo_cambio == "incremento_monto":
        textos = [cita("art_94_encabezado", "RGT art. 94"), cita("art_94_1", "RGT art. 94, numeral 1")]
        if dp["pendiente_proyecto"] is None or e.monto_nuevo_pendiente is None:
            faltan = []
            if dp["pendiente_proyecto"] is None:
                faltan.append(f"el proyecto {e.cod_proyecto or '(sin código)'} en el programa vigente de DS03")
            if e.monto_nuevo_pendiente is None:
                faltan.append("el nuevo monto pendiente del proyecto")
            return res(NO_DETERMINABLE, "No puedo determinar la vía", "RGT art. 94, numeral 1", textos,
                       "No puedo determinar: falta " + " y ".join(faltan) + ".", faltan)
        incremento = e.monto_nuevo_pendiente - dp["pendiente_proyecto"]
        acumulado = dp["incrementos_previos"] + max(incremento, Decimal(0))
        pct = acumulado / total * 100 if total else None
        calc.update(proyecto=e.cod_proyecto, nombre_proyecto=dp["nombre_proyecto"],
                    monto_pendiente_programado=str(dp["pendiente_proyecto"]), filas_proyecto=dp["filas_proyecto"],
                    monto_nuevo_pendiente=str(e.monto_nuevo_pendiente), incremento_solicitado=str(incremento),
                    incrementos_acumulados=str(acumulado),
                    porcentaje_del_programa=None if pct is None else str(pct.quantize(Decimal("0.01"))))
        if incremento <= 0:
            return res(NO_DETERMINABLE, "No es un incremento de monto", "RGT art. 94, numeral 1", textos,
                       f"El nuevo monto pendiente ({_soles(e.monto_nuevo_pendiente)}) no supera el programado "
                       f"({_soles(dp['pendiente_proyecto'])}). Si es una reprogramación, revise el art. 94, numeral 4.",
                       ["tipo de cambio correcto"])
        if acumulado <= total * umbral:
            return res(SOLO_COMUNICACION, "Solo comunicación (art. 94, numeral 1)", "RGT art. 94, numeral 1", textos,
                       f"Incrementos del periodo, incluido este: {_soles(acumulado)} = {_pct(pct)} % "
                       f"del programa ({_soles(total)}); no superan el 10 %.")
        adv.append("Podría ir solo con comunicación por el art. 94, numeral 3, si cumple a la vez sus cinco condiciones "
                   "(entre ellas, aprobación del SNPMGI y fondo insuficiente). La muestra no tiene esos datos.")
        return res(CONSEJO_DIRECTIVO, "Requiere aprobación del Consejo Directivo (art. 93)", "RGT art. 94, numeral 1",
                   textos + [cita("art_94_3", "RGT art. 94, numeral 3"), cita("art_93_6", "RGT art. 93.6")],
                   f"Incrementos del periodo, incluido este: {_soles(acumulado)} = {_pct(pct)} % "
                   f"del programa ({_soles(total)}); superan el 10 %. Va por el art. 93.")

    return res(CONSEJO_DIRECTIVO, "Requiere aprobación del Consejo Directivo (art. 93)", "RGT art. 93.1",
               [cita("art_93_1", "RGT art. 93.1"), cita("art_93_6", "RGT art. 93.6")],
               "Los demás casos del párrafo 93.1 requieren solicitud y autorización del Consejo Directivo.")
