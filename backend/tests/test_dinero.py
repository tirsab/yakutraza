"""Fase 4: ruta del dinero, visibilidad y contexto financiero (muestra sintética mínima en SQLite)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app import servicio
from app.config import Settings, get_settings
from app.dinero import ruta
from app.dinero import visibilidad as vis
from app.dinero.datos import tablas
from app.main import app
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from tests.conftest import escribir_csvs

RULES = get_settings().rules_dir
CFG = yaml.safe_load((RULES / "ruta_dinero.yaml").read_text(encoding="utf-8"))
FONDOS, TEXTOS, PARAMS = CFG["fondos"], CFG["textos"], CFG["parametros"]


def _d5(eps, mes, fondo, uso=0.0, exc=0.0, id_exp="", saldo=1000.0, dep=100.0, efe=100.0):
    return {"cod_eps": eps, "anio_mes": mes, "tipo_fondo": fondo, "porcentaje_ingresos": "10", "ingresos_base_mes": "1000",
            "saldo_inicial": "900", "deposito_programado": str(dep), "deposito_efectuado": str(efe), "intereses": "0",
            "uso_programado": "0", "uso_ejecutado": str(uso), "uso_excepcional": str(exc),
            "id_expediente_uso_excepcional": id_exp, "saldo_final": str(saldo), "fecha_reporte": f"{mes}-15"}


def _d3(cod, anio, orig, vig, mod="", fuente="fondo_inversiones", periodo="vigente", cui=""):
    return {"cod_eps": cod[:5], "periodo_regulatorio": "2025-2029", "tipo_periodo": periodo, "cod_proyecto": cod,
            "cui": cui, "nombre_proyecto": f"Proyecto {cod}", "localidad": "Localidad", "fuente_financiamiento": fuente,
            "meta_asociada": "MG01", "poblacion_beneficiaria": "1200", "anio": str(anio),
            "monto_programado_original": str(orig), "monto_programado_vigente": str(vig), "id_expediente_modificacion": mod}


def _d4(cod, tri, estado, fis, acum):
    return {"cod_eps": cod[:5], "cod_proyecto": cod, "anio_trimestre": tri, "estado": estado,
            "avance_fisico_acumulado_pct": str(fis), "ejecucion_financiera_trimestre": "0",
            "ejecucion_financiera_acumulada": str(acum), "fecha_reporte": "2026-07-15"}


def _ufi(i, estado, solicitado, aprobado, resultado):
    return {"id_expediente": i, "cod_eps": "EPS01", "tipo_procedimiento": "uso_excepcional_fondo",
            "base_normativa": "RGT art. 89", "fecha_inicio": "2025-03-03", "estado": estado, "resultado": resultado,
            "motivo": "rotura de tubería", "monto_solicitado": str(solicitado), "monto_aprobado": aprobado}


@pytest.fixture
def settings(tmp_path):
    data = escribir_csvs(tmp_path / "data", {
        "ds01_catalogo_eps": [{"cod_eps": "EPS01", "nombre_eps": "EPS Uno", "resolucion_estudio_vigente": "RCD 001-2025"},
                              {"cod_eps": "EPS02", "nombre_eps": "EPS Dos"}],
        "ds02_procedimientos": [
            _ufi("UFI-A", "concluido", 50000, "40000", "aprobado_parcial"),
            _ufi("UFI-B", "concluido", 20000, "0", "denegado"),
            _ufi("UFI-C", "en_tramite", 30000, "", ""),
            _ufi("UFI-D", "concluido", 10000, "5000", "aprobado"),
        ],
        "ds05_fondo_inversiones_reservas": [
            _d5("EPS01", "2025-04", "fondo_inversiones", uso=200, exc=40000, id_exp="UFI-A", saldo=5000),
            _d5("EPS01", "2025-05", "fondo_inversiones", uso=100, saldo=5100),
            _d5("EPS01", "2025-05", "reserva_grd_acc", exc=6000, id_exp="UFI-D", saldo=800),
            # Usos sin expediente: uso por emergencia (art. 90), antes y después del 01-08-2026.
            _d5("EPS02", "2026-03", "reserva_grd_acc", exc=700, saldo=300),
            _d5("EPS02", "2026-08", "reserva_grd_acc", exc=900, saldo=100),
        ],
        "ds03_programa_inversiones": [
            _d3("EPS01-P001", 2026, 1000, 1000, cui="9000001"),
            _d3("EPS01-P002", 2026, 1000, 800, mod="CPI-2026-0001"),
            _d3("EPS01-P002", 2027, 1000, 800, mod="CPI-2026-0001"),
            _d3("EPS01-P003", 2026, 1000, 1000, fuente="transferencia_gobierno_nacional"),
            _d3("EPS01-P004", 2026, 1000, 1000),
            _d3("EPS02-P001", 2020, 500, 500, periodo="anterior"),
        ],
        "ds04_ejecucion_inversiones": [
            _d4("EPS01-P001", "2026-T1", "en_ejecucion", 10, 100),
            _d4("EPS01-P001", "2026-T2", "en_ejecucion", 20, 500),   # 50 % financiero vs 20 % físico → señal
            _d4("EPS01-P002", "2026-T2", "en_ejecucion", 40, 640),   # 40 % sobre vigente 1600; 32 % sobre original
            _d4("EPS01-P003", "2026-T2", "en_ejecucion", 30, 300),
            _d4("EPS01-P003", "2026-T2", "en_ejecucion", 35, 350),   # llave repetida (CAL-DUP-02)
            _d4("EPS02-P001", "2021-T4", "concluido", 100, 500),
        ],
        "ds08_inversiones_mef": [{"cui": "9000001", "nombre_inversion": "X", "estado_inversion": "ACTIVO",
                                  "devengado_acumulado": "450", "avance_fisico_pct": "25",
                                  "fecha_ultima_actualizacion": "2026-09-01"}],
        "ds06_estados_financieros": [{"cod_eps": "EPS01", "anio": "2025", "estado_presentacion": "presentado",
                                      "margen_operativo_pct": "12.5", "liquidez_corriente": "1.4"}],
    })
    publico = tmp_path / "casos"
    publico.mkdir()
    (publico / "epssmu_ufi_2025.yaml").write_text(
        (Path(get_settings().casos_reales_dir) / "epssmu_ufi_2025.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    privado = tmp_path / "privado"
    privado.mkdir()
    s = Settings(data_dir=data, rules_dir=RULES, reportes_dir=tmp_path / "reportes", casos_reales_dir=publico,
                 casos_reales_privados_dir=privado, database_url=f"sqlite:///{(tmp_path / 'f4.db').as_posix()}")
    servicio.seed(s)
    return s


@pytest.fixture
def t(settings):
    return tablas(settings.database_url)


@pytest.fixture
def cliente(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app, headers={"X-Usuario": "coord-srt-01"})
    app.dependency_overrides.clear()


def _por_fondo(r):
    return {f["fondo"]: f for f in r["filas"]}


# ============================================================ totales por fondo
def test_resumen_fondos_columnas_y_categorias(t):
    r = ruta.resumen_fondos(t, fondos=FONDOS)
    f = _por_fondo(r)
    # Siempre hay una fila por fondo del catálogo, aunque no tenga datos, y la columna art. 90.
    assert set(FONDOS) <= set(f)
    assert all("uso_emergencia_art_90" in x for x in f.values())
    assert f["reserva_mrse"]["uso_emergencia_art_90"] == 0
    # Solicitado: DS02 no dice de qué fondo → «no indicado».
    assert f["sin_fondo_indicado"]["solicitado"] == 110000
    assert f["fondo_inversiones"]["solicitado"] == 0
    # Autorizado: al fondo donde DS05 registra el uso (supuesto).
    assert f["fondo_inversiones"]["autorizado"] == 40000
    assert f["reserva_grd_acc"]["autorizado"] == 5000
    assert f["fondo_inversiones"]["uso_excepcional_art_89"] == 40000
    assert f["fondo_inversiones"]["uso_ordinario"] == 300
    assert f["reserva_grd_acc"]["uso_emergencia_art_90"] == 1600
    # Verificado nunca es cero: es «pendiente» (None) con su conteo.
    assert f["fondo_inversiones"]["verificado"] is None
    assert f["fondo_inversiones"]["verificaciones_pendientes"] == 1
    assert f["reserva_grd_acc"]["verificaciones_pendientes"] == 3  # UFI-D + 2 usos por emergencia
    tot = r["total"]
    assert tot["autorizado"] == 45000 and tot["uso_emergencia_art_90"] == 1600 and tot["verificado"] is None
    assert any("art. 90" in n for n in r["notas"])


def test_resumen_fondos_filtros(t):
    assert _por_fondo(ruta.resumen_fondos(t, cod_eps="EPS02", fondos=FONDOS))["sin_fondo_indicado"]["solicitado"] == 0
    r = ruta.resumen_fondos(t, anio=2026, fondos=FONDOS)
    assert _por_fondo(r)["fondo_inversiones"]["uso_ordinario"] == 0
    solo = ruta.resumen_fondos(t, fondo="reserva_grd_acc", fondos=FONDOS)
    assert [x["fondo"] for x in solo["filas"]] == ["reserva_grd_acc"]


def test_usos_por_emergencia_y_su_informe(t):
    cal = calendario_desde(RULES / "feriados.yaml")
    cat = catalogo_desde(RULES / "plazos.yaml")
    usos = {u["anio_mes"]: u for u in ruta.usos_emergencia(t, cal, cat)}
    assert set(usos) == {"2026-03", "2026-08"}
    assert all(u["categoria"] == "uso_emergencia_art_90" and "No es un error" in u["texto"] for u in usos.values())
    # Antes del 01-08-2026 no hay regla leída aplicable: no se inventa el plazo.
    assert usos["2026-03"]["informe"]["estado"] == "no_calculable" and "DRE-22" in usos["2026-03"]["informe"]["mensaje"]
    # Desde el 01-08-2026: 10 DH desde el último día del mes (RCD 028-2026).
    inf = usos["2026-08"]["informe"]
    assert inf["fecha_limite"] == cal.sumar_dias_habiles(date(2026, 8, 31), 10)
    assert "10 DH" in inf["mensaje"]
    assert ruta.usos_emergencia(t, cal, cat, cod_eps="EPS01") == []
    assert [u["anio_mes"] for u in ruta.usos_emergencia(t, cal, cat, anio=2026)] == ["2026-03", "2026-08"]


def test_serie_fondo_clasifica_el_uso_excepcional(t):
    serie = ruta.serie_fondo(t, "EPS01")
    cat = {(s["anio_mes"], s["tipo_fondo"]): s["categoria_uso_excepcional"] for s in serie}
    assert cat[("2025-04", "fondo_inversiones")] == "uso_excepcional_art_89"
    assert cat[("2025-05", "fondo_inversiones")] is None
    assert ruta.serie_fondo(t, "EPS02")[0]["categoria_uso_excepcional"] == "uso_emergencia_art_90"
    assert ruta.serie_fondo(t, "EPS01", "reserva_grd_acc")[0]["diferencia_deposito"] == 0


# ======================================================= escalera de uso del fondo
def _peldanos(r):
    return {p["peldano"]: p for p in r["escalera"]}


def test_escalera_uso_autorizado(t):
    r = ruta.ruta_expediente_uso(t, "UFI-A", TEXTOS)
    p = _peldanos(r)
    assert list(p) == ["solicitado", "autorizado", "usado", "verificacion_posterior", "devolucion"]
    assert p["solicitado"]["fondo"] == "sin_fondo_indicado"
    assert p["autorizado"]["estado"] == "cumplido" and p["autorizado"]["fondo"] == ["fondo_inversiones"]
    assert p["usado"]["monto"] == 40000
    assert p["verificacion_posterior"]["estado"] == "pendiente"
    assert p["devolucion"]["estado"] == "sin_dato"
    assert r["senal"] is None


def test_escalera_uso_denegado_pendiente_y_senal(t):
    b = _peldanos(ruta.ruta_expediente_uso(t, "UFI-B", TEXTOS))
    assert b["autorizado"]["estado"] == "no_autorizado" and b["usado"]["estado"] == "no_aplica"
    c = _peldanos(ruta.ruta_expediente_uso(t, "UFI-C", TEXTOS))
    assert c["autorizado"]["estado"] == "pendiente" and c["autorizado"]["monto"] is None
    d = ruta.ruta_expediente_uso(t, "UFI-D", TEXTOS)
    assert "supera el monto autorizado" in d["senal"]  # usó 6000 con 5000 autorizados
    assert ruta.ruta_expediente_uso(t, "NO-EXISTE", TEXTOS) is None


# ================================================================== caso real
def test_caso_epssmu_solo_publico(cliente):
    r = cliente.get("/ruta-dinero/expedientes/REAL-EPSSMU-2025").json()
    p = _peldanos(r)
    assert r["naturaleza"] == "real" and r["con_detalle_privado"] is False
    assert "PCC/PAS" in p["autorizado"]["fondo"] and p["autorizado"]["monto"] == 217313.2
    assert p["verificacion_posterior"]["estado"] == "pendiente"
    assert p["devolucion"]["estado"] == "exonerada"
    assert r["visibilidad"]["fondo_origen"] == "publico"


def test_caso_epssmu_con_detalle_privado(settings, cliente):
    (settings.casos_reales_privados_dir / "epssmu_ufi_2025_detalle.yaml").write_text(yaml.safe_dump({
        "caso": "EPSSMU-UFI-2025",
        "ruta_dinero": {"solicitado": {"fondo": "fondo de inversiones y reservas (no indicó cuál)"},
                        "verificacion_posterior": {"area": "Oficina de prueba"}},
    }, allow_unicode=True), encoding="utf-8")
    r = cliente.get("/ruta-dinero/expedientes/REAL-EPSSMU-2025").json()
    p = _peldanos(r)
    assert r["con_detalle_privado"] is True
    assert p["solicitado"]["fondo"].startswith("fondo de inversiones y reservas")
    # La combinación es profunda: el área se agrega y el estado público se conserva.
    assert p["verificacion_posterior"]["area"] == "Oficina de prueba"
    assert p["verificacion_posterior"]["estado"] == "pendiente"


# ================================================================== proyectos
def _proys(t, **kw):
    return {p["cod_proyecto"]: p for p in ruta.proyectos(t, PARAMS, TEXTOS, **kw)}


def test_avance_financiero_base_vigente_y_original(t):
    p = _proys(t)
    p2 = p["EPS01-P002"]
    assert p2["modificado"] and p2["expediente_modificacion"] == ["CPI-2026-0001"]
    assert p2["monto_programado_vigente"] == 1600 and p2["monto_programado_original"] == 2000
    assert p2["avance_financiero"] == 40.0 and p2["avance_financiero_original"] == 32.0
    assert "programado vigente" in p2["base_avance_financiero"] and "original" in p2["base_avance_financiero"]
    p1 = p["EPS01-P001"]
    assert p1["avance_financiero_original"] is None and "original" not in p1["base_avance_financiero"]


def test_senal_para_revision_sobre_25_pp(t):
    p = _proys(t)
    assert p["EPS01-P001"]["diferencia_pp"] == 30.0 and p["EPS01-P001"]["senal_revision"]
    assert p["EPS01-P001"]["texto_senal"] == TEXTOS["senal"]
    assert p["EPS01-P002"]["senal_revision"] is False
    assert list(_proys(t, solo_senales=True)) == ["EPS01-P001"]


def test_ds04_repetido_o_ausente_no_se_adivina(t):
    p = _proys(t)
    assert p["EPS01-P003"]["ejecucion_financiera"] is None and "CAL-DUP-02" in p["EPS01-P003"]["aviso_ejecucion"]
    assert p["EPS01-P004"]["avance_financiero"] is None and "Sin reportes" in p["EPS01-P004"]["aviso_ejecucion"]
    assert p["EPS01-P004"]["etapa_escalera"] == "financiado"


def test_escalera_de_proyecto_y_filtros(t):
    p = _proys(t)
    e = {x["peldano"]: x for x in p["EPS02-P001"]["escalera"]}
    assert p["EPS02-P001"]["etapa_escalera"] == "concluido"
    assert e["verificacion_posterior"]["estado"] == "pendiente"
    assert e["beneficio_verificado"]["estado"] == "no_verificado"
    assert e["financiado"]["estado"] == "declarado"
    assert "RCD 001-2025" in {x["peldano"]: x for x in p["EPS01-P001"]["escalera"]}["aprobado"]["detalle"]
    assert p["EPS01-P001"]["conciliacion_mef"]["devengado_acumulado"] == 450
    assert list(_proys(t, fuente="transferencia_gobierno_nacional")) == ["EPS01-P003"]
    assert list(_proys(t, periodo="anterior")) == ["EPS02-P001"]
    assert list(_proys(t, etapa="concluido")) == ["EPS02-P001"]
    assert set(_proys(t, cod_eps="EPS02")) == {"EPS02-P001"}


def test_detalle_proyecto(t):
    d = ruta.detalle_proyecto(t, PARAMS, TEXTOS, "EPS01-P002")
    assert [a["anio"] for a in d["anios"]] == [2026, 2027]
    assert d["trimestres"][0]["ejecucion_acumulada"] == 640
    assert ruta.detalle_proyecto(t, PARAMS, TEXTOS, "NO-EXISTE") is None


# ================================================================ visibilidad
def test_visibilidad_solo_publico_y_por_defecto_reservado():
    cat = vis.catalogo(RULES / "visibilidad.yaml")
    assert vis.nivel(cat, "proyecto", "campo_inexistente") == "reservado"
    datos = {"nombre_proyecto": "X", "monto_programado_vigente": 10, "avance_financiero": 5, "naturaleza": "sintético"}
    assert vis.solo_publico(cat, "proyecto", datos) == {"nombre_proyecto": "X", "naturaleza": "sintético"}
    assert vis.mapa(cat, "fondo")["uso_emergencia_art_90"] == "reservado"


def test_visibilidad_rechaza_niveles_desconocidos(tmp_path):
    malo = tmp_path / "v.yaml"
    malo.write_text(yaml.safe_dump({"por_defecto": "reservado",
                                    "entidades": {"proyecto": {"x": {"nivel": "secreto"}}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        vis.catalogo(malo)


# ======================================================================= API
def test_api_resumen(cliente):
    r = cliente.get("/ruta-dinero/resumen").json()
    assert {"filas", "total", "usos_emergencia", "expedientes_uso", "casos_reales", "filtros", "visibilidad"} <= set(r)
    assert [c["id_expediente"] for c in r["casos_reales"]] == ["REAL-EPSSMU-2025"]
    assert {e["id_expediente"] for e in r["expedientes_uso"]} == {"UFI-A", "UFI-B", "UFI-C", "UFI-D"}
    assert r["filtros"]["anios"] == [2025, 2026] and "uso_emergencia_art_90" in r["categorias_uso"]
    assert isinstance(r["total"]["autorizado"], float)
    assert len(cliente.get("/ruta-dinero/resumen?cod_eps=EPS02&anio=2026").json()["usos_emergencia"]) == 2


def test_api_proyectos_y_detalle(cliente):
    r = cliente.get("/ruta-dinero/proyectos?solo_senales=true").json()
    assert r["total"] == 1 and r["umbral_senal_pp"] == 25
    d = cliente.get("/ruta-dinero/proyectos/EPS01-P002").json()
    assert d["avance_financiero_original"] == 32.0
    assert "avance_financiero" not in d["vista_publica"] and d["vista_publica"]["nombre_proyecto"]
    assert cliente.get("/ruta-dinero/proyectos/NO-EXISTE").status_code == 404


def test_api_fondos_expedientes_contexto_404(cliente):
    assert cliente.get("/ruta-dinero/fondos/EPS01").json()["serie"]
    assert cliente.get("/ruta-dinero/fondos/EPS99").status_code == 404
    assert cliente.get("/ruta-dinero/expedientes/UFI-A").json()["visibilidad"]["monto_autorizado"] == "publico"
    assert cliente.get("/ruta-dinero/expedientes/NO-EXISTE").status_code == 404
    c = cliente.get("/contexto-financiero/EPS01").json()
    assert c["anios"][0]["indicadores"]["margen_operativo_pct"] == 12.5 and "no es una nota" in c["aviso"]
    assert cliente.get("/contexto-financiero/EPS99").status_code == 404
    assert "entidades" in cliente.get("/visibilidad").json()


def test_api_ficha_incluye_ruta_del_dinero(cliente):
    f = cliente.get("/expedientes/UFI-A").json()
    assert f["ruta_dinero"]["escalera"][1]["fondo"] == ["fondo_inversiones"]


def test_sin_carga_devuelve_404(tmp_path):
    s = Settings(data_dir=tmp_path, rules_dir=RULES, reportes_dir=tmp_path, casos_reales_dir=tmp_path,
                 casos_reales_privados_dir=tmp_path, database_url=f"sqlite:///{(tmp_path / 'vacia.db').as_posix()}")
    from app.db import crear_esquema, get_engine
    crear_esquema(get_engine(s.database_url))
    app.dependency_overrides[get_settings] = lambda: s
    try:
        assert TestClient(app, headers={"X-Usuario": "coord-srt-01"}).get("/ruta-dinero/resumen").status_code == 404
    finally:
        app.dependency_overrides.clear()
