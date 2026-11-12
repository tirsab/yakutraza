"""Tablero gerencial de la DRE (Fase 5).

Todo se calcula a una fecha de corte elegida: los hechos posteriores a esa fecha no se
conocen todavía. El simulador trabaja sobre copias en memoria y nunca escribe en la base.
"""

from __future__ import annotations

import copy
import hashlib
import statistics
from dataclasses import dataclass, field, replace
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.engine import Engine

from app.config import Settings
from app.expediente.documentos import eventos_para_motor
from app.persistencia import leer_hallazgos, ultimo_lote
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from app.plazos.motor import EN_CURSO, Alerta, Expediente, MotorPlazos
from app.plazos.repositorio import expedientes_desde_bd

ORDEN = {"vencido": 0, "no_calculable": 1, "por_vencer": 2, "en_plazo": 3}
ESTADOS = ("vencido", "no_calculable", "por_vencer", "en_plazo")
ROTULO_BASE = "muestra simulada"


@lru_cache
def config(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def cfg_tablero(s: Settings) -> dict[str, Any]:
    return config(Path(s.rules_dir) / "tablero.yaml")


def motor_de(s: Settings, umbral_por_vencer: int | None = None) -> MotorPlazos:
    r = Path(s.rules_dir)
    cat = catalogo_desde(r / "plazos.yaml")
    if umbral_por_vencer is not None:
        cat = copy.copy(cat)  # copia: el catálogo en caché no cambia
        cat.umbral_por_vencer = umbral_por_vencer
    return MotorPlazos(calendario_desde(r / "feriados.yaml"), cat)


# ------------------------------------------------------------------ utilidades
def en_tramite_al(exp: Expediente, corte: date) -> bool:
    """En trámite a la fecha de corte: ya empezó y no había concluido."""
    if exp.fecha_inicio is None or exp.fecha_inicio > corte:
        return False
    if exp.fecha_conclusion is not None:
        return exp.fecha_conclusion > corte
    return exp.estado == "en_tramite"


def especialista_de(id_expediente: str, especialistas: list[str]) -> str:
    """Asignación ficticia y estable: hash SHA-256 del id, módulo el número de especialistas."""
    h = int(hashlib.sha256(id_expediente.encode("utf-8")).hexdigest(), 16)
    return especialistas[h % len(especialistas)]


def hito_al_corte(exp: Expediente, corte: date):
    """Hito en curso a la fecha de corte (el último que empezó y no terminó)."""
    abiertos = [h for h in exp.hitos if h.fecha_inicio and h.fecha_inicio <= corte
                and (h.fecha_fin is None or h.fecha_fin > corte)]
    return abiertos[-1] if abiertos else None


def truncar(exp: Expediente, corte: date) -> Expediente:
    """Copia del expediente tal como se conocía a la fecha de corte (para el escenario «sin acciones»)."""
    hitos = [replace(h, fecha_fin=None if h.fecha_fin and h.fecha_fin > corte else h.fecha_fin)
             for h in exp.hitos if h.fecha_inicio is None or h.fecha_inicio <= corte]
    concl = exp.fecha_conclusion if exp.fecha_conclusion and exp.fecha_conclusion <= corte else None
    return replace(exp, hitos=hitos, fecha_conclusion=concl, estado="en_tramite" if concl is None else exp.estado)


def principal(alertas: list[Alerta]) -> Alerta | None:
    abiertas = [a for a in alertas if a.estado in EN_CURSO or a.estado == "no_calculable"]
    if not abiertas:
        return None
    return min(abiertas, key=lambda a: (ORDEN[a.estado], a.dias_restantes if a.dias_restantes is not None else 10**6,
                                        {"normativo": 0, "oficio": 1, "interno": 2}.get(a.reloj, 3)))


def _mediana(xs: list[int]) -> float | None:
    return None if not xs else float(statistics.median(xs))


def _p90(xs: list[int]) -> int | None:
    if not xs:
        return None
    ys = sorted(xs)
    return ys[min(len(ys) - 1, int(round(0.9 * (len(ys) - 1))))]


# --------------------------------------------------------------- evaluación
@dataclass
class Fila:
    exp: Expediente
    especialista: str
    estado: str
    alerta: Alerta | None
    alertas: list[Alerta] = field(default_factory=list)
    hito: Any = None

    def como_dict(self) -> dict[str, Any]:
        h = self.hito
        return {"id_expediente": self.exp.id, "cod_eps": self.exp.cod_eps, "tipo_procedimiento": self.exp.tipo,
                "especialista": self.especialista, "estado": self.estado,
                "hito_al_corte": h.hito if h else None, "responsable_al_corte": h.responsable if h else None,
                "desde": h.fecha_inicio if h else None, "fecha_inicio": self.exp.fecha_inicio,
                "alerta": self.alerta.como_dict() if self.alerta else None,
                "relojes": {r: next((a.estado for a in self.alertas if a.reloj == r and
                                     (a.estado in EN_CURSO or a.estado == "no_calculable")), None)
                            for r in ("normativo", "interno", "oficio")},
                "fila_ds02": self.exp.fila, "naturaleza": "sintético"}


@dataclass
class Contexto:
    s: Settings
    engine: Engine
    corte: date
    exps: dict[str, Expediente]
    cfg: dict[str, Any]

    @property
    def especialistas(self) -> list[str]:
        return list(self.cfg["asignacion"]["especialistas"])


def contexto(engine: Engine, s: Settings, corte: date | None = None) -> Contexto:
    return Contexto(s, engine, corte or s.fecha_corte, expedientes_desde_bd(engine), cfg_tablero(s))


def evaluar(ctx: Contexto, *, motor: MotorPlazos | None = None, corte: date | None = None,
            sin_acciones_desde: date | None = None, especialistas: list[str] | None = None,
            con_eventos: bool = True) -> list[Fila]:
    """Expedientes en trámite a la fecha de corte, con su reloj más urgente."""
    motor = motor or motor_de(ctx.s)
    corte = corte or ctx.corte
    especialistas = especialistas or ctx.especialistas
    base = sin_acciones_desde or corte
    filas = []
    for exp in ctx.exps.values():
        if not en_tramite_al(exp, base):
            continue
        e = truncar(exp, base) if sin_acciones_desde else exp
        eventos = eventos_para_motor(ctx.engine, exp.id) if con_eventos else None
        alertas = motor.relojes(e, corte, eventos)
        p = principal(alertas)
        filas.append(Fila(exp=exp, especialista=especialista_de(exp.id, especialistas),
                          estado=p.estado if p else "en_plazo", alerta=p, alertas=alertas,
                          hito=hito_al_corte(e, corte)))
    return sorted(filas, key=lambda f: (ORDEN[f.estado], f.alerta.dias_restantes if f.alerta and
                                        f.alerta.dias_restantes is not None else 10**6, f.exp.id))


def filtrar(filas: list[Fila], *, tipo=None, cod_eps=None, responsable=None, especialista=None,
            estado=None) -> list[Fila]:
    def ok(f: Fila) -> bool:
        return ((not tipo or f.exp.tipo == tipo) and (not cod_eps or f.exp.cod_eps == cod_eps)
                and (not responsable or (f.hito and f.hito.responsable == responsable))
                and (not especialista or f.especialista == especialista) and (not estado or f.estado == estado))
    return [f for f in filas if ok(f)]


def indicadores(filas: list[Fila]) -> dict[str, Any]:
    res = {"en_tramite": {"n": len(filas), "ids": [f.exp.id for f in filas]}}
    for e in ESTADOS:
        ids = [f.exp.id for f in filas if f.estado == e]
        res[e] = {"n": len(ids), "ids": ids}
    return res


# ------------------------------------------------- línea base: supera el plazo
def supera_plazo(ctx: Contexto, *, cod_eps=None, tipo=None) -> dict[str, Any]:
    """Línea base: % de expedientes cuyo conteo de DS02 supera el plazo máximo.

    Compara dias_habiles_sunass con plazo_maximo_dh tal como DS02 los registra a la fecha de corte de la
    muestra: no depende del selector de fecha (DS02 no guarda el conteo histórico). Incluye los
    expedientes en trámite que ya superan el plazo. Sin alguno de los dos datos: «no calculable».
    """
    por_tipo: dict[str, dict[str, Any]] = {}
    por_eps: dict[str, dict[str, Any]] = {}
    total = _grupo()
    for exp in ctx.exps.values():
        if (cod_eps and exp.cod_eps != cod_eps) or (tipo and exp.tipo != tipo):
            continue
        for g in (por_tipo.setdefault(exp.tipo, _grupo()), por_eps.setdefault(exp.cod_eps, _grupo()), total):
            _sumar(g, exp)
    for g in [total, *por_tipo.values(), *por_eps.values()]:
        g["porcentaje"] = round(g["superan"] / g["calculables"] * 100, 1) if g["calculables"] else None
    return {"rotulo": ROTULO_BASE, "total": total, "por_tipo": por_tipo, "por_eps": por_eps,
            "formula": "días hábiles atribuibles a la Sunass (DS02 dias_habiles_sunass) > plazo máximo (DS02 plazo_maximo_dh)",
            "a_la_fecha": ctx.s.fecha_corte,
            "nota": "Valores de DS02 a la fecha de corte de la muestra: el selector de fecha no cambia esta línea base. "
                    "Incluye expedientes en trámite que ya superan el plazo. Si DS02 no trae los días o el plazo, el "
                    "expediente cuenta como «no calculable»: no se estima.",
            "fuente": "DS02 ds02_procedimientos (sintético)"}


def _grupo() -> dict[str, Any]:
    return {"superan": 0, "calculables": 0, "no_calculables": 0, "ids_superan": [], "en_tramite_superan": 0}


def _sumar(g: dict[str, Any], exp: Expediente) -> None:
    if exp.dias_sunass_ds02 is None or exp.plazo_maximo_dh is None:
        g["no_calculables"] += 1
        return
    g["calculables"] += 1
    if exp.dias_sunass_ds02 > exp.plazo_maximo_dh:
        g["superan"] += 1
        g["ids_superan"].append(exp.id)
        if exp.estado == "en_tramite":
            g["en_tramite_superan"] += 1


# ------------------------------------------------------ cuellos de botella
def _duraciones(ctx: Contexto, exps: list[Expediente]):
    cal = calendario_desde(Path(ctx.s.rules_dir) / "feriados.yaml")
    for exp in exps:
        for h in exp.hitos:
            if h.fecha_inicio is None or h.fecha_inicio > ctx.corte:
                continue
            if h.fecha_fin is not None and h.fecha_fin < h.fecha_inicio:
                yield exp, h, None, False  # fecha inconsistente: no se adivina la duración
                continue
            abierto = h.fecha_fin is None or h.fecha_fin > ctx.corte
            fin = ctx.corte if abierto else h.fecha_fin
            yield exp, h, cal.dias_habiles_entre(h.fecha_inicio, fin), abierto


def cuellos(ctx: Contexto, *, tipo=None, cod_eps=None) -> dict[str, Any]:
    """Demora en días hábiles por hito y por responsable, hasta la fecha de corte."""
    exps = [e for e in ctx.exps.values() if (not tipo or e.tipo == tipo) and (not cod_eps or e.cod_eps == cod_eps)]
    por_hito: dict[str, dict[str, Any]] = {}
    por_resp: dict[str, dict[str, Any]] = {}
    inconsistentes = []
    for exp, h, dh, abierto in _duraciones(ctx, exps):
        if dh is None:
            inconsistentes.append({"id_expediente": exp.id, "hito": h.hito, "fila_ds02": h.fila})
            continue
        for grupo, k in ((por_hito, h.hito), (por_resp, h.responsable or "sin responsable")):
            g = grupo.setdefault(k, {"dias": [], "en_curso": [], "supera_referencial": 0, "con_referencial": 0,
                                     "plazo_referencial_dh": set(), "responsables": set()})
            g["dias"].append(dh)
            if abierto and en_tramite_al(exp, ctx.corte):
                g["en_curso"].append(exp.id)
            if h.plazo_referencial_dh is not None:
                g["con_referencial"] += 1
                g["plazo_referencial_dh"].add(h.plazo_referencial_dh)
                if dh > h.plazo_referencial_dh:
                    g["supera_referencial"] += 1
            if h.responsable:
                g["responsables"].add(h.responsable)

    def resumir(grupo: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        res = [{"clave": k, "n": len(g["dias"]), "mediana_dh": _mediana(g["dias"]), "p90_dh": _p90(g["dias"]),
                "max_dh": max(g["dias"]), "total_dh": sum(g["dias"]), "en_curso": len(g["en_curso"]),
                "ids_en_curso": g["en_curso"], "supera_referencial": g["supera_referencial"],
                "con_referencial": g["con_referencial"], "plazo_referencial_dh": sorted(g["plazo_referencial_dh"]),
                "responsables": sorted(g["responsables"])} for k, g in grupo.items()]
        return sorted(res, key=lambda x: (-(x["mediana_dh"] or 0), -x["n"], x["clave"]))

    return {"por_hito": resumir(por_hito), "por_responsable": resumir(por_resp),
            "fechas_inconsistentes": inconsistentes,
            "nota": "Días hábiles desde el inicio hasta el fin de cada hito (o hasta la fecha de corte si sigue en "
                    "curso). Los hitos con fecha de fin anterior a la de inicio no se miden (CAL-FEC).",
            "fuente": "DS02 ds02_hitos_procedimientos (sintético)"}


def embudo(ctx: Contexto, *, tipo=None, cod_eps=None) -> dict[str, Any]:
    """Embudo de firmas: cuántos expedientes llegaron a cada etapa de firma, cuántos siguen ahí y cuánto tardan."""
    cfg = ctx.cfg["embudo_firmas"]
    exps = [e for e in ctx.exps.values() if (not tipo or e.tipo == tipo) and (not cod_eps or e.cod_eps == cod_eps)]
    durs: dict[str, list[tuple[str, Any, int | None, bool]]] = {}
    for exp, h, dh, abierto in _duraciones(ctx, exps):
        durs.setdefault(h.hito, []).append((exp.id, exp, dh, abierto))
    etapas = []
    for et in cfg["etapas"]:
        llegaron, en_curso, dias = set(), [], []
        for hito in et["hitos"]:
            for id_exp, exp, dh, abierto in durs.get(hito, []):
                llegaron.add(id_exp)
                if dh is not None:
                    dias.append(dh)
                if abierto and en_tramite_al(exp, ctx.corte):
                    en_curso.append(id_exp)
        etapas.append({"clave": et["clave"], "nombre": et["nombre"], "hitos": et["hitos"], "llegaron": len(llegaron),
                       "en_curso": len(set(en_curso)), "ids_en_curso": sorted(set(en_curso)),
                       "mediana_dh": _mediana(dias), "p90_dh": _p90(dias)})
    return {"etapas": etapas, "sustento": cfg["sustento"], "estado_validacion": "por validar",
            "fuente": "DS02 ds02_hitos_procedimientos (sintético); agrupación en rules/tablero.yaml"}


# ------------------------------------------------------------------- carga
def _pesos(ctx: Contexto) -> tuple[dict[str, int], int]:
    p = ctx.cfg["pesos_carga"]
    return p["valor"], p["por_defecto"]


def carga(ctx: Contexto, filas: list[Fila], especialistas: list[str] | None = None) -> dict[str, Any]:
    pesos, defecto = _pesos(ctx)
    especialistas = especialistas or ctx.especialistas
    actual = {e: {"especialista": e, "n": 0, "carga": 0, "vencidos": 0, "por_vencer": 0, "no_calculable": 0, "ids": []}
              for e in especialistas}
    for f in filas:
        a = actual.setdefault(f.especialista, {"especialista": f.especialista, "n": 0, "carga": 0, "vencidos": 0,
                                               "por_vencer": 0, "no_calculable": 0, "ids": []})
        a["n"] += 1
        a["carga"] += pesos.get(f.exp.tipo, defecto)
        a["ids"].append(f.exp.id)
        if f.estado == "vencido":
            a["vencidos"] += 1
        elif f.estado in ("por_vencer", "no_calculable"):
            a[f.estado] += 1
    # Propuesta: reparto por carga (de mayor a menor peso, cada uno a quien tenga menos carga). No se aplica.
    prop = {e: 0 for e in especialistas}
    asignado: dict[str, str] = {}
    for f in sorted(filas, key=lambda f: (-pesos.get(f.exp.tipo, defecto), ORDEN[f.estado], f.exp.id)):
        destino = min(especialistas, key=lambda e: (prop[e], e != f.especialista, e))
        prop[destino] += pesos.get(f.exp.tipo, defecto)
        asignado[f.exp.id] = destino
    movimientos = [{"id_expediente": f.exp.id, "tipo_procedimiento": f.exp.tipo, "de": f.especialista,
                    "a": asignado[f.exp.id], "peso": pesos.get(f.exp.tipo, defecto)}
                   for f in filas if asignado[f.exp.id] != f.especialista]
    cargas = [a["carga"] for a in actual.values()]
    return {"actual": list(actual.values()),
            "propuesta": [{"especialista": e, "carga": prop[e]} for e in especialistas],
            "movimientos": movimientos,
            "desbalance_actual": max(cargas) - min(cargas) if cargas else 0,
            "desbalance_propuesto": max(prop.values()) - min(prop.values()) if prop else 0,
            "pesos": pesos, "sustento_pesos": ctx.cfg["pesos_carga"]["sustento"].strip(),
            "pregunta_dre": ctx.cfg["pesos_carga"]["pregunta_dre"],
            "rotulo": ctx.cfg["asignacion"]["rotulo"], "metodo": ctx.cfg["asignacion"]["metodo"],
            "aviso": "Propuesta orientativa: no reasigna nada. Los especialistas son ficticios."}


# ---------------------------------------------------------- calidad de datos
def resumen_calidad(engine: Engine) -> dict[str, Any]:
    lote = ultimo_lote(engine)
    hs = leer_hallazgos(engine, lote["id"]) if lote else []
    def contar(clave: str) -> dict[str, int]:
        res: dict[str, int] = {}
        for h in hs:
            res[h[clave]] = res.get(h[clave], 0) + 1
        return dict(sorted(res.items(), key=lambda x: -x[1]))
    reglas: dict[str, dict[str, Any]] = {}
    for h in hs:
        r = reglas.setdefault(h["regla_id"], {"regla_id": h["regla_id"], "titulo": h["titulo"],
                                              "severidad": h["severidad"], "n": 0})
        r["n"] += 1
    return {"total": len(hs), "por_severidad": contar("severidad"), "por_tipo": contar("tipo"),
            "por_dataset": contar("dataset"),
            "reglas": sorted(reglas.values(), key=lambda r: -r["n"])[:10],
            "reporte": "/calidad/reporte.html",
            "nota": "Los hallazgos describen la muestra sintética; ninguno se corrigió en silencio."}


# ---------------------------------------------------------------- simulador
def simular(ctx: Contexto, *, dias_sin_accion: int = 0, umbral_por_vencer_dh: int | None = None,
            especialistas_adicionales: int = 0, filtros: dict[str, Any] | None = None) -> dict[str, Any]:
    """Escenario «¿qué pasaría si…?». Trabaja en memoria: nunca escribe en la base."""
    filtros = filtros or {}
    base = filtrar(evaluar(ctx), **filtros)
    cal = calendario_desde(Path(ctx.s.rules_dir) / "feriados.yaml")
    corte_esc = cal.sumar_dias_habiles(ctx.corte, dias_sin_accion) if dias_sin_accion > 0 else ctx.corte
    extra = [f"esp-sim-{i + 1:02d}" for i in range(max(0, especialistas_adicionales))]
    esc = filtrar(evaluar(ctx, motor=motor_de(ctx.s, umbral_por_vencer_dh), corte=corte_esc,
                          sin_acciones_desde=ctx.corte if dias_sin_accion > 0 else None), **filtros)
    antes = {f.exp.id: f.estado for f in base}
    cambios = [{"id_expediente": f.exp.id, "antes": antes.get(f.exp.id), "despues": f.estado,
                "dias_restantes": f.alerta.dias_restantes if f.alerta else None}
               for f in esc if antes.get(f.exp.id) != f.estado]
    c_base = carga(ctx, base)
    c_esc = carga(ctx, esc, ctx.especialistas + extra)
    return {"parametros": {"fecha_corte": ctx.corte, "dias_sin_accion": dias_sin_accion,
                           "fecha_escenario": corte_esc, "umbral_por_vencer_dh": umbral_por_vencer_dh,
                           "especialistas_adicionales": especialistas_adicionales},
            "base": indicadores(base), "escenario": indicadores(esc), "cambios": cambios,
            "carga_base": {"desbalance": c_base["desbalance_actual"], "por_especialista": c_base["actual"]},
            "carga_escenario": {"desbalance": c_esc["desbalance_propuesto"], "por_especialista": c_esc["propuesta"]},
            "rotulo": "Escenario simulado: no modifica los datos reales",
            "supuestos": [
                "«Días sin acción»: nadie registra avances después de la fecha de corte; los relojes siguen corriendo.",
                "El umbral «por vencer» es un supuesto (DRE-19).",
                "Los especialistas adicionales son ficticios; la carga se reparte con la propuesta por pesos (DRE-26).",
            ]}
