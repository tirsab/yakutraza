"""Pruebas unitarias de cada regla con muestras pequeñas armadas a mano."""

from __future__ import annotations

from datetime import date

import pytest

from app.calidad.base import cargar_catalogo, nuevo
from app.calidad.reglas._util import meses, trimestres


# ----------------------------------------------------------------- utilidades
def test_rangos_de_periodos():
    assert trimestres("2025-T3", "2026-T2") == ["2025-T3", "2025-T4", "2026-T1", "2026-T2"]
    assert meses("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_catalogo_valida_severidad(tmp_path):
    ruta = tmp_path / "c.yaml"
    ruta.write_text("reglas:\n- {id: X, tipo: t, titulo: t, severidad: grave, fuente: f, estado_validacion: validada}\n",
                    encoding="utf-8")
    with pytest.raises(ValueError):
        cargar_catalogo(ruta)


def test_hallazgo_hereda_fuente_de_la_regla(catalogo):
    h = nuevo(catalogo["CAL-CUI-01"], "ds03_programa_inversiones", 5, "cui = 1", "x")
    assert h.fuente_regla == catalogo["CAL-CUI-01"].fuente
    assert h.severidad == "alta"


def test_todas_las_reglas_tienen_fuente_y_estado(catalogo):
    for r in catalogo.values():
        assert r.fuente.strip()
        assert r.estado_validacion in ("validada", "por validar")


# ----------------------------------------------------------------- formato
def test_formato(muestra_de, correr):
    m = muestra_de({"ds09_ipm": [{"anio_mes": "2026-01", "fecha_publicacion": "01/02/2026"}]})
    (h,) = [x for x in correr("CAL-FMT-01", m) if x.dataset == "ds09_ipm"]
    assert (h.dataset, h.fila, h.llave, h.valor_observado) == ("ds09_ipm", 2, "fecha_publicacion", "01/02/2026")


# ----------------------------------------------------------------- duplicados
def test_filas_identicas(muestra_de, correr):
    fila = {"cod_eps": "EPS01", "anio": "2023", "estado_presentacion": "presentado"}
    m = muestra_de({"ds06_estados_financieros": [fila, fila, {**fila, "anio": "2024"}]})
    (h,) = correr("CAL-DUP-01", m)
    assert h.fila == 2 and h.detalle["filas"] == [2, 3]
    assert correr("CAL-DUP-02", m) == []  # idénticas: solo las reporta DUP-01


def test_llave_repetida_con_valores_distintos(muestra_de, correr):
    base = {"cod_eps": "EPS06", "cod_proyecto": "EPS06-P018", "anio_trimestre": "2023-T1"}
    m = muestra_de({"ds04_ejecucion_inversiones": [
        {**base, "ejecucion_financiera_trimestre": "100.00"},
        {**base, "ejecucion_financiera_trimestre": "110.00"},
    ]})
    (h,) = correr("CAL-DUP-02", m)
    assert h.detalle == {"filas": [2, 3], "columnas_distintas": ["ejecucion_financiera_trimestre"]}
    assert "«100.00» (fila 2) vs «110.00» (fila 3)" in h.explicacion


# ------------------------------------------------------------------ unidades
def test_monto_en_miles(muestra_de, correr):
    filas = [{"cod_eps": "EPS05", "anio": str(a), "ingresos_operativos": v}
             for a, v in [(2021, "220000"), (2022, "221000"), (2023, "217"), (2024, "225000")]]
    m = muestra_de({"ds06_estados_financieros": filas})
    (h,) = correr("CAL-UNI-01", m)
    assert h.fila == 4 and "miles de soles" in h.explicacion


def test_serie_corta_no_se_evalua(muestra_de, correr):
    filas = [{"cod_eps": "EPS05", "anio": "2021", "ingresos_operativos": "220000"},
             {"cod_eps": "EPS05", "anio": "2022", "ingresos_operativos": "2"}]
    assert correr("CAL-UNI-01", muestra_de({"ds06_estados_financieros": filas})) == []


# ------------------------------------------------------------------- llaves
def test_codigo_que_no_cruza_y_formato(muestra_de, correr):
    m = muestra_de({
        "ds03_programa_inversiones": [{"cod_eps": "EPS01", "cod_proyecto": "EPS01-P004", "tipo_periodo": "vigente"}],
        "ds04_ejecucion_inversiones": [{"cod_eps": "EPS01", "cod_proyecto": "EPS01-P04", "anio_trimestre": "2022-T1"},
                                       {"cod_eps": "EPS01", "cod_proyecto": "EPS01-P04", "anio_trimestre": "2022-T2"}],
    })
    rel = [h for h in correr("CAL-LLV-01", m) if h.dataset == "ds04_ejecucion_inversiones"]
    assert len(rel) == 1 and rel[0].detalle["filas"] == [2, 3]
    (fmt,) = correr("CAL-LLV-02", m)
    assert fmt.valor_observado == "EPS01-P04"
    (sin,) = correr("CAL-LLV-03", m)
    assert "EPS01-P04" in sin.explicacion and "No se corrige" in sin.explicacion


def test_entidad_mef_compara_sin_tildes(muestra_de, correr):
    m = muestra_de({
        "ds01_catalogo_eps": [{"cod_eps": "EPS05", "nombre_eps": "EPS Río Sereno S.A."},
                              {"cod_eps": "EPS06", "nombre_eps": "EPS Otra S.A."}],
        "ds03_programa_inversiones": [{"cod_eps": "EPS05", "cui": "9000001"}, {"cod_eps": "EPS06", "cui": "9000002"}],
        "ds08_inversiones_mef": [{"cui": "9000001", "entidad": "EPS RIO SERENO S.A."},
                                 {"cui": "9000002", "entidad": "EPS RIO SERENO S.A."}],
    })
    (h,) = correr("CAL-LLV-04", m)
    assert h.fila == 3


def test_cui_sin_mef(muestra_de, correr):
    m = muestra_de({
        "ds03_programa_inversiones": [{"cod_proyecto": "EPS09-P026", "cui": "9716915"},
                                      {"cod_proyecto": "EPS09-P001", "cui": "9000001"}],
        "ds08_inversiones_mef": [{"cui": "9000001"}],
    })
    (h,) = correr("CAL-CUI-01", m)
    assert h.llave == "cui = 9716915" and h.detalle["proyectos"] == ["EPS09-P026"]


# --------------------------------------------------------------- faltantes
def test_trimestre_sin_reporte_cita_ds02(muestra_de, correr, catalogo):
    trims = trimestres("2022-T1", "2026-T2")
    filas = [{"cod_eps": "EPS01", "cod_proyecto": "EPS01-P001", "anio_trimestre": t} for t in trims if t != "2024-T1"]
    m = muestra_de({
        "ds04_ejecucion_inversiones": filas,
        "ds02_procedimientos": [{"id_expediente": "RPI-2024-0002", "cod_eps": "EPS01", "tipo_procedimiento": "reporte_periodico",
                                 "periodo_reportado": "2024-T1", "estado": "en_tramite", "fecha_limite": "2024-04-30"}],
    })
    (h,) = correr("CAL-FAL-01", m)
    assert h.llave == "EPS01 · 2024-T1" and h.severidad == "media"
    assert h.detalle["expediente_ds02"] == "RPI-2024-0002"


def test_trimestre_sin_filas_pero_presentado_en_ds02_es_alta(muestra_de, correr):
    filas = [{"cod_eps": "EPS01", "cod_proyecto": "EPS01-P001", "anio_trimestre": t}
             for t in trimestres("2022-T1", "2026-T2") if t != "2023-T1"]
    m = muestra_de({
        "ds04_ejecucion_inversiones": filas,
        "ds02_procedimientos": [{"id_expediente": "RPI-2023-0001", "cod_eps": "EPS01", "tipo_procedimiento": "reporte_periodico",
                                 "periodo_reportado": "2023-T1", "fecha_presentacion": "2023-04-20"}],
    })
    (h,) = correr("CAL-FAL-01", m)
    assert h.severidad == "alta" and "Inconsistencia" in h.explicacion


def test_mes_sin_reporte_agrupa_fondos(muestra_de, correr):
    filas = [{"cod_eps": "EPS02", "anio_mes": am, "tipo_fondo": f}
             for am in meses("2026-05", "2026-08") if am != "2026-07" for f in ("fondo_inversiones", "reserva_pcc")]
    (h,) = correr("CAL-FAL-02", muestra_de({"ds05_fondo_inversiones_reservas": filas}))
    assert h.llave == "EPS02 · 2026-07" and h.detalle["fondos"] == ["fondo_inversiones", "reserva_pcc"]


def test_estados_no_presentados_y_metas(muestra_de, correr):
    m = muestra_de({
        "ds06_estados_financieros": [{"cod_eps": "EPS01", "anio": "2025", "estado_presentacion": "no_presentado"}],
        "ds07_metas_gestion": [{"cod_eps": "EPS01", "cod_meta": "MG01", "anio": "2024"},
                               {"cod_eps": "EPS01", "cod_meta": "MG01", "anio": "2026"}],
    })
    assert len(correr("CAL-FAL-03", m)) == 1
    (meta,) = correr("CAL-FAL-04", m)
    assert meta.fila == 2


def test_mef_sin_avance_es_informativo_y_agrupado(muestra_de, correr):
    m = muestra_de({"ds08_inversiones_mef": [{"cui": "9000001", "estado_inversion": "ACTIVO"},
                                             {"cui": "9000002", "avance_fisico_pct": "10.0"}]})
    (h,) = correr("CAL-FAL-05", m)
    assert h.severidad == "informativa" and h.detalle["filas"] == [2]


# ------------------------------------------------------------------ fechas
def test_fechas_de_hitos(muestra_de, correr):
    m = muestra_de({"ds02_hitos_procedimientos": [
        {"id_expediente": "RP-2026-0002", "nro_hito": "5", "hito": "informe_inicio",
         "fecha_inicio": "2026-02-04", "fecha_fin": "2025-03-02"},
        {"id_expediente": "RP-2026-0002", "nro_hito": "6", "hito": "firma_informe_inicio",
         "fecha_inicio": "2026-03-02", "fecha_fin": "2026-03-04"},
    ]})
    (fin,) = correr("CAL-FEC-01", m)
    assert fin.fila == 2
    (enc,) = correr("CAL-FEC-02", m)
    assert enc.fila == 3 and "solo difieren en el año" in enc.explicacion


def test_hito_fuera_de_orden(muestra_de, correr):
    m = muestra_de({"ds02_hitos_procedimientos": [
        {"id_expediente": "CPI-2026-0001", "nro_hito": "1", "fecha_inicio": "2026-05-08", "fecha_fin": "2026-05-10"},
        {"id_expediente": "CPI-2026-0001", "nro_hito": "2", "fecha_inicio": "2026-05-01", "fecha_fin": "2026-05-12"},
    ]})
    (h,) = correr("CAL-FEC-02", m)
    assert "fuera de orden" in h.explicacion


def test_conclusion_antes_del_inicio_y_reporte_tardio_permitido(muestra_de, correr):
    m = muestra_de({"ds02_procedimientos": [
        {"id_expediente": "CPI-2026-0009", "tipo_procedimiento": "cambio_programa_inversiones",
         "fecha_inicio": "2026-05-08", "fecha_conclusion": "2026-05-01"},
        {"id_expediente": "RPI-2022-0001", "tipo_procedimiento": "reporte_periodico",
         "fecha_inicio": "2022-06-22", "fecha_limite": "2022-05-02"},
    ]})
    (h,) = correr("CAL-FEC-01", m)
    assert h.llave == "CPI-2026-0009"


def test_fecha_posterior_al_corte_y_reporte_antes_del_cierre(muestra_de, correr):
    m = muestra_de({
        "ds04_ejecucion_inversiones": [
            {"cod_proyecto": "EPS01-P001", "anio_trimestre": "2026-T2", "fecha_reporte": "2026-10-05"},
            {"cod_proyecto": "EPS01-P002", "anio_trimestre": "2026-T2", "fecha_reporte": "2026-06-15"},
        ],
        "ds06_estados_financieros": [{"cod_eps": "EPS01", "anio": "2025", "fecha_presentacion": "2025-12-31"}],
    })
    (corte,) = correr("CAL-FEC-03", m)
    assert corte.fila == 2
    antes = correr("CAL-FEC-04", m)
    assert {(h.dataset, h.fila) for h in antes} == {("ds04_ejecucion_inversiones", 3), ("ds06_estados_financieros", 2)}


# ---------------------------------------------------------------------- MEF
def _d4(t, acu, tri="0.00", av="10.0", estado="en_ejecucion"):
    return {"cod_proyecto": "EPS01-P001", "anio_trimestre": t, "ejecucion_financiera_acumulada": acu,
            "ejecucion_financiera_trimestre": tri, "avance_fisico_acumulado_pct": av, "estado": estado,
            "fecha_reporte": "2026-07-24"}


def _mef(muestra_de, filas_d4, devengado, devengado_2026, avance="", actualizado="2026-09-10"):
    return muestra_de({
        "ds03_programa_inversiones": [{"cod_proyecto": "EPS01-P001", "cui": "9000001"}],
        "ds04_ejecucion_inversiones": filas_d4,
        "ds08_inversiones_mef": [{"cui": "9000001", "devengado_acumulado": devengado, "devengado_2026": devengado_2026,
                                  "avance_fisico_pct": avance, "fecha_ultima_actualizacion": actualizado}],
    })


def test_mef_financiero_explicado_por_desfase(muestra_de, correr):
    # Caso real EPS01-P001: hoy difieren 31 %, pero al cierre de 2025-T4 solo 3,4 %.
    m = _mef(muestra_de, [_d4("2025-T4", "59899.13"), _d4("2026-T2", "294573.56")], "427293.13", "369420.65")
    (h,) = correr("CAL-MEF-02", m)
    assert (h.tipo, h.severidad, h.detalle["clasificacion"]) == ("desfase_mef", "informativa", "explicada_por_desfase")
    assert h.detalle["corte_comun"] == "2025-T4"
    assert h.detalle["diferencia_relativa_corte_pct"] == pytest.approx(3.38, abs=0.01)
    assert "no es una alerta" in h.explicacion


def test_mef_financiero_real_en_el_mismo_corte(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2025-T4", "100.00"), _d4("2026-T2", "200.00")], "300.00", "100.00")
    (h,) = correr("CAL-MEF-02", m)
    assert (h.tipo, h.severidad, h.detalle["clasificacion"]) == ("diferencia_mef", "media", "diferencia_real")
    assert h.detalle["ds08_corte"] == "200.00" and h.detalle["ds04_corte"] == "100.00"


def test_mef_corte_derivado_del_trimestre_siguiente(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2026-T1", "150.00", tri="50.00"), _d4("2026-T2", "400.00")], "700.00", "600.00")
    (h,) = correr("CAL-MEF-02", m)  # corte: EPS 100 vs MEF 100 -> desfase
    assert h.detalle["ds04_corte"] == "100.00" and h.detalle["clasificacion"] == "explicada_por_desfase"
    assert "2026-T1" in h.explicacion and "menos lo ejecutado" in h.explicacion


def test_mef_proyecto_concluido_antes_del_corte(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2025-T3", "411988.24", estado="concluido")], "631680.82", "0.00")
    (h,) = correr("CAL-MEF-02", m)
    assert h.severidad == "media" and "supuesto: un proyecto concluido no ejecuta más" in h.explicacion


def test_mef_sin_corte_comun_no_estima(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2025-T2", "100.00")], "300.00", "0.00")
    (h,) = correr("CAL-MEF-02", m)
    assert h.severidad == "informativa" and h.detalle["clasificacion"] == "sin_corte_comun"
    assert "No puedo comparar" in h.explicacion


def test_mef_posterior_y_menor_es_real(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2025-T4", "100.00"), _d4("2026-T2", "200.00")], "110.00", "10.00")
    (h,) = correr("CAL-MEF-02", m)  # en el corte coinciden, pero hoy el MEF (posterior) es menor
    assert h.severidad == "media" and "el desfase no lo explica" in h.explicacion


def test_mef_avance_fisico_mayor_no_verificable(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2026-T2", "1.00", av="29.2")], "1.00", "0.00", avance="50.0")
    (h,) = correr("CAL-MEF-01", m)
    assert (h.tipo, h.severidad) == ("desfase_mef", "informativa")
    assert h.detalle["diferencia_pp"] == pytest.approx(20.8) and "2026-09-10" in h.explicacion


def test_mef_avance_fisico_menor_es_real(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2026-T2", "1.00", av="60.0")], "1.00", "0.00", avance="40.0")
    (h,) = correr("CAL-MEF-01", m)
    assert (h.tipo, h.severidad, h.detalle["clasificacion"]) == ("diferencia_mef", "media", "diferencia_real")


def test_mef_sin_diferencia_o_sin_dato(muestra_de, correr):
    m = _mef(muestra_de, [_d4("2025-T4", "100.00"), _d4("2026-T2", "105.00", av="45.0")], "110.00", "5.00",
             avance="50.0")
    assert correr("CAL-MEF-01", m) == [] and correr("CAL-MEF-02", m) == []
    vacio = _mef(muestra_de, [_d4("2026-T2", "0.00")], "0.00", "0.00")
    assert correr("CAL-MEF-01", vacio) == [] and correr("CAL-MEF-02", vacio) == []


# --------------------------------------------------------------- aritmética
def _fondo(**kw):
    base = {"cod_eps": "EPS04", "anio_mes": "2024-07", "tipo_fondo": "fondo_inversiones", "saldo_inicial": "100.00",
            "deposito_efectuado": "10.00", "intereses": "1.00", "uso_ejecutado": "5.00", "uso_excepcional": "0.00",
            "saldo_final": "106.00", "porcentaje_ingresos": "12.81", "ingresos_base_mes": "236921.51",
            "deposito_programado": "30347.68"}
    return {**base, **kw}


def test_saldo_final_error_y_redondeo(muestra_de, correr):
    m = muestra_de({"ds05_fondo_inversiones_reservas": [
        _fondo(),                                     # exacto: sin hallazgo
        _fondo(anio_mes="2024-08", saldo_final="106.02"),   # redondeo
        _fondo(anio_mes="2024-09", saldo_final="92143.47"),  # error
    ]})
    hs = correr("CAL-ARI-01", m)
    error = [h for h in hs if h.severidad == "alta"]
    info = [h for h in hs if h.severidad == "informativa"]
    assert [h.fila for h in error] == [4]
    assert info[0].detalle["filas"] == [3]


def test_tolerancia_deposito_programado_es_relativa_a_ingresos(muestra_de, correr):
    # Fila real de DS05 (EPS01 2022-01): 12,81 % × 236 921,51 = 30 349,65 vs 30 347,68 → diferencia 1,97.
    # Tolerancia derivada: 236 921,51 × 0,00005 + 0,005 = 11,85 → dentro.
    # Con ingresos 1 000 veces menores la tolerancia baja a 0,017 y la misma
    # proporción de error queda fuera: la tolerancia no es un monto fijo.
    m = muestra_de({"ds05_fondo_inversiones_reservas": [
        _fondo(),
        _fondo(anio_mes="2022-02", ingresos_base_mes="236.92", deposito_programado="30.00"),
        _fondo(anio_mes="2022-03", deposito_programado="30500.00"),
    ]})
    hs = correr("CAL-ARI-02", m)
    fuera = sorted(h.fila for h in hs if h.severidad == "media")
    assert fuera == [3, 4]
    (info,) = [h for h in hs if h.severidad == "informativa"]
    assert info.detalle["filas"] == [2]
    assert info.detalle["por_rango_soles"]["S/ 1 a S/ 10"] == 1
    assert "SUPUESTO" in info.explicacion


def test_continuidad_de_saldo(muestra_de, correr):
    m = muestra_de({"ds05_fondo_inversiones_reservas": [
        _fondo(anio_mes="2024-01", saldo_final="200.00"),
        _fondo(anio_mes="2024-02", saldo_inicial="200.00"),
        _fondo(anio_mes="2024-03", saldo_inicial="999.00"),
        _fondo(anio_mes="2024-05", saldo_inicial="1.00"),  # falta abril: no se compara
    ]})
    (h,) = correr("CAL-ARI-03", m)
    assert h.fila == 4


def test_acumulados_ds04(muestra_de, correr):
    def f(t, av, tri, acu):
        return {"cod_proyecto": "EPS01-P007", "anio_trimestre": t, "avance_fisico_acumulado_pct": av,
                "ejecucion_financiera_trimestre": tri, "ejecucion_financiera_acumulada": acu}
    m = muestra_de({"ds04_ejecucion_inversiones": [
        f("2023-T3", "36.5", "10.00", "100.00"),
        f("2023-T4", "50.0", "10.00", "110.00"),
        f("2024-T2", "7.6", "10.00", "150.00"),   # falta 2024-T1: el avance sí se compara, la suma no
        f("2024-T3", "60.0", "10.00", "999.00"),
    ]})
    hs = correr("CAL-ARI-04", m)
    assert {(h.titulo, h.fila) for h in hs} == {
        ("Avance físico acumulado que retrocede", 4), ("Ejecución acumulada que no suma", 5)}


def _ds06(**kw):
    base = {"cod_eps": "EPS03", "anio": "2024", "estado_presentacion": "presentado",
            "ingresos_operativos": "96384209", "costo_ventas": "51049792", "gastos_administracion": "17242315",
            "gastos_ventas": "6085651", "depreciacion_amortizacion": "13521245", "resultado_operativo": "22006451",
            "ingresos_financieros": "1928285", "gastos_financieros": "3425219", "impuesto_renta": "6050308",
            "resultado_neto": "14459210", "margen_operativo_pct": "22.83"}
    return {**base, **kw}


def test_margen_con_signo_invertido(muestra_de, correr):
    # Registro real EPS03 2024: los montos dan utilidad y el margen trae el signo invertido.
    (h,) = correr("CAL-ARI-05", muestra_de({"ds06_estados_financieros": [_ds06(margen_operativo_pct="-22.83")]}))
    assert h.severidad == "media" and "signo está invertido" in h.explicacion
    assert "utilidad operativa" in h.explicacion and "no en los montos" in h.explicacion


def test_perdida_real_no_es_error(muestra_de, correr):
    # Pérdida que cuadra: ingresos 1 000 − costos y gastos 1 200 = −200; margen −20 %.
    perdida = _ds06(ingresos_operativos="1000", costo_ventas="1000", gastos_administracion="150",
                    gastos_ventas="50", resultado_operativo="-200", ingresos_financieros="0",
                    gastos_financieros="0", impuesto_renta="0", resultado_neto="-200",
                    margen_operativo_pct="-20.0")
    assert correr("CAL-ARI-05", muestra_de({"ds06_estados_financieros": [perdida]})) == []


def test_resultado_que_no_cuadra(muestra_de, correr):
    (h,) = correr("CAL-ARI-05", muestra_de({"ds06_estados_financieros": [_ds06(resultado_neto="1")]}))
    assert h.titulo == "Resultado que no cuadra con los montos del registro" and h.severidad == "media"


def test_indicadores_y_catalogo(muestra_de, correr):
    m = muestra_de({
        "ds06_estados_financieros": [{
            "cod_eps": "EPS05", "anio": "2023", "ingresos_operativos": "1000", "resultado_operativo": "100",
            "margen_operativo_pct": "11.0", "activo_corriente": "10", "pasivo_corriente": "0",
            "liquidez_corriente": "1.0"}],
        "ds01_catalogo_eps": [{"cod_eps": "EPS01", "conexiones_agua": "10", "conexiones_alcantarillado": "5",
                               "poblacion_servida": "40", "n_localidades": "2"}],
        "ds01_localidades_eps": [{"cod_eps": "EPS01", "localidad": "A", "conexiones_agua": "6",
                                  "conexiones_alcantarillado": "5", "poblacion_servida": "40"}],
    })
    (ind,) = correr("CAL-ARI-05", m)  # la división por cero de liquidez no se reporta
    assert "margen_operativo_pct" in ind.llave and ind.severidad == "baja"
    cat = correr("CAL-ARI-06", m)
    assert {h.llave for h in cat} == {"EPS01 · conexiones_agua", "EPS01 · n_localidades"}


def test_reglas_toleran_datasets_ausentes(muestra_de, correr, catalogo):
    m = muestra_de({})
    for rid in catalogo:
        if rid != "CAL-FMT-01":
            assert correr(rid, m) == [], rid


def test_motor_rechaza_regla_sin_implementacion(tmp_path, muestra_de):
    from app.calidad.motor import evaluar
    ruta = tmp_path / "c.yaml"
    ruta.write_text("reglas:\n- {id: CAL-XXX-99, tipo: t, titulo: t, severidad: alta, fuente: f, "
                    "estado_validacion: validada}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sin implementación"):
        evaluar(muestra_de({}), ruta, date(2026, 9, 30))
