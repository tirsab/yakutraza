"""Conciliación del avance que reporta la EPS (DS04) con el MEF (DS08).

DS04 llega al último trimestre reportado (2026-T2) y DS08 es una foto única
actualizada entre agosto y septiembre de 2026. Para no confundir desfase con
error, se compara en un corte común cuando los datos lo permiten:

- Ejecución financiera: el devengado del MEF al cierre del año anterior se
  obtiene como devengado_acumulado − devengado_<año> (hoja ds08: «devengado
  acumulado al corte» y «devengado <año> al corte»). Se compara con la
  ejecución acumulada de DS04 en el trimestre T4 de ese año anterior.
- Avance físico: DS08 no trae historia, así que no hay corte común. Una
  diferencia en la dirección del desfase (MEF mayor, con fecha posterior) no
  se puede verificar y se informa; un MEF menor que la EPS no lo explica el
  desfase (un acumulado no retrocede) y se marca como diferencia real.

Las diferencias que el desfase explica son informativas (tipo desfase_mef),
no alertas.
"""

from __future__ import annotations

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import dec, fin_trimestre, num, soles

TIPO_DESFASE = "desfase_mef"


def _pares(m):
    """(fila DS04 del último trimestre de cada proyecto, fila DS08 de su CUI, CUI, índice DS04)."""
    req = ("ds03_programa_inversiones", "ds04_ejecucion_inversiones", "ds08_inversiones_mef")
    if any(r not in m.tablas for r in req):
        return [], {}
    d3, d4, d8 = (m[r] for r in req)
    cui_por_proyecto = {}
    for cod, cui in zip(d3["cod_proyecto"], d3["cui"]):
        if cui is not None:
            cui_por_proyecto.setdefault(cod, cui)
    d8_por_cui = {r["cui"]: r for _, r in d8.iterrows()}
    # Las llaves repetidas (CAL-DUP-02) no sirven para leer un acumulado: se excluyen del índice.
    unicas = d4[~d4.duplicated(["cod_proyecto", "anio_trimestre"], keep=False)]
    indice = {(r["cod_proyecto"], r["anio_trimestre"]): r for _, r in unicas.iterrows()}
    ultimos = d4.sort_values(["cod_proyecto", "anio_trimestre", "_fila"]).groupby("cod_proyecto").tail(1)
    pares = []
    for _, r4 in ultimos.iterrows():
        cui = cui_por_proyecto.get(r4["cod_proyecto"])
        if cui is not None and cui in d8_por_cui:
            pares.append((r4, d8_por_cui[cui], cui))
    return pares, indice


def _fechas(r4, r8) -> str:
    return (f"La EPS reporta al trimestre {r4['anio_trimestre']} (cierre {fin_trimestre(r4['anio_trimestre'])}); "
            f"el MEF se actualizó el {r8['fecha_ultima_actualizacion']}.")


@regla("CAL-MEF-01")
def avance_fisico(m, cfg, ctx):
    umbral = float(cfg.param("umbral_puntos_porcentuales"))
    pares, _ = _pares(m)
    res = []
    for r4, r8, cui in pares:
        a4, a8 = r4["avance_fisico_acumulado_pct"], r8["avance_fisico_pct"]
        if a4 is None or a8 is None:
            continue
        dif = float(a8) - float(a4)
        if abs(dif) <= umbral:
            continue
        llave = f"{r4['cod_proyecto']} · CUI {cui}"
        base = (f"Avance físico de {r4['cod_proyecto']}: la EPS reporta {num(a4)} % (DS04, fila {r4['_fila']}) y el "
                f"MEF {num(a8)} % (DS08, fila {r8['_fila']}); diferencia de {dec(abs(dif), 1)} puntos (umbral "
                f"{umbral:g}, supuesto). {_fechas(r4, r8)}")
        detalle = {"fila_ds08": int(r8["_fila"]), "cui": cui, "diferencia_pp": round(dif, 2)}
        posterior = r8["fecha_ultima_actualizacion"] is not None and \
            r8["fecha_ultima_actualizacion"] > fin_trimestre(r4["anio_trimestre"])
        if dif > 0 and posterior:
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r4["_fila"], llave,
                base + " El MEF es posterior y mayor, en la dirección del desfase. DS08 no trae la historia del avance "
                "físico, así que no se puede comparar en el mismo corte: se informa, no es una alerta.",
                observado=f"{num(a4)} %", esperado=f"{num(a8)} % (MEF, otra fecha)", severidad="informativa",
                tipo=TIPO_DESFASE, titulo="Avance físico distinto al MEF, no comparable en el mismo corte",
                detalle={**detalle, "clasificacion": "desfase_no_verificable"},
            ))
        else:
            motivo = ("El MEF, con fecha posterior, registra menos avance que la EPS: un acumulado no retrocede, así "
                      "que el desfase no lo explica." if posterior else
                      "Las fechas no explican la diferencia.")
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r4["_fila"], llave, f"{base} {motivo}",
                observado=f"{num(a4)} %", esperado=f"{num(a8)} % ± {umbral:g}",
                detalle={**detalle, "clasificacion": "diferencia_real"},
            ))
    return res


def _ds04_en_corte(proyecto, corte, r4_ultimo, indice):
    """Ejecución acumulada de DS04 al cierre del trimestre `corte` y cómo se obtuvo."""
    r = indice.get((proyecto, corte))
    if r is not None and r["ejecucion_financiera_acumulada"] is not None:
        return r["ejecucion_financiera_acumulada"], f"DS04 {corte}, fila {r['_fila']}"
    a, q = int(corte[:4]), int(corte[-1])
    siguiente = f"{a + 1}-T1" if q == 4 else f"{a}-T{q + 1}"
    s = indice.get((proyecto, siguiente))
    if s is not None and None not in (s["ejecucion_financiera_acumulada"], s["ejecucion_financiera_trimestre"]):
        return (s["ejecucion_financiera_acumulada"] - s["ejecucion_financiera_trimestre"],
                f"DS04 {siguiente} (fila {s['_fila']}) menos lo ejecutado en ese trimestre, porque {corte} no tiene reporte")
    if r4_ultimo["anio_trimestre"] < corte and r4_ultimo["estado"] == "concluido" \
            and r4_ultimo["ejecucion_financiera_acumulada"] is not None:
        return (r4_ultimo["ejecucion_financiera_acumulada"],
                f"último reporte de DS04 ({r4_ultimo['anio_trimestre']}, fila {r4_ultimo['_fila']}, proyecto concluido; "
                "supuesto: un proyecto concluido no ejecuta más)")
    return None, None


def _relativa(a, b) -> float | None:
    mayor = max(float(a), float(b))
    return None if mayor == 0 else abs(float(a) - float(b)) / mayor * 100


@regla("CAL-MEF-02")
def ejecucion_financiera(m, cfg, ctx):
    umbral = float(cfg.param("umbral_relativo_pct"))
    anio = int(cfg.param("anio_devengado"))
    corte = f"{anio - 1}-T4"
    col_anio = f"devengado_{anio}"
    pares, indice = _pares(m)
    res = []
    for r4, r8, cui in pares:
        e4, e8 = r4["ejecucion_financiera_acumulada"], r8["devengado_acumulado"]
        if e4 is None or e8 is None:
            continue
        rel_actual = _relativa(e4, e8)
        llave = f"{r4['cod_proyecto']} · CUI {cui}"
        actual = (f"Hoy: la EPS reporta {soles(e4)} (DS04, {r4['anio_trimestre']}, fila {r4['_fila']}) y el MEF un "
                  f"devengado de {soles(e8)} (DS08, fila {r8['_fila']}, al {r8['fecha_ultima_actualizacion']})")
        detalle = {"fila_ds08": int(r8["_fila"]), "cui": cui, "corte_comun": corte,
                   "diferencia_relativa_actual_pct": None if rel_actual is None else round(rel_actual, 2)}

        e4c, como = _ds04_en_corte(r4["cod_proyecto"], corte, r4, indice)
        e8c = None if r8[col_anio] is None else e8 - r8[col_anio]
        if e4c is None or e8c is None:
            if rel_actual is not None and rel_actual > umbral:
                res.append(nuevo(
                    cfg, "ds04_ejecucion_inversiones", r4["_fila"], llave,
                    f"{actual}; diferencia de {dec(rel_actual, 1)} %. No puedo comparar en el corte común {corte}: falta "
                    f"{'el dato de DS04 en ese corte' if e4c is None else col_anio + ' en DS08'}. Se informa sin "
                    "calificarla.",
                    severidad="informativa", tipo=TIPO_DESFASE,
                    titulo="Ejecución distinta al MEF, sin corte común para compararla",
                    detalle={**detalle, "clasificacion": "sin_corte_comun"},
                ))
            continue

        rel_comun = _relativa(e4c, e8c)
        comun = (f"Al cierre de {corte}: la EPS {soles(e4c)} ({como}) y el MEF {soles(e8c)} (devengado acumulado "
                 f"{soles(e8)} menos {col_anio} {soles(r8[col_anio])})")
        detalle.update(ds04_corte=str(e4c), ds08_corte=str(e8c),
                       diferencia_relativa_corte_pct=None if rel_comun is None else round(rel_comun, 2))
        posterior_menor = float(e8) < float(e4) and rel_actual is not None and rel_actual > umbral
        if (rel_comun is not None and rel_comun > umbral) or posterior_menor:
            motivo = (f"La diferencia se mantiene en el mismo corte ({dec(rel_comun, 1)} %, umbral {umbral:g} %, "
                      "supuesto): no la explica el desfase de fechas." if rel_comun is not None and rel_comun > umbral
                      else "El MEF, con fecha posterior, registra menos que la EPS: el desfase no lo explica.")
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r4["_fila"], llave, f"{comun}. {motivo} {actual}.",
                observado=soles(e4c), esperado=f"{soles(e8c)} ± {umbral:g} %",
                titulo="Ejecución distinta al MEF en el mismo corte de fecha",
                detalle={**detalle, "clasificacion": "diferencia_real"},
            ))
        elif rel_actual is not None and rel_actual > umbral:
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r4["_fila"], llave,
                f"{actual}; diferencia de {dec(rel_actual, 1)} %. {comun}: diferencia de {dec(rel_comun or 0, 1)} %, dentro del "
                f"umbral de {umbral:g} %. La diferencia de hoy aparece después de {corte} y se explica por el desfase "
                "de fechas: se informa, no es una alerta.",
                observado=soles(e4), esperado=f"{soles(e8)} (MEF, otra fecha)", severidad="informativa",
                tipo=TIPO_DESFASE, titulo="Ejecución distinta al MEF explicada por el desfase de fechas",
                detalle={**detalle, "clasificacion": "explicada_por_desfase"},
            ))
    return res
