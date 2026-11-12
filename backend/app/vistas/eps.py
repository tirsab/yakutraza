"""Vista EPS (Fase 5): sus trámites, qué le falta y hasta cuándo, y su fondo con los usos autorizados.

Solo su cod_eps. Sin documentos internos de Sunass. Una acción por pantalla.
"""

from __future__ import annotations

from typing import Any

from app.dinero import ruta
from app.dinero.datos import tablas
from app.vistas.bandeja import EP, SUNASS_TECNICO
from app.vistas.etiquetas import etiqueta
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
    return {
        "id_expediente": f.exp.id, "tipo_procedimiento": f.exp.tipo, "hito": hito,
        "accion": f"Enviar a la Sunass: {etiqueta(cat, 'hito', hito)}.",
        "fecha_limite": oficio.fecha_limite if oficio else None,
        "dias_restantes": oficio.dias_restantes if oficio else None,
        "estado": oficio.estado if oficio else "sin_plazo",
        "detalle": oficio.mensaje if oficio else "No hay un plazo registrado para esta respuesta.",
        "documento": oficio.documento_inicio if oficio else None,
        "fuente": oficio.fuente if oficio else f"DS02 fila {h.fila}",
    }


def resumen_eps(ctx: Contexto, cod_eps: str, cat: dict[str, Any], textos: dict[str, str]) -> dict[str, Any]:
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
            "en_que_va": ("Le toca a su EPS." if p else
                          f"Está en la Sunass ({etiqueta(cat, 'responsable', quien)})." if quien in SUNASS_TECNICO
                          or quien not in EP else "En espera."),
        })
    pendientes.sort(key=lambda p: (p["dias_restantes"] if p["dias_restantes"] is not None else 10**6))
    concluidos = sorted([e for e in ctx.exps.values() if e.cod_eps == cod_eps and e.fecha_conclusion
                         and e.fecha_conclusion <= ctx.corte], key=lambda e: e.fecha_conclusion, reverse=True)[:5]
    t = tablas(ctx.s.database_url)
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
        "concluidos": [{"id_expediente": e.id, "tipo_procedimiento": e.tipo, "fecha_conclusion": e.fecha_conclusion}
                       for e in concluidos],
        "fondo": [{k: f[k] for k in ("fondo", "deposito_programado", "deposito_efectuado", "saldo_final", "saldo_al",
                                     "uso_ordinario", "uso_excepcional_art_89", "uso_emergencia_art_90")}
                  for f in fondos["filas"] if f["fondo"] != "sin_fondo_indicado" and f["filas_ds05"]],
        "usos_autorizados": usos,
        "aviso_correo": _aviso(cod_eps, siguiente, cat),
        "naturaleza": "sintético",
        "fuente": "DS02, DS05 y relojes del motor de plazos (sintético)",
    }


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
