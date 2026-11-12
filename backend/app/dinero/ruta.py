"""Ruta del dinero: fondos y reservas, usos excepcionales y por emergencia, y proyectos.

Que algo esté aprobado no significa que esté ejecutado. Cada monto dice de qué fondo o reserva
sale, su fuente (dataset y filas) y su naturaleza. Lo que la muestra no trae se muestra como
pendiente o «no puedo determinar», nunca como cero.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from app.calidad.reglas._util import fin_mes, soles
from app.plazos.calendario import Calendario
from app.plazos.catalogo import CatalogoPlazos

CERO = Decimal(0)
SIN_FONDO = "sin_fondo_indicado"
ESTADOS_EJECUCION = ("en_ejecucion", "paralizado", "concluido")


def a_json(x: Any) -> Any:
    """Montos Decimal → número con 2 decimales (soles) para la API."""
    if isinstance(x, Decimal):
        return float(x.quantize(Decimal("0.01")))
    if isinstance(x, dict):
        return {k: a_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [a_json(v) for v in x]
    return x


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else CERO


def _pct(num: Decimal, den: Decimal) -> float | None:
    return None if den == 0 else round(float(num / den * 100), 1)


def _filas(df: pd.DataFrame) -> list[int]:
    return [int(f) for f in df["_fila"]]


def _anio(v) -> int | None:
    if v is None:
        return None
    return v.year if isinstance(v, date) else int(str(v)[:4])


# =============================================================== usos del fondo
def _ufi(t: dict[str, pd.DataFrame], cod_eps: str | None = None, anio: int | None = None) -> pd.DataFrame:
    p = t["ds02_procedimientos"]
    p = p[p["tipo_procedimiento"] == "uso_excepcional_fondo"]
    if cod_eps:
        p = p[p["cod_eps"] == cod_eps]
    if anio:
        p = p[p["fecha_inicio"].map(_anio) == anio]
    return p


def _usos_de(t: dict[str, pd.DataFrame], id_expediente: str) -> pd.DataFrame:
    d5 = t["ds05_fondo_inversiones_reservas"]
    return d5[d5["id_expediente_uso_excepcional"] == id_expediente]


def ruta_expediente_uso(t: dict[str, pd.DataFrame], id_expediente: str, textos: dict[str, str]) -> dict[str, Any] | None:
    """Escalera de un uso excepcional del fondo (art. 89): solicitado → autorizado → usado → verificación → devolución."""
    p = t["ds02_procedimientos"]
    fila = p[p["id_expediente"] == id_expediente]
    if fila.empty:
        return None
    r = fila.iloc[0]
    usos = _usos_de(t, id_expediente)
    usado = sum((D(v) for v in usos["uso_excepcional"]), CERO)
    fondos_uso = sorted(set(usos["tipo_fondo"]))
    autorizado = r["monto_aprobado"]
    if r["estado"] == "en_tramite":
        est_aut, det_aut = "pendiente", "Pendiente de decisión: el expediente sigue en trámite."
    elif autorizado is not None and D(autorizado) > 0:
        est_aut, det_aut = "cumplido", f"Resultado: {r['resultado']}."
    else:
        est_aut, det_aut = "no_autorizado", f"Resultado: {r['resultado']}; monto aprobado 0."
    if fondos_uso:
        origen, det_origen = fondos_uso, "Fondo o reserva donde DS05 registra el uso (supuesto: es el fondo autorizado)."
    elif est_aut == "cumplido":
        origen, det_origen = None, "No puedo determinar el fondo de origen: DS05 no registra el uso de este expediente."
    else:
        origen, det_origen = None, "No aplica."
    senal = None
    if autorizado is not None and usado > D(autorizado):
        senal = f"El uso registrado ({soles(usado)}) supera el monto autorizado ({soles(D(autorizado))})."
    escalera = [
        {"peldano": "solicitado", "estado": "cumplido", "monto": D(r["monto_solicitado"]), "fondo": SIN_FONDO,
         "detalle": "DS02 no indica de qué fondo o reserva se pidió.",
         "fuente": f"DS02 ds02_procedimientos, fila {r['_fila']}"},
        {"peldano": "autorizado", "estado": est_aut, "monto": None if autorizado is None else D(autorizado),
         "fondo": origen, "detalle": f"{det_aut} {det_origen}",
         "fuente": f"DS02 fila {r['_fila']}; DS05 filas {_filas(usos) or '—'}"},
        {"peldano": "usado", "estado": "cumplido" if usado > 0 else ("pendiente" if est_aut == "cumplido" else "no_aplica"),
         "monto": usado, "fondo": fondos_uso or None,
         "detalle": "; ".join(f"{u['anio_mes']}: {soles(D(u['uso_excepcional']))} ({u['tipo_fondo']})" for _, u in usos.iterrows())
                    or "Sin usos registrados en DS05.",
         "fuente": f"DS05 filas {_filas(usos) or '—'}"},
        {"peldano": "verificacion_posterior", "estado": "pendiente" if usado > 0 else "no_aplica", "monto": None,
         "fondo": None, "area": None,
         "detalle": textos["verificacion_pendiente"] if usado > 0 else "No hay uso registrado que verificar.", "fuente": "—"},
        {"peldano": "devolucion", "estado": "sin_dato", "monto": None, "fondo": None,
         "detalle": "La muestra no registra si se dispuso devolución o exoneración.", "fuente": "—"},
    ]
    return {"id_expediente": id_expediente, "cod_eps": r["cod_eps"], "naturaleza": "sintético", "motivo": r["motivo"],
            "articulo": "RGT art. 89", "escalera": escalera, "senal": senal}


def ruta_caso_real(caso) -> dict[str, Any] | None:
    """Ruta del dinero de un caso real (casos_reales/*.yaml, sección ruta_dinero)."""
    rd = caso.datos.get("ruta_dinero")
    if not rd:
        return None
    e = caso.datos["expediente"]
    escalera = []
    for peldano in ("solicitado", "autorizado", "usado", "verificacion_posterior", "devolucion"):
        x = rd.get(peldano) or {}
        escalera.append({"peldano": peldano, "estado": x.get("estado", "sin_dato"),
                         "monto": None if x.get("monto") is None else D(x["monto"]), "fondo": x.get("fondo"),
                         "area": x.get("area"), "detalle": x.get("detalle", ""),
                         "fuente": x.get("fuente", caso.datos.get("fuente_principal", ""))})
    return {"id_expediente": e["id"], "cod_eps": None, "empresa": e.get("empresa"), "naturaleza": "real",
            "articulo": rd.get("articulo"), "escalera": escalera, "senal": None,
            "con_detalle_privado": caso.con_detalle_privado}


def usos_emergencia(t: dict[str, pd.DataFrame], cal: Calendario, cat: CatalogoPlazos,
                    cod_eps: str | None = None, anio: int | None = None) -> list[dict[str, Any]]:
    """Usos excepcionales sin expediente: uso por emergencia (art. 90). Requieren informe mensual, no son error."""
    d5 = t["ds05_fondo_inversiones_reservas"]
    sel = d5[d5["uso_excepcional"].map(lambda v: v is not None and D(v) > 0)
             & d5["id_expediente_uso_excepcional"].isna()]
    if cod_eps:
        sel = sel[sel["cod_eps"] == cod_eps]
    if anio:
        sel = sel[sel["anio_mes"].map(lambda m: int(m[:4])) == anio]
    res = []
    for _, r in sel.iterrows():
        cierre = fin_mes(r["anio_mes"])
        regla = cat.normativa("uso_emergencia_fondo", cierre)
        if regla is not None and regla.plazo_dh:
            limite = cal.sumar_dias_habiles(cierre, regla.plazo_dh)
            informe = {"estado": "informe no registrado", "fecha_limite": limite, "regla_id": regla.id,
                       "mensaje": f"Requiere informe mensual en {regla.plazo_dh} DH desde el cierre del mes: vence el "
                                  f"{limite}. La muestra no registra informes."}
        else:
            informe = {"estado": "no_calculable", "fecha_limite": None, "regla_id": None,
                       "mensaje": "No puedo calcular el plazo del informe: el uso es anterior al 01-08-2026 y falta la "
                                  "versión intermedia del art. 90 (RCD 037-2024, DRE-22)."}
        res.append({"cod_eps": r["cod_eps"], "anio_mes": r["anio_mes"], "tipo_fondo": r["tipo_fondo"],
                    "monto": D(r["uso_excepcional"]), "categoria": "uso_emergencia_art_90",
                    "texto": "Uso por emergencia (art. 90): requiere informe mensual en 10 DH. No es un error.",
                    "informe": informe, "fila": int(r["_fila"]),
                    "fuente": f"DS05 ds05_fondo_inversiones_reservas, fila {r['_fila']}; RGT art. 90 (RCD 028-2026)"})
    return res


def resumen_fondos(t: dict[str, pd.DataFrame], cod_eps: str | None = None, anio: int | None = None,
                   fondo: str | None = None, fondos: dict[str, str] | None = None) -> dict[str, Any]:
    """Totales por fondo o reserva: solicitado, autorizado, usado (ordinario, art. 89, art. 90) y verificado."""
    nombres = fondos or {}
    d5 = t["ds05_fondo_inversiones_reservas"]
    if cod_eps:
        d5 = d5[d5["cod_eps"] == cod_eps]
    if anio:
        d5 = d5[d5["anio_mes"].map(lambda m: int(m[:4])) == anio]
    claves = [k for k in nombres if k != SIN_FONDO] + [SIN_FONDO]

    def vacia(k: str) -> dict[str, Any]:
        return {"fondo": k, "nombre": nombres.get(k, k), "solicitado": CERO, "autorizado": CERO, "uso_ordinario": CERO,
                "uso_excepcional_art_89": CERO, "uso_emergencia_art_90": CERO, "verificado": None,
                "verificaciones_pendientes": 0, "deposito_programado": CERO, "deposito_efectuado": CERO,
                "saldo_final": None, "saldo_al": None, "expedientes": [], "filas_ds05": []}

    filas: dict[str, dict[str, Any]] = {k: vacia(k) for k in claves}
    for k, g in d5.groupby("tipo_fondo"):
        f = filas.setdefault(k, vacia(k))
        f["deposito_programado"] = sum((D(v) for v in g["deposito_programado"]), CERO)
        f["deposito_efectuado"] = sum((D(v) for v in g["deposito_efectuado"]), CERO)
        f["uso_ordinario"] = sum((D(v) for v in g["uso_ejecutado"]), CERO)
        con_id = g[g["id_expediente_uso_excepcional"].notna()]
        sin_id = g[g["id_expediente_uso_excepcional"].isna()]
        f["uso_excepcional_art_89"] = sum((D(v) for v in con_id["uso_excepcional"]), CERO)
        f["uso_emergencia_art_90"] = sum((D(v) for v in sin_id["uso_excepcional"]), CERO)
        f["verificaciones_pendientes"] += int((sin_id["uso_excepcional"].map(lambda v: D(v) > 0)).sum())
        ultimos = g.sort_values("anio_mes").groupby("cod_eps").tail(1)
        f["saldo_final"] = sum((D(v) for v in ultimos["saldo_final"]), CERO)
        f["saldo_al"] = max(g["anio_mes"])
        f["filas_ds05"] = _filas(g)
    for _, r in _ufi(t, cod_eps, anio).iterrows():
        usos = _usos_de(t, r["id_expediente"])
        filas[SIN_FONDO]["solicitado"] += D(r["monto_solicitado"])
        filas[SIN_FONDO]["expedientes"].append(r["id_expediente"])
        aprobado = D(r["monto_aprobado"])
        if aprobado > 0:
            destino = sorted(set(usos["tipo_fondo"]))[0] if not usos.empty else SIN_FONDO
            if destino in filas:
                filas[destino]["autorizado"] += aprobado
                filas[destino]["expedientes"].append(r["id_expediente"])
                if not usos.empty:
                    filas[destino]["verificaciones_pendientes"] += 1
    if fondo:
        filas = {k: v for k, v in filas.items() if k == fondo}
    lista = list(filas.values())
    total = {"fondo": "total", "nombre": "Total"}
    for c in ("solicitado", "autorizado", "uso_ordinario", "uso_excepcional_art_89", "uso_emergencia_art_90",
              "deposito_programado", "deposito_efectuado"):
        total[c] = sum((x[c] for x in lista), CERO)
    total["saldo_final"] = sum((x["saldo_final"] for x in lista if x["saldo_final"] is not None), CERO)
    total["verificado"] = None
    total["verificaciones_pendientes"] = sum(x["verificaciones_pendientes"] for x in lista)
    return {"filas": lista, "total": total, "naturaleza": "sintético",
            "notas": [
                "Solicitado: DS02 no indica de qué fondo se pidió; se agrupa en «Fondo o reserva no indicado».",
                "Autorizado: se asigna al fondo donde DS05 registra el uso (supuesto); si no hay uso registrado, "
                "queda en «no indicado».",
                "Verificado: la muestra no registra verificaciones posteriores; se muestra «pendiente», no cero.",
                "Uso por emergencia (art. 90, RCD 028-2026): usos excepcionales sin expediente. Requieren informe "
                "mensual en 10 DH; no son error. La muestra no tiene casos.",
                "Los casos reales (por ejemplo, EPSSMU) se muestran aparte y no se suman a estos totales de la muestra "
                "sintética.",
            ],
            "fuente": "DS05 ds05_fondo_inversiones_reservas y DS02 ds02_procedimientos (uso_excepcional_fondo)"}


def serie_fondo(t: dict[str, pd.DataFrame], cod_eps: str, fondo: str | None = None) -> list[dict[str, Any]]:
    d5 = t["ds05_fondo_inversiones_reservas"]
    g = d5[d5["cod_eps"] == cod_eps]
    if fondo:
        g = g[g["tipo_fondo"] == fondo]
    res = []
    for _, r in g.sort_values(["tipo_fondo", "anio_mes"]).iterrows():
        exc = D(r["uso_excepcional"])
        res.append({"anio_mes": r["anio_mes"], "tipo_fondo": r["tipo_fondo"],
                    "deposito_programado": D(r["deposito_programado"]), "deposito_efectuado": D(r["deposito_efectuado"]),
                    "diferencia_deposito": D(r["deposito_efectuado"]) - D(r["deposito_programado"]),
                    "uso_ordinario": D(r["uso_ejecutado"]), "uso_excepcional": exc,
                    "categoria_uso_excepcional": None if exc == 0 else (
                        "uso_excepcional_art_89" if r["id_expediente_uso_excepcional"] else "uso_emergencia_art_90"),
                    "id_expediente_uso_excepcional": r["id_expediente_uso_excepcional"],
                    "saldo_final": D(r["saldo_final"]), "fila": int(r["_fila"])})
    return res


# =================================================================== proyectos
def _ultimo_ds04(d4: pd.DataFrame) -> tuple[pd.Series | None, str | None]:
    """Último trimestre reportado de un proyecto. Si su llave está repetida, no se elige una fila."""
    if d4.empty:
        return None, "Sin reportes de ejecución en DS04."
    ultimo = max(d4["anio_trimestre"])
    filas = d4[d4["anio_trimestre"] == ultimo]
    if len(filas) > 1:
        return None, (f"No puedo determinar la ejecución: el trimestre {ultimo} está repetido en DS04 "
                      f"(filas {_filas(filas)}, CAL-DUP-02).")
    return filas.iloc[0], None


def _escalera(p: dict[str, Any], textos: dict[str, str]) -> list[dict[str, Any]]:
    est = p["estado_ejecucion"]
    e = [{"peldano": "programado", "estado": "cumplido",
          "detalle": f"Programado original {soles(p['monto_programado_original'])}; vigente {soles(p['monto_programado_vigente'])}.",
          "fuente": f"DS03 filas {p['filas_ds03']}"}]
    if p["monto_programado_original"] == 0 and p["expediente_modificacion"]:
        e.append({"peldano": "aprobado", "estado": "cumplido",
                  "detalle": f"Incorporado por el cambio {', '.join(p['expediente_modificacion'])}.",
                  "fuente": "DS03 id_expediente_modificacion"})
    elif p["tipo_periodo"] == "vigente":
        e.append({"peldano": "aprobado", "estado": "cumplido",
                  "detalle": f"Aprobado en el estudio tarifario del periodo {p['periodo_regulatorio']} "
                             f"({p.get('resolucion_estudio') or 'resolución no registrada'}).",
                  "fuente": "DS01 resolucion_estudio_vigente"})
    else:
        e.append({"peldano": "aprobado", "estado": "cumplido",
                  "detalle": f"Aprobado en el estudio del periodo anterior {p['periodo_regulatorio']} (la resolución no "
                             "figura en la muestra).", "fuente": "DS03 tipo_periodo"})
    e.append({"peldano": "financiado", "estado": "declarado",
              "detalle": f"Fuente declarada: {p['fuente_financiamiento']} (supuesto: declaración, no verificación).",
              "fuente": "DS03 fuente_financiamiento"})
    if est in ESTADOS_EJECUCION:
        e.append({"peldano": "en_ejecucion", "estado": "paralizado" if est == "paralizado" else "cumplido",
                  "detalle": f"Estado reportado: {est} ({p['ultimo_trimestre']}).", "fuente": f"DS04 fila {p['fila_ds04']}"})
    else:
        e.append({"peldano": "en_ejecucion", "estado": "pendiente",
                  "detalle": f"Estado reportado: {est or 'sin reporte'}.",
                  "fuente": f"DS04 fila {p['fila_ds04']}" if p["fila_ds04"] else "DS04"})
    concluido = est == "concluido"
    e.append({"peldano": "concluido", "estado": "cumplido" if concluido else "pendiente",
              "detalle": "Reportado como concluido por la EPS." if concluido else "Aún no concluido.",
              "fuente": f"DS04 fila {p['fila_ds04']}" if p["fila_ds04"] else "DS04"})
    e.append({"peldano": "verificacion_posterior", "estado": "pendiente" if concluido else "no_aplica",
              "detalle": textos["verificacion_pendiente"] if concluido else "Se verifica después de concluir.",
              "fuente": "—"})
    e.append({"peldano": "beneficio_verificado", "estado": "no_verificado", "detalle": textos["beneficio_no_verificado"],
              "fuente": "—"})
    return e


def _proyecto(cod: str, g3: pd.DataFrame, d4: pd.DataFrame, d8: pd.DataFrame, resoluciones: dict[str, str],
              umbral: float, textos: dict[str, str]) -> dict[str, Any]:
    f0 = g3.iloc[0]
    original = sum((D(v) for v in g3["monto_programado_original"]), CERO)
    vigente = sum((D(v) for v in g3["monto_programado_vigente"]), CERO)
    mods = sorted({m for m in g3["id_expediente_modificacion"] if m})
    ultimo, aviso = _ultimo_ds04(d4)
    ejecutado = D(ultimo["ejecucion_financiera_acumulada"]) if ultimo is not None else None
    fisico = float(ultimo["avance_fisico_acumulado_pct"]) if ultimo is not None and ultimo["avance_fisico_acumulado_pct"] is not None else None
    av_vig = _pct(ejecutado, vigente) if ejecutado is not None else None
    modificado = bool(mods) or original != vigente
    av_orig = _pct(ejecutado, original) if (ejecutado is not None and modificado) else None
    dif = None if av_vig is None or fisico is None else round(av_vig - fisico, 1)
    senal = dif is not None and abs(dif) > umbral
    cui = next((c for c in g3["cui"] if c is not None), None)
    mef = None
    if cui is not None:
        m = d8[d8["cui"] == cui]
        if not m.empty:
            r8 = m.iloc[0]
            mef = {"cui": int(cui), "estado_inversion": r8["estado_inversion"],
                   "devengado_acumulado": None if r8["devengado_acumulado"] is None else D(r8["devengado_acumulado"]),
                   "avance_fisico_pct": None if r8["avance_fisico_pct"] is None else float(r8["avance_fisico_pct"]),
                   "fecha_ultima_actualizacion": r8["fecha_ultima_actualizacion"], "fila": int(r8["_fila"]),
                   "nota": "Registro del MEF simulado. La conciliación en el corte común está en el reporte de calidad "
                           "(CAL-MEF-01 y 02)."}
        else:
            mef = {"cui": int(cui), "nota": "El CUI no figura en DS08 (CAL-CUI-01)."}
    p = {
        "cod_proyecto": cod, "cod_eps": f0["cod_eps"], "nombre_proyecto": f0["nombre_proyecto"],
        "localidad": f0["localidad"], "ubigeo": f0["ubigeo"], "componente": f0["componente"],
        "fuente_financiamiento": f0["fuente_financiamiento"], "periodo_regulatorio": f0["periodo_regulatorio"],
        "tipo_periodo": f0["tipo_periodo"], "meta_asociada": f0["meta_asociada"],
        "poblacion_beneficiaria": f0["poblacion_beneficiaria"], "naturaleza_poblacion": "estimado",
        "monto_programado_original": original, "monto_programado_vigente": vigente, "modificado": modificado,
        "expediente_modificacion": mods, "ejecucion_financiera": ejecutado,
        "ultimo_trimestre": None if ultimo is None else ultimo["anio_trimestre"],
        "estado_ejecucion": None if ultimo is None else ultimo["estado"], "avance_fisico": fisico,
        "avance_financiero": av_vig, "avance_financiero_original": av_orig,
        "base_avance_financiero": f"programado vigente ({soles(vigente)})"
                                  + (f"; original {soles(original)}" if modificado else ""),
        "diferencia_pp": dif, "senal_revision": senal, "aviso_ejecucion": aviso,
        "conciliacion_mef": mef, "resolucion_estudio": resoluciones.get(f0["cod_eps"]) if f0["tipo_periodo"] == "vigente" else None,
        "filas_ds03": _filas(g3), "fila_ds04": None if ultimo is None else int(ultimo["_fila"]),
        "naturaleza": "sintético",
        "fuente": f"DS03 filas {_filas(g3)}; DS04 {'fila ' + str(int(ultimo['_fila'])) if ultimo is not None else 'sin fila'}",
    }
    p["escalera"] = _escalera(p, textos)
    actual = [x for x in p["escalera"] if x["estado"] in ("cumplido", "declarado", "paralizado")]
    p["etapa_escalera"] = actual[-1]["peldano"] if actual else "programado"
    if p["estado_ejecucion"] == "paralizado":
        p["etapa_escalera"] = "paralizado"
    p["verificacion_posterior"] = next(x["estado"] for x in p["escalera"] if x["peldano"] == "verificacion_posterior")
    if senal:
        p["texto_senal"] = textos["senal"]
    return p


def proyectos(t: dict[str, pd.DataFrame], params: dict[str, Any], textos: dict[str, str], *, cod_eps: str | None = None,
              fuente: str | None = None, etapa: str | None = None, solo_senales: bool = False,
              periodo: str | None = None, cod_proyecto: str | None = None) -> list[dict[str, Any]]:
    d3, d4, d8 = t["ds03_programa_inversiones"], t["ds04_ejecucion_inversiones"], t["ds08_inversiones_mef"]
    resoluciones = dict(zip(t["ds01_catalogo_eps"]["cod_eps"], t["ds01_catalogo_eps"]["resolucion_estudio_vigente"]))
    if cod_eps:
        d3 = d3[d3["cod_eps"] == cod_eps]
    if fuente:
        d3 = d3[d3["fuente_financiamiento"] == fuente]
    if periodo:
        d3 = d3[d3["tipo_periodo"] == periodo]
    if cod_proyecto:
        d3 = d3[d3["cod_proyecto"] == cod_proyecto]
    umbral = float(params["umbral_senal_pp"]["valor"])
    por_proy = dict(tuple(d4.groupby("cod_proyecto"))) if not d4.empty else {}
    res = []
    for cod, g in d3.groupby("cod_proyecto", sort=True):
        p = _proyecto(cod, g, por_proy.get(cod, d4.iloc[0:0]), d8, resoluciones, umbral, textos)
        if etapa and p["etapa_escalera"] != etapa:
            continue
        if solo_senales and not p["senal_revision"]:
            continue
        res.append(p)
    return res


def detalle_proyecto(t: dict[str, pd.DataFrame], params: dict[str, Any], textos: dict[str, str], cod: str) -> dict[str, Any] | None:
    lista = proyectos(t, params, textos, cod_proyecto=cod)
    if not lista:
        return None
    p = lista[0]
    g3 = t["ds03_programa_inversiones"]
    g3 = g3[g3["cod_proyecto"] == cod].sort_values("anio")
    d4 = t["ds04_ejecucion_inversiones"]
    d4 = d4[d4["cod_proyecto"] == cod].sort_values(["anio_trimestre", "_fila"])
    p["anios"] = [{"anio": r["anio"], "original": D(r["monto_programado_original"]), "vigente": D(r["monto_programado_vigente"]),
                   "id_expediente_modificacion": r["id_expediente_modificacion"], "fila": int(r["_fila"])}
                  for _, r in g3.iterrows()]
    p["trimestres"] = [{"anio_trimestre": r["anio_trimestre"], "estado": r["estado"],
                        "ejecucion_trimestre": D(r["ejecucion_financiera_trimestre"]),
                        "ejecucion_acumulada": D(r["ejecucion_financiera_acumulada"]),
                        "avance_fisico": None if r["avance_fisico_acumulado_pct"] is None else float(r["avance_fisico_acumulado_pct"]),
                        "fecha_reporte": r["fecha_reporte"], "fila": int(r["_fila"])} for _, r in d4.iterrows()]
    return p


# =========================================================== contexto financiero
FORMULAS = {
    "margen_operativo_pct": "resultado_operativo / ingresos_operativos × 100",
    "relacion_trabajo_pct": "(costo_ventas + gastos_administracion + gastos_ventas − depreciacion_amortizacion) / ingresos_operativos × 100",
    "liquidez_corriente": "activo_corriente / pasivo_corriente",
    "endeudamiento": "pasivo_total / patrimonio",
    "morosidad_pct": "cuentas_por_cobrar_comerciales / facturacion_servicios × 100",
    "eficiencia_cobranza_pct": "recaudacion / facturacion_servicios × 100",
}


def contexto_financiero(t: dict[str, pd.DataFrame], cod_eps: str, hallazgos: list[dict[str, Any]]) -> dict[str, Any]:
    d6 = t["ds06_estados_financieros"]
    g = d6[d6["cod_eps"] == cod_eps].sort_values("anio")
    anios = []
    for _, r in g.iterrows():
        avisos = [f"{h['regla_id']}: {h['titulo']}" for h in hallazgos
                  if h["dataset"] == "ds06_estados_financieros" and h["fila"] == int(r["_fila"])]
        anios.append({"anio": r["anio"], "estado_presentacion": r["estado_presentacion"],
                      "indicadores": {k: (None if r[k] is None else float(r[k])) for k in FORMULAS},
                      "avisos_calidad": avisos, "fila": int(r["_fila"])})
    return {"cod_eps": cod_eps, "anios": anios, "formulas": FORMULAS, "naturaleza": "sintético",
            "aviso": "Contexto financiero: no es una nota ni un diagnóstico de la EPS.",
            "fuente": "DS06 ds06_estados_financieros; fórmulas de la hoja Supuestos del diccionario"}
