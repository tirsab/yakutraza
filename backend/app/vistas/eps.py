"""Vista EPS (Fase 5): sus trámites, qué le falta y hasta cuándo, y su fondo con los usos autorizados.

Solo su cod_eps. Sin documentos internos de Sunass. Una acción por pantalla.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.dinero import ruta
from app.dinero.datos import tablas
from app.vistas.bandeja import EP, SUNASS_TECNICO
from app.vistas.etiquetas import etiqueta
from app.vistas.pasos import catalogo as cat_pasos, pasos_de
from app.vistas.tablero import Contexto, evaluar, filtrar

AVISO_CORREO = "Vista previa: este aviso no se envía. Fuera del alcance del prototipo (sin envío real de mensajes)."


def _pendiente(f, cat: dict[str, Any]) -> dict[str, Any] | None:
    """Lo que le toca a la EPS en un expediente, si algo le toca."""
    oficio = next((a for a in f.alertas if a.reloj == "oficio" and a.estado in ("en_plazo", "por_vencer", "vencido")),
                  None)
    h = f.hito
    if oficio is None and not (h and h.responsable in EP):
        return None
    hito = oficio.hito if oficio else h.hito
    del_hito = next((x for x in f.exp.hitos if x.hito == hito), None)
    return {
        # Solo si el hito no cuenta para el plazo de Sunass (DS02 cuenta_plazo = False): la EP suspende el plazo.
        "suspende_plazo": bool(del_hito and del_hito.cuenta_plazo is False),
        "id_expediente": f.exp.id, "tipo_procedimiento": f.exp.tipo, "hito": hito,
        "accion": (cat["categorias"].get("accion_ep", {}).get(hito) or f"Enviar a la Sunass: {etiqueta(cat, 'hito', hito)}") + ".",
        "fecha_limite": oficio.fecha_limite if oficio else None,
        "dias_restantes": oficio.dias_restantes if oficio else None,
        "estado": oficio.estado if oficio else "sin_plazo",
        "detalle": oficio.mensaje if oficio else "No hay un plazo registrado para esta respuesta.",
        "documento": oficio.documento_inicio if oficio else None,
        "fuente": oficio.fuente if oficio else f"DS02 fila {h.fila}",
    }


def resumen_eps(ctx: Contexto, cod_eps: str, cat: dict[str, Any], textos: dict[str, str]) -> dict[str, Any]:
    cp = cat_pasos(Path(ctx.s.rules_dir) / "pasos_procedimiento.yaml")
    filas = filtrar(evaluar(ctx), cod_eps=cod_eps)
    pendientes, tramites = [], []
    for f in filas:
        p = _pendiente(f, cat)
        if p:
            pendientes.append(p)
        quien = f.hito.responsable if f.hito else None
        tramites.append({
            "id_expediente": f.exp.id, "tipo_procedimiento": f.exp.tipo, "fecha_inicio": f.exp.fecha_inicio,
            "hito_al_corte": f.hito.hito if f.hito else None, "responsable_al_corte": quien,
            "le_toca_a_la_eps": p is not None,
            "pasos": pasos_de(f.exp, cp, ctx.corte),
            "en_que_va": ("Le toca a su EPS." if p else
                          f"Está en la Sunass ({etiqueta(cat, 'responsable', quien)})." if quien in SUNASS_TECNICO
                          or quien not in EP else "En espera."),
        })
    pendientes.sort(key=lambda p: (p["dias_restantes"] if p["dias_restantes"] is not None else 10**6))
    concluidos = sorted([e for e in ctx.exps.values() if e.cod_eps == cod_eps and e.fecha_conclusion
                         and e.fecha_conclusion <= ctx.corte], key=lambda e: e.fecha_conclusion, reverse=True)[:5]
    t = tablas(ctx.s.database_url)
    d2 = t["ds02_procedimientos"]
    resultados = dict(zip(d2["id_expediente"], d2["resultado"]))
    fondos = ruta.resumen_fondos(t, cod_eps, None, None, None)
    usos = []
    for id_exp in ruta._ufi(t, cod_eps)["id_expediente"]:
        r = ruta.ruta_expediente_uso(t, id_exp, textos)
        aut = next(p for p in r["escalera"] if p["peldano"] == "autorizado")
        usos.append({"id_expediente": id_exp, "estado": aut["estado"], "monto_autorizado": aut["monto"],
                     "fondo": aut["fondo"], "escalera": r["escalera"]})
    siguiente = pendientes[0] if pendientes else None
    return {
        "cod_eps": cod_eps, "fecha_corte": ctx.corte,
        "siguiente_accion": siguiente,
        "pendientes": pendientes, "tramites": tramites,
        "concluidos": [{"id_expediente": e.id, "tipo_procedimiento": e.tipo, "fecha_conclusion": e.fecha_conclusion,
                        "resultado": resultados.get(e.id), "pasos": pasos_de(e, cp, ctx.corte)}
                       for e in concluidos],
        "resumen_fondo": _resumen_fondo(t, cod_eps, fondos, usos),
        "proyectos": [{"cod_proyecto": p["cod_proyecto"], "nombre_proyecto": p["nombre_proyecto"]}
                      for p in ruta.proyectos(t, {"umbral_senal_pp": {"valor": 25}}, textos, cod_eps=cod_eps,
                                              periodo="vigente")],
        "fondo": [{k: f[k] for k in ("fondo", "deposito_programado", "deposito_efectuado", "saldo_final", "saldo_al",
                                     "uso_ordinario", "uso_excepcional_art_89", "uso_emergencia_art_90")}
                  for f in fondos["filas"] if f["fondo"] != "sin_fondo_indicado" and f["filas_ds05"]],
        "usos_autorizados": usos,
        "aviso_correo": _aviso(cod_eps, siguiente, cat),
        "naturaleza": "sintético",
        "fuente": "DS02, DS05 y relojes del motor de plazos (sintético)",
    }


def _resumen_fondo(t, cod_eps: str, fondos: dict[str, Any], usos: list[dict[str, Any]]) -> dict[str, Any]:
    """Cuatro recuadros del portal EPS (DS05 y DS02) y un aviso del depósito."""
    d5 = t["ds05_fondo_inversiones_reservas"]
    d5 = d5[d5["cod_eps"] == cod_eps].sort_values("anio_mes")
    prog = sum((ruta.D(v) for v in d5["deposito_programado"]), ruta.CERO)
    dep = sum((ruta.D(v) for v in d5["deposito_efectuado"]), ruta.CERO)
    usado = sum((ruta.D(v) for v in d5["uso_ejecutado"]), ruta.CERO) + sum((ruta.D(v) for v in d5["uso_excepcional"]),
                                                                          ruta.CERO)
    autorizado = sum((ruta.D(u["monto_autorizado"]) for u in usos if u["estado"] == "cumplido" and u["monto_autorizado"]),
                     ruta.CERO)
    meses = d5.groupby("anio_mes").agg({"deposito_programado": "sum", "deposito_efectuado": "sum"}).reset_index()
    ultimos = meses.tail(3)
    incompletos = [r["anio_mes"] for _, r in ultimos.iterrows()
                   if ruta.D(r["deposito_efectuado"]) < ruta.D(r["deposito_programado"])]
    pct = None if prog == 0 else round(float(dep / prog * 100), 1)
    if pct is None:
        aviso = "DS05 no registra depósitos programados para su EPS."
    elif incompletos:
        aviso = (f"Lleva depositado el {pct} % de lo programado. En {', '.join(incompletos)} depositó menos de lo "
                 "programado.")
    else:
        aviso = f"Lleva depositado el {pct} % de lo programado. Los últimos tres meses depositó lo programado o más."
    return {"programado": prog, "depositado": dep, "autorizado": autorizado, "usado": usado,
            "porcentaje_depositado": pct, "meses_incompletos": incompletos, "aviso": aviso,
            "hasta": max(d5["anio_mes"]) if len(d5) else None,
            "definiciones": {"programado": "Suma de depósitos programados (DS05)",
                             "depositado": "Suma de depósitos efectuados (DS05)",
                             "autorizado": "Usos excepcionales autorizados por Sunass (DS02 monto aprobado)",
                             "usado": "Uso ordinario más uso excepcional registrados (DS05)"},
            "fuente": "DS05 ds05_fondo_inversiones_reservas y DS02 (sintético)"}


def _aviso(cod_eps: str, p: dict[str, Any] | None, cat: dict[str, Any]) -> dict[str, Any]:
    if p is None:
        cuerpo = "Su EPS no tiene respuestas pendientes ante la Sunass a la fecha de corte."
        asunto = "Sin pendientes ante la Sunass"
    else:
        limite = f" a más tardar el {p['fecha_limite']:%d-%m-%Y}" if p["fecha_limite"] else ""
        asunto = f"Pendiente: {etiqueta(cat, 'hito', p['hito'])} ({p['id_expediente']})"
        cuerpo = (f"Estimado equipo de {cod_eps}: en el expediente {p['id_expediente']} "
                  f"({etiqueta(cat, 'tipo_procedimiento', p['tipo_procedimiento'])}) la Sunass espera "
                  f"«{etiqueta(cat, 'hito', p['hito'])}»{limite}.")
    return {"asunto": asunto, "cuerpo": cuerpo, "aviso": AVISO_CORREO}
