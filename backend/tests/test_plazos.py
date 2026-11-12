"""Pruebas del calendario, el catálogo y el motor de tres relojes (Fase 2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import yaml

from app.plazos.calendario import Calendario, calendario_desde
from app.plazos.catalogo import CatalogoPlazos, catalogo_desde
from app.plazos.motor import EventoPlazo, Expediente, Hito, MotorPlazos
from app.plazos.simulados import (
    limite_aplicacion_reajuste,
    limite_reporte_fondos,
    limite_reporte_trimestral,
    mes_de_disparo,
    reproducir_reajustes,
    variacion_acumulada,
)
from tests.conftest import CATALOGO

RULES = CATALOGO.parent
CORTE = date(2026, 9, 30)


@pytest.fixture(scope="module")
def cal():
    return calendario_desde(RULES / "feriados.yaml")


@pytest.fixture(scope="module")
def motor(cal):
    return MotorPlazos(cal, catalogo_desde(RULES / "plazos.yaml"))


# ================================================================ calendario
def test_fines_de_semana_y_feriados(cal):
    assert not cal.es_habil(date(2026, 9, 26))          # sábado
    assert not cal.es_habil(date(2026, 7, 28))          # Independencia
    assert not cal.es_habil(date(2026, 7, 29))          # Gran Parada Militar
    assert cal.es_habil(date(2026, 7, 30))


def test_vigencias_exactas(cal):
    assert not cal.es_feriado(date(2021, 12, 9)) and cal.es_feriado(date(2022, 12, 9))
    assert not cal.es_feriado(date(2022, 7, 23)) and cal.es_feriado(date(2023, 7, 23))
    assert not cal.es_feriado(date(2023, 6, 7)) and cal.es_feriado(date(2024, 6, 7))


def test_sumar_y_contar_dias_habiles(cal):
    # Viernes 2026-07-24 + 1 DH = lunes 27; desde el lunes 27, +1 DH = jueves 30 (28 y 29 son feriados).
    assert cal.sumar_dias_habiles(date(2026, 7, 24), 1) == date(2026, 7, 27)
    assert cal.sumar_dias_habiles(date(2026, 7, 27), 1) == date(2026, 7, 30)  # 28 y 29 feriados
    assert cal.sumar_dias_habiles(date(2026, 7, 27), 0) == date(2026, 7, 27)
    assert cal.dias_habiles_entre(date(2026, 7, 27), date(2026, 7, 30)) == 1
    assert cal.dias_habiles_entre(date(2026, 7, 30), date(2026, 7, 27)) == 0
    with pytest.raises(ValueError):
        cal.sumar_dias_habiles(date(2026, 1, 1), -1)


def test_siguiente_habil(cal):
    assert cal.siguiente_habil(date(2022, 4, 30)) == date(2022, 5, 2)
    assert cal.siguiente_habil(date(2022, 5, 2)) == date(2022, 5, 2)


def test_feriados_del_anio_tienen_fuente(cal):
    fs = cal.feriados(2026)
    assert any(f.fecha == date(2026, 6, 7) for f in fs)
    assert all(f.fuente for f in fs)


def test_libreria_y_supuestos_coinciden(cal):
    assert cal.diferencias_con_supuestos() == []


def test_diferencia_se_registra_sin_decidir_en_silencio():
    cfg = yaml.safe_load((RULES / "feriados.yaml").read_text(encoding="utf-8"))
    cfg["feriados_con_vigencia"].append({"mes": 3, "dia": 3, "nombre": "Feriado de prueba", "desde": 2026})
    cfg["anios_verificados"] = {"desde": 2026, "hasta": 2026}
    cal = Calendario(cfg)
    (d,) = cal.diferencias_con_supuestos()
    assert d.fecha == date(2026, 3, 3) and d.en_supuestos and not d.en_libreria
    assert "Validar con el calendario oficial" in d.explicacion
    assert cal.es_feriado(date(2026, 3, 3))  # manda la hoja Supuestos, y la diferencia queda visible


# ================================================================== catálogo
def test_catalogo_campos_obligatorios():
    cat = catalogo_desde(RULES / "plazos.yaml")
    for r in cat.reglas.values():
        assert r.estado_validacion == "por validar", r.id   # ninguna validada por la DRE
        assert r.fuentes, r.id
        assert r.tipo_reloj in ("normativo", "interno", "oficio")
    assert cat.normativa("cambio_programa_inversiones").plazo_dh == 30
    assert set(cat.etapas("revision_periodica")) == {"1_inicio", "2_evaluacion", "3_difusion", "4_aprobacion"}
    assert cat.de_oficio("cambio_programa_inversiones", "subsanacion_ep").plazo_dh == 2
    assert cat.de_oficio("revision_periodica", "subsanacion_ep").plazo_dh == 10
    assert cat.interna("revision_periodica", "comentarios").discrepancia is None   # resuelta por la RCD 124-2025
    assert cat.normativa_de_hito("revision_periodica", "comentarios", date(2025, 10, 26)).plazo_dh == 5
    assert cat.normativa_de_hito("revision_periodica", "comentarios", date(2025, 10, 27)).plazo_dh == 15
    assert cat.normativa_de_hito("revision_periodica", "audiencia_publica", date(2025, 1, 1)) is None
    assert cat.normativa_de_hito("revision_periodica", "audiencia_publica", date(2026, 1, 1)).plazo_dh == 30
    assert [r.id for r in cat.versiones("PLZ-N-RP-3")] == ["PLZ-N-RP-3-V2021", "PLZ-N-RP-3-V2025"]


def test_catalogo_rechaza_documento_no_declarado():
    datos = yaml.safe_load((RULES / "plazos.yaml").read_text(encoding="utf-8"))
    datos["reglas"][0]["fuentes"] = [{"doc": "NO_EXISTE"}]
    with pytest.raises(ValueError, match="no declarado"):
        CatalogoPlazos(datos)


@pytest.mark.parametrize("campo,valor", [("tipo_reloj", "lunar"), ("respaldo", "intuición"),
                                         ("estado_validacion", "aprobada")])
def test_catalogo_rechaza_valores_invalidos(campo, valor):
    datos = yaml.safe_load((RULES / "plazos.yaml").read_text(encoding="utf-8"))
    datos["reglas"][0][campo] = valor
    with pytest.raises(ValueError):
        CatalogoPlazos(datos)


def test_vigencia_de_regla():
    cat = catalogo_desde(RULES / "plazos.yaml")
    r = cat.reglas["PLZ-N-CPI"]
    assert r.vigente_en(date(2021, 7, 28)) and not r.vigente_en(date(2021, 7, 27))


# ===================================================================== motor
def _cpi(hitos, estado="en_tramite", conclusion=None, inicio=date(2026, 7, 27)):
    return Expediente(id="CPI-T", cod_eps="EPS99", tipo="cambio_programa_inversiones", fecha_inicio=inicio,
                      plazo_maximo_dh=30, estado=estado, fecha_conclusion=conclusion, hito_actual="informe",
                      responsable_actual="Equipo SRT", hitos=hitos)


def _h(nro, hito, ini, fin, cuenta=True, doc=None, ref=None):
    return Hito(nro=nro, hito=hito, etapa="unica", responsable="EP" if not cuenta else "SRT", fecha_inicio=ini,
                fecha_fin=fin, plazo_referencial_dh=ref, plazo_etapa_dh=30, cuenta_plazo=cuenta, documento=doc,
                fila=nro + 1)


def test_cpi_2026_0004_vencido_con_suspension(motor):
    # Reproduce el expediente de la demo (DS02, CPI-2026-0004).
    hitos = [
        _h(1, "solicitud", date(2026, 7, 27), date(2026, 7, 27)),
        _h(2, "derivacion", date(2026, 7, 27), date(2026, 7, 30), ref=1),
        _h(3, "oficio_informacion", date(2026, 7, 30), date(2026, 8, 19), doc="OF-2026-0018"),
        _h(4, "informacion_ep", date(2026, 8, 19), date(2026, 8, 28), cuenta=False, ref=10),
        _h(5, "memo_gg", date(2026, 8, 28), date(2026, 9, 11), doc="MEM-2026-0007"),
        _h(6, "elevacion_cd", date(2026, 9, 11), None),
    ]
    alertas = motor.relojes(_cpi(hitos), CORTE)
    (norm,) = [a for a in alertas if a.reloj == "normativo"]
    assert norm.fecha_limite == date(2026, 9, 21) and norm.estado == "vencido" and norm.dias_restantes == -7
    assert "RGT (RCD 028-2021-SUNASS-CD), art. 93.8" in norm.fuente
    assert norm.documento_estado.startswith("declarado, no verificado")
    (ofi,) = [a for a in alertas if a.reloj == "oficio"]
    assert ofi.estado == "cumplido" and ofi.documento_inicio == "OF-2026-0018"
    der = next(a for a in alertas if a.hito == "derivacion")
    assert der.estado == "cumplido" and der.dias_transcurridos == 1   # 28 y 29 de julio son feriados
    bloque5 = next(a for a in alertas if a.regla_id == "PLZ-I-CPI-BLOQUE-5")
    assert bloque5.estado == "vencido" and bloque5.detalle["solo_flujograma"]


def test_en_plazo_por_vencer_y_cumplido(motor):
    h = [_h(1, "solicitud", date(2026, 9, 1), date(2026, 9, 1)), _h(2, "evaluacion", date(2026, 9, 1), None)]
    a = motor.reloj_normativo(_cpi(h, inicio=date(2026, 9, 1)), date(2026, 9, 2))[0]
    assert a.estado == "en_plazo" and a.dias_restantes == 29
    a = motor.reloj_normativo(_cpi(h, inicio=date(2026, 9, 1)), date(2026, 10, 7))[0]
    assert a.estado == "por_vencer" and 0 <= a.dias_restantes <= 5
    h2 = [_h(1, "solicitud", date(2026, 9, 1), date(2026, 9, 1)), _h(2, "resolucion_cd", date(2026, 9, 1), date(2026, 9, 10))]
    a = motor.reloj_normativo(_cpi(h2, "concluido", date(2026, 9, 10), date(2026, 9, 1)), CORTE)[0]
    assert a.estado == "cumplido" and a.dias_transcurridos == 7


def test_concluido_fuera_de_plazo(motor):
    h = [_h(1, "solicitud", date(2026, 6, 1), date(2026, 6, 1)), _h(2, "resolucion_cd", date(2026, 6, 1), date(2026, 7, 31))]
    a = motor.reloj_normativo(_cpi(h, "concluido", date(2026, 7, 31), date(2026, 6, 1)), CORTE)[0]
    assert a.estado == "incumplido" and "superó el plazo" in a.mensaje


def test_no_puedo_calcular_sin_fecha_o_con_fecha_inconsistente(motor):
    sin = motor.reloj_normativo(_cpi([], inicio=None), CORTE)[0]
    assert sin.estado == "no_calculable" and "falta la fecha de inicio" in sin.mensaje
    mal = [_h(1, "solicitud", date(2026, 2, 4), date(2025, 3, 2))]
    a = motor.reloj_normativo(_cpi(mal, inicio=date(2026, 2, 4)), CORTE)[0]
    assert a.estado == "no_calculable" and "fecha confiable" in a.mensaje and a.fecha_limite is None
    vacio = [_h(1, "solicitud", None, None)]
    assert motor.reloj_normativo(_cpi(vacio), CORTE)[0].estado == "no_calculable"


def test_procedimiento_sin_plazo_en_dh_no_genera_reloj_normativo(motor):
    exp = Expediente(id="RTI-T", cod_eps="EPS99", tipo="reajuste_ipm", fecha_inicio=date(2026, 1, 1),
                     plazo_maximo_dh=None, estado="en_tramite")
    assert motor.reloj_normativo(exp, CORTE) == []


def _con_info(fin=None):
    return [_h(1, "solicitud", date(2026, 9, 1), date(2026, 9, 1)),
            _h(2, "oficio_informacion", date(2026, 9, 1), date(2026, 9, 2), doc="OF-2026-0099"),
            _h(3, "informacion_ep", date(2026, 9, 2), fin, cuenta=False)]


def test_reloj_oficio_en_curso_y_vencido(motor):
    exp = _cpi(_con_info(), inicio=date(2026, 9, 1))
    (a,) = motor.reloj_oficio(exp, date(2026, 9, 10))
    assert a.estado == "por_vencer" and a.fecha_limite == date(2026, 9, 16) and a.dias_restantes == 4
    (b,) = motor.reloj_oficio(exp, CORTE)
    assert b.estado == "vencido" and "Vencido hace" in b.mensaje


def test_prorroga_documentada(motor):
    exp = _cpi(_con_info(), inicio=date(2026, 9, 1))
    p = EventoPlazo(expediente="CPI-T", hito="informacion_ep", tipo="prorroga", documento="OF-PRUEBA",
                    fecha_documento=date(2026, 9, 15), dias_adicionales_dh=5, fecha_solicitud=date(2026, 9, 14),
                    naturaleza="sintético (prueba)")
    (a,) = motor.reloj_oficio(exp, date(2026, 9, 17), [p])
    assert a.fecha_limite == date(2026, 9, 23) and a.estado == "por_vencer"
    assert a.detalle["prorroga"]["documento"] == "OF-PRUEBA" and "prorrogado por OF-PRUEBA" in a.mensaje


def test_prorroga_pedida_tarde_o_repetida_se_advierte(motor):
    exp = _cpi(_con_info(date(2026, 9, 25)), inicio=date(2026, 9, 1))
    tarde = EventoPlazo(expediente="CPI-T", hito="informacion_ep", tipo="prorroga", documento="OF-1",
                        fecha_documento=date(2026, 9, 18), nueva_fecha_limite=date(2026, 9, 30),
                        fecha_solicitud=date(2026, 9, 17))
    otra = EventoPlazo(expediente="CPI-T", hito="informacion_ep", tipo="prorroga", documento="OF-2",
                       fecha_documento=date(2026, 9, 20), dias_adicionales_dh=2)
    (a,) = motor.reloj_oficio(exp, CORTE, [tarde, otra])
    assert a.estado == "cumplido" and a.fecha_limite == date(2026, 9, 30)
    assert "después del vencimiento" in a.mensaje and "única vez" in a.mensaje


def test_oficio_sin_regla_no_calculable(motor):
    h = [_h(1, "solicitud", date(2026, 9, 1), date(2026, 9, 1)), _h(2, "hito_raro_ep", date(2026, 9, 1), None, cuenta=False)]
    (a,) = motor.reloj_oficio(_cpi(h, inicio=date(2026, 9, 1)), CORTE)
    assert a.estado == "no_calculable" and "falta el plazo del oficio" in a.mensaje


def test_reloj_interno_y_discrepancia(motor):
    exp = Expediente(id="RP-T", cod_eps="EPS99", tipo="revision_periodica", fecha_inicio=date(2026, 6, 1),
                     plazo_maximo_dh=195, estado="en_tramite", hitos=[
                         Hito(1, "solicitud", "3_difusion", "EP", date(2026, 6, 1), date(2026, 6, 1), None, 45, True, None),
                         Hito(2, "audiencia_publica", "3_difusion", "DU", date(2026, 6, 1), date(2026, 7, 31), 30, 45, True, None),
                         Hito(3, "comentarios", "3_difusion", "EP e interesados", date(2026, 7, 31), None, 12, 45, True,
                              None),
                     ])
    al = motor.reloj_interno(exp, date(2026, 8, 5))
    aud = next(a for a in al if a.hito == "audiencia_publica")
    assert aud.estado == "incumplido"
    com = next(a for a in al if a.hito == "comentarios")
    assert com.estado == "en_plazo" and com.discrepancia is None
    assert "DS02 indica 12 DH" in com.mensaje
    etapa = [a for a in motor.reloj_normativo(exp, date(2026, 8, 20)) if a.etapa == "3_difusion"][0]
    assert etapa.estado == "vencido" and etapa.dias_restantes < 0  # más de 45 DH desde el 2026-06-01
    mal = Expediente(id="RP-M", cod_eps="EPS99", tipo="revision_periodica", fecha_inicio=date(2026, 6, 1),
                     plazo_maximo_dh=195, estado="en_tramite",
                     hitos=[Hito(1, "derivacion", "1_inicio", "DRE", date(2026, 6, 3), date(2026, 6, 1), 1, 30, True, None)])
    assert motor.reloj_interno(mal, CORTE)[0].estado == "no_calculable"


# ================================================================ simulados
def test_vencimientos_de_reportes(cal):
    assert limite_reporte_trimestral("2022-T1", cal) == date(2022, 5, 2)   # 30/04 sábado → lunes
    assert limite_reporte_trimestral("2026-T2", cal) == date(2026, 7, 30)  # 30/07 hábil
    assert limite_reporte_fondos("2026-08") == date(2026, 9, 15)
    assert limite_aplicacion_reajuste("2026-03") == date(2026, 6, 29)


def test_ipm_disparo_y_variacion():
    idx = {"2025-12": Decimal(100), "2026-01": Decimal("101"), "2026-02": Decimal("103"), "2026-03": Decimal("104")}
    assert variacion_acumulada(idx, "2025-12", "2026-02") == Decimal(3)
    assert mes_de_disparo(idx, "2025-12") == "2026-02"
    assert mes_de_disparo(idx, "2026-02") is None
    assert variacion_acumulada(idx, "2020-01", "2026-02") is None


def test_reproduccion_de_reajustes_con_base_y_sin_base():
    ipm = [{"anio_mes": m, "indice_base_dic2020": v, "fecha_publicacion": p} for m, v, p in [
        ("2025-12", "100", "2026-01-02"), ("2026-01", "101", "2026-02-02"), ("2026-02", "103", "2026-03-02"),
        ("2026-03", "104", "2026-04-01"), ("2026-04", "105.5", "2026-05-04"), ("2026-05", "107.12", "2026-06-01")]]
    rti = [
        {"id_expediente": "RTI-1", "cod_eps": "EPS99", "fecha_inicio": "2026-03-02", "porcentaje_previsto": "3.0",
         "resultado": "reajuste_aplicado", "_fila": 2},
        {"id_expediente": "RTI-2", "cod_eps": "EPS99", "fecha_inicio": "2026-06-01", "porcentaje_previsto": "4.0",
         "resultado": "reajuste_aplicado", "_fila": 3},
    ]
    r1, r2 = reproducir_reajustes(rti, ipm, {"EPS99": 2022})
    assert r1.reproduce is None and "falta" in r1.motivo_base
    assert r2.base == "2026-02" and r2.mes_calculado == "2026-05" and r2.reproduce is True
    assert r2.limite_aplicacion == date(2026, 8, 29)
    # Inicio de un periodo regulatorio posterior al último reajuste: la base se reinicia.
    (_, r2b) = reproducir_reajustes(rti, ipm, {"EPS99": 2026})
    assert r2b.base == "2026-02"  # el periodo 2026 empieza antes del último reajuste: no cambia
    rti[1]["porcentaje_previsto"] = "9.9"
    assert reproducir_reajustes(rti, ipm, {"EPS99": 2022})[1].reproduce is False


# ========================================================= muestra real
@pytest.mark.muestra
def test_motor_reproduce_ds02(muestra_real, motor):
    from app.plazos.repositorio import expedientes_desde_muestra
    exps = expedientes_desde_muestra(muestra_real)
    con_plazo = [e for e in exps.values() if e.plazo_maximo_dh is not None]
    assert len(con_plazo) == 65
    resultados = {}
    for e in con_plazo:
        a = next(x for x in motor.reloj_normativo(e, CORTE) if x.etapa is None and x.hito is None)
        resultados[e.id] = (a.estado, a.fecha_limite == e.fecha_limite_ds02, a.dias_transcurridos == e.dias_sunass_ds02)
    assert sum(1 for v in resultados.values() if v[1] and v[2]) == 64
    assert resultados["RP-2026-0002"][0] == "no_calculable"
    cpi = next(a for a in motor.relojes(exps["CPI-2026-0004"], CORTE) if a.reloj == "normativo")
    assert cpi.estado == "vencido" and cpi.fecha_limite == date(2026, 9, 21)


def test_versiones_por_fecha_en_el_motor(motor):
    """La misma etapa de difusión se evalúa con la norma vigente cuando ocurrió cada hito."""
    def rp(anio):
        return Expediente(id=f"RP-{anio}", cod_eps="EPS99", tipo="revision_periodica",
                          fecha_inicio=date(anio, 6, 1), plazo_maximo_dh=195, estado="concluido",
                          fecha_conclusion=date(anio, 9, 30), hitos=[
                              Hito(1, "publicacion", "3_difusion", "GG", date(anio, 6, 1), date(anio, 6, 5), None, 45, True, None),
                              Hito(2, "audiencia_publica", "3_difusion", "DU", date(anio, 6, 5), date(anio, 7, 3), 30, 45, True, None),
                              Hito(3, "comentarios", "3_difusion", "EP e interesados", date(anio, 7, 3), date(anio, 7, 17),
                                   15, 45, True, None),
                          ])
    antes = {a.regla_id: a for a in motor.reloj_normativo(rp(2024), CORTE) if a.hito}
    assert set(antes) == {"PLZ-N-RP-COMENTARIOS-V2021"}          # sin máximo de audiencia antes de 2025-10-27
    # DS02 junta a la EP (40 DH) y a los interesados (5 DH) en un hito: no se califica.
    assert antes["PLZ-N-RP-COMENTARIOS-V2021"].estado == "no_calculable"
    assert "No puedo comparar" in antes["PLZ-N-RP-COMENTARIOS-V2021"].mensaje
    despues = {a.regla_id: a for a in motor.reloj_normativo(rp(2026), CORTE) if a.hito}
    assert set(despues) == {"PLZ-N-RP-AUDIENCIA-V2025", "PLZ-N-RP-COMENTARIOS-V2025"}
    assert all(a.estado == "cumplido" for a in despues.values())
    etapa = next(a for a in motor.reloj_normativo(rp(2026), CORTE) if a.etapa == "3_difusion")
    assert etapa.regla_id == "PLZ-N-RP-3-V2025"


def test_catalogo_rechaza_versiones_superpuestas():
    datos = yaml.safe_load((RULES / "plazos.yaml").read_text(encoding="utf-8"))
    for r in datos["reglas"]:
        if r["id"] == "PLZ-N-RP-3-V2021":
            r["vigente_hasta"] = date(2026, 1, 1)
    with pytest.raises(ValueError, match="superpuestas"):
        CatalogoPlazos(datos)


def test_informes_de_emergencia(cal):
    from app.plazos.simulados import limites_informe_emergencia
    # Declaratoria del 2026-08-10 al 2026-10-15: informes de agosto y septiembre, y uno al término.
    lims = limites_informe_emergencia(date(2026, 8, 10), date(2026, 10, 15), cal)
    assert lims == [cal.sumar_dias_habiles(date(2026, 8, 31), 10), cal.sumar_dias_habiles(date(2026, 9, 30), 10),
                    cal.sumar_dias_habiles(date(2026, 10, 15), 10)]
    assert len(limites_informe_emergencia(date(2026, 9, 1), None, cal)) == 1
