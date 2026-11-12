"""Reglas CAL-PLZ: validación de plazos de DS02 en el reporte de calidad."""

from __future__ import annotations

import pytest


# 2026-09-01 + 30 DH (el 8 de octubre, Combate de Angamos, es feriado).
def _proc(**kw):
    base = {"id_expediente": "CPI-2026-0099", "cod_eps": "EPS01", "tipo_procedimiento": "cambio_programa_inversiones",
            "fecha_inicio": "2026-09-01", "plazo_maximo_dh": "30", "dias_suspension_dh": "0",
            "dias_habiles_sunass": "1", "fecha_limite": "2026-10-14", "estado": "en_tramite"}
    return {**base, **kw}


def _hitos(fin="2026-09-02"):
    return [{"id_expediente": "CPI-2026-0099", "nro_hito": "1", "hito": "solicitud", "fecha_inicio": "2026-09-01",
             "fecha_fin": "2026-09-01", "cuenta_plazo": "True"},
            {"id_expediente": "CPI-2026-0099", "nro_hito": "2", "hito": "evaluacion", "fecha_inicio": "2026-09-01",
             "fecha_fin": fin, "cuenta_plazo": "True"}]


def test_fecha_limite_coincide_y_discrepa(muestra_de, correr):
    ok = muestra_de({"ds02_procedimientos": [_proc()], "ds02_hitos_procedimientos": _hitos()})
    (res,) = correr("CAL-PLZ-01", ok)
    assert res.severidad == "informativa" and res.llave == "1 de 1"
    mal = muestra_de({"ds02_procedimientos": [_proc(fecha_limite="2026-10-20")], "ds02_hitos_procedimientos": _hitos()})
    hs = correr("CAL-PLZ-01", mal)
    assert [h.severidad for h in hs] == ["informativa", "media"]
    assert hs[1].valor_esperado == "2026-10-14"


def test_dias_habiles_discrepan(muestra_de, correr):
    m = muestra_de({"ds02_procedimientos": [_proc(dias_habiles_sunass="5")], "ds02_hitos_procedimientos": _hitos()})
    hs = correr("CAL-PLZ-02", m)
    assert hs[1].valor_observado == "5 / 0" and hs[1].valor_esperado == "1 / 0"


def test_fecha_no_confiable_no_se_recalcula(muestra_de, correr):
    m = muestra_de({"ds02_procedimientos": [_proc()], "ds02_hitos_procedimientos": _hitos(fin="2025-09-02")})
    for rid in ("CAL-PLZ-01", "CAL-PLZ-02"):
        hs = correr(rid, m)
        assert hs[0].llave == "0 de 1" and "No puedo recalcular" in hs[1].explicacion


def test_reporte_trimestral(muestra_de, correr):
    base = {"cod_eps": "EPS01", "tipo_procedimiento": "reporte_periodico"}
    m = muestra_de({"ds02_procedimientos": [
        {**base, "id_expediente": "RPI-2022-0001", "periodo_reportado": "2022-T1", "fecha_limite": "2022-05-02"},
        {**base, "id_expediente": "RPI-2022-0002", "periodo_reportado": "2022-T2", "fecha_limite": "2022-07-29"},
        {**base, "id_expediente": "RPI-2022-0003", "periodo_reportado": "", "fecha_limite": "2022-07-29"},
    ]})
    hs = correr("CAL-PLZ-03", m)
    assert hs[0].llave == "1 de 3" and "días calendario" in hs[0].explicacion
    assert {h.llave for h in hs[1:]} == {"RPI-2022-0002", "RPI-2022-0003"}


def test_calendario_sin_diferencias(muestra_de, correr):
    (h,) = correr("CAL-PLZ-04", muestra_de({}))
    assert h.severidad == "informativa" and "coinciden" in h.explicacion


@pytest.mark.muestra
def test_validacion_de_plazos_en_la_muestra(hallazgos_reales):
    por_regla = {}
    for h in hallazgos_reales:
        if h.regla_id.startswith("CAL-PLZ"):
            por_regla.setdefault(h.regla_id, []).append(h)
    resumen = {rid: next(h.llave for h in hs if h.severidad == "informativa") for rid, hs in por_regla.items()}
    assert resumen["CAL-PLZ-01"] == "64 de 65" and resumen["CAL-PLZ-02"] == "64 de 65"
    assert resumen["CAL-PLZ-03"] == "360 de 360" and resumen["CAL-PLZ-05"] == "35 de 35"
    discrepancias = [h for rid in ("CAL-PLZ-01", "CAL-PLZ-02") for h in por_regla[rid] if h.severidad != "informativa"]
    assert {h.llave for h in discrepancias} == {"RP-2026-0002"}
