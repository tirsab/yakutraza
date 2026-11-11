"""Reportes y datos faltantes."""

from __future__ import annotations

from collections import defaultdict

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import meses, rango_filas, trimestres


@regla("CAL-FAL-01")
def trimestres_sin_reporte(m, cfg, ctx):
    if "ds04_ejecucion_inversiones" not in m.tablas:
        return []
    esperados = trimestres(cfg.param("primer_trimestre"), cfg.param("ultimo_trimestre_vencido"))
    d4 = m.tablas["ds04_ejecucion_inversiones"].crudos
    rpi = {}
    if "ds02_procedimientos" in m.tablas:
        p = m.tablas["ds02_procedimientos"].crudos
        for fila, r in p[p["tipo_procedimiento"] == "reporte_periodico"].iterrows():
            rpi[(r["cod_eps"], r["periodo_reportado"])] = (int(fila), r)
    res = []
    for eps, g in d4.groupby("cod_eps", sort=True):
        presentes = set(g["anio_trimestre"])
        for t in esperados:
            if t in presentes:
                continue
            ref = rpi.get((eps, t))
            if ref is None:
                cita, sev, det = " DS02 no tiene expediente de reporte periódico para ese trimestre.", None, {}
            else:
                fila_p, r = ref
                det = {"expediente_ds02": r["id_expediente"], "fila_ds02": fila_p}
                if r["fecha_presentacion"]:
                    cita = (f" Inconsistencia: DS02 ({r['id_expediente']}, fila {fila_p}) registra el reporte como "
                            f"presentado el {r['fecha_presentacion']}, pero DS04 no tiene filas.")
                    sev = "alta"
                else:
                    cita = (f" Coincide con DS02: {r['id_expediente']} (fila {fila_p}) está «{r['estado']}» sin fecha "
                            f"de presentación; fecha límite {r['fecha_limite']}.")
                    sev = None
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", None, f"{eps} · {t}",
                f"{eps} no tiene ninguna fila de ejecución en DS04 para el trimestre {t}, cuyo reporte ya venció "
                f"al corte.{cita}",
                observado="sin filas", esperado=f"reporte del trimestre {t}", severidad=sev, detalle=det,
            ))
    return res


@regla("CAL-FAL-02")
def meses_sin_reporte(m, cfg, ctx):
    if "ds05_fondo_inversiones_reservas" not in m.tablas:
        return []
    d5 = m.tablas["ds05_fondo_inversiones_reservas"].crudos
    ultimo = cfg.param("ultimo_mes_vencido")
    primer = cfg.param("primer_mes")
    faltan: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (eps, fondo), g in d5.groupby(["cod_eps", "tipo_fondo"], sort=True):
        presentes = set(g["anio_mes"])
        desde = max(primer, min(presentes))
        for mes in meses(desde, ultimo):
            if mes not in presentes:
                faltan[(eps, mes)].append(fondo)
    res = []
    for (eps, mes), fondos in sorted(faltan.items()):
        res.append(nuevo(
            cfg, "ds05_fondo_inversiones_reservas", None, f"{eps} · {mes}",
            f"{eps} no reportó el mes {mes} en DS05 para: {', '.join(fondos)}. El reporte mensual vence 15 días "
            "calendario después del cierre del mes (hoja Supuestos), antes de la fecha de corte.",
            observado="sin fila", esperado=f"reporte de {mes}", detalle={"fondos": fondos},
        ))
    return res


@regla("CAL-FAL-03")
def estados_no_presentados(m, cfg, ctx):
    if "ds06_estados_financieros" not in m.tablas:
        return []
    d6 = m.tablas["ds06_estados_financieros"].crudos
    res = []
    for fila, r in d6[d6["estado_presentacion"] == "no_presentado"].iterrows():
        res.append(nuevo(
            cfg, "ds06_estados_financieros", int(fila), f"{r['cod_eps']} · {r['anio']}",
            f"{r['cod_eps']} no presentó sus estados financieros de {r['anio']}: la fila no tiene montos ni "
            "indicadores. El contexto financiero de ese año queda sin dato.",
            observado="no_presentado", esperado="presentado",
        ))
    return res


@regla("CAL-FAL-04")
def metas_sin_valor(m, cfg, ctx):
    if "ds07_metas_gestion" not in m.tablas:
        return []
    anio_curso = int(cfg.param("anio_en_curso"))
    d7 = m["ds07_metas_gestion"]
    res = []
    vacias = d7[d7["valor_alcanzado"].isna() & (d7["anio"] < anio_curso)]
    for _, r in vacias.iterrows():
        res.append(nuevo(
            cfg, "ds07_metas_gestion", r["_fila"], f"{r['cod_eps']} · {r['cod_meta']} · {r['anio']}",
            f"La meta {r['cod_meta']} de {r['cod_eps']} no tiene valor alcanzado en {r['anio']}, un año ya "
            f"evaluado (solo {anio_curso} puede estar vacío).",
            observado="(vacío)", esperado="valor alcanzado",
        ))
    return res


@regla("CAL-FAL-05")
def mef_sin_avance(m, cfg, ctx):
    if "ds08_inversiones_mef" not in m.tablas:
        return []
    d8 = m.tablas["ds08_inversiones_mef"].crudos
    vacias = d8[d8["avance_fisico_pct"] == ""]
    if vacias.empty:
        return []
    filas = [int(i) for i in vacias.index]
    por_estado = vacias["estado_inversion"].value_counts().to_dict()
    sin_viab = int((vacias["fecha_viabilidad"] == "").sum())
    return [nuevo(
        cfg, "ds08_inversiones_mef", None, f"{len(filas)} CUI",
        f"{len(filas)} inversiones de DS08 no registran avance físico (filas {rango_filas(filas)}). "
        f"Por estado: {', '.join(f'{k} {v}' for k, v in por_estado.items())}; {sin_viab} siguen en formulación "
        "(sin fecha de viabilidad). El diccionario permite el vacío, pero no se puede conciliar su avance con DS04.",
        observado=f"{len(filas)} sin avance", esperado="avance físico registrado",
        detalle={"filas": filas, "cui": list(vacias["cui"]), "por_estado": por_estado},
    )]
