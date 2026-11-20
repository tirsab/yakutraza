"""Fase 6: extracción asistida con IA. Solo texto SINTÉTICO: ningún texto de oficios reales ni nombres de personas.

Los «nombres» de estas pruebas son marcadores artificiales (Nombrea, Apellidob…), no personas.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app import servicio
from app.config import Settings, get_settings
from app.extraccion import evaluacion, privacidad
from app.extraccion import servicio as sv
from app.extraccion.anonimizar import Anonimizador, lista_privada, restos_de_firma
from app.extraccion.extraer import ESQUEMA, SISTEMA, leer_fecha, mensaje_usuario, validar
from app.extraccion.proveedores import Anthropic, ErrorProveedor, Ollama, crear
from app.extraccion.texto import leer_pdf, limpiar
from app.main import app
from tests.pdf_sintetico import escribir_pdf
from tests.test_vistas import RULES, _muestra

COORD = "coord-srt-01"

# Documento sintético (inventado para las pruebas).
PAG1 = ["SUPERINTENDENCIA SINTETICA DE PRUEBA",
        "OFICIO N.° 999-2099-PRUEBA",
        "Lugar de prueba, 14 de agosto de 2099",
        "Asunto: plazo de prueba",
        "Se otorga una prórroga de dos (2) días hábiles para enviar lo pedido.",
        "Se requiere remitir el anexo de prueba.",
        "Atentamente",
        "NOMBREA APELLIDOB"]
PAG2 = ["SUPERINTENDENCIA SINTETICA DE PRUEBA",
        "Contacto: Ing. Nombrea Apellidob Apellidoc, DNI 12345678, correo ejemplo@ejemplo.pe, teléfono 987 654 321.",
        "Texto de relleno para que la página tenga suficientes caracteres y se considere procesable por el lector."]


class Falso:
    """Proveedor falso: devuelve una respuesta fija (o la que se le dé) y guarda lo que recibió."""
    nombre = "falso"
    modelo = "modelo-de-prueba"

    def __init__(self, respuesta=None):
        self.respuesta = respuesta
        self.recibido = None

    def extraer(self, sistema, usuario, esquema):
        self.recibido = usuario
        return self.respuesta or {
            "numero_documento": {"valor": "OFICIO N.° 999-2099-PRUEBA", "cita": "OFICIO N.° 999-2099-PRUEBA", "pagina": 1},
            "fecha": {"valor": "2099-08-14", "cita": "14 de agosto de 2099", "pagina": 1},
            "remitente": {"valor": None, "cita": None, "pagina": None},
            "plazo": {"dias_habiles": 2, "tipo": "prorroga", "cita": "prórroga de dos (2) días hábiles", "pagina": 1},
            "requerimientos": [{"texto": "Anexo", "cita": "remitir el anexo de prueba", "pagina": 1},
                               {"texto": "Inventado", "cita": "texto que no existe", "pagina": 1}],
        }


# ================================================================ texto
def test_leer_pdf_y_limpiar(tmp_path):
    pdf = escribir_pdf(tmp_path / "a.pdf", [PAG1, PAG2, []])
    d = leer_pdf(pdf)
    assert len(d.paginas) == 3 and d.procesable and d.requiere_ocr == [3]
    limpias = limpiar(d.paginas[:2])
    # El encabezado que se repite en todas las páginas se quita.
    assert all("SUPERINTENDENCIA SINTETICA" not in p for p in limpias)
    assert "OFICIO N.° 999-2099-PRUEBA" in limpias[0]


def test_limpiar_firma_y_palabras_cortadas():
    p = limpiar(["Firmado digitalmente por alguien\nMotivo: Soy el autor del documento\nSe otorga un plazo de diez días hábi-\nles."])[0]
    assert "Firmado" not in p and "Motivo" not in p
    assert "hábiles" in p


# ================================================================ anonimizar
def test_anonimizar_lista_privada_tratamientos_firma_y_datos():
    an = Anonimizador(["Nombrea Apellidob Apellidoc"])
    r = an.anonimizar(["\n".join(PAG1), "\n".join(PAG2).replace("Nombrea Apellidob", "NOMBREA APELLIDOB")])
    texto = " ".join(r.paginas)
    assert "Nombrea" not in texto and "NOMBREA" not in texto and "Apellidob" not in texto.title()
    assert "[PERSONA_" in texto
    assert "[DNI]" in texto and "[CORREO]" in texto and "[TELÉFONO]" in texto
    assert "12345678" not in texto and "ejemplo@ejemplo.pe" not in texto
    assert r.seguro and r.pendientes == []
    assert r.reemplazos["dni"] == 1 and r.reemplazos["correo"] == 1


def test_anonimizar_sin_tildes_ni_mayusculas():
    r = Anonimizador(["Ñandú Pérez"]).anonimizar(["Firma: ÑANDU PEREZ y también ñandú pérez."])
    assert "ÑANDU" not in r.paginas[0] and "pérez" not in r.paginas[0]
    assert r.paginas[0].count("[PERSONA_1]") == 2


def test_tratamiento_con_cargo_no_es_persona():
    r = Anonimizador().anonimizar(["El Sr. GERENTE GENERAL de la EPS."])
    assert "GERENTE GENERAL" in r.paginas[0]


# Nombres visiblemente inventados (ninguno es de una persona real).
MEMO_FICTICIO = """MEMORANDO N.° 999-2099-PRUEBA
PARA : FICTICIO PRUEBAUNO INVENTADO
Gerente General
DE : Ficticia Pruebados Inventada
Directora de Regulación Tarifaria
A : Dirección de Regulación Tarifaria
Señora:
FICTICIA PRUEBASEIS INVENTADA
Lima, 28 de agosto de 2099"""


def test_anonimizar_cabeceras_para_de_y_senora():
    r = Anonimizador().anonimizar([MEMO_FICTICIO])
    t = r.paginas[0]
    assert "PRUEBAUNO" not in t and "Pruebados" not in t and "PRUEBASEIS" not in t
    assert "PARA : [PERSONA_1]" in t and "DE : [PERSONA_2]" in t
    # Los cargos, las oficinas y la fecha no se tocan.
    assert "Gerente General" in t and "Directora de Regulación Tarifaria" in t
    assert "A : Dirección de Regulación Tarifaria" in t and "Lima, 28 de agosto de 2099" in t
    assert r.reemplazos["cabecera"] == 3 and r.seguro


def test_anonimizar_cabecera_con_nombre_en_la_linea_siguiente():
    r = Anonimizador().anonimizar(["PARA :\nFICTICIO PRUEBASIETE INVENTADO\nJefe de la Oficina"])
    assert "PRUEBASIETE" not in r.paginas[0] and "[PERSONA_1]" in r.paginas[0]


def test_anonimizar_sellos_de_firma_con_fecha_y_hora():
    sello = "FICTICIO PRUEBATRES INVENTADO23/09/2099 17:09:03 "
    r = Anonimizador().anonimizar([sello * 3 + "\nFicticia Pruebaocho\n01/09/2099 16:11:54"])
    t = r.paginas[0]
    assert "PRUEBATRES" not in t and "Pruebaocho" not in t
    assert t.count("[PERSONA_1]") == 3 and "23/09/2099 17:09:03" in t
    assert r.restos == 0 and r.seguro


def test_anonimizar_firmado_digitalmente_y_bloque_de_firma():
    r = Anonimizador().anonimizar(["Firmado digitalmente por: FICTICIO PRUEBACINCO INVENTADO\n"
                                   "<Firmado digitalmente>\nFicticia Pruebanueve Inventada\n\n"
                                   "FICTICIO PRUEBADIEZ INVENTADO\nGerente General"])
    t = r.paginas[0]
    assert "PRUEBACINCO" not in t and "Pruebanueve" not in t and "PRUEBADIEZ" not in t
    assert "Gerente General" in t


def test_anonimizar_firmantes_despues_de_registrese():
    texto = ("Regístrese y comuníquese.\n\n\nFicticio PRUEBACUATRO INVENTADO\nPresidente Ejecutivo\n"
             "EXPOSICIÓN DE MOTIVOS\nEMAPA PASCO S.A.\nANEXO N° 1\nFicticio Despuesdelanexo Inventado")
    r = Anonimizador().anonimizar([texto])
    t = r.paginas[0]
    assert "PRUEBACUATRO" not in t and "[PERSONA_1]" in t
    # Cargos, títulos y empresas se conservan; después del anexo ya no se buscan firmantes.
    assert "Presidente Ejecutivo" in t and "EXPOSICIÓN DE MOTIVOS" in t and "EMAPA PASCO S.A." in t
    assert "Despuesdelanexo" in t
    assert r.reemplazos["firmante"] == 1


def test_sello_que_queda_hace_inseguro_el_documento():
    assert restos_de_firma("FICTICIO PRUEBAONCE INVENTADO23/09/2099 17:09:03") == 1
    assert restos_de_firma("[PERSONA_1] 23/09/2099 17:09:03") == 0
    assert restos_de_firma("CUADRO N° 1: TOTAL 12 527 medidores") == 0
    from app.extraccion.anonimizar import Resultado
    assert not Resultado(paginas=[], restos=1).seguro


def test_rastros_por_patron_en_textos_del_repositorio(tmp_path):
    limpio = tmp_path / "limpio.md"
    limpio.write_text("# Caso real\nRCD 032-2026, pág. 4: 19 935 medidores. PARA : [PERSONA_1]\n"
                      "Pruebas: FICTICIO PRUEBATRES INVENTADO23/09/2099 17:09:03\n", encoding="utf-8")
    sucio = tmp_path / "sucio.yaml"
    # Se arma por partes para que este archivo de pruebas no tenga, él mismo, los patrones que busca.
    sucio.write_text("PA" + "RA : Zeta Omega Lambda\n" + "ZETA OMEGA LAMBDA" + "23/09/2099 17:09:03\n"
                     "contacto: alguien" + "@empresa.pe\nhttps://drive." + "google.com/drive/folders/abc\n",
                     encoding="utf-8")
    h = privacidad.rastros_en_repo([limpio, sucio])
    assert {x.tipo for x in h if x.archivo.endswith("sucio.yaml")} == {
        "sello_de_firma", "cabecera_con_nombre", "correo", "enlace_privado"}
    assert not [x for x in h if x.archivo.endswith("limpio.md")]


def test_repositorio_sin_rastros_de_oficios():
    """Ningún archivo versionado tiene sellos de firma, cabeceras con nombre, correos ni enlaces privados."""
    assert privacidad.rastros_en_repo() == []


def test_lista_privada(tmp_path):
    f = tmp_path / "nombres_a_ocultar.txt"
    f.write_text("# comentario\nNombrea Apellidob\n\n", encoding="utf-8")
    assert lista_privada(f) == ["Nombrea Apellidob"]
    assert lista_privada(tmp_path / "no-existe.txt") == [] and lista_privada(None) == []


# ================================================================ validar
PAGINAS = ["OFICIO N.° 999-2099-PRUEBA\nLugar, 14 de agosto de 2099\nSe otorga una prórroga de dos (2) días h ábiles.",
           "Página dos."]


def test_validar_conserva_citas_literales_y_descarta_el_resto():
    r = validar({
        "numero_documento": {"valor": "OFICIO N.° 999-2099-PRUEBA", "cita": "OFICIO N.° 999-2099-PRUEBA", "pagina": 1},
        "fecha": {"valor": "2099-08-14", "cita": "14 de agosto de 2099", "pagina": 1},
        "remitente": {"valor": "Sunass", "cita": "Sunass dispone", "pagina": 1},     # la cita no existe
        "plazo": {"dias_habiles": 2, "tipo": "prorroga", "cita": "prórroga de dos (2) días hábiles", "pagina": 1},
        "requerimientos": [{"texto": "x", "cita": "Página dos.", "pagina": 5}],         # la página no existe
    }, PAGINAS)
    c = r["campos"]
    assert c["numero_documento"]["valor"] == "OFICIO N.° 999-2099-PRUEBA"
    assert c["fecha"]["pagina"] == 1
    # La cita es literal aunque el PDF partió «días h ábiles».
    assert c["plazo"]["dias_habiles"] == 2 and c["plazo"]["tipo"] == "prorroga"
    assert c["remitente"] is None and c["requerimientos"] == []
    motivos = {d["campo"]: d["motivo"] for d in r["descartados"]}
    assert "no aparece literalmente" in motivos["remitente"]
    assert "no existe" in motivos["requerimientos[0]"]


def test_validar_valor_que_no_esta_en_la_cita():
    r = validar({"numero_documento": {"valor": "OFICIO 123", "cita": "OFICIO N.° 999-2099-PRUEBA", "pagina": 1},
                 "plazo": {"dias_habiles": 5, "tipo": None, "cita": "prórroga de dos (2) días", "pagina": 1}}, PAGINAS)
    assert r["campos"]["numero_documento"] is None and r["campos"]["plazo"] is None
    assert {d["motivo"] for d in r["descartados"]} == {"el valor no aparece en la cita", "los días no aparecen en la cita"}


def test_campo_sin_valor_queda_vacio_sin_descartarse():
    r = validar({"fecha": {"valor": None, "cita": None, "pagina": None}}, PAGINAS)
    assert r["campos"]["fecha"] is None and r["descartados"] == []


def test_leer_fecha():
    from datetime import date
    assert leer_fecha("2099-08-14") == date(2099, 8, 14)
    assert leer_fecha("14 de agosto de 2099") == date(2099, 8, 14)
    assert leer_fecha("3 de setiembre del 2099") == date(2099, 9, 3)
    assert leer_fecha("14/08/2099") == date(2099, 8, 14)
    assert leer_fecha("sin fecha") is None and leer_fecha(None) is None


def test_mensaje_numera_las_paginas():
    m = mensaje_usuario(["uno", "dos"])
    assert "=== Página 1 ===" in m and "=== Página 2 ===\ndos" in m


# ================================================================ proveedores
def test_ollama_pide_json_con_el_esquema_y_sin_razonamiento():
    visto = {}

    def responder(req: httpx.Request) -> httpx.Response:
        visto.update(json.loads(req.content))
        return httpx.Response(200, json={"message": {"content": json.dumps({"fecha": None})}})

    o = Ollama("http://ollama.prueba", "modelo-x", cliente=httpx.Client(transport=httpx.MockTransport(responder)))
    assert o.extraer(SISTEMA, "texto", ESQUEMA) == {"fecha": None}
    assert visto["model"] == "modelo-x" and visto["format"] == ESQUEMA and visto["think"] is False
    assert visto["stream"] is False and visto["options"]["temperature"] == 0


@pytest.mark.parametrize("respuesta, mensaje", [
    (httpx.Response(404, json={}), "ollama pull modelo-x"),
    (httpx.Response(500, text="falla"), "Ollama respondió 500"),
    (httpx.Response(200, json={"message": {"content": "no es json"}}), "JSON válido"),
])
def test_ollama_errores_claros(respuesta, mensaje):
    o = Ollama("http://ollama.prueba", "modelo-x", cliente=httpx.Client(transport=httpx.MockTransport(lambda r: respuesta)))
    with pytest.raises(ErrorProveedor, match=mensaje):
        o.extraer(SISTEMA, "texto", ESQUEMA)


def test_ollama_sin_conexion():
    def caer(req):
        raise httpx.ConnectError("sin conexión", request=req)
    o = Ollama("http://ollama.prueba", "m", cliente=httpx.Client(transport=httpx.MockTransport(caer)))
    with pytest.raises(ErrorProveedor, match="¿Está instalado y abierto?"):
        o.extraer(SISTEMA, "texto", ESQUEMA)


class ClienteAnthropicFalso:
    def __init__(self, respuesta):
        self.llamadas = []
        self.messages = SimpleNamespace(create=self._crear)
        self.respuesta = respuesta

    def _crear(self, **kw):
        self.llamadas.append(kw)
        return self.respuesta


def test_anthropic_salida_estructurada_con_el_esquema():
    c = ClienteAnthropicFalso(SimpleNamespace(stop_reason="end_turn",
                                              content=[SimpleNamespace(type="text", text=json.dumps({"fecha": None}))]))
    a = Anthropic("claude-opus-5-5", cliente=c)
    assert a.extraer(SISTEMA, "texto anonimizado", ESQUEMA) == {"fecha": None}
    kw = c.llamadas[0]
    assert kw["model"] == "claude-opus-5-5" and kw["system"] == SISTEMA
    assert kw["output_config"]["format"] == {"type": "json_schema", "schema": ESQUEMA}
    assert kw["messages"] == [{"role": "user", "content": "texto anonimizado"}]


def test_anthropic_rechazo():
    c = ClienteAnthropicFalso(SimpleNamespace(stop_reason="refusal", content=[]))
    with pytest.raises(ErrorProveedor, match="declinó"):
        Anthropic("claude-opus-5-5", cliente=c).extraer(SISTEMA, "t", ESQUEMA)


def test_crear_proveedor():
    assert crear("ninguno", ollama_url="u", ollama_modelo="m", anthropic_modelo="a") is None
    assert isinstance(crear("ollama", ollama_url="http://x", ollama_modelo="m", anthropic_modelo="a"), Ollama)


# ================================================================ servicio (índice por alias y extracción)
@pytest.fixture
def privado(tmp_path):
    base = tmp_path / "privado"
    escribir_pdf(base / "Tacna documentos" / "b documento.pdf", [PAG1, PAG2])
    escribir_pdf(base / "Tacna documentos" / "A documento.pdf", [["Documento sintético A con texto suficiente para leerlo bien y superar el mínimo de caracteres por página."]])
    escribir_pdf(base / "Otra carpeta" / "c.pdf", [["Sin caso asociado."]])
    return base


@pytest.fixture
def s_ext(tmp_path, privado):
    return Settings(data_dir=tmp_path, rules_dir=RULES, casos_reales_privados_dir=privado,
                    extraccion_dir=tmp_path / "extraccion", database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}")


def test_indice_por_alias_sin_nombres_de_archivo(s_ext):
    docs = sv.indice(s_ext)
    assert [d.alias for d in docs] == ["TACNA-01", "TACNA-02"]          # orden sin distinguir mayúsculas
    assert docs[0].ruta.name == "A documento.pdf"
    publico = json.dumps([d.publico() for d in docs])
    assert "documento" not in publico and ".pdf" not in publico
    assert all(d.id_expediente == "REAL-TACNA-2026" for d in docs)


def test_indice_vacio_sin_parte_privada(s_ext):
    s_ext.casos_reales_privados = False
    assert sv.indice(s_ext) == []
    with pytest.raises(LookupError):
        sv.buscar(s_ext, "TACNA-01")


def test_extraer_anonimiza_valida_y_guarda(s_ext, privado):
    (privado / "nombres_a_ocultar.txt").write_text("Nombrea Apellidob Apellidoc\n", encoding="utf-8")
    p = Falso()
    r = sv.extraer(s_ext, "TACNA-02", proveedor=p)
    # El proveedor solo recibe texto anonimizado.
    assert "Nombrea" not in p.recibido and "NOMBREA" not in p.recibido and "12345678" not in p.recibido
    assert r["campos"]["plazo"]["dias_habiles"] == 2 and r["campos"]["fecha"]["valor"] == "2099-08-14"
    assert [x["texto"] for x in r["campos"]["requerimientos"]] == ["Anexo"]
    assert r["descartados"] and r["proveedor"] == "falso" and "confirme" in r["aviso"]
    assert sv.ultimo(s_ext, "TACNA-02")["campos"] == r["campos"]
    assert ".pdf" not in json.dumps(r) and "b documento" not in json.dumps(r)


def test_extraer_sin_proveedor_o_con_nombre_pendiente(s_ext, monkeypatch):
    with pytest.raises(ErrorProveedor, match="desactivada"):
        sv.extraer(s_ext, "TACNA-02")
    from app.extraccion import anonimizar
    original = anonimizar.Anonimizador.anonimizar
    monkeypatch.setattr(anonimizar.Anonimizador, "anonimizar",
                        lambda self, pags: (lambda r: (r.pendientes.append("x"), r)[1])(original(self, pags)))
    p = Falso()
    with pytest.raises(sv.ErrorPrivacidad):
        sv.extraer(s_ext, "TACNA-02", proveedor=p)
    assert p.recibido is None                                           # no se envió nada


# ================================================================ API
@pytest.fixture
def cliente_ext(tmp_path, privado, monkeypatch):
    s = Settings(data_dir=_muestra(tmp_path), rules_dir=RULES, reportes_dir=tmp_path / "reportes",
                 casos_reales_privados_dir=privado, extraccion_dir=tmp_path / "extraccion",
                 database_url=f"sqlite:///{(tmp_path / 'f6.db').as_posix()}")
    servicio.seed(s)
    monkeypatch.setattr(sv, "proveedor_de", lambda _s: Falso())
    app.dependency_overrides[get_settings] = lambda: s
    yield TestClient(app)
    app.dependency_overrides.clear()


def h(u):
    return {"X-Usuario": u}


def test_api_documentos_y_permisos(cliente_ext):
    assert cliente_ext.get("/extraccion/documentos", headers=h("eps-EPS02")).status_code == 403
    docs = cliente_ext.get("/extraccion/documentos?id_expediente=REAL-TACNA-2026", headers=h(COORD)).json()
    assert [d["alias"] for d in docs] == ["TACNA-01", "TACNA-02"] and not any(d["procesado"] for d in docs)
    assert ".pdf" not in json.dumps(docs)
    assert cliente_ext.get("/extraccion/documentos/TACNA-02", headers=h(COORD)).status_code == 404
    assert cliente_ext.post("/extraccion/documentos/NO-EXISTE", headers=h(COORD)).status_code == 404


def test_api_leer_y_confirmar_con_bitacora(cliente_ext):
    r = cliente_ext.post("/extraccion/documentos/TACNA-02", headers=h(COORD))
    assert r.status_code == 200 and r.json()["campos"]["plazo"]["dias_habiles"] == 2
    url = "/extraccion/documentos/TACNA-02/confirmar"
    base = {"hito": "informacion_ep", "numero_documento": "OFICIO N.° 999-2099-PRUEBA", "fecha": "2099-08-14",
            "remitente": None, "plazo": {"dias_habiles": 2, "tipo": "prorroga"}}
    # Si cambia un valor, la corrección exige motivo.
    sin_motivo = cliente_ext.post(url, headers=h(COORD), json={**base, "plazo": {"dias_habiles": 3, "tipo": "prorroga"}})
    assert sin_motivo.status_code == 422 and "motivo" in sin_motivo.json()["detail"]
    ok = cliente_ext.post(url, headers=h(COORD), json=base)
    assert ok.status_code == 201 and ok.json()["evento_id"] and ok.json()["corregidos"] == []
    assert cliente_ext.post(url, headers=h(COORD), json=base).status_code == 409
    ficha = cliente_ext.get("/expedientes/REAL-TACNA-2026", headers=h(COORD)).json()
    doc = next(d for d in ficha["documentos"] if d["origen"] == "extraido_ia")
    assert doc["estado_registro"] == "confirmado" and "TACNA-02" in doc["fuente"]
    assert cliente_ext.get("/extraccion/documentos?id_expediente=REAL-TACNA-2026", headers=h(COORD)).json()[1]["procesado"]


def test_api_estado_sin_proveedor(tmp_path, privado):
    s = Settings(data_dir=_muestra(tmp_path), rules_dir=RULES, casos_reales_privados_dir=privado,
                 database_url=f"sqlite:///{(tmp_path / 'e.db').as_posix()}")
    servicio.seed(s)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        e = TestClient(app).get("/extraccion/estado", headers=h(COORD)).json()
        assert e["proveedor"] == "ninguno" and e["disponible"] is False and "desactivada" in e["detalle"]
        assert e["lista_privada"] is False
    finally:
        app.dependency_overrides.clear()


# ================================================================ evaluación independiente
def test_plantilla_con_campos_vacios(s_ext):
    ruta = evaluacion.plantilla(s_ext)
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert "La llena el EQUIPO" in ruta.read_text(encoding="utf-8")
    assert [d["alias"] for d in datos["documentos"]] == ["TACNA-01", "TACNA-02"]
    for d in datos["documentos"]:
        assert all(v == {"valor": None, "cita": None, "pagina": None} for v in d["campos"].values())


def test_evaluar_precision_y_exhaustividad(s_ext):
    carpeta = evaluacion.carpeta(s_ext)
    carpeta.mkdir(parents=True)
    (carpeta / "anotaciones.yaml").write_text(yaml.safe_dump({"documentos": [{"alias": "TACNA-02", "campos": {
        "numero_documento": {"valor": "OFICIO N.° 999-2099-PRUEBA"}, "fecha": {"valor": "14 de agosto de 2099"},
        "remitente": {"valor": "Unidad de prueba"}, "plazo_dias_habiles": {"valor": 2}}}]}, allow_unicode=True), encoding="utf-8")
    res = evaluacion.evaluar(s_ext, extraer=lambda s, alias: {"segundos": 1.0, "campos": {
        "numero_documento": {"valor": "OFICIO N.° 999-2099-PRUEBA"}, "fecha": {"valor": "2099-08-14"},
        "remitente": None, "plazo": {"dias_habiles": 3}}})
    pc = res["por_campo"]
    assert pc["numero_documento"]["precision"] == 1.0 and pc["fecha"]["vp"] == 1
    assert pc["remitente"]["fn"] == 1 and pc["remitente"]["precision"] is None
    assert pc["plazo_dias_habiles"] == {"vp": 0, "fp": 1, "fn": 1, "precision": 0.0, "exhaustividad": 0.0}
    assert res["detalle"][0]["campos"]["remitente"] == "falta"
    assert (carpeta / "resultado.yaml").exists()


def test_evaluar_sin_anotaciones(s_ext):
    with pytest.raises(FileNotFoundError, match="plantilla-evaluacion"):
        evaluacion.evaluar(s_ext)


# ================================================================ verificación de privacidad del repositorio
def test_verificar_privacidad_detecta_texto_nombres_y_archivos(s_ext, privado, tmp_path, monkeypatch):
    monkeypatch.setattr(privacidad, "_normas", lambda: [])
    (privado / "nombres_a_ocultar.txt").write_text("Nombrea Apellidob\n", encoding="utf-8")
    escribir_pdf(privado / "Tacna documentos" / "Oficio Nombreuno Apellidodos Apellidotres.pdf",
                 [["Frase única de prueba que solo aparece en este documento intermedio sintético y en ningún otro."]])
    limpio = tmp_path / "limpio.md"
    limpio.write_text("Texto propio del proyecto, sin fragmentos de oficios.", encoding="utf-8")
    copia = tmp_path / "copia.md"
    copia.write_text("Nota: frase única de prueba que solo aparece en este documento intermedio.", encoding="utf-8")
    nombre = tmp_path / "nombre.md"
    nombre.write_text("Lo firmó NOMBREA APELLIDOB.", encoding="utf-8")
    archivo = tmp_path / "archivo.md"
    archivo.write_text("Ver oficio nombreuno apellidodos apellidotres.", encoding="utf-8")
    h = privacidad.verificar(s_ext, archivos=[limpio, copia, nombre, archivo])
    tipos = {(Path(x.archivo).name, x.tipo) for x in h}
    assert tipos == {("copia.md", "fragmento_de_oficio"), ("nombre.md", "nombre_privado"), ("archivo.md", "nombre_de_archivo")}
    # Lo aprobado en rules/privacidad_revisado.yaml (solo la huella) deja de marcarse.
    frag = next(x for x in h if x.tipo == "fragmento_de_oficio").fragmentos
    monkeypatch.setattr(privacidad, "revisados", lambda s: {privacidad.huella(f) for f in frag})
    assert all(x.tipo != "fragmento_de_oficio" for x in privacidad.verificar(s_ext, archivos=[copia]))


def test_anthropic_solo_recibe_documentos_publicados(s_ext, privado):
    """Acuerdo del equipo: la API de Anthropic solo con textos públicos o sintéticos (y anonimizados)."""
    p = Falso()
    p.nombre = "anthropic"
    with pytest.raises(sv.ErrorPrivacidad, match="solo recibe textos públicos"):
        sv.extraer(s_ext, "TACNA-02", proveedor=p)
    assert p.recibido is None
    escribir_pdf(privado / "Tacna documentos" / "RCD 032-2026 publicada.pdf", [PAG1])
    alias = next(d.alias for d in sv.indice(s_ext) if d.publicado)
    assert sv.extraer(s_ext, alias, proveedor=p)["proveedor"] == "anthropic"
    assert p.recibido is not None
