"""Vista ciudadana pública (Fase 5).

Solo lee campos marcados «público» en rules/visibilidad.yaml (función solo_publico). Muestra
información agregada y no reservada: proyectos de la localidad con su etapa, la población
beneficiaria (estimada), la decisión de Sunass vinculada y las audiencias públicas.
"""

from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.db import TABLAS_DATASETS, resumenes_quechua
from app.dinero import ruta
from app.dinero import visibilidad as vis
from app.plazos.motor import Expediente

HITOS_AUDIENCIA = ("audiencia_publica", "comentarios")

# Seis etapas en lenguaje simple (rotuladas «por validar», E-2). La etapa 6 exige verificar el beneficio:
# ninguna obra de la muestra la alcanza, así que nunca se afirma «en funcionamiento» sin verificación.
ETAPAS_CIUDADANAS = [
    {"n": 1, "clave": "programada", "nombre": "Programada", "detalle": "Está en el programa de inversiones del estudio tarifario."},
    {"n": 2, "clave": "aprobada", "nombre": "Aprobada", "detalle": "Aprobada por Sunass; aún no hay reporte de inicio."},
    {"n": 3, "clave": "en_preparacion", "nombre": "En preparación", "detalle": "Sin iniciar la obra o con expediente técnico."},
    {"n": 4, "clave": "en_obra", "nombre": "En obra", "detalle": "La obra está en ejecución."},
    {"n": 5, "clave": "terminada", "nombre": "Terminada", "detalle": "Reportada como concluida; la verificación posterior está pendiente."},
    {"n": 6, "clave": "beneficio_verificado", "nombre": "Beneficio verificado", "detalle": "Sunass verificó el beneficio. Ninguna obra de la muestra tiene esta verificación."},
]


def etapa_ciudadana(p: dict[str, Any]) -> dict[str, Any]:
    """Etapa simple a partir de la escalera del proyecto (DS03 y DS04). Detenida = paralizada (sigue en la etapa 4)."""
    est = p.get("estado_ejecucion")
    if est in ("no_iniciado", "expediente_tecnico"):
        n = 3
    elif est in ("en_ejecucion", "paralizado"):
        n = 4
    elif est == "concluido":
        n = 5
    else:
        n = 2  # programada y aprobada en el estudio; sin reporte de ejecución
    e = ETAPAS_CIUDADANAS[n - 1]
    return {"n": n, "de": len(ETAPAS_CIUDADANAS), "clave": e["clave"], "nombre": e["nombre"],
            "detenida": est == "paralizado", "estado_validacion": "por validar (E-2)"}


def _plano(t: str | None) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _filas(engine: Engine, nombre: str, *cond) -> list[dict[str, Any]]:
    t = TABLAS_DATASETS[nombre]
    q = select(t)
    for c in cond:
        q = q.where(c(t))
    with engine.connect() as cx:
        return [dict(r) for r in cx.execute(q).mappings()]


def _nombres_eps(engine: Engine) -> dict[str, str]:
    return {r["cod_eps"]: r["nombre_eps"] for r in _filas(engine, "ds01_catalogo_eps")}


def buscar(engine: Engine, cat_vis: dict[str, Any], q: str, limite: int = 20) -> list[dict[str, Any]]:
    """Localidades por nombre, ubigeo, distrito, provincia o departamento (sin distinguir tildes)."""
    clave = _plano(q)
    if len(clave) < 2:
        return []
    nombres = _nombres_eps(engine)
    res = []
    for r in _filas(engine, "ds01_localidades_eps"):
        campos = [r["localidad"], r["ubigeo"], r["distrito"], r["provincia"], r["departamento"]]
        if any(clave in _plano(str(c)) for c in campos if c):
            res.append(vis.solo_publico(cat_vis, "localidad", {**r, "nombre_eps": nombres.get(r["cod_eps"])}))
    res.sort(key=lambda r: (not _plano(r["localidad"]).startswith(clave), r["localidad"]))
    return res[:limite]


def _estado_audiencia(inicio: date | None, fin: date | None, corte: date) -> str:
    if inicio is None:
        return "sin fecha"
    if inicio > corte:
        return "próxima"
    if fin is None or fin >= corte:
        return "en curso"
    return "realizada"


def localidad(engine: Engine, cat_vis: dict[str, Any], t: dict[str, Any], params: dict[str, Any],
              textos: dict[str, str], exps: dict[str, Expediente], ubigeo: str, corte: date) -> dict[str, Any] | None:
    locs = _filas(engine, "ds01_localidades_eps", lambda tb: tb.c.ubigeo == ubigeo)
    if not locs:
        return None
    nombres = _nombres_eps(engine)
    loc = locs[0]
    cod = loc["cod_eps"]
    info = vis.solo_publico(cat_vis, "localidad", {**loc, "nombre_eps": nombres.get(cod)})

    # Proyectos de la localidad (DS03 por ubigeo): solo campos públicos.
    proys = [p for p in ruta.proyectos(t, params, textos, cod_eps=cod) if str(p.get("ubigeo")) == str(ubigeo)]
    ds02 = {r["id_expediente"]: r for r in _filas(engine, "ds02_procedimientos", lambda tb: tb.c.cod_eps == cod)}
    proyectos = []
    for p in proys:
        pub = vis.solo_publico(cat_vis, "proyecto", {**p, "etapa_ciudadana": etapa_ciudadana(p)})
        pub["decisiones"] = [vis.solo_publico(cat_vis, "decision_sunass", ds02[i]) for i in p["expediente_modificacion"]
                             if i in ds02]
        pub["naturaleza_poblacion"] = "estimado"
        proyectos.append(pub)

    # Audiencias públicas y plazos de comentarios de las revisiones periódicas de su EPS.
    audiencias = []
    for e in exps.values():
        if e.cod_eps != cod or e.tipo != "revision_periodica":
            continue
        for h in e.hitos:
            if h.hito in HITOS_AUDIENCIA:
                audiencias.append(vis.solo_publico(cat_vis, "audiencia", {
                    "id_expediente": e.id, "cod_eps": cod, "nombre_eps": nombres.get(cod), "hito": h.hito,
                    "fecha_inicio": h.fecha_inicio, "fecha_fin": h.fecha_fin if h.fecha_fin and h.fecha_fin <= corte else None,
                    "plazo_referencial_dh": h.plazo_referencial_dh,
                    "estado": _estado_audiencia(h.fecha_inicio, h.fecha_fin, corte)}))
    audiencias.sort(key=lambda a: (a["fecha_inicio"] or date.min), reverse=True)

    etapas: dict[str, int] = {}
    for p in proyectos:
        etapas[p.get("etapa_escalera") or "sin dato"] = etapas.get(p.get("etapa_escalera") or "sin dato", 0) + 1
    return {
        "localidad": info, "fecha_corte": corte, "etapas": ETAPAS_CIUDADANAS,
        "agregados": {"proyectos": len(proyectos), "por_etapa": etapas,
                      "monto_programado_original": sum(float(p.get("monto_programado_original") or 0) for p in proyectos)},
        "proyectos": proyectos, "audiencias": audiencias,
        "resumen_quechua": resumen_validado(engine, ubigeo),
        "avisos": ["Datos de la muestra sintética del Hackathon Sunass, no de la localidad real.",
                   "La población beneficiaria es una estimación.",
                   "Lo marcado «por validar» depende de la confirmación de la DRE sobre qué es público (E-2)."],
        "naturaleza": "sintético",
        "fuente": "DS01 localidades, DS02 y DS03 (sintéticos); campos públicos según rules/visibilidad.yaml",
    }


def ubicaciones(engine: Engine) -> list[dict[str, Any]]:
    """Departamento → provincia → distritos (DS01 localidades), para los selectores públicos."""
    arbol: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in _filas(engine, "ds01_localidades_eps"):
        arbol.setdefault(r["departamento"], {}).setdefault(r["provincia"], []).append(
            {"distrito": r["distrito"], "ubigeo": r["ubigeo"], "localidad": r["localidad"]})
    return [{"departamento": d, "provincias": [{"provincia": p, "distritos": sorted(ds, key=lambda x: x["distrito"])}
                                               for p, ds in sorted(provs.items())]}
            for d, provs in sorted(arbol.items())]


def mapa(engine: Engine, cat_vis: dict[str, Any], t: dict[str, Any], params: dict[str, Any], textos: dict[str, str],
         departamento: str, provincia: str) -> dict[str, Any]:
    """Mapa ESQUEMÁTICO: DS01 no trae coordenadas; los distritos se ordenan por nombre, no por ubicación real."""
    locs = [r for r in _filas(engine, "ds01_localidades_eps")
            if r["departamento"] == departamento and r["provincia"] == provincia]
    ubigeos = {str(r["ubigeo"]) for r in locs}
    por_ubigeo: dict[str, list[dict[str, Any]]] = {}
    for cod in sorted({r["cod_eps"] for r in locs}):
        for p in ruta.proyectos(t, params, textos, cod_eps=cod):
            if str(p.get("ubigeo")) in ubigeos:
                por_ubigeo.setdefault(str(p["ubigeo"]), []).append(vis.solo_publico(cat_vis, "proyecto", {
                    "cod_proyecto": p["cod_proyecto"], "nombre_proyecto": p["nombre_proyecto"],
                    "etapa_ciudadana": etapa_ciudadana(p)}))
    return {"departamento": departamento, "provincia": provincia, "tipo": "esquemático",
            "aviso": "Mapa esquemático: DS01 no trae coordenadas. Los distritos se ordenan por nombre, no por ubicación.",
            "distritos": [{"distrito": r["distrito"], "ubigeo": r["ubigeo"], "localidad": r["localidad"],
                           "obras": por_ubigeo.get(str(r["ubigeo"]), [])}
                          for r in sorted(locs, key=lambda x: x["distrito"])],
            "etapas": ETAPAS_CIUDADANAS, "naturaleza": "sintético"}


def resumen_validado(engine: Engine, ubigeo: str) -> dict[str, Any] | None:
    with engine.connect() as cx:
        r = cx.execute(select(resumenes_quechua.c.texto, resumenes_quechua.c.validado_en)
                       .where(resumenes_quechua.c.ubigeo == ubigeo, resumenes_quechua.c.estado == "validado")
                       .order_by(resumenes_quechua.c.id.desc()).limit(1)).mappings().first()
    return None if r is None else {"texto": r["texto"], "estado": "validado por una persona"}
