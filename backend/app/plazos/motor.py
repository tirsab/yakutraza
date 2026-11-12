"""Motor de plazos con tres relojes: normativo, interno y del oficio.

Cada resultado es una `Alerta` explicable: dice la regla aplicada, su fuente,
su estado de validación y el documento que inició el conteo. Si falta un dato
para calcular, el estado es «no_calculable» y el mensaje dice qué falta: el
motor nunca estima una fecha.

Estados:
- en curso: en_plazo, por_vencer, vencido
- concluidos: cumplido, incumplido
- no_calculable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.plazos.calendario import Calendario
from app.plazos.catalogo import CatalogoPlazos, ReglaPlazo

EN_CURSO = ("en_plazo", "por_vencer", "vencido")
SIN_DOCUMENTO = "declarado, no verificado"


@dataclass
class Hito:
    nro: int
    hito: str
    etapa: str | None
    responsable: str | None
    fecha_inicio: date | None
    fecha_fin: date | None
    plazo_referencial_dh: int | None
    plazo_etapa_dh: int | None
    cuenta_plazo: bool | None
    documento: str | None
    descripcion: str | None = None
    fila: int | None = None


@dataclass
class Expediente:
    id: str
    cod_eps: str
    tipo: str
    fecha_inicio: date | None
    plazo_maximo_dh: int | None
    estado: str | None
    fecha_conclusion: date | None = None
    fecha_limite_ds02: date | None = None
    dias_suspension_ds02: int | None = None
    dias_sunass_ds02: int | None = None
    hito_actual: str | None = None
    responsable_actual: str | None = None
    fila: int | None = None
    hitos: list[Hito] = field(default_factory=list)


@dataclass
class EventoPlazo:
    """Prórroga u otra decisión registrada desde un documento (nunca inventada).

    `naturaleza`: real (caso real), sintético o registrado en la demo.
    """
    expediente: str
    hito: str
    tipo: str  # "prorroga"
    documento: str
    fecha_documento: date
    dias_adicionales_dh: int | None = None
    nueva_fecha_limite: date | None = None
    documento_solicitud: str | None = None
    fecha_solicitud: date | None = None
    naturaleza: str = "real"
    fuente: str = ""


@dataclass
class Alerta:
    expediente: str
    cod_eps: str
    reloj: str
    estado: str
    titulo: str
    mensaje: str
    regla_id: str | None
    fuente: str
    estado_validacion: str
    respaldo: str | None
    hito: str | None = None
    etapa: str | None = None
    fecha_inicio: date | None = None
    fecha_limite: date | None = None
    plazo_dh: int | None = None
    dias_transcurridos: int | None = None
    dias_restantes: int | None = None
    documento_inicio: str | None = None
    documento_estado: str | None = None
    discrepancia: dict[str, str] | None = None
    detalle: dict[str, Any] = field(default_factory=dict)

    @property
    def en_curso(self) -> bool:
        return self.estado in EN_CURSO or self.estado == "no_calculable"

    def como_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["en_curso"] = self.en_curso
        return d


def _texto_dh(n: int) -> str:
    return f"{n} día hábil" if abs(n) == 1 else f"{n} días hábiles"


class MotorPlazos:
    def __init__(self, calendario: Calendario, catalogo: CatalogoPlazos):
        self.cal = calendario
        self.cat = catalogo

    # -------------------------------------------------------------- utilidades
    def _fuente(self, regla: ReglaPlazo) -> str:
        return self.cat.reglas[regla.id].fuente_texto(self.cat.documentos)

    def _estado_en_curso(self, restantes: int) -> str:
        if restantes < 0:
            return "vencido"
        return "por_vencer" if restantes <= self.cat.umbral_por_vencer else "en_plazo"

    @staticmethod
    def _documento_previo(exp: Expediente, h: Hito) -> tuple[str, str]:
        """Documento que inició el conteo de un hito: el que cerró el hito anterior."""
        previos = [x for x in exp.hitos if x.nro < h.nro]
        doc = previos[-1].documento if previos else None
        return (doc, "verificado en DS02") if doc else (None, SIN_DOCUMENTO)

    def _hito_sin_fecha_confiable(self, exp: Expediente) -> str | None:
        for h in exp.hitos:
            if h.fecha_inicio is None:
                return f"el hito {h.nro} ({h.hito}, fila {h.fila}) no tiene fecha de inicio"
            if h.fecha_fin is not None and h.fecha_fin < h.fecha_inicio:
                return (f"una fecha confiable en el hito {h.nro} ({h.hito}, fila {h.fila}): termina el {h.fecha_fin} "
                        f"y empieza el {h.fecha_inicio}")
        return None

    def _dias(self, h: Hito, corte: date) -> int:
        fin = h.fecha_fin if h.fecha_fin is not None else corte
        return self.cal.dias_habiles_entre(h.fecha_inicio, min(fin, corte))

    def _base(self, exp: Expediente, reloj: str, regla: ReglaPlazo | None, **kw) -> Alerta:
        return Alerta(
            expediente=exp.id, cod_eps=exp.cod_eps, reloj=reloj,
            regla_id=regla.id if regla else None,
            fuente=self._fuente(regla) if regla else "",
            estado_validacion=regla.estado_validacion if regla else "por validar",
            respaldo=regla.respaldo if regla else None,
            discrepancia=regla.discrepancia if regla else None,
            **kw,
        )

    # -------------------------------------------------------------- normativo
    def suspension_y_sunass(self, exp: Expediente, corte: date, hitos: list[Hito] | None = None) -> tuple[int, int]:
        """(días de suspensión a cargo de la EP, días atribuibles a la Sunass) hasta el corte."""
        susp = sunass = 0
        for h in (hitos if hitos is not None else exp.hitos):
            if h.fecha_inicio is None or h.fecha_inicio > corte:
                continue
            n = self._dias(h, corte)
            if h.cuenta_plazo is False:
                susp += n
            else:
                sunass += n
        return susp, sunass

    def reloj_normativo(self, exp: Expediente, corte: date) -> list[Alerta]:
        regla = self.cat.normativa(exp.tipo, exp.fecha_inicio)
        if regla is None or regla.plazo_dh is None:
            return []  # procedimientos sin plazo en DH (reajuste, reportes): ver plazos.simulados
        plazo = exp.plazo_maximo_dh if exp.plazo_maximo_dh is not None else regla.plazo_dh
        solicitud = exp.hitos[0] if exp.hitos else None
        doc_ini = solicitud.documento if solicitud and solicitud.documento else None
        comun = dict(titulo=f"Plazo máximo del procedimiento ({_texto_dh(plazo)})", plazo_dh=plazo,
                     fecha_inicio=exp.fecha_inicio, documento_inicio=doc_ini,
                     documento_estado="verificado en DS02" if doc_ini else
                     f"{SIN_DOCUMENTO}: DS02 no registra el documento de la solicitud")
        if exp.fecha_inicio is None:
            return [self._base(exp, "normativo", regla, estado="no_calculable",
                               mensaje="No puedo calcular: falta la fecha de inicio del expediente en DS02.", **comun)]
        falta = self._hito_sin_fecha_confiable(exp)
        if falta:
            return [self._base(exp, "normativo", regla, estado="no_calculable",
                               mensaje=f"No puedo calcular: falta {falta}.", **comun)]
        if exp.plazo_maximo_dh is not None and exp.plazo_maximo_dh != regla.plazo_dh:
            comun["detalle"] = {"aviso": f"DS02 indica {exp.plazo_maximo_dh} DH y el catálogo {regla.plazo_dh} DH."}
        hasta = min(exp.fecha_conclusion, corte) if exp.fecha_conclusion else corte
        susp, sunass = self.suspension_y_sunass(exp, hasta)
        limite = self.cal.sumar_dias_habiles(exp.fecha_inicio, plazo + susp)
        base = (f"Plazo de {_texto_dh(plazo)} desde el {exp.fecha_inicio}, más {_texto_dh(susp)} de suspensión a "
                f"cargo de la EP: vence el {limite}.")
        alertas = []
        if exp.fecha_conclusion and exp.fecha_conclusion <= corte:
            ok = exp.fecha_conclusion <= limite
            alertas.append(self._base(
                exp, "normativo", regla, estado="cumplido" if ok else "incumplido", fecha_limite=limite,
                dias_transcurridos=sunass, dias_restantes=plazo - sunass,
                mensaje=f"{base} Concluyó el {exp.fecha_conclusion} con {_texto_dh(sunass)} de la Sunass"
                        + ("." if ok else f": superó el plazo en {_texto_dh(sunass - plazo)}."), **comun))
        else:
            restantes = plazo - sunass
            estado = self._estado_en_curso(restantes)
            quien = f" Hoy lo tiene: {exp.responsable_actual} ({exp.hito_actual})." if exp.hito_actual else ""
            texto = (f"Vencido hace {_texto_dh(-restantes)}." if restantes < 0 else
                     f"Vence en {_texto_dh(restantes)}.")
            alertas.append(self._base(
                exp, "normativo", regla, estado=estado, fecha_limite=limite, dias_transcurridos=sunass,
                dias_restantes=restantes, mensaje=f"{texto} {base}{quien}", **comun))
        alertas.extend(self._etapas(exp, corte))
        alertas.extend(self._hitos_normativos(exp, corte))
        return alertas

    def _etapas(self, exp: Expediente, corte: date) -> list[Alerta]:
        """Plazo de cada etapa, con la versión de la regla vigente cuando la etapa empezó."""
        res = []
        etapas = list(dict.fromkeys(h.etapa for h in exp.hitos if h.etapa))
        for etapa in etapas:
            hs = [h for h in exp.hitos if h.etapa == etapa and h.fecha_inicio and h.fecha_inicio <= corte]
            if not hs:
                continue
            regla = self.cat.etapa(exp.tipo, etapa, hs[0].fecha_inicio)
            if regla is None:
                continue
            siguiente = any(h.nro > hs[-1].nro and h.etapa != etapa and h.fecha_inicio is not None
                            and h.fecha_inicio <= corte for h in exp.hitos)
            terminada = siguiente or (exp.fecha_conclusion is not None and exp.fecha_conclusion <= corte)
            susp, sunass = self.suspension_y_sunass(exp, corte, hs)
            plazo = regla.plazo_dh
            inicio = hs[0].fecha_inicio
            limite = self.cal.sumar_dias_habiles(inicio, plazo + susp)
            comun = dict(titulo=f"Etapa {etapa} ({_texto_dh(plazo)})", etapa=etapa, plazo_dh=plazo,
                         fecha_inicio=inicio, fecha_limite=limite, dias_transcurridos=sunass,
                         dias_restantes=plazo - sunass)
            if terminada:
                ok = sunass <= plazo
                res.append(self._base(exp, "normativo", regla, estado="cumplido" if ok else "incumplido",
                                      mensaje=f"Etapa {etapa}: {_texto_dh(sunass)} de la Sunass de un máximo de "
                                              f"{plazo}" + ("." if ok else f"; la superó en {_texto_dh(sunass - plazo)}."),
                                      **comun))
            else:
                restantes = plazo - sunass
                res.append(self._base(exp, "normativo", regla, estado=self._estado_en_curso(restantes),
                                      mensaje=f"Etapa {etapa} en curso desde el {inicio}: "
                                              + (f"vencida hace {_texto_dh(-restantes)}." if restantes < 0 else
                                                 f"vence en {_texto_dh(restantes)} ({limite})."),
                                      **comun))
        return res

    # ---------------------------------------------------------------- interno
    def _evaluar_hito(self, exp: Expediente, h: Hito, regla: ReglaPlazo, corte: date, reloj: str) -> Alerta:
        """Compara la duración de un hito con el plazo de una regla (meta interna o plazo de la norma)."""
        doc, est = self._documento_previo(exp, h)
        tipo = "Meta interna" if reloj == "interno" else "Plazo de la norma"
        meta = "meta" if reloj == "interno" else "plazo"
        comun = dict(titulo=f"{tipo}: {h.hito} ({_texto_dh(regla.plazo_dh)})", hito=h.hito, etapa=h.etapa,
                     plazo_dh=regla.plazo_dh, fecha_inicio=h.fecha_inicio, documento_inicio=doc,
                     documento_estado=est,
                     fecha_limite=self.cal.sumar_dias_habiles(h.fecha_inicio, regla.plazo_dh))
        if h.fecha_fin is not None and h.fecha_fin < h.fecha_inicio:
            return self._base(exp, reloj, regla, estado="no_calculable",
                              mensaje=f"No puedo calcular: falta una fecha confiable en el hito {h.nro} "
                                      f"(fila {h.fila}).", **comun)
        usados = self._dias(h, corte)
        nota_ds02 = ""
        if reloj == "interno" and h.plazo_referencial_dh is not None and h.plazo_referencial_dh != regla.plazo_dh:
            nota_ds02 = f" DS02 indica {h.plazo_referencial_dh} DH para este hito."
        if h.fecha_fin is not None and h.fecha_fin <= corte:
            ok = usados <= regla.plazo_dh
            return self._base(exp, reloj, regla, estado="cumplido" if ok else "incumplido",
                              dias_transcurridos=usados, dias_restantes=regla.plazo_dh - usados,
                              mensaje=f"{h.hito}: tomó {_texto_dh(usados)} de un {meta} de {regla.plazo_dh}"
                                      + ("." if ok else f" (+{usados - regla.plazo_dh}).") + nota_ds02,
                              **comun)
        restantes = regla.plazo_dh - usados
        return self._base(exp, reloj, regla, estado=self._estado_en_curso(restantes),
                          dias_transcurridos=usados, dias_restantes=restantes,
                          mensaje=f"{h.hito} en curso ({h.responsable}): lleva {_texto_dh(usados)} de un {meta} de "
                                  f"{regla.plazo_dh}." + nota_ds02, **comun)

    def _hitos_normativos(self, exp: Expediente, corte: date) -> list[Alerta]:
        """Plazos que la norma fija a hitos concretos (audiencia, comentarios), según la versión vigente."""
        res = []
        for h in exp.hitos:
            if h.fecha_inicio is None or h.fecha_inicio > corte:
                continue
            regla = self.cat.normativa_de_hito(exp.tipo, h.hito, h.fecha_inicio)
            if regla is None:
                continue
            motivo = regla.extra.get("no_comparable")
            if motivo:
                res.append(self._base(exp, "normativo", regla, estado="no_calculable", hito=h.hito, etapa=h.etapa,
                                      titulo=f"Plazo de la norma: {h.hito}", plazo_dh=regla.plazo_dh,
                                      fecha_inicio=h.fecha_inicio,
                                      mensaje=f"No puedo comparar: {motivo}"))
                continue
            res.append(self._evaluar_hito(exp, h, regla, corte, "normativo"))
        return res

    # ---------------------------------------------------------------- interno
    def reloj_interno(self, exp: Expediente, corte: date) -> list[Alerta]:
        res = []
        for h in exp.hitos:
            if h.fecha_inicio is None or h.fecha_inicio > corte:
                continue
            regla = self.cat.interna(exp.tipo, h.hito, h.fecha_inicio)
            if regla is not None:
                res.append(self._evaluar_hito(exp, h, regla, corte, "interno"))
        res.extend(self._bloques(exp, corte))
        return res

    def _bloques(self, exp: Expediente, corte: date) -> list[Alerta]:
        res = []
        for regla in self.cat.bloques(exp.tipo):
            hs = [h for h in exp.hitos if h.hito in regla.hitos and h.fecha_inicio and h.fecha_inicio <= corte]
            if not hs or any(h.fecha_fin is not None and h.fecha_fin < h.fecha_inicio for h in hs):
                continue
            usados = sum(self._dias(h, corte) for h in hs if h.cuenta_plazo is not False)
            abierto = any(h.fecha_fin is None or h.fecha_fin > corte for h in hs)
            restantes = regla.plazo_dh - usados
            estado = self._estado_en_curso(restantes) if abierto else ("cumplido" if restantes >= 0 else "incumplido")
            res.append(self._base(
                exp, "interno", regla, estado=estado, titulo=f"Bloque del flujograma ({_texto_dh(regla.plazo_dh)})",
                hito=", ".join(h.hito for h in hs), plazo_dh=regla.plazo_dh, fecha_inicio=hs[0].fecha_inicio,
                dias_transcurridos=usados, dias_restantes=restantes,
                mensaje=f"Referencia solo del flujograma (la hoja Hitos no le da plazo): {', '.join(regla.hitos)} "
                        f"llevan {_texto_dh(usados)} de {regla.plazo_dh}.",
                detalle={"solo_flujograma": True}))
        return res

    # ----------------------------------------------------------------- oficio
    def reloj_oficio(self, exp: Expediente, corte: date, eventos: list[EventoPlazo] | None = None) -> list[Alerta]:
        res = []
        eventos = [e for e in (eventos or []) if e.expediente == exp.id]
        for h in exp.hitos:
            if h.cuenta_plazo is not False or h.fecha_inicio is None or h.fecha_inicio > corte:
                continue
            regla = self.cat.de_oficio(exp.tipo, h.hito, h.fecha_inicio)
            doc, est = self._documento_previo(exp, h)
            fijados = [e for e in eventos if e.hito == h.hito and e.tipo == "plazo_oficio" and e.dias_adicionales_dh is not None]
            if regla is None and not fijados:
                res.append(self._base(exp, "oficio", None, estado="no_calculable", titulo=f"Plazo del oficio: {h.hito}",
                                      hito=h.hito, fecha_inicio=h.fecha_inicio, documento_inicio=doc,
                                      documento_estado=est,
                                      mensaje=f"No puedo calcular: falta el plazo del oficio para {h.hito} (no hay "
                                              "regla en el catálogo ni documento registrado)."))
                continue
            detalle: dict[str, Any] = {}
            if fijados:
                f = fijados[-1]
                plazo = f.dias_adicionales_dh
                plazo_txt = f"{_texto_dh(plazo)} fijados por {f.documento} ({f.naturaleza})"
                if regla is not None:
                    plazo_txt += f"; el máximo de la regla {regla.id} es {regla.plazo_dh} DH"
                detalle["plazo_fijado"] = {"documento": f.documento, "dias_dh": plazo, "naturaleza": f.naturaleza,
                                           "fuente": f.fuente}
            else:
                plazo = regla.plazo_dh
                plazo_txt = f"{_texto_dh(plazo)} (máximo por defecto; prima el plazo que fije el oficio)"
            limite = self.cal.sumar_dias_habiles(h.fecha_inicio, plazo)
            prorrogas = [e for e in eventos if e.hito == h.hito and e.tipo == "prorroga"]
            avisos = []
            if prorrogas:
                p = prorrogas[0]
                if p.fecha_solicitud and p.fecha_solicitud > limite:
                    avisos.append(f"La prórroga se pidió el {p.fecha_solicitud}, después del vencimiento ({limite}); "
                                  "la norma exige pedirla antes.")
                detalle["prorroga"] = {"documento": p.documento, "fecha": str(p.fecha_documento),
                                       "naturaleza": p.naturaleza, "fuente": p.fuente}
                if p.nueva_fecha_limite is None and p.dias_adicionales_dh is None:
                    res.append(self._base(
                        exp, "oficio", regla, estado="no_calculable", titulo=f"Plazo del oficio: {h.hito}",
                        hito=h.hito, etapa=h.etapa, plazo_dh=plazo, fecha_inicio=h.fecha_inicio,
                        documento_inicio=doc, documento_estado=est, detalle=detalle,
                        mensaje=f"No puedo calcular el nuevo vencimiento: {p.documento} concedió una prórroga, pero "
                                f"no se conoce su plazo. Plazo original: {plazo_txt}, vencía el {limite}."))
                    continue
                limite = p.nueva_fecha_limite or self.cal.sumar_dias_habiles(limite, p.dias_adicionales_dh or 0)
                plazo_txt += (f"; prorrogado por {p.documento} ({p.naturaleza}) hasta el {limite}")
                if len(prorrogas) > 1:
                    avisos.append("Hay más de una prórroga registrada: la norma la permite por única vez.")
            comun = dict(titulo=f"Plazo del oficio: {h.hito}", hito=h.hito, etapa=h.etapa, plazo_dh=plazo,
                         fecha_inicio=h.fecha_inicio, fecha_limite=limite, documento_inicio=doc, documento_estado=est,
                         detalle=detalle)
            aviso = (" " + " ".join(avisos)) if avisos else ""
            if h.fecha_fin is not None and h.fecha_fin <= corte:
                ok = h.fecha_fin <= limite
                usados = self._dias(h, corte)
                res.append(self._base(exp, "oficio", regla, estado="cumplido" if ok else "incumplido",
                                      dias_transcurridos=usados,
                                      mensaje=f"La EP respondió el {h.fecha_fin} ({_texto_dh(usados)}); plazo de "
                                              f"{plazo_txt}." + ("" if ok else " Respondió fuera de plazo.") + aviso,
                                      **comun))
            else:
                restantes = self.cal.dias_habiles_entre(corte, limite) if limite >= corte else \
                    -self.cal.dias_habiles_entre(limite, corte)
                res.append(self._base(exp, "oficio", regla, estado=self._estado_en_curso(restantes),
                                      dias_restantes=restantes,
                                      mensaje=(f"Vencido hace {_texto_dh(-restantes)}" if restantes < 0 else
                                               f"Vence en {_texto_dh(restantes)}")
                                              + f" ({limite}): la EP debe responder; plazo de {plazo_txt}." + aviso,
                                      **comun))
        return res

    # ----------------------------------------------------------------- todos
    def relojes(self, exp: Expediente, corte: date, eventos: list[EventoPlazo] | None = None) -> list[Alerta]:
        return (self.reloj_normativo(exp, corte) + self.reloj_interno(exp, corte)
                + self.reloj_oficio(exp, corte, eventos))
