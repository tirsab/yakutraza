"""Fechas inconsistentes."""

from __future__ import annotations

from datetime import date

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import fin_mes, fin_trimestre


def _solo_cambia_el_anio(a: date, b: date) -> bool:
    return a.year != b.year and (a.month, a.day) == (b.month, b.day)


@regla("CAL-FEC-01")
def fin_antes_de_inicio(m, cfg, ctx):
    res = []
    if "ds02_hitos_procedimientos" in m.tablas:
        h = m["ds02_hitos_procedimientos"]
        for _, r in h.iterrows():
            ini, fin = r["fecha_inicio"], r["fecha_fin"]
            if ini and fin and fin < ini:
                res.append(nuevo(
                    cfg, "ds02_hitos_procedimientos", r["_fila"], f"{r['id_expediente']} · hito {r['nro_hito']}",
                    f"El hito {r['nro_hito']} ({r['hito']}) de {r['id_expediente']} termina el {fin} pero empieza "
                    f"el {ini}. Sin una fecha confiable no se puede calcular su duración.",
                    observado=f"fecha_fin {fin}", esperado=f"fecha_fin ≥ {ini}",
                ))
    if "ds02_procedimientos" in m.tablas:
        p = m["ds02_procedimientos"]
        for _, r in p.iterrows():
            ini = r["fecha_inicio"]
            for col in ("fecha_conclusion", "fecha_limite"):
                if col == "fecha_limite" and r["tipo_procedimiento"] == "reporte_periodico":
                    continue  # en reportes, fecha_inicio es la presentación y puede ser tardía
                v = r[col]
                if ini and v and v < ini:
                    res.append(nuevo(
                        cfg, "ds02_procedimientos", r["_fila"], r["id_expediente"],
                        f"En {r['id_expediente']}, {col} ({v}) es anterior a fecha_inicio ({ini}).",
                        observado=f"{col} {v}", esperado=f"{col} ≥ {ini}",
                    ))
    return res


@regla("CAL-FEC-02")
def hitos_encadenados(m, cfg, ctx):
    if "ds02_hitos_procedimientos" not in m.tablas:
        return []
    h = m["ds02_hitos_procedimientos"].sort_values(["id_expediente", "nro_hito"])
    res = []
    for exp, g in h.groupby("id_expediente", sort=False):
        previo = None
        for _, r in g.iterrows():
            if previo is not None:
                fin_ant, ini = previo["fecha_fin"], r["fecha_inicio"]
                if fin_ant and ini and ini != fin_ant:
                    nota = ""
                    if _solo_cambia_el_anio(ini, fin_ant):
                        nota = " Las dos fechas solo difieren en el año."
                    orden = " El hito empieza antes que el anterior: está fuera de orden." if (
                        previo["fecha_inicio"] and ini < previo["fecha_inicio"]) else ""
                    res.append(nuevo(
                        cfg, "ds02_hitos_procedimientos", r["_fila"], f"{exp} · hito {r['nro_hito']}",
                        f"El hito {r['nro_hito']} ({r['hito']}) de {exp} empieza el {ini}, pero el hito "
                        f"{previo['nro_hito']} ({previo['hito']}, fila {previo['_fila']}) terminó el {fin_ant}."
                        f"{nota}{orden} No se corrige: se necesita el documento que fije la fecha real.",
                        observado=f"fecha_inicio {ini}", esperado=f"fecha_inicio = {fin_ant}",
                        detalle={"fila_hito_anterior": int(previo["_fila"])},
                    ))
            previo = r
    return res


@regla("CAL-FEC-03")
def posteriores_al_corte(m, cfg, ctx):
    res = []
    for nombre, cols in (cfg.param("columnas") or {}).items():
        if nombre not in m.tablas:
            continue
        df = m[nombre]
        llave = m.tablas[nombre].spec.llave
        for col in cols:
            for _, r in df[df[col].map(lambda v: v is not None and v > ctx.fecha_corte)].iterrows():
                res.append(nuevo(
                    cfg, nombre, r["_fila"], " · ".join(str(r[c]) for c in llave),
                    f"{col} = {r[col]} es posterior a la fecha de corte {ctx.fecha_corte}.",
                    observado=str(r[col]), esperado=f"≤ {ctx.fecha_corte}",
                ))
    return res


@regla("CAL-FEC-04")
def reporte_antes_del_cierre(m, cfg, ctx):
    casos = (
        ("ds04_ejecucion_inversiones", "anio_trimestre", "fecha_reporte", lambda r: fin_trimestre(r["anio_trimestre"]),
         ("cod_proyecto", "anio_trimestre")),
        ("ds05_fondo_inversiones_reservas", "anio_mes", "fecha_reporte", lambda r: fin_mes(r["anio_mes"]),
         ("cod_eps", "anio_mes", "tipo_fondo")),
        ("ds06_estados_financieros", "anio", "fecha_presentacion", lambda r: date(int(r["anio"]), 12, 31),
         ("cod_eps", "anio")),
    )
    res = []
    for nombre, periodo, col, cierre, llave in casos:
        if nombre not in m.tablas:
            continue
        for _, r in m[nombre].iterrows():
            if r[col] is None or r[periodo] is None:
                continue
            fin = cierre(r)
            if r[col] <= fin:
                res.append(nuevo(
                    cfg, nombre, r["_fila"], " · ".join(str(r[c]) for c in llave),
                    f"{col} = {r[col]} no es posterior al cierre del periodo reportado {r[periodo]} ({fin}).",
                    observado=str(r[col]), esperado=f"> {fin}",
                ))
    return res
