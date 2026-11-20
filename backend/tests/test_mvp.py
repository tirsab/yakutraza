"""Modo MVP: con MVP_EPS, ninguna vista ni selector muestra otra EPS; el interruptor «Ver la muestra completa»
(encabezado X-Alcance: muestra) las muestra sin volver a cargar los datos."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import alcance, servicio
from app.config import Settings, get_settings
from app.main import app
from tests.test_vistas import AREA, COORD, DIR, ESP, RULES, _muestra

MUESTRA = {"X-Alcance": "muestra"}


def _cliente(s: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: s
    return TestClient(app)


@pytest.fixture
def settings_mvp(tmp_path):
    (tmp_path / "casos").mkdir()
    (tmp_path / "privado").mkdir()
    s = Settings(data_dir=_muestra(tmp_path), rules_dir=RULES, reportes_dir=tmp_path / "reportes",
                 casos_reales_dir=tmp_path / "casos", casos_reales_privados_dir=tmp_path / "privado",
                 database_url=f"sqlite:///{(tmp_path / 'mvp.db').as_posix()}", mvp_eps="EPS02")
    servicio.seed(s)
    return s


@pytest.fixture
def cliente_mvp(settings_mvp):
    yield _cliente(settings_mvp)
    app.dependency_overrides.clear()


# Vistas, selectores y datos que la interfaz pide, con el usuario que puede verlos.
RECORRIDO = [
    ("/config", None), ("/sesion", DIR), ("/usuarios-demo", None),
    ("/bandeja", ESP), ("/bandeja", COORD), ("/tablero", DIR), ("/expedientes", AREA), ("/alertas", DIR),
    ("/ruta-dinero/resumen", DIR), ("/ruta-dinero/proyectos", DIR),
    ("/publico/localidades?q=be", None), ("/publico/localidades?q=ti", None), ("/publico/ubicaciones", None),
    ("/calidad/hallazgos", None), ("/calidad/resumen", None),
    ("/calidad/reporte.html", None),
]


def _get(c, url, u=None, extra=None):
    h = {"X-Usuario": u} if u else {}
    return c.get(url, headers={**h, **(extra or {})})


def _recorrer(c):
    """Respuestas de todo el recorrido, más el mapa de cada departamento y provincia que ofrece el selector."""
    for url, u in RECORRIDO:
        yield url, _get(c, url, u)
    for d in _get(c, "/publico/ubicaciones").json():
        for p in d.get("provincias", []):
            url = f"/publico/mapa?departamento={d['departamento']}&provincia={p['provincia'] if isinstance(p, dict) else p}"
            yield url, _get(c, url)


def test_mvp_eps_y_tipos():
    assert alcance.mvp_eps(" eps02, EPS07 ,,EPS09") == {"EPS02", "EPS07", "EPS09"}
    assert alcance.mvp_eps("") == frozenset() and not alcance.modo_mvp()
    token = alcance.fijar({"EPS02"})
    try:
        assert alcance.visible("EPS02") and not alcance.visible("EPS08") and alcance.visible(None)
        assert alcance.tipo_en_vistas("revision_periodica") and not alcance.tipo_en_vistas("reporte_periodico")
    finally:
        alcance.restaurar(token)
    assert alcance.visible("EPS08") and alcance.tipo_en_vistas("reporte_periodico")


def test_ninguna_vista_muestra_otra_eps(cliente_mvp):
    for url, r in _recorrer(cliente_mvp):
        assert r.status_code == 200, (url, r.status_code, r.text[:200])
        assert "EPS08" not in r.text, f"{url} muestra una EPS fuera del MVP"
    # La ficha, los relojes, el fondo y el portal de una EPS fuera del MVP no existen en modo MVP.
    assert _get(cliente_mvp, "/expedientes/RPI-2026-0002", AREA).status_code == 404
    assert _get(cliente_mvp, "/mi-eps", "eps-EPS08").status_code == 404
    assert _get(cliente_mvp, "/ruta-dinero/fondos/EPS08", DIR).status_code == 404


def test_config_informa_el_modo_y_el_interruptor_muestra_todo(cliente_mvp):
    cfg = _get(cliente_mvp, "/config").json()
    assert cfg["mvp"]["configurado"] and cfg["mvp"]["activo"] and cfg["mvp"]["eps"] == ["EPS02"]
    assert "Base pequeña" in cfg["mvp"]["aviso"]
    assert [e["cod_eps"] for e in cfg["eps"]] == ["EPS02"]
    todo = _get(cliente_mvp, "/config", extra=MUESTRA).json()
    assert not todo["mvp"]["activo"] and [e["cod_eps"] for e in todo["eps"]] == ["EPS02", "EPS08"]
    ids = {x["id_expediente"] for x in _get(cliente_mvp, "/expedientes", AREA, MUESTRA).json()}
    assert "RPI-2026-0002" in ids
    assert _get(cliente_mvp, "/expedientes/RPI-2026-0002", AREA, MUESTRA).status_code == 200


def test_en_modo_mvp_bandeja_y_tablero_solo_con_los_procedimientos_del_desafio(cliente_mvp):
    t = _get(cliente_mvp, "/tablero", DIR).json()
    tipos = set(t["supera_plazo"]["por_tipo"])
    assert tipos <= alcance.TIPOS_DESAFIO
    # La ficha de la EPS sí muestra todos sus trámites.
    assert _get(cliente_mvp, "/mi-eps", "eps-EPS02").status_code == 200


def test_calidad_evaluada_con_cada_alcance(settings_mvp, cliente_mvp):
    from sqlalchemy import func, select
    from app.db import calidad_hallazgos, get_engine
    with get_engine(settings_mvp.database_url).connect() as cx:
        por_alcance = dict(cx.execute(select(calidad_hallazgos.c.alcance, func.count())
                                      .group_by(calidad_hallazgos.c.alcance)).all())
    assert set(por_alcance) == {"muestra", "mvp"}
    assert len(_get(cliente_mvp, "/calidad/hallazgos").json()) == por_alcance["mvp"]
    assert len(_get(cliente_mvp, "/calidad/hallazgos", extra=MUESTRA).json()) == por_alcance["muestra"]
    assert not any("EPS08" in str(h) for h in _get(cliente_mvp, "/calidad/hallazgos").json())


def test_sin_mvp_eps_todo_se_ve_como_antes(tmp_path):
    (tmp_path / "c").mkdir()
    s = Settings(data_dir=_muestra(tmp_path), rules_dir=RULES, reportes_dir=tmp_path / "r", casos_reales_dir=tmp_path / "c",
                 casos_reales_privados_dir=tmp_path / "c", database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    servicio.seed(s)
    try:
        c = _cliente(s)
        cfg = _get(c, "/config").json()
        assert not cfg["mvp"]["configurado"] and not cfg["mvp"]["activo"]
        assert {e["cod_eps"] for e in cfg["eps"]} == {"EPS02", "EPS08"}
    finally:
        app.dependency_overrides.clear()


# ------------------------------------------------------------------ con la muestra real (20 EPS)
OTRAS = re.compile(r"\bEPS(0[134568]|1\d|20)\b")


@pytest.mark.muestra
def test_muestra_real_en_modo_mvp(data_dir_real, tmp_path):
    (tmp_path / "c").mkdir()
    s = Settings(data_dir=data_dir_real, rules_dir=RULES, reportes_dir=tmp_path / "r", casos_reales_dir=tmp_path / "c",
                 casos_reales_privados_dir=tmp_path / "c", database_url=f"sqlite:///{(tmp_path / 'm.db').as_posix()}",
                 mvp_eps="EPS02,EPS07,EPS09")
    servicio.seed(s)
    try:
        c = _cliente(s)
        for url, r in _recorrer(c):
            assert r.status_code == 200, (url, r.status_code)
            m = OTRAS.search(r.text)
            assert m is None, f"{url} muestra {m.group(0)}, que no es del MVP"
        # Cifras del MVP (solo los tres procedimientos del desafío) y de la muestra completa.
        # En modo MVP el tablero cuenta solo CPI, UFI y RP: 3 de 7 (con las verificaciones serían 3 de 11).
        sp = _get(c, "/tablero", DIR).json()["supera_plazo"]["total"]
        assert (sp["superan"], sp["calculables"]) == (3, 7)
        sp_todo = _get(c, "/tablero", DIR, MUESTRA).json()["supera_plazo"]["total"]
        assert (sp_todo["superan"], sp_todo["calculables"]) == (12, 65)
        assert _get(c, "/calidad/resumen").json()["total"] == 35
        assert _get(c, "/calidad/resumen", extra=MUESTRA).json()["total"] == 202
    finally:
        app.dependency_overrides.clear()
