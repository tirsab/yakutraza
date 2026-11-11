"""Control de calidad sobre la muestra real del Desafío 3.

Comprueba que se detecte al menos un caso de cada tipo que anuncia el
diccionario y que queden confirmados los hallazgos vistos en el sondeo.
Si un tipo no aparece, la prueba falla con un mensaje explícito: no se fuerza.
"""

from __future__ import annotations

from collections import Counter

import pytest

from app.calidad.base import TIPOS_ANUNCIADOS

pytestmark = pytest.mark.muestra


def _de(hallazgos, regla_id):
    return [h for h in hallazgos if h.regla_id == regla_id]


def test_cada_tipo_anunciado_aparece(hallazgos_reales):
    conteo = Counter(h.tipo for h in hallazgos_reales)
    faltan = [f"{t} ({e})" for t, e in TIPOS_ANUNCIADOS.items() if conteo[t] == 0]
    assert not faltan, f"Tipos anunciados por el diccionario que NO se encontraron: {faltan}"


def test_todo_hallazgo_tiene_fuente_y_ubicacion(hallazgos_reales):
    for h in hallazgos_reales:
        assert h.fuente_regla and h.explicacion and h.dataset
        assert h.fila is not None or h.llave, h


def test_llaves_repetidas_en_ds04(hallazgos_reales):
    filas = sorted(tuple(h.detalle["filas"]) for h in _de(hallazgos_reales, "CAL-DUP-02")
                   if h.dataset == "ds04_ejecucion_inversiones")
    assert filas == [(1221, 1222), (2776, 2777), (4485, 4486)]


def test_codigo_eps01_p04(hallazgos_reales):
    assert any(h.llave == "cod_proyecto = EPS01-P04" for h in _de(hallazgos_reales, "CAL-LLV-01"))
    assert any(h.llave == "cod_proyecto = EPS01-P04" for h in _de(hallazgos_reales, "CAL-LLV-02"))
    (sin,) = [h for h in _de(hallazgos_reales, "CAL-LLV-03") if h.llave == "cod_proyecto = EPS01-P004"]
    assert "EPS01-P04" in sin.explicacion


def test_cui_9716915(hallazgos_reales):
    (h,) = _de(hallazgos_reales, "CAL-CUI-01")
    assert h.llave == "cui = 9716915" and h.detalle["proyectos"] == ["EPS09-P026"]


def test_fechas_rp_2026_0002(hallazgos_reales):
    fin = [h for h in _de(hallazgos_reales, "CAL-FEC-01") if h.llave == "RP-2026-0002 · hito 5"]
    enc = [h for h in _de(hallazgos_reales, "CAL-FEC-02") if h.llave == "RP-2026-0002 · hito 6"]
    assert [h.fila for h in fin] == [67] and [h.fila for h in enc] == [68]


def test_saldo_ds05(hallazgos_reales):
    alta = [h for h in _de(hallazgos_reales, "CAL-ARI-01") if h.severidad == "alta"]
    assert [(h.fila, h.llave) for h in alta] == [(437, "EPS04 · 2024-07 · fondo_inversiones")]
    assert any(h.severidad == "informativa" for h in _de(hallazgos_reales, "CAL-ARI-01"))


def test_ds06_no_presentado(hallazgos_reales):
    (h,) = _de(hallazgos_reales, "CAL-FAL-03")
    assert h.llave == "EPS01 · 2025"


def test_ds08_sin_avance_fisico(hallazgos_reales):
    (h,) = _de(hallazgos_reales, "CAL-FAL-05")
    assert h.severidad == "informativa" and len(h.detalle["filas"]) == 53


def test_ds06_eps05_2023_en_otra_unidad(hallazgos_reales):
    (h,) = _de(hallazgos_reales, "CAL-UNI-01")
    assert h.llave.startswith("EPS05 · 2023") and "miles de soles" in h.explicacion


def test_trimestres_faltantes_coinciden_con_ds02(hallazgos_reales):
    fal = _de(hallazgos_reales, "CAL-FAL-01")
    assert len(fal) == 17
    assert all("expediente_ds02" in h.detalle and h.severidad == "media" for h in fal)


def test_deposito_programado_todo_dentro_de_tolerancia(hallazgos_reales):
    hs = _de(hallazgos_reales, "CAL-ARI-02")
    assert [h.severidad for h in hs] == ["informativa"]
    (h,) = hs
    assert len(h.detalle["filas"]) == 3202
    assert sum(h.detalle["por_rango_soles"].values()) == 3202
    assert h.detalle["por_fraccion_de_tolerancia"]["más de 100 %"] == 0


def test_mef_separa_diferencias_reales_del_desfase(hallazgos_reales):
    mef = [h for h in hallazgos_reales if h.regla_id.startswith("CAL-MEF")]
    reales = [h for h in mef if h.tipo == "diferencia_mef"]
    desfase = [h for h in mef if h.tipo == "desfase_mef"]
    assert len(mef) == 122
    assert [h.llave for h in reales] == ["EPS13-P003 · CUI 9744763"]
    assert all(h.severidad == "media" for h in reales)
    assert len(desfase) == 121 and all(h.severidad == "informativa" for h in desfase)


def test_margen_eps03_2024_es_error_de_signo(hallazgos_reales):
    ari = [h for h in hallazgos_reales if h.regla_id == "CAL-ARI-05" and h.llave.startswith("EPS03")]
    assert [h.llave for h in ari] == ["EPS03 · 2024 · margen_operativo_pct"]
    assert ari[0].severidad == "media" and "utilidad operativa" in ari[0].explicacion
    # Los márgenes negativos que cuadran (pérdidas reales) no se marcan.
    assert not any(h.titulo == "Resultado que no cuadra con los montos del registro" for h in hallazgos_reales)
