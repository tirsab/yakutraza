"""Casos reales del MVP: EPS TACNA (CPI), EPSSMU (UFI) y EMAPA PASCO (RP). Parte pública solo con resoluciones
publicadas; cuadros con documento y página; texto ciudadano solo de lo publicado; plazos de Pasco con las reglas de 2024."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.dinero import ruta
from app.expediente.casos_reales import cargar_casos, expediente_de
from app.extraccion import privacidad
from app.main import app
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from app.plazos.motor import EventoPlazo, MotorPlazos

PUBLICO = Path(get_settings().casos_reales_dir)
RULES = Path(get_settings().rules_dir)
FIRMAS = re.compile(r"(?i)\b(firm|vis)ado\s+por\b|motivo:\s*firm|\bFAU\s*\d{11}")
# Documentos de Pasco que NO son resoluciones publicadas: no pueden estar en la parte pública.
PRIVADOS_PASCO = ("431-2024", "515-2024", "493-2024", "409-2024", "554-2024", "00150-2024", "369-2024", "955-2024",
                  "15.11.2024", "zoom", "virtual")


def _num(x: str) -> int:
    return int(x.replace(" ", "")) if x not in ("-", "") else 0


def _motor() -> MotorPlazos:
    return MotorPlazos(calendario_desde(RULES / "feriados.yaml"), catalogo_desde(RULES / "plazos.yaml"))


def test_tres_casos_reales_y_parte_publica_sin_rastros():
    casos = cargar_casos(PUBLICO, None)
    assert set(casos) == {"REAL-TACNA-2026", "REAL-EPSSMU-2025", "REAL-PASCO-2024"}
    assert all(c.datos["naturaleza"] == "real" and not c.con_detalle_privado for c in casos.values())
    for f in PUBLICO.glob("*.yaml"):
        texto = f.read_text(encoding="utf-8")
        assert not FIRMAS.search(texto), f.name
        assert privacidad.rastros(texto) == [], f.name


def test_pasco_publico_solo_con_las_tres_resoluciones():
    texto = (PUBLICO / "pasco_rp_2024.yaml").read_text(encoding="utf-8")
    assert not [x for x in PRIVADOS_PASCO if x.lower() in texto.lower()]
    c = cargar_casos(PUBLICO, None)["REAL-PASCO-2024"]
    # Solo lo que dicen la RD 015-2024, la RCD 060-2024 y la RCD 076-2024 (incluidos los documentos que ellas citan).
    tipos = {d["tipo"] for d in c.datos["documentos"]}
    assert {d["numero"] for d in c.datos["documentos"] if d["tipo"] in ("RD", "RCD")} == {
        "Resolución N.° 00015-2024-SUNASS-DRT", "Resolución de Consejo Directivo N.° 00060-2024-SUNASS-CD",
        "Resolución de Consejo Directivo N.° 00076-2024-SUNASS-CD"}
    assert tipos <= {"OF", "RD", "RCD", "MEM"}
    # El canal de la subsanación no está documentado.
    assert next(d for d in c.datos["documentos"] if d["clave"] == "PASCO:OF-366-2024")["canal"] == "no_indicado"
    assert c.datos["expediente"]["localidades"] == ["Pasco", "Vicco"]
    assert all(t["publica"] is True for t in c.datos["tablas"])
    # Cuadros 92 a 94 del estudio final: públicos porque la RCD 076-2024 (art. 6) dispone su difusión.
    est = [t for t in c.datos["tablas"] if t["clave"].startswith("PASCO:ET-CUADRO-")]
    assert len(est) == 3 and all("art. 6" in " ".join(t["notas"]) for t in est)
    c93 = next(t for t in est if t["clave"] == "PASCO:ET-CUADRO-93")
    assert c93["estado"] == "por_verificar" and c93["filas"][-1][-1] == "2 237 550"


def test_cuadros_de_tacna_cuadran_con_la_resolucion():
    c = cargar_casos(PUBLICO, None)["REAL-TACNA-2026"]
    t = {x["clave"]: x for x in c.datos["tablas"]}
    soles, cantidad = t["TACNA:RCD032-CUADRO-1"], t["TACNA:RCD032-CUADRO-2"]
    assert sum(_num(f[-1]) for f in soles["filas"][:-1]) == _num(soles["filas"][-1][-1]) == 3_817_752
    assert sum(_num(f[-1]) for f in cantidad["filas"][:-1]) == _num(cantidad["filas"][-1][-1]) == 19_935
    renov = sum(_num(f[-1]) for f in cantidad["filas"] if f[0].startswith("Mejoramiento"))
    ampl = sum(_num(f[-1]) for f in cantidad["filas"] if f[0] == "Ampliación")
    assert (renov, ampl) == (12_527, 7_408)
    # Los años van tal cual («Año 3», «Año 4»), sin convertirlos a años calendario.
    assert soles["columnas"][2:7] == ["Año 1", "Año 2", "Año 3", "Año 4", "Año 5"]
    assert c.datos["localidades"] == ["Tacna", "Pachía", "Locumba"]


def _pasco_con_privado(tmp_path) -> Path:
    privado = tmp_path / "privado"
    privado.mkdir()
    (privado / "pasco_rp_2024_detalle.yaml").write_text(yaml.safe_dump({
        "caso": "PASCO-RP-2024",
        "documentos": [{"clave": "PASCO:OF-431-2024", "nuevo": True, "tipo": "OF", "numero": "Oficio de prueba 431",
                        "hito": "comentarios", "remitente": "DRT", "fecha_emision": date(2024, 10, 1)}],
        "hitos": [{"nro": 8, "fin": date(2024, 11, 15)}, {"nro": 9, "inicio": date(2024, 11, 15), "fin": date(2024, 12, 5)},
                  {"nro": 10, "inicio": date(2024, 12, 5)}],
        "tablas": [{"clave": "PASCO:ET-CUADRO-92", "nuevo": True, "titulo": "Copia privada", "documento": "x",
                    "pagina": "1", "publica": False, "columnas": ["a"], "filas": [["1"]]},
                   {"clave": "PASCO:PRIVADA", "nuevo": True, "titulo": "Cuadro privado", "documento": "Informe interno",
                    "pagina": "1", "publica": True, "estado": "verificado", "columnas": ["a"], "filas": [["1"]]}],
    }, allow_unicode=True), encoding="utf-8")
    return privado


def test_pasco_plazos_con_las_reglas_de_2024(tmp_path):
    c = cargar_casos(PUBLICO, _pasco_con_privado(tmp_path))["REAL-PASCO-2024"]
    exp = expediente_de(c)
    sin_notificacion = EventoPlazo(expediente=exp.id, hito="comentarios", tipo="plazo_oficio", documento="Oficio de prueba 431",
                                   fecha_documento=date(2024, 10, 1), dias_adicionales_dh=40)
    al = {a.regla_id: a for a in _motor().relojes(exp, date(2026, 9, 30), [sin_notificacion]) if a.regla_id}
    for etapa in ("PLZ-N-RP-1", "PLZ-N-RP-2-V2022", "PLZ-N-RP-3-V2021", "PLZ-N-RP-4-V2021"):
        assert al[etapa].estado == "cumplido", (etapa, al[etapa].mensaje)
    # Comentarios de los interesados: hasta el quinto día hábil después de la audiencia (8-11-2024 → 15-11-2024).
    com = al["PLZ-N-RP-COMENTARIOS-V2021"]
    assert com.estado == "cumplido" and com.fecha_limite == date(2024, 11, 15)
    assert al["PLZ-O-RP-SUBSANACION-10"].estado == "cumplido"
    # Los 40 DH de la EP corren desde la notificación, que ningún documento indica: no se calcula.
    ep = next(a for a in _motor().plazos_de_documento(exp, date(2026, 9, 30), [sin_notificacion]))
    assert ep.estado == "no_calculable" and "fecha de notificación" in ep.mensaje and ep.fecha_limite is None


def test_comentarios_de_ds02_siguen_sin_compararse(tmp_path):
    """En DS02 el hito «comentarios» junta EP e interesados: sin `plazo_de` sigue «no comparable»."""
    c = cargar_casos(PUBLICO, _pasco_con_privado(tmp_path))["REAL-PASCO-2024"]
    exp = expediente_de(c)
    for h in exp.hitos:
        h.plazo_de = None
    com = next(a for a in _motor().relojes(exp, date(2026, 9, 30)) if a.regla_id == "PLZ-N-RP-COMENTARIOS-V2021")
    assert com.estado == "no_calculable" and "No puedo comparar" in com.mensaje


@pytest.fixture
def cliente_casos(tmp_path):
    s = Settings(casos_reales_dir=PUBLICO, casos_reales_privados_dir=_pasco_con_privado(tmp_path), rules_dir=RULES,
                 database_url=f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    app.dependency_overrides[get_settings] = lambda: s
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_vista_ciudadana_solo_casos_con_resolucion_publicada(cliente_casos):
    casos = cliente_casos.get("/publico/casos-reales").json()
    assert {c["id_expediente"] for c in casos} == {"REAL-TACNA-2026", "REAL-PASCO-2024"}  # EPSSMU no se publica
    pasco = next(c for c in casos if c["id_expediente"] == "REAL-PASCO-2024")
    assert pasco["naturaleza"] == "real" and pasco["fuentes"] and "8 de noviembre de 2024" in pasco["texto"]
    assert "10 %" in pasco["texto"] and "12,1 %" in pasco["texto"]
    # Un cuadro de la parte privada nunca sale en la vista ciudadana, aunque diga «publica: true».
    assert "PASCO:PRIVADA" not in {t["clave"] for t in pasco["tablas"]}
    # La copia privada de un cuadro público no lo reemplaza.
    c92 = next(t for t in pasco["tablas"] if t["clave"] == "PASCO:ET-CUADRO-92")
    assert c92["titulo"] != "Copia privada" and c92["publica"]
    texto = str(casos).lower()
    assert "oficio de prueba" not in texto and "informe interno" not in texto


def test_ruta_del_dinero_con_los_cuadros_de_cada_caso(tmp_path):
    casos = cargar_casos(PUBLICO, _pasco_con_privado(tmp_path))
    cuadros = {c.id_expediente: ruta.cuadros_caso_real(c) for c in casos.values()}
    assert {t["clave"] for t in cuadros["REAL-PASCO-2024"]["tablas"]} >= {"PASCO:RCD076-FORMULA", "PASCO:PRIVADA"}
    assert all(t["documento"] and t["pagina"] for x in cuadros.values() for t in x["tablas"])
    assert ruta.ciudadana_caso_real(casos["REAL-EPSSMU-2025"]) is None


def test_solo_parte_publica_ningun_hito_sin_fin_aparece_vencido():
    """Enlace público (sin parte privada): Pasco concluyó; un hito sin fecha de fin no es «vencido»."""
    exp = expediente_de(cargar_casos(PUBLICO, None)["REAL-PASCO-2024"])
    al = _motor().relojes(exp, date(2026, 9, 30))
    assert not [a.regla_id for a in al if a.estado in ("vencido", "por_vencer", "en_plazo")]
    com = next(a for a in al if a.regla_id == "PLZ-I-RP-COMENTARIOS")
    assert com.estado == "no_calculable" and "concluyó" in com.mensaje
