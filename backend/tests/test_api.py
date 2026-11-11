"""Carga en base de datos, reporte HTML y API, con una muestra pequeña."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import servicio
from app.config import Settings, get_settings
from app.main import app
from tests.conftest import escribir_csvs


@pytest.fixture
def settings(tmp_path):
    data = escribir_csvs(tmp_path / "data", {
        "ds01_catalogo_eps": [{"cod_eps": "EPS01", "nombre_eps": "EPS Demo S.A."}],
        "ds03_programa_inversiones": [{"cod_eps": "EPS01", "cod_proyecto": "EPS01-P001", "cui": "9716915",
                                       "tipo_periodo": "vigente", "anio": "2026",
                                       "monto_programado_vigente": "1000.00"}],
        "ds08_inversiones_mef": [{"cui": "9000001", "entidad": "EPS DEMO S.A."}],
        "ds06_estados_financieros": [{"cod_eps": "EPS01", "anio": "2025", "estado_presentacion": "no_presentado"}],
    })
    return Settings(data_dir=data, rules_dir=get_settings().rules_dir, reportes_dir=tmp_path / "reportes",
                    database_url=f"sqlite:///{(tmp_path / 't.db').as_posix()}")


@pytest.fixture
def cliente(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_sin_carga_responde_404(cliente):
    assert cliente.get("/health").json() == {"estado": "ok"}
    assert cliente.get("/calidad/hallazgos").status_code == 404
    ds = cliente.get("/datasets").json()
    assert len(ds) == 11 and ds[0]["filas_cargadas"] is None


def test_seed_api_y_reporte(settings, cliente):
    r = servicio.seed(settings)
    assert r.filas["ds03_programa_inversiones"] == 1
    assert r.reporte.exists()

    ds = {d["nombre"]: d for d in cliente.get("/datasets").json()}
    assert ds["ds03_programa_inversiones"]["filas_cargadas"] == 1
    assert ds["ds09_ipm"]["naturaleza"] == "real"
    pob = next(c for c in ds["ds03_programa_inversiones"]["columnas"] if c["nombre"] == "poblacion_beneficiaria")
    assert pob["naturaleza"] == "estimado"

    hs = cliente.get("/calidad/hallazgos", params={"regla_id": "CAL-CUI-01"}).json()
    assert len(hs) == 1 and hs[0]["fila"] == 2 and hs[0]["fuente_regla"]
    assert cliente.get("/calidad/hallazgos", params={"severidad": "informativa", "tipo": "cui_sin_mef"}).json() == []

    res = cliente.get("/calidad/resumen").json()
    assert res["total"] == r.hallazgos
    cui = next(t for t in res["tipos"] if t["tipo"] == "cui_sin_mef")
    assert cui["hallazgos"] == 1 and cui["anunciado_en_diccionario"]

    html = cliente.get("/calidad/reporte.html", params={"descargar": True})
    assert html.headers["content-disposition"].startswith("attachment")
    assert "9716915" in html.text and "No encontrado en la muestra" in html.text
    assert "Ninguna salida es una decisión regulatoria" in html.text

    # Volver a evaluar no duplica hallazgos y una segunda carga crea otro lote.
    assert servicio.recalcular_calidad(settings) == r.hallazgos
    assert servicio.seed(settings).lote_id == r.lote_id + 1
    assert cliente.get("/calidad/resumen").json()["total"] == r.hallazgos


def test_recalcular_exige_mismos_archivos(settings):
    servicio.seed(settings)
    (settings.data_dir / "ds09_ipm.csv").write_text(
        "anio_mes,variacion_mensual_pct,indice_base_dic2020,variacion_12m_pct,fecha_publicacion,fuente\n",
        encoding="utf-8")
    with pytest.raises(RuntimeError, match="cambiaron"):
        servicio.recalcular_calidad(settings)


def test_seed_sin_data_dir(tmp_path):
    s = Settings(data_dir=tmp_path / "no_existe", database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    with pytest.raises(FileNotFoundError):
        servicio.seed(s)


def test_cli_verificar_diccionario_sin_archivo(settings, monkeypatch, capsys):
    from app import cli
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    assert cli.main(["verificar-diccionario"]) == 1
    assert "No se encontró" in capsys.readouterr().out
