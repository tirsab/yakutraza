"""Demo publicada en un solo proceso: API bajo /api e interfaz con respaldo a index.html."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.publicar import crear


def _cliente(tmp_path):
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>YakuTraza</title>", encoding="utf-8")
    (web / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secreto.txt").write_text("no se sirve", encoding="utf-8")
    return TestClient(crear(web))


def test_interfaz_y_rutas_del_navegador(tmp_path):
    c = _cliente(tmp_path)
    assert "YakuTraza" in c.get("/").text
    assert "YakuTraza" in c.get("/bandeja/CPI-2026-0004").text  # ruta de React Router
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/assets/no-existe.js").status_code == 404


def test_no_sirve_archivos_fuera_de_la_web(tmp_path):
    c = _cliente(tmp_path)
    for ruta in ("/../secreto.txt", "/%2e%2e/secreto.txt", "/assets/%2e%2e/%2e%2e/secreto.txt"):
        assert "no se sirve" not in c.get(ruta).text


def test_api_bajo_api(tmp_path):
    r = _cliente(tmp_path).get("/api/etiquetas")
    assert r.status_code == 200 and isinstance(r.json(), dict)
