"""Fase 3: expediente vivo, documentos, eventos de plazo, bitácora, casos reales y pre-chequeo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from pathlib import Path

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import insert, text

from app import servicio
from app.config import Settings, get_settings
from app.db import bitacora as tabla_bitacora
from app.db import get_engine
from app.expediente import bitacora, casos_reales
from app.expediente.documentos import (
    ErrorRegistro, confirmar_documento, insertar_evento, registrar_documento, registrar_evento,
)
from app.expediente.prechequeo import CONSEJO_DIRECTIVO, NO_DETERMINABLE, SOLO_COMUNICACION, Entrada, catalogo_desde, prechequear
from app.expediente.usuarios import ErrorPermiso, usuarios_desde
from app.main import app
from tests.conftest import escribir_csvs

RULES = get_settings().rules_dir
# Rastros de un bloque de firma digital: «(firm|vis)ado por», «motivo: firma», cargo del firmante, RUC de la FAU.
FIRMAS = re.compile(r"(?i)\b(firm|vis)ado\s+por\b|motivo:\s*firm|presidente\s+ejecutivo|\bFAU\s*\d{11}")
USUARIOS = usuarios_desde(RULES / "usuarios_demo.yaml")
ESP, EPS02, LECTURA = USUARIOS["esp-srt-01"], USUARIOS["eps-02"], USUARIOS["area-01"]


def _hitos_cpi(exp="CPI-2026-0004"):
    base = [("solicitud", "2026-07-27", "2026-07-27", "True", ""),
            ("derivacion", "2026-07-27", "2026-07-30", "True", ""),
            ("oficio_informacion", "2026-07-30", "2026-08-19", "True", "OF-2026-0018"),
            ("informacion_ep", "2026-08-19", "2026-08-28", "False", ""),
            ("memo_gg", "2026-08-28", "2026-09-11", "True", "MEM-2026-0007"),
            ("elevacion_cd", "2026-09-11", "", "True", "")]
    return [{"id_expediente": exp, "nro_hito": str(i + 1), "etapa": "unica", "plazo_etapa_dh": "30", "hito": h,
             "responsable": "EP" if c == "False" else "SRT", "fecha_inicio": a, "fecha_fin": b, "cuenta_plazo": c,
             "documento": d} for i, (h, a, b, c, d) in enumerate(base)]


@pytest.fixture
def settings(tmp_path):
    data = escribir_csvs(tmp_path / "data", {
        "ds01_catalogo_eps": [{"cod_eps": "EPS02", "nombre_eps": "EPS Demo"}],
        "ds02_procedimientos": [
            {"id_expediente": "CPI-2026-0004", "cod_eps": "EPS02", "tipo_procedimiento": "cambio_programa_inversiones",
             "base_normativa": "RGT art. 93", "fecha_inicio": "2026-07-27", "plazo_maximo_dh": "30",
             "dias_suspension_dh": "7", "dias_habiles_sunass": "37", "fecha_limite": "2026-09-21", "estado": "en_tramite",
             "hito_actual": "elevacion_cd", "responsable_actual": "GG", "cod_proyecto": "EPS02-P014",
             "monto_solicitado": "159441.32"},
            {"id_expediente": "CPI-2026-0003", "cod_eps": "EPS08", "tipo_procedimiento": "cambio_programa_inversiones",
             "fecha_inicio": "2026-09-07", "plazo_maximo_dh": "30", "estado": "en_tramite"},
        ],
        "ds02_hitos_procedimientos": _hitos_cpi(),
        "ds03_programa_inversiones": [
            {"cod_eps": "EPS02", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "EPS02-P014",
             "nombre_proyecto": "Medidores", "localidad": "Tingo María", "meta_asociada": "MG09", "anio": str(a),
             "monto_programado_original": m, "monto_programado_vigente": m} for a, m in [(2026, "70000.00"), (2027, "69000.00")]
        ] + [{"cod_eps": "EPS02", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "EPS02-P001",
              "anio": "2026", "monto_programado_original": "861000.00", "monto_programado_vigente": "900000.00",
              "id_expediente_modificacion": "CPI-2025-0009"}],
    })
    publico = tmp_path / "casos"
    publico.mkdir()
    (publico / "tacna_cpi_2026.yaml").write_text(
        (Path(get_settings().casos_reales_dir) / "tacna_cpi_2026.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    privado = tmp_path / "privado"
    privado.mkdir()
    return Settings(data_dir=data, rules_dir=RULES, reportes_dir=tmp_path / "reportes", casos_reales_dir=publico,
                    casos_reales_privados_dir=privado, database_url=f"sqlite:///{(tmp_path / 'f3.db').as_posix()}")


def _privado(settings):
    """Detalle privado de prueba: lo mínimo que agregan los oficios intermedios."""
    (settings.casos_reales_privados_dir / "tacna_cpi_2026_detalle.yaml").write_text(yaml.safe_dump({
        "caso": "TACNA-CPI-2026",
        "documentos": [{"clave": "TACNA:INF-031-2026", "fecha_emision": date(2026, 8, 24)},
                       {"clave": "TACNA:NO-EXISTE", "fecha_emision": date(2026, 1, 1)}],
        "eventos": [{"clave": "TACNA:PRORROGA-OF-00162", "dias_dh": 2, "fuente_detalle": "Oficio 162, pág. 1"}],
        "hitos": [{"nro": 4, "fin": date(2026, 8, 24)}, {"nro": 5, "inicio": date(2026, 8, 24)}],
    }, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def cliente(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


# ================================================================== bitácora
def test_bitacora_encadenada_y_solo_agregar(settings):
    servicio.seed(settings)
    e = get_engine(settings.database_url)
    with e.begin() as cx:
        bitacora.registrar(cx, ESP, "prueba", "x", "1", id_expediente="CPI-2026-0004", despues={"a": 1})
        bitacora.registrar(cx, ESP, "prueba", "x", "2", id_expediente="CPI-2026-0004", antes={"a": 1}, despues={"a": 2})
    v = bitacora.verificar(e)
    assert v["integra"] and v["entradas"] >= 2
    with pytest.raises(Exception, match="solo agregado"):
        with e.begin() as cx:
            cx.execute(text("UPDATE bitacora SET motivo = 'cambio' WHERE id = 1"))
    with pytest.raises(Exception, match="solo agregado"):
        with e.begin() as cx:
            cx.execute(text("DELETE FROM bitacora"))
    # Una entrada insertada por fuera de la API rompe la cadena y se detecta.
    with e.begin() as cx:
        cx.execute(insert(tabla_bitacora).values(cuando=date(2026, 1, 1), usuario="intruso", rol="x", accion="x",
                                                 entidad="x", entidad_id="9", hash_anterior="0" * 64, hash="f" * 64))
    v = bitacora.verificar(e)
    assert not v["integra"] and v["primera_alterada"] == v["entradas"]


# ================================================================ documentos
def test_registro_confirmacion_y_permisos(settings):
    servicio.seed(settings)
    e = get_engine(settings.database_url)
    doc = {"id_expediente": "CPI-2026-0004", "tipo": "CORREO", "canal": "correo", "numero": "Correo (demo)",
           "hito": "elevacion_cd", "fecha_recepcion": date(2026, 9, 15)}
    rid = registrar_documento(e, ESP, doc, "EPS02")
    with pytest.raises(ErrorRegistro, match="Ya existe"):
        registrar_documento(e, ESP, doc, "EPS02")
    with pytest.raises(ErrorRegistro, match="Canal no válido"):
        registrar_documento(e, ESP, {**doc, "numero": "x", "canal": "paloma"}, "EPS02")
    with pytest.raises(ErrorRegistro, match="al menos una fecha"):
        registrar_documento(e, ESP, {**doc, "numero": "y", "fecha_recepcion": None}, "EPS02")
    with pytest.raises(ErrorPermiso, match="Falta identificar"):
        registrar_documento(e, None, {**doc, "numero": "z"}, "EPS02")
    with pytest.raises(ErrorPermiso, match="no tiene el permiso"):
        registrar_documento(e, LECTURA, {**doc, "numero": "z"}, "EPS02")
    with pytest.raises(ErrorPermiso, match="EPS02 no puede"):
        registrar_documento(e, EPS02, {**doc, "id_expediente": "CPI-2026-0003", "numero": "z"}, "EPS08")
    propuesto = registrar_documento(e, EPS02, {**doc, "numero": "Oficio de la EPS", "canal": "enlace_externo"}, "EPS02")
    with pytest.raises(ErrorPermiso):
        confirmar_documento(e, EPS02, propuesto)
    conf = confirmar_documento(e, ESP, propuesto)
    assert conf["estado_registro"] == "confirmado" and conf["confirmado_por"] == "esp-srt-01"
    with pytest.raises(ErrorRegistro, match="ya estaba confirmado"):
        confirmar_documento(e, ESP, rid)
    with pytest.raises(LookupError):
        confirmar_documento(e, ESP, 9999)
    acciones = [b["accion"] for b in bitacora.leer(e, id_expediente="CPI-2026-0004")]
    assert acciones.count("registrar_documento") == 2 and "confirmar_documento" in acciones
    assert bitacora.verificar(e)["integra"]


def test_eventos_cambian_el_reloj_del_oficio(settings, cliente):
    servicio.seed(settings)
    e = get_engine(settings.database_url)
    with pytest.raises(ErrorRegistro, match="necesita los días"):
        registrar_evento(e, ESP, {"id_expediente": "CPI-2026-0004", "hito": "informacion_ep", "tipo": "plazo_oficio"},
                         "EPS02")
    with pytest.raises(ErrorRegistro, match="Tipo de evento"):
        registrar_evento(e, ESP, {"id_expediente": "CPI-2026-0004", "hito": "informacion_ep", "tipo": "otro"}, "EPS02")
    registrar_evento(e, ESP, {"id_expediente": "CPI-2026-0004", "hito": "informacion_ep", "tipo": "plazo_oficio",
                              "dias_dh": 5}, "EPS02")
    oficio = next(a for a in cliente.get("/expedientes/CPI-2026-0004").json()["relojes"] if a["reloj"] == "oficio")
    # 2026-08-19 + 5 DH = 2026-08-26; la EP respondió el 2026-08-28: fuera de plazo.
    assert oficio["estado"] == "incumplido" and oficio["fecha_limite"] == "2026-08-26"
    assert "fijados por" in oficio["mensaje"]
    # La EPS no registra prórrogas (las concede Sunass): solo su solicitud, como documento.
    with pytest.raises(ErrorPermiso, match="registrar_evento"):
        registrar_evento(e, EPS02, {"id_expediente": "CPI-2026-0004", "hito": "informacion_ep", "tipo": "prorroga",
                                    "dias_dh": 2}, "EPS02")
    # Una prórroga transcrita (propuesta) no cambia el reloj hasta que una persona la confirma.
    with e.begin() as cx:
        insertar_evento(cx, casos_reales.SISTEMA, {"id_expediente": "CPI-2026-0004", "hito": "informacion_ep",
                                                   "tipo": "prorroga", "dias_dh": 2, "fecha_solicitud": date(2026, 8, 25)},
                        origen="transcrito_ia", naturaleza="real", estado="propuesto")
    oficio = next(a for a in cliente.get("/expedientes/CPI-2026-0004").json()["relojes"] if a["reloj"] == "oficio")
    assert oficio["estado"] == "incumplido"
    ev = cliente.get("/expedientes/CPI-2026-0004").json()["eventos"][-1]
    assert cliente.post(f"/eventos/{ev['id']}/confirmar", headers={"X-Usuario": "esp-srt-01"}).status_code == 200
    oficio = next(a for a in cliente.get("/expedientes/CPI-2026-0004").json()["relojes"] if a["reloj"] == "oficio")
    assert oficio["estado"] == "cumplido" and oficio["fecha_limite"] == "2026-08-28"


# ============================================================ casos reales
def test_caso_tacna_solo_parte_publica(settings, cliente):
    r = servicio.seed(settings)
    # 9 documentos + el plazo fijado por el Oficio 156 + la prórroga (sin días en la parte pública).
    assert r.casos_reales == {"casos": 1, "con_detalle_privado": 0, "insertados": 11, "actualizados": 0,
                              "confirmados_intactos": 0}
    f = cliente.get("/expedientes/REAL-TACNA-2026").json()
    assert f["expediente"]["naturaleza"] == "real" and not f["expediente"]["con_detalle_privado"]
    (r0,) = f["relojes"]
    assert r0["estado"] == "no_calculable" and "falta que una persona confirme" in r0["mensaje"]
    assert all(h["evidencia"]["estado"] == "registro propuesto, falta confirmar" for h in f["linea_de_tiempo"])
    texto = yaml.safe_dump(f, allow_unicode=True)
    # Sin nombres de personas: ningún bloque de firma digital ni cargo de firmante transcrito.
    # Los patrones se escriben como expresiones (sin la frase literal) para que el propio test
    # no aparezca como un bloque de firma en las auditorías del repositorio.
    assert not FIRMAS.search(texto), FIRMAS.search(texto)
    # Al confirmar todo con solo la parte pública, el reloj dice qué falta (no estima).
    H = {"X-Usuario": "esp-srt-01"}
    for d in f["documentos"]:
        cliente.post(f"/documentos/{d['id']}/confirmar", headers=H)
    for ev in f["eventos"]:
        cliente.post(f"/eventos/{ev['id']}/confirmar", headers=H)
    f = cliente.get("/expedientes/REAL-TACNA-2026").json()
    norm = next(a for a in f["relojes"] if a["reloj"] == "normativo")
    assert norm["estado"] == "no_calculable" and "hito 5" in norm["mensaje"]
    oficio = next(a for a in f["relojes"] if a["reloj"] == "oficio")
    assert oficio["estado"] == "no_calculable" and "no se conoce su plazo" in oficio["mensaje"]
    assert next(h for h in f["linea_de_tiempo"] if h["hito"] == "solicitud")["evidencia"]["estado"] == "documento registrado"


def test_caso_tacna_con_detalle_privado(settings, cliente):
    _privado(settings)
    r = servicio.seed(settings)
    assert r.casos_reales["con_detalle_privado"] == 1 and r.casos_reales["insertados"] == 11
    f = cliente.get("/expedientes/REAL-TACNA-2026").json()
    assert "documento TACNA:INF-031-2026: fecha_emision" in f["expediente"]["campos_privados"]
    H = {"X-Usuario": "coord-srt-01"}
    for d in f["documentos"]:
        assert cliente.post(f"/documentos/{d['id']}/confirmar", headers=H).status_code == 200
    for ev in f["eventos"]:
        assert cliente.post(f"/eventos/{ev['id']}/confirmar", headers=H).status_code == 200
    f = cliente.get("/expedientes/REAL-TACNA-2026").json()
    relojes = {a["reloj"]: a for a in f["relojes"] if a.get("regla_id") != "PLZ-I-CPI-BLOQUE-24"}
    assert relojes["normativo"]["estado"] == "cumplido" and relojes["normativo"]["fecha_limite"] == "2026-09-08"
    # Oficio 156: 3 DH desde el 11-08 (vencía el 14-08) + prórroga de 2 DH (18-08); la EP respondió el 14-08.
    assert relojes["oficio"]["estado"] == "cumplido" and relojes["oficio"]["fecha_limite"] == "2026-08-18"
    # Un segundo seed no duplica ni toca lo confirmado.
    r2 = servicio.seed(settings)
    assert r2.casos_reales["insertados"] == 0 and r2.casos_reales["confirmados_intactos"] == 11
    assert bitacora.verificar(get_engine(settings.database_url))["integra"]


def test_transcripcion_propuesta_se_actualiza(settings):
    servicio.seed(settings)
    _privado(settings)
    r = servicio.seed(settings)
    # La prórroga ya existía (sin días): ahora se completa con los días de la parte privada.
    assert r.casos_reales["actualizados"] >= 2 and r.casos_reales["insertados"] == 0
    acciones = [b["accion"] for b in bitacora.leer(get_engine(settings.database_url), id_expediente="REAL-TACNA-2026")]
    assert "actualizar_transcripcion" in acciones


def test_carga_de_casos_combina_sin_crear(settings):
    _privado(settings)
    casos = casos_reales.cargar_casos(settings.casos_reales_dir, settings.casos_reales_privados_dir)
    c = casos["REAL-TACNA-2026"]
    assert c.con_detalle_privado and all("NO-EXISTE" not in x for x in c.campos_privados)
    assert len(c.datos["documentos"]) == 9


# ================================================================ ficha y API
def test_ficha_ds02_pasaporte_y_proyectos(settings, cliente):
    assert cliente.get("/expedientes").status_code == 404  # sin carga
    servicio.seed(settings)
    lista = cliente.get("/expedientes").json()
    assert lista[0]["id_expediente"] == "REAL-TACNA-2026" and lista[0]["naturaleza"] == "real"
    assert [x["id_expediente"] for x in cliente.get("/expedientes", params={"cod_eps": "EPS02"}).json()] == ["CPI-2026-0004"]
    assert cliente.get("/expedientes", params={"tipo": "revision_periodica"}).json() == []
    f = cliente.get("/expedientes/CPI-2026-0004").json()
    ev = {h["hito"]: h["evidencia"]["estado"] for h in f["linea_de_tiempo"]}
    assert ev["solicitud"] == "declarado, no verificado" and ev["oficio_informacion"] == "código en DS02, sin archivo"
    assert next(h for h in f["linea_de_tiempo"] if h["hito"] == "elevacion_cd")["estado"] == "en curso"
    assert f["proyectos"][0]["meta_asociada"] == "MG09" and f["proyectos"][0]["naturaleza_poblacion"] == "estimado"
    norm = next(a for a in f["relojes"] if a["reloj"] == "normativo" and a["hito"] is None)
    assert norm["estado"] == "vencido"
    assert f["prechequeo"]["ruta"] == SOLO_COMUNICACION and "art. 92" in f["prechequeo"]["advertencias"][0]
    assert cliente.get("/expedientes/NO-EXISTE").status_code == 404
    r = cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": "esp-srt-01"},
                     json={"tipo": "CORREO", "canal": "correo", "hito": "elevacion_cd", "fecha_recepcion": "2026-09-15"})
    assert r.status_code == 201
    f = cliente.get("/expedientes/CPI-2026-0004").json()
    assert next(h for h in f["linea_de_tiempo"] if h["hito"] == "elevacion_cd")["evidencia"]["estado"] == "documento registrado"
    assert cliente.post("/expedientes/CPI-2026-0004/documentos", json={"tipo": "OF", "canal": "correo",
                                                                       "fecha_recepcion": "2026-09-15"}).status_code == 401
    assert cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": "nadie"},
                        json={"tipo": "OF", "canal": "correo", "fecha_recepcion": "2026-09-15"}).status_code == 401
    assert cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": "area-01"},
                        json={"tipo": "OF", "canal": "correo", "fecha_recepcion": "2026-09-15"}).status_code == 403
    assert cliente.post("/expedientes/CPI-2026-0004/documentos", headers={"X-Usuario": "esp-srt-01"},
                        json={"tipo": "XX", "canal": "correo", "fecha_recepcion": "2026-09-15"}).status_code == 422
    assert cliente.post("/expedientes/NO-EXISTE/documentos", headers={"X-Usuario": "esp-srt-01"},
                        json={"tipo": "OF", "canal": "correo", "fecha_recepcion": "2026-09-15"}).status_code == 404
    assert cliente.post("/documentos/9999/confirmar", headers={"X-Usuario": "esp-srt-01"}).status_code == 404
    assert cliente.post("/expedientes/REAL-TACNA-2026/eventos", headers={"X-Usuario": "eps-02"},
                        json={"hito": "informacion_ep", "tipo": "prorroga", "dias_dh": 1}).status_code == 403
    assert len(cliente.get("/usuarios-demo").json()) == 6
    assert cliente.get("/bitacora", params={"id_expediente": "CPI-2026-0004"}).json()[0]["accion"] == "registrar_documento"
    assert cliente.get("/bitacora/verificacion").json()["integra"]


# ================================================================== pre-chequeo
def _ds03():
    filas = [
        {"cod_eps": "EPS99", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "P1",
         "nombre_proyecto": "Uno", "meta_asociada": None, "anio": 2026, "monto_programado_original": Decimal("1000000"),
         "monto_programado_vigente": Decimal("1000000"), "id_expediente_modificacion": None, "_fila": 2},
        {"cod_eps": "EPS99", "periodo_regulatorio": "2025-2029", "tipo_periodo": "vigente", "cod_proyecto": "P2",
         "nombre_proyecto": "Dos", "meta_asociada": "MG01", "anio": 2027, "monto_programado_original": Decimal("9000000"),
         "monto_programado_vigente": Decimal("9500000"), "id_expediente_modificacion": "CPI-2025-0001", "_fila": 3},
    ]
    return pd.DataFrame(filas, dtype=object)


CAT = catalogo_desde(RULES / "prechequeo_pi.yaml")


@pytest.mark.parametrize("entrada,ruta,texto", [
    (dict(tipo_cambio="incremento_monto", cod_proyecto="P1", monto_nuevo_pendiente=Decimal("1300000")),
     SOLO_COMUNICACION, "no superan el 10 %"),            # 500 000 previos + 300 000 = 8 % de 10 000 000
    (dict(tipo_cambio="incremento_monto", cod_proyecto="P1", monto_nuevo_pendiente=Decimal("1600000")),
     CONSEJO_DIRECTIVO, "superan el 10 %"),               # 1 100 000 = 11 %
    (dict(tipo_cambio="incremento_monto", cod_proyecto="P1", monto_nuevo_pendiente=Decimal("900000")),
     NO_DETERMINABLE, "no supera el programado"),
    (dict(tipo_cambio="incremento_monto", cod_proyecto="P9", monto_nuevo_pendiente=Decimal("1")),
     NO_DETERMINABLE, "falta el proyecto P9"),
    (dict(tipo_cambio="sustitucion_93_1_3", costo_proyecto_sustituto=Decimal("900000")),
     SOLO_COMUNICACION, "suma de sustituciones"),          # tope min(1 000 000; 5 000 000)
    (dict(tipo_cambio="sustitucion_93_1_4", costo_proyecto_sustituto=Decimal("1200000")),
     CONSEJO_DIRECTIVO, "supera el menor valor"),
    (dict(tipo_cambio="sustitucion_93_1_3", costo_proyecto_sustituto=Decimal("900000"), suma_sustituciones_previas=None),
     NO_DETERMINABLE, "no puedo comprobar"),
    (dict(tipo_cambio="sustitucion_93_1_3"), NO_DETERMINABLE, "falta el costo"),
    (dict(tipo_cambio="recursos_liberados_93_2"), CONSEJO_DIRECTIVO, "RCD 032-2026"),
    (dict(tipo_cambio="reprogramacion_94_4"), SOLO_COMUNICACION, "montos anuales"),
    (dict(tipo_cambio="otro_93_1"), CONSEJO_DIRECTIVO, "Consejo Directivo"),
])
def test_prechequeo_ramas(entrada, ruta, texto):
    previas = entrada.pop("suma_sustituciones_previas", Decimal("50000"))
    e = Entrada(cod_eps="EPS99", anio_solicitud=2026, suma_sustituciones_previas=previas, **entrada)
    r = prechequear(_ds03(), e, CAT)
    assert r.ruta == ruta, r.explicacion
    assert texto in r.explicacion + " ".join(r.faltantes) + " ".join(t["ubicacion"] for t in r.texto_citado)
    assert r.estado_validacion == "por validar" and r.texto_citado or r.ruta == NO_DETERMINABLE
    assert any("ORIGINAL" in s for s in r.supuestos)


def test_prechequeo_suma_de_sustituciones_supera_y_advertencia_de_metas():
    e = Entrada(cod_eps="EPS99", anio_solicitud=2026, tipo_cambio="sustitucion_93_1_3",
                costo_proyecto_sustituto=Decimal("900000"), suma_sustituciones_previas=Decimal("200000"))
    assert prechequear(_ds03(), e, CAT).ruta == CONSEJO_DIRECTIVO
    e2 = Entrada(cod_eps="EPS99", anio_solicitud=2027, tipo_cambio="incremento_monto", cod_proyecto="P2",
                 monto_nuevo_pendiente=Decimal("9600000"), id_expediente="CPI-2025-0001")
    r = prechequear(_ds03(), e2, CAT)
    assert "MG01" in r.advertencias[0]
    assert r.calculos["monto_pendiente_programado"] == "9000000"  # su propia modificación no cuenta como previa
    sin = prechequear(_ds03(), Entrada(cod_eps="EPS00", anio_solicitud=2026, tipo_cambio="otro_93_1"), CAT)
    assert sin.ruta == NO_DETERMINABLE
    with pytest.raises(ValueError):
        prechequear(_ds03(), Entrada(cod_eps="EPS99", anio_solicitud=2026, tipo_cambio="magia"), CAT)


def test_api_prechequeo(settings, cliente):
    servicio.seed(settings)
    assert "incremento_monto" in cliente.get("/prechequeo/tipos").json()
    r = cliente.post("/prechequeo/programa-inversiones", json={
        "cod_eps": "EPS02", "tipo_cambio": "incremento_monto", "anio_solicitud": 2026, "cod_proyecto": "EPS02-P014",
        "monto_nuevo_pendiente": 159441.32})
    assert r.status_code == 200 and r.json()["ruta"] == SOLO_COMUNICACION
    assert cliente.post("/prechequeo/programa-inversiones", json={
        "cod_eps": "EPS02", "tipo_cambio": "x", "anio_solicitud": 2026}).status_code == 422


def test_patron_de_firmas_detecta_bloques():
    # Ejemplos armados por partes: el archivo no contiene la frase literal de un bloque de firma.
    assert FIRMAS.search("Fir" + "mado por: X")
    assert FIRMAS.search("Vis" + "ado  por Y")
    assert FIRMAS.search("Mot" + "ivo: Fir" + "ma Digital")
    assert FIRMAS.search("FA" + "U 20158219655")
    assert not FIRMAS.search("Consejo Directivo aprueba la resolución")
