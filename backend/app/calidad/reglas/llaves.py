"""Llaves: cruces de la hoja Relaciones, formatos de código y CUI sin MEF."""

from __future__ import annotations

import re
from collections import defaultdict

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import normalizar, rango_filas


def _filas_por_valor(crudos, columna) -> dict[str, list[int]]:
    res: dict[str, list[int]] = defaultdict(list)
    for fila, v in crudos[columna].items():
        if v != "":
            res[v].append(int(fila))
    return res


@regla("CAL-LLV-01")
def relaciones(m, cfg, ctx):
    res = []
    for rel in cfg.param("relaciones", []):
        o, d = rel["origen"], rel["destino"]
        if o not in m.tablas or d not in m.tablas:
            continue
        destino = set(m.tablas[d].crudos[rel["columna_destino"]]) - {""}
        for valor, filas in _filas_por_valor(m.tablas[o].crudos, rel["columna"]).items():
            if valor in destino:
                continue
            res.append(nuevo(
                cfg, o, filas[0], f"{rel['columna']} = {valor}",
                f"{rel['columna']} «{valor}» de {o} (filas {rango_filas(filas)}) no existe en "
                f"{d}.{rel['columna_destino']}. Mientras no cruce, estas filas no se pueden vincular.",
                observado=valor, esperado=f"un valor existente en {d}.{rel['columna_destino']}",
                detalle={"filas": filas, "destino": d},
            ))
    return res


@regla("CAL-LLV-02")
def formatos(m, cfg, ctx):
    patrones = {c: re.compile(p) for c, p in cfg.param("formatos", {}).items()}
    res = []
    for nombre, t in m.tablas.items():
        for col, patron in patrones.items():
            if col not in t.crudos.columns:
                continue
            for valor, filas in _filas_por_valor(t.crudos, col).items():
                if patron.match(valor):
                    continue
                res.append(nuevo(
                    cfg, nombre, filas[0], f"{col} = {valor}",
                    f"{col} «{valor}» en {nombre} (filas {rango_filas(filas)}) no sigue el formato del "
                    f"diccionario ({patron.pattern}).",
                    observado=valor, esperado=patron.pattern, detalle={"filas": filas},
                ))
    return res


_COD = re.compile(r"^(EPS\d{2})-P0*(\d+)$")


@regla("CAL-LLV-03")
def proyectos_sin_ejecucion(m, cfg, ctx):
    if "ds03_programa_inversiones" not in m.tablas or "ds04_ejecucion_inversiones" not in m.tablas:
        return []
    d3 = m.tablas["ds03_programa_inversiones"].crudos
    d4 = m.tablas["ds04_ejecucion_inversiones"].crudos
    en_d4 = set(d4["cod_proyecto"])
    huerfanos_d4 = _filas_por_valor(d4, "cod_proyecto")
    huerfanos_d4 = {k: v for k, v in huerfanos_d4.items() if k not in set(d3["cod_proyecto"])}
    res = []
    vigentes = d3[d3["tipo_periodo"] == "vigente"]
    for cod, filas in _filas_por_valor(vigentes, "cod_proyecto").items():
        if cod in en_d4:
            continue
        pista = ""
        mc = _COD.match(cod)
        for otro, filas_otro in huerfanos_d4.items():
            mo = _COD.match(otro)
            if mc and mo and mc.groups() == mo.groups():
                pista = (f" En DS04 hay un código que no cruza, «{otro}» (filas {rango_filas(filas_otro)}), "
                         "con la misma EPS y número: podría ser este proyecto mal escrito. No se corrige; validar con la EPS.")
        res.append(nuevo(
            cfg, "ds03_programa_inversiones", filas[0], f"cod_proyecto = {cod}",
            f"El proyecto {cod} del periodo vigente (DS03, filas {rango_filas(filas)}) no tiene ninguna fila de "
            f"ejecución en DS04.{pista}",
            observado="0 filas en DS04", esperado="reportes trimestrales en DS04", detalle={"filas": filas},
        ))
    return res


@regla("CAL-LLV-04")
def entidad_mef(m, cfg, ctx):
    req = ("ds01_catalogo_eps", "ds03_programa_inversiones", "ds08_inversiones_mef")
    if any(r not in m.tablas for r in req):
        return []
    nombres = dict(zip(m["ds01_catalogo_eps"]["cod_eps"], m["ds01_catalogo_eps"]["nombre_eps"]))
    d3 = m.tablas["ds03_programa_inversiones"].crudos
    eps_por_cui: dict[str, set[str]] = defaultdict(set)
    for cui, eps in zip(d3["cui"], d3["cod_eps"]):
        if cui:
            eps_por_cui[cui].add(eps)
    res = []
    for fila, r in m.tablas["ds08_inversiones_mef"].crudos.iterrows():
        for eps in sorted(eps_por_cui.get(r["cui"], ())):
            nombre = nombres.get(eps)
            if nombre is None or normalizar(nombre) == normalizar(r["entidad"]):
                continue
            res.append(nuevo(
                cfg, "ds08_inversiones_mef", int(fila), f"cui = {r['cui']}",
                f"El CUI {r['cui']} pertenece en DS03 a {eps} ({nombre}), pero DS08 lo registra a nombre de "
                f"«{r['entidad']}» (comparado sin tildes ni mayúsculas).",
                observado=r["entidad"], esperado=normalizar(nombre),
            ))
    return res


@regla("CAL-CUI-01")
def cui_sin_mef(m, cfg, ctx):
    if "ds03_programa_inversiones" not in m.tablas or "ds08_inversiones_mef" not in m.tablas:
        return []
    d3 = m.tablas["ds03_programa_inversiones"].crudos
    en_mef = set(m.tablas["ds08_inversiones_mef"].crudos["cui"])
    res = []
    for cui, filas in _filas_por_valor(d3, "cui").items():
        if cui in en_mef:
            continue
        proyectos = sorted(set(d3.loc[filas, "cod_proyecto"]))
        res.append(nuevo(
            cfg, "ds03_programa_inversiones", filas[0], f"cui = {cui}",
            f"El proyecto {', '.join(proyectos)} declara el CUI {cui} en DS03 (filas {rango_filas(filas)}), "
            "pero ese CUI no figura en el registro del MEF (DS08). No se puede conciliar su avance.",
            observado=cui, esperado="CUI presente en DS08", detalle={"filas": filas, "proyectos": proyectos},
        ))
    return res
