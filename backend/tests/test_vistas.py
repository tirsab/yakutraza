"""Fase 5: permisos por rol, bandeja, tablero gerencial, simulador, vista EPS, vista ciudadana y etiquetas."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import servicio
from app.config import Settings, get_settings
from app.db import get_engine, metadata
from app.dinero import visibilidad as vis
from app.main import app
from app.vistas import tablero
from app.vistas.privacidad import TEXTO, ocultar_internos
from tests.conftest import escribir_csvs
from tests.test_expediente import _hitos_cpi

RULES = get_settings().rules_dir
ESP, COORD, DIR, AREA = "esp-srt-01", "coord-srt-01", "dir-dre-01", "area-01"


def _h(exp, n, hito, resp, ini, fin, cuenta="True", doc="", ref="", etapa="unica", plazo_etapa="30"):
    return {"id_expediente": exp, "nro_hito": str(n), "etapa": etapa, "plazo_etapa_dh": plazo_etapa, "hito": hito,
            "responsable": resp, "fecha_inicio": ini, "fecha_fin": fin, "cuenta_plazo": cuenta, "documento": doc,
            "plazo_referencial_dh": ref}


def _muestra(tmp_path):
    hitos = _hitos_cpi()
    # CPI-2026-0005: la EP tiene que responder un oficio de información (10 DH).
    hitos += [_h("CPI-2026-0005", 1, "solicitud", "EP", "2026-08-31", "2026-08-31"),
              _h("CPI-2026-0005", 2, "oficio_informacion", "SRT", "2026-08-31", "2026-09-14", doc="OF-2026-0030"),
              _h("CPI-2026-0005", 3, "informacion_ep", "EP", "2026-09-14", "", cuenta="False", ref="10")]
    # Revisión periódica concluida, con audiencia pública y comentarios; superó el plazo.
    hitos += [_h("RP-2025-0001", 1, "solicitud", "EP", "2025-01-06", "2025-01-06", etapa="1_inicio"),
              _h("RP-2025-0001", 2, "audiencia_publica", "DU", "2025-06-02", "2025-06-20", ref="30", etapa="3_difusion"),
              _h("RP-2025-0001", 3, "comentarios", "EP e interesados", "2025-06-20", "2025-07-11", ref="15",
                 etapa="3_difusion"),
              _h("RP-2025-0001", 4, "memo_gg_final", "DRE", "2025-08-01", "2025-08-05", etapa="4_aprobacion"),
              _h("RP-2025-0001", 5, "resolucion_tarifaria", "CD", "2025-08-05", "2025-08-20", etapa="4_aprobacion")]
    data = escribir_csvs(tmp_path / "data", {
        "ds01_catalogo_eps": [{"cod_eps": "EPS02", "nombre_eps": "EPS Demo"}, {"cod_eps": "EPS08", "nombre_eps": "EPS Ocho"}],
        "ds01_localidades_eps": [
            {"cod_eps": "EPS02", "localidad": "Tingo María", "ubigeo": "100601", "departamento": "HUANUCO",
             "provincia": "LEONCIO PRADO", "distrito": "RUPA-RUPA", "es_sede": "True", "poblacion_servida": "50000",
             "conexiones_agua": "12000", "conexiones_alcantarillado": "9000"},
            {"cod_eps": "EPS08", "localidad": "Belén", "ubigeo": "160112", "departamento": "LORETO", "provincia": "MAYNAS",
             "distrito": "BELEN", "es_sede": "False", "poblacion_servida": "70000", "conexiones_agua": "20000",
             "conexiones_alcantarillado": "16000"}],
        "ds02_procedimientos": [
            {"id_expediente": "CPI-2026-0004", "cod_eps": "EPS02", "tipo_procedimiento": "cambio_programa_inversiones",
             "base_normativa": "RGT art. 93", "fecha_inicio": "2026-07-27", "plazo_maximo_dh": "30",
             "dias_suspension_dh": "7", "dias_habiles_sunass": "37", "fecha_limite": "2026-09-21", "estado": "en_tramite",
             "hito_actual": "elevacion_cd", "responsable_actual": "GG", "cod_proyecto": "EPS02-P014",
             "monto_solicitado": "159441.32"},
            {"id_expediente": "CPI-2026-0005", "cod_eps": "EPS02", "tipo_procedimiento": "cambio_programa_inversiones",
             "fecha_inicio": "2026-08-31", "plazo_maximo_dh": "30", "estado": "en_tramite"},
            {"id_expediente": "CPI-2025-0009", "cod_eps": "EPS02", "tipo_procedimiento": "cambio_programa_inversiones",
             "fecha_inicio": "2025-03-03", "fecha_conclusion": "2025-04-10", "plazo_maximo_dh": "30",
             "dias_habiles_sunass": "20", "estado": "concluido", "resultado": "aprobado",
             "documento_final": "RCD-2025-0101", "monto_solicitado": "39000.00"},
            {"id_expediente": "RP-2025-0001", "cod_eps": "EPS02", "tipo_procedimiento": "revision_periodica",
             "fecha_inicio": "2025-01-06", "fecha_conclusion": "2025-08-20", "plazo_maximo_dh": "150",
             "dias_habiles_sunass": "160", "estado": "concluido", "resultado": "aprobado",
             "documento_final": "RCD-2025-0200"},
            {"id_expediente": "RPI-2026-0002", "cod_eps": "EPS08", "tipo_procedimiento": "reporte_periodico",
             "fecha_inicio": "2026-07-15", "estado": "en_tramite"},
        ],
        "ds02_hitos_procedimientos": hitos + [_h("RPI-2026-0002", 1, "presentacion", "EP", "2026-07-15", "")],
        "ds03_programa_inversiones": [
            {"cod_eps": "EPS02", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "EPS02-P014",
             "nombre_proyecto": "Medidores", "localidad": "Tingo María", "ubigeo": "100601", "meta_asociada": "MG09",
             "poblacion_beneficiaria": "1500", "anio": "2026", "monto_programado_original": "70000.00",
             "monto_programado_vigente": "70000.00", "fuente_financiamiento": "fondo_inversiones"},
            {"cod_eps": "EPS02", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "EPS02-P001",
             "nombre_proyecto": "Colector", "localidad": "Tingo María", "ubigeo": "100601", "anio": "2026",
             "monto_programado_original": "861000.00", "monto_programado_vigente": "900000.00",
             "id_expediente_modificacion": "CPI-2025-0009", "fuente_financiamiento": "fondo_inversiones"}],
    })
    return data


@pytest.fixture
def settings(tmp_path):
    publico = tmp_path / "casos"
    publico.mkdir()
    privado = tmp_path / "privado"
    privado.mkdir()
    s = Settings(data_dir=_muestra(tmp_path), rules_dir=RULES, reportes_dir=tmp_path / "reportes",
                 casos_reales_dir=publico, casos_reales_privados_dir=privado,
                 database_url=f"sqlite:///{(tmp_path / 'f5.db').as_posix()}")
    servicio.seed(s)
    return s


@pytest.fixture
def cliente(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def get(c, url, u=None, **kw):
    return c.get(url, headers={"X-Usuario": u} if u else {}, **kw)


# ========================================================== roles y permisos
def test_matriz_de_permisos(cliente):
    assert get(cliente, "/expedientes").status_code == 401            # ciudadanía no ve expedientes
    assert get(cliente, "/tablero").status_code == 401
    assert get(cliente, "/tablero", ESP).status_code == 403           # especialista no ve el tablero
    assert get(cliente, "/bandeja", DIR).status_code == 403           # dirección no tiene bandeja
    assert get(cliente, "/tablero", DIR).status_code == 200
    assert get(cliente, "/expedientes", AREA).status_code == 200      # otras áreas: solo lectura
    assert cliente.post("/simulador", json={}, headers={"X-Usuario": AREA}).status_code == 403
    assert get(cliente, "/mi-eps", ESP).status_code == 403
    assert get(cliente, "/ruta-dinero/resumen", "eps-EPS02").status_code == 403
    assert get(cliente, "/publico/localidades?q=tingo").status_code == 200
    assert get(cliente, "/sesion", "eps-XYZ").status_code == 401


def test_eps_solo_ve_su_cod_eps(cliente):
    ids = {x["id_expediente"] for x in get(cliente, "/expedientes", "eps-EPS02").json()}
    assert ids == {"CPI-2026-0004", "CPI-2026-0005", "CPI-2025-0009", "RP-2025-0001"}
    assert get(cliente, "/expedientes?cod_eps=EPS08", "eps-EPS02").status_code == 403
    assert get(cliente, "/expedientes/RPI-2026-0002", "eps-EPS08").status_code == 200
    assert get(cliente, "/expedientes/CPI-2026-0004", "eps-EPS08").status_code == 403
    assert get(cliente, "/expedientes/CPI-2026-0004/relojes", "eps-EPS08").status_code == 403
    assert get(cliente, "/bitacora", "eps-EPS02").status_code == 403


def test_eps_no_ve_documentos_internos(cliente):
    r = cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": ESP},
                     json={"tipo": "INF", "canal": "tramite", "numero": "INF-2026-0099", "hito": "memo_gg",
                           "fecha_emision": "2026-09-01"})
    assert r.status_code == 201
    interna = get(cliente, "/expedientes/CPI-2026-0004", ESP).json()
    assert any(d["numero"] == "INF-2026-0099" for d in interna["documentos"])
    f = get(cliente, "/expedientes/CPI-2026-0004", "eps-EPS02").json()
    assert f["vista"] == "eps"
    assert not any(d["tipo"] in ("INF", "MEM") for d in f["documentos"])
    textos = json.dumps(f, default=str)
    assert "INF-2026-0099" not in textos and "MEM-2026-0007" not in textos
    assert TEXTO in textos


def test_ocultar_internos_enmascara_referencias():
    f = {"documentos": [{"id": 1, "tipo": "MEM", "numero": "MEM-1", "reservado": True},
                        {"id": 2, "tipo": "OF", "numero": "OF-1", "reservado": False}],
         "linea_de_tiempo": [{"hito": "x", "evidencia": {"referencia": "MEM-2026-0007", "codigo_ds02": None,
                                                         "documentos": [1, 2]}, "alertas": []}],
         "relojes": [{"documento_inicio": "INF-2026-0001"}],
         "bitacora": [{"entidad": "documento", "entidad_id": "1"}, {"entidad": "documento", "entidad_id": "2"}]}
    g = ocultar_internos(f)
    assert [d["id"] for d in g["documentos"]] == [2]
    assert g["linea_de_tiempo"][0]["evidencia"] == {"referencia": TEXTO, "codigo_ds02": None, "documentos": [2]}
    assert g["relojes"][0]["documento_inicio"] == TEXTO
    assert [b["entidad_id"] for b in g["bitacora"]] == ["2"]
    assert f["documentos"][0]["id"] == 1  # el original no cambia


def test_modo_demo_desactivado(settings, cliente):
    settings.modo_demo = False
    try:
        assert get(cliente, "/expedientes", COORD).status_code == 401   # el encabezado se ignora
        cfg = get(cliente, "/config").json()
        assert cfg["modo_demo"] is False and [r["rol"] for r in cfg["roles"]] == ["ciudadania"] and cfg["eps"] == []
        assert get(cliente, "/usuarios-demo").json() == []
        assert cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": ESP},
                            json={"tipo": "OF", "canal": "correo", "fecha_recepcion": "2026-09-15"}).status_code == 401
        assert get(cliente, "/publico/localidades?q=tingo").status_code == 200
    finally:
        settings.modo_demo = True


def test_config_y_sesion(cliente):
    cfg = get(cliente, "/config").json()
    assert cfg["modo_demo"] and cfg["corte_max"] == "2026-09-30" and cfg["corte_min"] == "2025-01-06"
    roles = {r["rol"]: r for r in cfg["roles"]}
    assert list(roles) == ["especialista_srt", "coordinacion_srt", "direccion_dre", "otras_areas", "eps", "ciudadania"]
    assert roles["especialista_srt"]["usuario"] == ESP and roles["especialista_srt"]["inicio"] == "/bandeja"
    assert [e["cod_eps"] for e in cfg["eps"]] == ["EPS02", "EPS08"]
    assert "datos sintéticos" in cfg["rotulo"]
    s = get(cliente, "/sesion", "eps-EPS08").json()
    assert s["rol"] == "eps" and s["cod_eps"] == "EPS08" and s["inicio"] == "/mi-eps"
    assert get(cliente, "/sesion").json()["rol"] == "ciudadania"


# ================================================================== tablero
def test_tablero_indicadores_y_transicion_por_fecha_de_corte(cliente):
    t = get(cliente, "/tablero", COORD).json()
    ind = t["indicadores"]
    assert ind["en_tramite"]["n"] == 3
    assert sum(ind[e]["n"] for e in tablero.ESTADOS) == 3
    assert "CPI-2026-0004" in ind["vencido"]["ids"]
    # Antes del vencimiento, el mismo expediente estaba en plazo: la fecha de corte mueve los estados.
    antes = get(cliente, "/tablero?fecha_corte=2026-08-03", COORD).json()["indicadores"]
    assert "CPI-2026-0004" in antes["en_plazo"]["ids"] and antes["en_tramite"]["n"] == 2
    assert get(cliente, "/tablero?fecha_corte=2026-10-15", COORD).status_code == 422
    assert get(cliente, "/tablero?fecha_corte=2020-01-01", COORD).status_code == 422


def test_tablero_filtros_y_clic_hasta_el_expediente(cliente):
    t = get(cliente, "/tablero?estado=vencido", COORD).json()
    assert t["expedientes"] and all(x["estado"] == "vencido" for x in t["expedientes"])
    # Los indicadores no se filtran por estado (son el menú), sí por EPS.
    assert t["indicadores"]["en_tramite"]["n"] == 3
    assert get(cliente, "/tablero?cod_eps=EPS08", COORD).json()["indicadores"]["en_tramite"]["n"] == 1
    for id_exp in t["indicadores"]["vencido"]["ids"]:
        assert get(cliente, f"/expedientes/{id_exp}", COORD).status_code == 200
    resp = get(cliente, "/tablero?responsable=EP", COORD).json()
    assert {x["id_expediente"] for x in resp["expedientes"]} == {"CPI-2026-0005", "RPI-2026-0002"}


def test_linea_base_supera_plazo(cliente):
    sp = get(cliente, "/tablero", COORD).json()["supera_plazo"]
    assert sp["rotulo"] == "muestra simulada"
    assert sp["total"]["calculables"] == 3 and sp["total"]["superan"] == 2
    assert sp["total"]["en_tramite_superan"] == 1 and sp["total"]["porcentaje"] == 66.7
    assert sp["por_tipo"]["revision_periodica"]["ids_superan"] == ["RP-2025-0001"]
    assert sp["por_tipo"]["reporte_periodico"]["no_calculables"] == 1


def test_cuellos_de_botella_y_embudo(cliente):
    t = get(cliente, "/tablero", COORD).json()
    resp = {x["clave"]: x for x in t["cuellos"]["por_responsable"]}
    assert resp["EP"]["ids_en_curso"] == ["CPI-2026-0005", "RPI-2026-0002"]
    hito = {x["clave"]: x for x in t["cuellos"]["por_hito"]}
    assert hito["elevacion_cd"]["ids_en_curso"] == ["CPI-2026-0004"] and hito["elevacion_cd"]["responsables"] == ["SRT"]
    assert hito["audiencia_publica"]["supera_referencial"] == 0 and hito["audiencia_publica"]["con_referencial"] == 1
    emb = {e["clave"]: e for e in t["embudo"]["etapas"]}
    assert list(emb) == ["informe", "firma_informe", "memo_gg", "elevacion_cd", "resolucion"]
    assert emb["memo_gg"]["llegaron"] == 2 and emb["elevacion_cd"]["en_curso"] == 1
    assert emb["resolucion"]["llegaron"] == 1


def test_carga_asignacion_ficticia_y_propuesta(cliente, settings):
    c = get(cliente, "/tablero", COORD).json()["carga"]
    assert {a["especialista"] for a in c["actual"]} == {"esp-srt-01", "esp-srt-02", "esp-srt-03"}
    assert sum(a["n"] for a in c["actual"]) == 3
    assert c["pregunta_dre"] == "DRE-26" and "ficticia" in c["rotulo"]
    assert c["desbalance_propuesto"] <= c["desbalance_actual"]
    # La asignación es estable: mismo id, mismo especialista.
    esp = tablero.especialista_de("CPI-2026-0004", ["a", "b", "c"])
    assert esp == tablero.especialista_de("CPI-2026-0004", ["a", "b", "c"])


def test_calidad_resumida(cliente):
    q = get(cliente, "/tablero", COORD).json()["calidad"]
    assert q["total"] == sum(q["por_severidad"].values()) and q["reporte"] == "/calidad/reporte.html"


# ================================================================ simulador
def _huella(settings) -> str:
    h = hashlib.sha256()
    with get_engine(settings.database_url).connect() as cx:
        for t in sorted(metadata.tables.values(), key=lambda t: t.name):
            for r in cx.execute(select(t)).all():
                h.update(repr(tuple(r)).encode())
    return h.hexdigest()


def test_simulador_no_toca_los_datos(cliente, settings):
    antes = _huella(settings)
    r = cliente.post("/simulador", headers={"X-Usuario": DIR},
                     json={"fecha_corte": "2026-09-10", "dias_sin_accion": 10, "umbral_por_vencer_dh": 8,
                           "especialistas_adicionales": 2})
    assert r.status_code == 200
    sim = r.json()
    assert _huella(settings) == antes
    assert "no modifica los datos reales" in sim["rotulo"]
    assert sim["parametros"]["fecha_escenario"] > "2026-09-10"
    assert sim["escenario"]["vencido"]["n"] >= sim["base"]["vencido"]["n"]
    assert len(sim["carga_escenario"]["por_especialista"]) == 5
    assert all(c["antes"] != c["despues"] for c in sim["cambios"])
    assert cliente.post("/simulador", headers={"X-Usuario": DIR}, json={"dias_sin_accion": -1}).status_code == 422


# ================================================================== bandeja
def test_bandeja_responde_las_tres_preguntas(cliente):
    b = get(cliente, "/bandeja", COORD).json()
    items = b["items"]
    assert [x["id_expediente"] for x in items][0] == "CPI-2026-0004"   # vencido primero
    claves = [(tablero.ORDEN[x["estado"]], (x["alerta"] or {}).get("dias_restantes") or 10**6) for x in items]
    assert claves == sorted(claves)
    x = items[0]
    assert x["alerta"]["estado"] == "vencido" and x["siguiente_paso"]                    # qué requiere acción
    assert any("declarado, no verificado" in e["texto"] for e in x["evidencia_faltante"])  # qué falta
    razones = " ".join(x["por_que_importa"])                                               # por qué importa
    assert "Vencido hace" in razones and "S/ 159 441,32" in razones and "1 500 personas" in razones and "MG09" in razones


def test_bandeja_de_especialista_solo_sus_expedientes(cliente, settings):
    esp = tablero.cfg_tablero(settings)["asignacion"]["especialistas"]
    todos = get(cliente, "/bandeja", COORD).json()["items"]
    for e in esp:
        propios = get(cliente, "/bandeja", e).json()["items"]
        assert {x["id_expediente"] for x in propios} == {x["id_expediente"] for x in todos if x["especialista"] == e}


def test_bandeja_incluye_casos_reales_por_confirmar(settings, cliente):
    (settings.casos_reales_dir / "tacna_cpi_2026.yaml").write_text(
        (Path(get_settings().casos_reales_dir) / "tacna_cpi_2026.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    servicio.seed(settings)
    real = [x for x in get(cliente, "/bandeja", COORD).json()["items"] if x["naturaleza"] == "real"]
    assert real and real[0]["estado"] == "no_calculable" and real[0]["evidencia_faltante"]


# ================================================================ vista EPS
def test_mi_eps_que_le_falta_y_hasta_cuando(cliente):
    m = get(cliente, "/mi-eps", "eps-EPS02").json()
    s = m["siguiente_accion"]
    assert s["id_expediente"] == "CPI-2026-0005" and s["hito"] == "informacion_ep" and s["fecha_limite"]
    assert {t["id_expediente"] for t in m["tramites"]} == {"CPI-2026-0004", "CPI-2026-0005"}
    assert next(t for t in m["tramites"] if t["id_expediente"] == "CPI-2026-0004")["le_toca_a_la_eps"] is False
    assert "no se envía" in m["aviso_correo"]["aviso"] and "CPI-2026-0005" in m["aviso_correo"]["asunto"]
    assert [c["id_expediente"] for c in m["concluidos"]] == ["RP-2025-0001", "CPI-2025-0009"]


# =========================================================== vista ciudadana
def _claves(x, acc=None):
    acc = set() if acc is None else acc
    if isinstance(x, dict):
        for k, v in x.items():
            acc.add(k)
            _claves(v, acc)
    elif isinstance(x, list):
        for v in x:
            _claves(v, acc)
    return acc


def test_ciudadana_busqueda_sin_tildes(cliente):
    assert [r["localidad"] for r in get(cliente, "/publico/localidades?q=belen").json()] == ["Belén"]
    assert [r["ubigeo"] for r in get(cliente, "/publico/localidades?q=1006").json()] == ["100601"]
    assert get(cliente, "/publico/localidades?q=x").status_code == 422


def test_ciudadana_solo_campos_publicos(cliente):
    cat = vis.catalogo(RULES / "visibilidad.yaml")
    publicos = {c for e in cat["entidades"].values() for c, r in e.items() if r["nivel"] == "publico"}
    contexto = {"localidad", "fecha_corte", "agregados", "proyectos", "por_etapa", "monto_programado_original",
                "audiencias", "resumen_quechua", "avisos", "naturaleza", "fuente", "decisiones",
                "naturaleza_poblacion", "texto", "estado",
                # Seis etapas ciudadanas (lenguaje simple, por validar): describen la etapa, no son datos reservados.
                "etapas", "n", "de", "clave", "nombre", "detalle", "detenida", "estado_validacion"}
    r = get(cliente, "/publico/localidades/100601").json()
    claves = _claves({**r, "agregados": {**r["agregados"], "por_etapa": {}}})  # por_etapa: claves son valores
    assert claves <= publicos | contexto, claves - publicos - contexto
    p = {x["cod_proyecto"]: x for x in r["proyectos"]}
    assert set(p) == {"EPS02-P001", "EPS02-P014"}
    assert "monto_programado_vigente" not in p["EPS02-P001"] and "avance_financiero" not in p["EPS02-P001"]
    assert p["EPS02-P001"]["decisiones"][0]["documento_final"] == "RCD-2025-0101"
    assert "monto_solicitado" not in p["EPS02-P001"]["decisiones"][0]
    assert {a["hito"] for a in r["audiencias"]} == {"audiencia_publica", "comentarios"}
    assert all(a["estado"] == "realizada" for a in r["audiencias"])
    assert "conexiones_agua" not in r["localidad"]
    assert get(cliente, "/publico/localidades/999999").status_code == 404


def test_resumen_quechua_requiere_validacion_humana(cliente):
    assert cliente.post("/resumenes-quechua", json={"ubigeo": "100601", "texto": "Kay llaqtapi..."}).status_code == 401
    r = cliente.post("/resumenes-quechua", headers={"X-Usuario": ESP},
                     json={"ubigeo": "100601", "texto": "Texto de prueba escrito por una persona."})
    assert r.status_code == 201 and r.json()["estado"] == "propuesto"
    rid = r.json()["id"]
    assert get(cliente, "/publico/localidades/100601").json()["resumen_quechua"] is None   # aún no se publica
    assert cliente.post(f"/resumenes-quechua/{rid}/validar", headers={"X-Usuario": ESP}).status_code == 403
    assert cliente.post(f"/resumenes-quechua/{rid}/validar", headers={"X-Usuario": AREA}).status_code == 403
    assert cliente.post(f"/resumenes-quechua/{rid}/validar", headers={"X-Usuario": COORD}).json()["estado"] == "validado"
    pub = get(cliente, "/publico/localidades/100601").json()["resumen_quechua"]
    assert pub["texto"].startswith("Texto de prueba") and "validado_por" not in pub
    assert get(cliente, "/resumenes-quechua", "eps-EPS02").status_code == 403
    assert get(cliente, "/resumenes-quechua?ubigeo=100601", COORD).json()[0]["validado_por"] == COORD
    assert cliente.post("/resumenes-quechua/999/validar", headers={"X-Usuario": COORD}).status_code == 404


# ================================================================= etiquetas
def test_etiquetas_cubren_los_codigos_de_la_muestra(muestra_real):
    cat = yaml.safe_load((RULES / "etiquetas.yaml").read_text(encoding="utf-8"))["categorias"]
    def faltan(categoria, valores):
        return sorted({str(v) for v in valores if v is not None and v == v} - set(cat[categoria]))
    h, p = muestra_real["ds02_hitos_procedimientos"], muestra_real["ds02_procedimientos"]
    assert faltan("hito", h["hito"]) == []
    assert faltan("responsable", h["responsable"]) == []
    assert faltan("tipo_procedimiento", p["tipo_procedimiento"]) == []
    assert faltan("resultado", p["resultado"]) == []
    assert faltan("estado_expediente", p["estado"]) == []
    assert faltan("etapa", h["etapa"]) == []
    assert faltan("estado_ejecucion", muestra_real["ds04_ejecucion_inversiones"]["estado"]) == []
    assert faltan("fuente_financiamiento", muestra_real["ds03_programa_inversiones"]["fuente_financiamiento"]) == []
    assert faltan("componente", muestra_real["ds03_programa_inversiones"]["componente"]) == []


def test_etiquetas_del_catalogo_y_embudo(cliente):
    cat = get(cliente, "/etiquetas").json()["categorias"]
    emb = yaml.safe_load((RULES / "tablero.yaml").read_text(encoding="utf-8"))["embudo_firmas"]["etapas"]
    assert all(h in cat["hito"] for e in emb for h in e["hitos"])
    roles = yaml.safe_load((RULES / "roles.yaml").read_text(encoding="utf-8"))["roles"]
    assert set(roles) <= set(cat["rol"])
    assert all("_" not in v for c in cat.values() for v in c.values())


def test_etiqueta_por_defecto_sin_guiones():
    from app.vistas.etiquetas import catalogo, etiqueta
    cat = catalogo(RULES / "etiquetas.yaml")
    assert etiqueta(cat, "hito", "memo_gg") == "Memorándum a la Gerencia General"
    assert etiqueta(cat, "hito", "hito_nuevo") == "hito nuevo"
    assert etiqueta(cat, "hito", None) == "—"


# ========================================================= docs/indicadores.md
def test_indicadores_markdown_y_cli(settings, tmp_path, monkeypatch):
    from app import cli
    from app.vistas import indicadores
    from app.vistas.etiquetas import catalogo
    md = indicadores.markdown(tablero.contexto(get_engine(settings.database_url), settings),
                              catalogo(RULES / "etiquetas.yaml"))
    assert "muestra simulada" in md and "2 de 3 expedientes con datos (66,7 %)" in md
    assert "| Revisión periódica de tarifas | 1 | 1 | 100,0 % | 0 |" in md
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    salida = tmp_path / "indicadores.md"
    assert cli.main(["indicadores", "--salida", str(salida)]) == 0
    assert salida.read_text(encoding="utf-8") == md


# ============================================================ Fase 5b
def test_corregir_registro_propuesto_con_motivo_y_bitacora(cliente):
    r = cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": "eps-EPS02"},
                     json={"tipo": "OF", "canal": "correo", "numero": "OF-EP-1", "hito": "elevacion_cd",
                           "fecha_recepcion": "2026-09-15"})
    did = r.json()["id"]
    url = f"/documentos/{did}/corregir"
    assert cliente.post(url, headers={"X-Usuario": ESP}, json={"numero": "OF-EP-2"}).status_code == 422  # sin motivo
    assert cliente.post(url, headers={"X-Usuario": ESP}, json={"motivo": "abc", "numero": "x"}).status_code == 422
    assert cliente.post(url, headers={"X-Usuario": "eps-EPS02"},
                        json={"motivo": "La EPS se corrige sola", "numero": "OF-EP-3"}).status_code == 403
    ok = cliente.post(url, headers={"X-Usuario": ESP},
                      json={"motivo": "El número no coincide con el documento", "numero": "OF-EP-9", "pagina": 2})
    assert ok.status_code == 200 and ok.json()["origen"] == "corregido" and ok.json()["estado_registro"] == "propuesto"
    b = [x for x in get(cliente, "/bitacora", COORD).json() if x["accion"] == "corregir_documento"]
    assert b and b[-1]["motivo"] == "El número no coincide con el documento" and b[-1]["despues"]["numero"] == "OF-EP-9"
    assert cliente.post(f"/documentos/{did}/confirmar", headers={"X-Usuario": ESP}).status_code == 200
    assert cliente.post(url, headers={"X-Usuario": ESP},
                        json={"motivo": "Ya estaba confirmado", "numero": "OF-EP-10"}).status_code == 422
    assert cliente.post("/documentos/9999/corregir", headers={"X-Usuario": ESP},
                        json={"motivo": "No existe este registro", "numero": "x"}).status_code == 404
    assert cliente.post(url, headers={"X-Usuario": ESP}, json={"motivo": "Campos no corregibles"}).status_code == 422


def test_corregir_evento_y_la_carga_no_lo_sobrescribe(settings, cliente):
    (settings.casos_reales_dir / "tacna_cpi_2026.yaml").write_text(
        (Path(get_settings().casos_reales_dir) / "tacna_cpi_2026.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    servicio.seed(settings)
    f = get(cliente, "/expedientes/REAL-TACNA-2026", ESP).json()
    ev = f["eventos"][0]
    r = cliente.post(f"/eventos/{ev['id']}/corregir", headers={"X-Usuario": ESP},
                     json={"motivo": "El oficio dice otro plazo", "dias_dh": 4})
    assert r.status_code == 200 and r.json()["dias_dh"] == 4
    servicio.seed(settings)  # recargar el caso real no deshace la corrección de una persona
    ev2 = next(e for e in get(cliente, "/expedientes/REAL-TACNA-2026", ESP).json()["eventos"] if e["id"] == ev["id"])
    assert ev2["dias_dh"] == 4 and ev2["origen"] == "corregido"


def test_pasos_del_procedimiento(cliente):
    f = get(cliente, "/expedientes/CPI-2026-0004", COORD).json()
    p = f["pasos"]
    assert p["n"] == 7 and p["pasos"][p["actual"]]["clave"] == "consejo" and not p["terminado"]
    assert get(cliente, "/expedientes/RP-2025-0001", COORD).json()["pasos"]["terminado"] is True
    item = next(x for x in get(cliente, "/bandeja", COORD).json()["items"] if x["id_expediente"] == "CPI-2026-0005")
    assert item["pasos"]["pasos"][item["pasos"]["actual"]]["clave"] == "evaluacion"
    assert item["en_pausa"] is True and item["te_toca"] is False
    pp = get(cliente, "/tablero", COORD).json()["por_paso"]
    assert pp["cambio_programa_inversiones"]["total"] == 2
    assert sum(x["n"] for x in pp["cambio_programa_inversiones"]["pasos"]) == 2


def test_ruta_del_dinero_por_eps(cliente):
    r = get(cliente, "/tablero", COORD).json()["ruta_por_eps"]
    eps = {x["cod_eps"]: x for x in r["eps"]}
    assert eps["EPS02"]["programado_vigente"] == 970000.0 and eps["EPS02"]["estado"] == "vencido"
    assert eps["EPS02"]["uso_solicitado"] == 0  # los cambios al programa no se suman como «solicitado»
    assert "no se suman" in r["nota"]


def test_mi_eps_pausa_fondo_y_proyectos(cliente):
    m = get(cliente, "/mi-eps", "eps-EPS02").json()
    assert m["siguiente_accion"]["suspende_plazo"] is True
    rf = m["resumen_fondo"]
    assert set(rf) >= {"programado", "depositado", "autorizado", "usado", "aviso", "definiciones"}
    assert {p["cod_proyecto"] for p in m["proyectos"]} == {"EPS02-P001", "EPS02-P014"}
    assert {c["resultado"] for c in m["concluidos"]} == {"aprobado"}


def test_prechequeo_lista_documentos_de_la_norma(cliente):
    r = cliente.post("/prechequeo/programa-inversiones", headers={"X-Usuario": "eps-EPS02"},
                     json={"cod_eps": "EPS02", "tipo_cambio": "cambio_nombre_94_5", "anio_solicitud": 2026}).json()
    assert r["ruta"] == "solo_comunicacion_art_94"
    assert r["documentos"][0]["fuente"] == "RGT art. 94 (encabezado)"
    assert r["documentos_pendientes"]["pregunta_dre"] == "DRE-27" and "Sunass" in r["decision"]


def test_ubicaciones_mapa_y_etapas_ciudadanas(cliente):
    u = get(cliente, "/publico/ubicaciones").json()
    assert [d["departamento"] for d in u] == ["HUANUCO", "LORETO"]
    assert u[0]["provincias"][0]["distritos"][0]["ubigeo"] == "100601"
    m = get(cliente, "/publico/mapa", params={"departamento": "HUANUCO", "provincia": "LEONCIO PRADO"}).json()
    assert m["tipo"] == "esquemático" and "coordenadas" in m["aviso"]
    obras = m["distritos"][0]["obras"]
    assert {o["cod_proyecto"] for o in obras} == {"EPS02-P001", "EPS02-P014"}
    assert all(o["etapa_ciudadana"]["n"] == 2 for o in obras)  # sin reporte de ejecución en la muestra de prueba
    assert get(cliente, "/publico/mapa", params={"departamento": "X", "provincia": "Y"}).status_code == 404
    loc = get(cliente, "/publico/localidades/100601").json()
    assert [e["n"] for e in loc["etapas"]] == [1, 2, 3, 4, 5, 6]
    assert all(p["etapa_ciudadana"]["n"] < 6 for p in loc["proyectos"])


def test_etapa_ciudadana_nunca_afirma_funcionamiento():
    from app.vistas.ciudadana import etapa_ciudadana
    assert etapa_ciudadana({"estado_ejecucion": "concluido"})["nombre"] == "Terminada"
    assert etapa_ciudadana({"estado_ejecucion": "paralizado"}) | {} == {
        "n": 4, "de": 6, "clave": "en_obra", "nombre": "En obra", "detenida": True, "estado_validacion": "por validar (E-2)"}
    assert etapa_ciudadana({"estado_ejecucion": "expediente_tecnico"})["n"] == 3
    assert etapa_ciudadana({"estado_ejecucion": None})["n"] == 2
