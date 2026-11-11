"""Coherencia aritmética interna de los datasets."""

from __future__ import annotations

from decimal import Decimal

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import dec, mes_anterior, num, rango_filas, soles, trimestre_anterior

MEDIO = Decimal("0.5")


def _medio_ulp(decimales: int) -> Decimal:
    """Error máximo de redondear a `decimales` decimales: 0,5 × 10^-decimales."""
    return MEDIO * Decimal(10) ** -decimales


# Rangos para describir la distribución de diferencias que caen en la tolerancia.
RANGOS_SOLES = (Decimal("0.01"), Decimal("1"), Decimal("10"), Decimal("50"), Decimal("100"), Decimal("250"))
RANGOS_RELATIVOS = (Decimal("0.25"), Decimal("0.5"), Decimal("0.75"), Decimal("0.9"), Decimal("1"))


def _histograma(valores, cortes, formato) -> dict[str, int]:
    etiquetas = []
    previo = Decimal(0)
    for c in cortes:
        etiquetas.append((previo, c, f"{formato(previo)} a {formato(c)}"))
        previo = c
    res = {e: 0 for _, _, e in etiquetas}
    res[f"más de {formato(previo)}"] = 0
    for v in valores:
        for lo, hi, e in etiquetas:
            if (v == 0 and lo == 0) or lo < v <= hi:
                res[e] += 1
                break
        else:
            res[f"más de {formato(previo)}"] += 1
    return res


def _fmt_soles(d: Decimal) -> str:
    return f"S/ {num(d)}"


def _fmt_rel(d: Decimal) -> str:
    return f"{int(d * 100)} %"


@regla("CAL-ARI-01")
def saldo_final(m, cfg, ctx):
    if "ds05_fondo_inversiones_reservas" not in m.tablas:
        return []
    d5 = m["ds05_fondo_inversiones_reservas"]
    tol = 6 * _medio_ulp(int(cfg.param("decimales_monto")))
    dentro, res = [], []
    for _, r in d5.iterrows():
        partes = [r[c] for c in ("saldo_inicial", "deposito_efectuado", "intereses", "uso_ejecutado", "uso_excepcional", "saldo_final")]
        if any(p is None for p in partes):
            continue
        si, dep, inte, uso, exc, sf = partes
        calc = si + dep + inte - uso - exc
        dif = abs(calc - sf)
        if dif == 0:
            continue
        llave = f"{r['cod_eps']} · {r['anio_mes']} · {r['tipo_fondo']}"
        if dif <= tol:
            dentro.append((int(r["_fila"]), dif))
        else:
            res.append(nuevo(
                cfg, "ds05_fondo_inversiones_reservas", r["_fila"], llave,
                f"Saldo final de {llave}: el CSV dice {soles(sf)}, pero saldo inicial + depósito + intereses − uso − "
                f"uso excepcional da {soles(calc)}. Diferencia de {soles(dif)}, mayor a la tolerancia de redondeo "
                f"({soles(tol)}). Puede faltar un movimiento: revisar con la EPS.",
                observado=soles(sf), esperado=soles(calc), detalle={"diferencia": str(dif)},
            ))
    if dentro:
        filas = [f for f, _ in dentro]
        res.append(nuevo(
            cfg, "ds05_fondo_inversiones_reservas", None, f"{len(dentro)} filas",
            f"{len(dentro)} filas tienen una diferencia de hasta {soles(max(d for _, d in dentro))} entre el saldo "
            f"final y su fórmula (filas {rango_filas(filas)}). Está dentro de la tolerancia derivada del redondeo de "
            f"los 6 montos a 2 decimales ({soles(tol)}): se informa, no se considera error.",
            severidad="informativa", titulo="Saldo final con diferencias de redondeo",
            observado=f"{len(dentro)} filas", esperado=f"diferencia ≤ {soles(tol)}",
            detalle={"filas": filas, "tolerancia": str(tol)},
        ))
    return res


@regla("CAL-ARI-02")
def deposito_programado(m, cfg, ctx):
    """deposito_programado = porcentaje_ingresos × ingresos_base_mes / 100.

    Tolerancia relativa a los ingresos del mes, derivada del redondeo:
    ingresos_base_mes × (0,5 × 10^-decimales_porcentaje) / 100 + 0,5 × 10^-decimales_monto.
    """
    if "ds05_fondo_inversiones_reservas" not in m.tablas:
        return []
    d5 = m["ds05_fondo_inversiones_reservas"]
    ulp_pct = _medio_ulp(int(cfg.param("decimales_porcentaje")))
    ulp_monto = _medio_ulp(int(cfg.param("decimales_monto")))
    dentro, res = [], []
    for _, r in d5.iterrows():
        pct, base, prog = r["porcentaje_ingresos"], r["ingresos_base_mes"], r["deposito_programado"]
        if pct is None or base is None or prog is None:
            continue
        calc = pct * base / 100
        dif = abs(prog - calc)
        tol = abs(base) * ulp_pct / 100 + ulp_monto
        llave = f"{r['cod_eps']} · {r['anio_mes']} · {r['tipo_fondo']}"
        if dif <= tol:
            if dif > 0:
                dentro.append((int(r["_fila"]), dif, dif / tol))
            continue
        res.append(nuevo(
            cfg, "ds05_fondo_inversiones_reservas", r["_fila"], llave,
            f"Depósito programado de {llave}: el CSV dice {soles(prog)}, pero {num(pct)} % × {soles(base)} = "
            f"{soles(calc)}. La diferencia ({soles(dif)}) supera la tolerancia que explicaría el redondeo del "
            f"porcentaje ({soles(tol)}).",
            observado=soles(prog), esperado=f"{soles(calc)} ± {soles(tol)}",
            detalle={"diferencia": str(dif), "tolerancia": str(tol)},
        ))
    if dentro:
        filas = [f for f, _, _ in dentro]
        hist_soles = _histograma([d for _, d, _ in dentro], RANGOS_SOLES, _fmt_soles)
        hist_rel = _histograma([q for _, _, q in dentro], RANGOS_RELATIVOS, _fmt_rel)
        txt_soles = "; ".join(f"{k}: {v}" for k, v in hist_soles.items() if v)
        txt_rel = "; ".join(f"{k}: {v}" for k, v in hist_rel.items() if v)
        res.append(nuevo(
            cfg, "ds05_fondo_inversiones_reservas", None, f"{len(dentro)} filas",
            f"{len(dentro)} filas tienen diferencias de hasta {soles(max(d for _, d, _ in dentro))} entre el depósito "
            "programado y porcentaje × ingresos base. Todas caben en la tolerancia derivada del redondeo: el CSV "
            f"publica el porcentaje con {cfg.param('decimales_porcentaje')} decimales, así que el porcentaje real "
            f"puede diferir hasta {num(ulp_pct)} puntos, es decir, ingresos_base_mes × {num(ulp_pct / 100)} soles "
            f"(más S/ {num(ulp_monto)} por el redondeo del depósito). La tolerancia no es un monto fijo: crece con "
            f"los ingresos del mes. Filas por diferencia en soles: {txt_soles}. Filas por fracción de la tolerancia "
            f"usada: {txt_rel}. Que el porcentaje esté redondeado es un SUPUESTO por validar.",
            severidad="informativa", titulo="Depósito programado con diferencias de redondeo del porcentaje",
            observado=f"{len(dentro)} filas", esperado="diferencia ≤ tolerancia de redondeo",
            detalle={"filas": filas, "por_rango_soles": hist_soles, "por_fraccion_de_tolerancia": hist_rel},
        ))
    return res


@regla("CAL-ARI-03")
def continuidad_saldo(m, cfg, ctx):
    if "ds05_fondo_inversiones_reservas" not in m.tablas:
        return []
    tol = Decimal(str(cfg.param("tolerancia")))
    d5 = m["ds05_fondo_inversiones_reservas"]
    indice = {(r["cod_eps"], r["tipo_fondo"], r["anio_mes"]): r for _, r in d5.iterrows()}
    res = []
    for (eps, fondo, mes), r in indice.items():
        ant = indice.get((eps, fondo, mes_anterior(mes)))
        if ant is None or ant["saldo_final"] is None or r["saldo_inicial"] is None:
            continue
        dif = abs(r["saldo_inicial"] - ant["saldo_final"])
        if dif > tol:
            res.append(nuevo(
                cfg, "ds05_fondo_inversiones_reservas", r["_fila"], f"{eps} · {mes} · {fondo}",
                f"El saldo inicial de {mes} ({soles(r['saldo_inicial'])}) no es igual al saldo final de "
                f"{mes_anterior(mes)} ({soles(ant['saldo_final'])}, fila {ant['_fila']}); diferencia de {soles(dif)}.",
                observado=soles(r["saldo_inicial"]), esperado=soles(ant["saldo_final"]),
                detalle={"fila_mes_anterior": int(ant["_fila"])},
            ))
    return res


@regla("CAL-ARI-04")
def acumulados_ds04(m, cfg, ctx):
    if "ds04_ejecucion_inversiones" not in m.tablas:
        return []
    tol = Decimal(str(cfg.param("tolerancia_soles")))
    d4 = m["ds04_ejecucion_inversiones"]
    claves = d4.groupby(["cod_proyecto", "anio_trimestre"]).size()
    unicos = {k for k, n in claves.items() if n == 1}  # las llaves repetidas las reporta CAL-DUP-02
    indice = {(r["cod_proyecto"], r["anio_trimestre"]): r for _, r in d4.iterrows()
              if (r["cod_proyecto"], r["anio_trimestre"]) in unicos}
    res = []
    # Avance físico: se compara con el último trimestre reportado, aunque haya trimestres sin reporte.
    previo: dict[str, object] = {}
    for (proy, t), r in sorted(indice.items()):
        ant = previo.get(proy)
        previo[proy] = r
        if ant is None:
            continue
        a, b = ant["avance_fisico_acumulado_pct"], r["avance_fisico_acumulado_pct"]
        if a is not None and b is not None and b < a:
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r["_fila"], f"{proy} · {t}",
                f"El avance físico acumulado de {proy} baja de {num(a)} % en {ant['anio_trimestre']} "
                f"(fila {ant['_fila']}) a {num(b)} % en {t}. Un acumulado no debería retroceder.",
                observado=f"{num(b)} %", esperado=f"≥ {num(a)} %", titulo="Avance físico acumulado que retrocede",
                detalle={"fila_trimestre_anterior": int(ant["_fila"])},
            ))
    # Ejecución financiera: solo entre trimestres consecutivos (si falta uno, su monto no se conoce).
    for (proy, t), r in indice.items():
        ant = indice.get((proy, trimestre_anterior(t)))
        if ant is None:
            continue
        llave = f"{proy} · {t}"
        ea, eb, et = ant["ejecucion_financiera_acumulada"], r["ejecucion_financiera_acumulada"], r["ejecucion_financiera_trimestre"]
        if None not in (ea, eb, et) and abs((eb - ea) - et) > tol:
            res.append(nuevo(
                cfg, "ds04_ejecucion_inversiones", r["_fila"], llave,
                f"En {proy}, la ejecución acumulada pasa de {soles(ea)} ({trimestre_anterior(t)}, fila {ant['_fila']}) "
                f"a {soles(eb)} ({t}): sube {soles(eb - ea)}, pero lo ejecutado en el trimestre es {soles(et)}.",
                observado=soles(eb - ea), esperado=soles(et), titulo="Ejecución acumulada que no suma",
                detalle={"fila_trimestre_anterior": int(ant["_fila"])},
            ))
    return res


_FORMULAS = {
    # Hoja Supuestos del diccionario (Indicadores financieros DS06).
    "margen_operativo_pct": lambda r: r["resultado_operativo"] / r["ingresos_operativos"] * 100,
    "relacion_trabajo_pct": lambda r: (r["costo_ventas"] + r["gastos_administracion"] + r["gastos_ventas"]
                                       - r["depreciacion_amortizacion"]) / r["ingresos_operativos"] * 100,
    "liquidez_corriente": lambda r: r["activo_corriente"] / r["pasivo_corriente"],
    "endeudamiento": lambda r: r["pasivo_total"] / r["patrimonio"],
    "morosidad_pct": lambda r: r["cuentas_por_cobrar_comerciales"] / r["facturacion_servicios"] * 100,
    "eficiencia_cobranza_pct": lambda r: r["recaudacion"] / r["facturacion_servicios"] * 100,
}


_IDENTIDADES = {
    # Estado de resultados del mismo registro (ver parámetro `identidades` en rules/calidad.yaml).
    "resultado_operativo": lambda r: r["ingresos_operativos"] - r["costo_ventas"] - r["gastos_administracion"]
    - r["gastos_ventas"],
    "resultado_neto": lambda r: r["resultado_operativo"] + r["ingresos_financieros"] - r["gastos_financieros"]
    - r["impuesto_renta"],
}


def _calcular(f, r):
    try:
        return f(r)
    except (TypeError, ZeroDivisionError, ArithmeticError):
        return None


@regla("CAL-ARI-05")
def indicadores_ds06(m, cfg, ctx):
    """Recalcula indicadores y resultados de DS06.

    Un margen negativo no es un error: solo se marca si no cuadra con los
    montos del mismo registro. Si el indicador tiene el signo invertido
    respecto de su fórmula, se dice explícitamente y se aclara si el
    registro muestra pérdida o utilidad.
    """
    if "ds06_estados_financieros" not in m.tablas:
        return []
    tol = float(cfg.param("tolerancia"))
    tol_soles = int(cfg.param("tolerancia_identidades_soles"))
    res = []
    for _, r in m["ds06_estados_financieros"].iterrows():
        base = f"{r['cod_eps']} {r['anio']}"
        identidades_ok = True
        for col, f in _IDENTIDADES.items():
            calc = _calcular(f, r)
            if calc is None or r[col] is None:
                continue
            if abs(calc - r[col]) > tol_soles:
                identidades_ok = False
                res.append(nuevo(
                    cfg, "ds06_estados_financieros", r["_fila"], f"{r['cod_eps']} · {r['anio']} · {col}",
                    f"{col} de {base} figura como {soles(r[col])}, pero los montos del mismo registro dan "
                    f"{soles(calc)}.",
                    observado=soles(r[col]), esperado=soles(calc), severidad="media",
                    titulo="Resultado que no cuadra con los montos del registro",
                ))
        for ind, f in _FORMULAS.items():
            calc = _calcular(f, r)
            if calc is None or r[ind] is None:
                continue
            calc, publicado = float(calc), float(r[ind])
            if abs(calc - publicado) <= tol:
                continue
            llave = f"{r['cod_eps']} · {r['anio']} · {ind}"
            if abs(calc + publicado) <= tol and calc != 0:
                if ind == "margen_operativo_pct" and r["resultado_operativo"] is not None and identidades_ok:
                    estado = ("utilidad operativa" if r["resultado_operativo"] > 0 else "pérdida operativa")
                    lectura = (f" El registro cuadra (ingresos {soles(r['ingresos_operativos'])} − costos y gastos = "
                               f"resultado operativo {soles(r['resultado_operativo'])}) y muestra una {estado}, así "
                               f"que el error está en el signo del margen, no en los montos.")
                else:
                    lectura = ""
                res.append(nuevo(
                    cfg, "ds06_estados_financieros", r["_fila"], llave,
                    f"{ind} de {base} figura como {num(r[ind])}, pero la fórmula de la hoja Supuestos da "
                    f"{dec(calc, 2)}: el signo está invertido.{lectura} Mostrarlo tal cual haría leer lo contrario.",
                    observado=num(r[ind]), esperado=f"{dec(calc, 2)}", severidad="media",
                    titulo="Indicador financiero con el signo invertido",
                ))
                continue
            res.append(nuevo(
                cfg, "ds06_estados_financieros", r["_fila"], llave,
                f"{ind} de {base} figura como {num(r[ind])}, pero la fórmula de la hoja Supuestos da {dec(calc, 4)}.",
                observado=num(r[ind]), esperado=f"{dec(calc, 2)}",
            ))
    return res


@regla("CAL-ARI-06")
def catalogo_vs_localidades(m, cfg, ctx):
    if "ds01_catalogo_eps" not in m.tablas or "ds01_localidades_eps" not in m.tablas:
        return []
    loc = m["ds01_localidades_eps"]
    sumas = loc.groupby("cod_eps").agg(
        conexiones_agua=("conexiones_agua", "sum"),
        conexiones_alcantarillado=("conexiones_alcantarillado", "sum"),
        poblacion_servida=("poblacion_servida", "sum"),
        n_localidades=("localidad", "count"),
    )
    res = []
    for _, r in m["ds01_catalogo_eps"].iterrows():
        eps = r["cod_eps"]
        for col in ("conexiones_agua", "conexiones_alcantarillado", "poblacion_servida", "n_localidades"):
            esperado = int(sumas.loc[eps, col]) if eps in sumas.index else 0
            if r[col] is not None and int(r[col]) != esperado:
                res.append(nuevo(
                    cfg, "ds01_catalogo_eps", r["_fila"], f"{eps} · {col}",
                    f"{col} de {eps} en el catálogo es {r[col]}, pero la suma de sus localidades es {esperado}.",
                    observado=r[col], esperado=esperado,
                ))
    return res
