"""Validación de plazos de DS02 con el motor de la Fase 2 (CAL-PLZ-01 a 05).

Cada regla informa cuántos casos coinciden (hallazgo informativo con el
conteo) y marca cada discrepancia fila por fila. No corrige DS02.
"""

from __future__ import annotations

from pathlib import Path

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import rango_filas
from app.config import get_settings
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from app.plazos.motor import MotorPlazos
from app.plazos.repositorio import expedientes_desde_muestra
from app.plazos.simulados import limite_reporte_trimestral, reproducir_reajustes

DS02 = "ds02_procedimientos"


def _rules(ctx) -> Path:
    return Path(ctx.rules_dir or get_settings().rules_dir)


def _motor(ctx) -> MotorPlazos:
    r = _rules(ctx)
    return MotorPlazos(calendario_desde(r / "feriados.yaml"), catalogo_desde(r / "plazos.yaml"))


DH = "calendario de rules/feriados.yaml, conteo desde el día hábil siguiente"


def _resumen(cfg, total, coinciden, que, filas_ok, metodo=DH):
    return nuevo(
        cfg, DS02, None, f"{coinciden} de {total}",
        f"{que}: {coinciden} de {total} coinciden con el cálculo del motor ({metodo}).",
        severidad="informativa", titulo=f"Validación: {que}",
        observado=f"{coinciden} de {total}", esperado=f"{total} de {total}", detalle={"filas": filas_ok},
    )


def _normativos(m, ctx):
    if DS02 not in m.tablas or "ds02_hitos_procedimientos" not in m.tablas:
        return None, []
    mot = _motor(ctx)
    pares = []
    for exp in expedientes_desde_muestra(m).values():
        if exp.plazo_maximo_dh is None:
            continue
        alerta = next(a for a in mot.reloj_normativo(exp, ctx.fecha_corte) if a.etapa is None)
        pares.append((exp, alerta))
    return mot, pares


@regla("CAL-PLZ-01")
def fecha_limite(m, cfg, ctx):
    _, pares = _normativos(m, ctx)
    if not pares:
        return []
    res, ok = [], []
    for exp, a in pares:
        if a.estado == "no_calculable":
            res.append(nuevo(cfg, DS02, exp.fila, exp.id,
                             f"No puedo recalcular la fecha límite de {exp.id}: {a.mensaje.removeprefix('No puedo calcular: ')} "
                             f"DS02 indica {exp.fecha_limite_ds02}.",
                             observado=exp.fecha_limite_ds02, esperado="(no calculable)"))
        elif a.fecha_limite != exp.fecha_limite_ds02:
            res.append(nuevo(cfg, DS02, exp.fila, exp.id,
                             f"DS02 indica fecha_limite {exp.fecha_limite_ds02} para {exp.id}, pero el motor calcula "
                             f"{a.fecha_limite} ({a.plazo_dh} DH desde {exp.fecha_inicio} más la suspensión).",
                             observado=exp.fecha_limite_ds02, esperado=a.fecha_limite))
        else:
            ok.append(exp.fila)
    return [_resumen(cfg, len(pares), len(ok), "fecha_limite de DS02", ok)] + res


@regla("CAL-PLZ-02")
def dias_habiles(m, cfg, ctx):
    mot, pares = _normativos(m, ctx)
    if not pares:
        return []
    res, ok = [], []
    for exp, a in pares:
        if a.estado == "no_calculable":
            res.append(nuevo(cfg, DS02, exp.fila, exp.id,
                             f"No puedo recalcular los días hábiles de {exp.id}: "
                             f"{a.mensaje.removeprefix('No puedo calcular: ')} DS02 indica {exp.dias_sunass_ds02} DH de "
                             f"la Sunass y {exp.dias_suspension_ds02} DH de suspensión.",
                             observado=exp.dias_sunass_ds02, esperado="(no calculable)"))
            continue
        hasta = min(exp.fecha_conclusion, ctx.fecha_corte) if exp.fecha_conclusion else ctx.fecha_corte
        susp, sunass = mot.suspension_y_sunass(exp, hasta)
        if (sunass, susp) != (exp.dias_sunass_ds02, exp.dias_suspension_ds02):
            res.append(nuevo(cfg, DS02, exp.fila, exp.id,
                             f"{exp.id}: DS02 indica {exp.dias_sunass_ds02} DH de la Sunass y {exp.dias_suspension_ds02} "
                             f"de suspensión; sumando los hitos el motor obtiene {sunass} y {susp}.",
                             observado=f"{exp.dias_sunass_ds02} / {exp.dias_suspension_ds02}",
                             esperado=f"{sunass} / {susp}"))
        else:
            ok.append(exp.fila)
    return [_resumen(cfg, len(pares), len(ok), "dias_habiles_sunass y dias_suspension_dh de DS02", ok)] + res


@regla("CAL-PLZ-03")
def reportes_trimestrales(m, cfg, ctx):
    if DS02 not in m.tablas:
        return []
    cal = calendario_desde(_rules(ctx) / "feriados.yaml")
    p = m[DS02]
    rp = p[p["tipo_procedimiento"] == "reporte_periodico"]
    if rp.empty:
        return []
    res, ok = [], []
    for _, r in rp.iterrows():
        if not r["periodo_reportado"]:
            res.append(nuevo(cfg, DS02, r["_fila"], r["id_expediente"],
                             f"No puedo calcular el vencimiento de {r['id_expediente']}: falta periodo_reportado.",
                             observado=r["fecha_limite"], esperado="(no calculable)"))
            continue
        calc = limite_reporte_trimestral(r["periodo_reportado"], cal)
        if calc != r["fecha_limite"]:
            res.append(nuevo(cfg, DS02, r["_fila"], r["id_expediente"],
                             f"El reporte {r['periodo_reportado']} de {r['cod_eps']} vence el {calc} según la hoja "
                             f"Supuestos, pero DS02 indica {r['fecha_limite']}.",
                             observado=r["fecha_limite"], esperado=calc))
        else:
            ok.append(int(r["_fila"]))
    return [_resumen(cfg, len(rp), len(ok), "fecha_limite de los reportes trimestrales", ok,
                     "30 días calendario tras el cierre del trimestre; si cae en día no hábil, el siguiente hábil")] + res


@regla("CAL-PLZ-04")
def diferencias_calendario(m, cfg, ctx):
    cal = calendario_desde(_rules(ctx) / "feriados.yaml")
    difs = cal.diferencias_con_supuestos()
    if not difs:
        return [nuevo(cfg, "diccionario", None, "hoja Supuestos · Feriados",
                      "La librería holidays y la hoja Supuestos coinciden en los cuatro feriados con vigencia "
                      "(6 de agosto y 9 de diciembre desde 2022, 23 de julio desde 2023, 7 de junio desde 2024) en "
                      "todos los años verificados.", severidad="informativa", titulo="Calendario: sin diferencias")]
    return [nuevo(cfg, "diccionario", None, f"{d.fecha} · {d.nombre}", d.explicacion,
                  observado="feriado en la librería" if d.en_libreria else "no feriado en la librería",
                  esperado="feriado (Supuestos)" if d.en_supuestos else "no feriado (Supuestos)")
            for d in difs]


@regla("CAL-PLZ-05")
def reajustes_ipm(m, cfg, ctx):
    req = (DS02, "ds09_ipm", "ds01_catalogo_eps")
    if any(r not in m.tablas for r in req):
        return []
    p = m[DS02]
    rti = [r.to_dict() for _, r in p[p["tipo_procedimiento"] == "reajuste_ipm"].iterrows()]
    if not rti:
        return []
    ipm = [r.to_dict() for _, r in m["ds09_ipm"].iterrows()]
    ini = {r["cod_eps"]: int(r["periodo_regulatorio_inicio"]) for _, r in m["ds01_catalogo_eps"].iterrows()
           if r["periodo_regulatorio_inicio"] is not None}
    rep = reproducir_reajustes(rti, ipm, ini)
    calculables = [r for r in rep if r.reproduce is not None]
    ok = [r for r in calculables if r.reproduce]
    sin_base = [r for r in rep if r.reproduce is None]
    res = [nuevo(cfg, DS02, None, f"{len(ok)} de {len(calculables)}",
                 f"Reajustes por IPM: {len(ok)} de {len(calculables)} con base conocida se reproducen desde DS09 (mes "
                 "de disparo y variación acumulada). Base: último reajuste aplicado o inicio del periodo regulatorio "
                 f"(hoja Supuestos). {len(sin_base)} no se pueden calcular: falta el último reajuste anterior a la "
                 f"muestra (filas {rango_filas([r.fila for r in sin_base])}).",
                 severidad="informativa", titulo="Validación: reajustes por IPM",
                 observado=f"{len(ok)} de {len(calculables)}", esperado=f"{len(calculables)} de {len(calculables)}",
                 detalle={"filas": [r.fila for r in ok], "sin_base": [r.expediente for r in sin_base]})]
    for r in calculables:
        if not r.reproduce:
            res.append(nuevo(cfg, DS02, r.fila, r.expediente,
                             f"{r.expediente}: DS02 dispara el reajuste en {r.mes_ds02} con {r.variacion_ds02} %; desde "
                             f"la base {r.base} ({r.motivo_base}) DS09 da {r.mes_calculado} y {r.variacion_calculada} %.",
                             observado=f"{r.mes_ds02} · {r.variacion_ds02} %",
                             esperado=f"{r.mes_calculado} · {r.variacion_calculada} %"))
    return res
