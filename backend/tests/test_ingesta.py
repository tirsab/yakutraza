from datetime import date
from decimal import Decimal

import pytest

from app.ingesta.conversion import ErrorConversion, convertir
from app.ingesta.diccionario import verificar_contra_diccionario
from app.ingesta.especificacion import DATASETS, NATURALEZAS


@pytest.mark.parametrize("valor,tipo,esperado", [
    ("", "entero", None),
    ("2711204.0", "entero", 2711204),
    ("010101", "texto", "010101"),
    ("12.81", "decimal", Decimal("12.81")),
    ("2026-09-30", "fecha", date(2026, 9, 30)),
    ("True", "booleano", True),
    ("False", "booleano", False),
])
def test_convertir_valores_validos(valor, tipo, esperado):
    assert convertir(valor, tipo) == esperado


@pytest.mark.parametrize("valor,tipo", [
    ("2711204.5", "entero"), ("abc", "entero"), ("1,5", "decimal"), ("NaN", "decimal"),
    ("30/09/2026", "fecha"), ("2026-02-30", "fecha"), ("si", "booleano"),
])
def test_convertir_rechaza_sin_corregir(valor, tipo):
    with pytest.raises(ErrorConversion):
        convertir(valor, tipo)


def test_tipo_desconocido():
    with pytest.raises(ValueError):
        convertir("x", "moneda")


def test_ubigeo_conserva_cero_inicial(muestra_de):
    m = muestra_de({"ds01_localidades_eps": [{"cod_eps": "EPS01", "ubigeo": "010101", "es_sede": "True"}]})
    assert m["ds01_localidades_eps"].loc[2, "ubigeo"] == "010101"


def test_valor_invalido_queda_vacio_y_se_registra(muestra_de):
    m = muestra_de({"ds06_estados_financieros": [{"cod_eps": "EPS01", "anio": "2023", "ingresos_operativos": "12.5"}]})
    assert m["ds06_estados_financieros"].loc[2, "ingresos_operativos"] is None
    assert m.tablas["ds06_estados_financieros"].crudos.loc[2, "ingresos_operativos"] == "12.5"
    (p,) = [x for x in m.problemas if x.fila is not None]
    assert (p.dataset, p.fila, p.columna, p.valor) == ("ds06_estados_financieros", 2, "ingresos_operativos", "12.5")


def test_columnas_distintas_y_archivo_faltante(tmp_path):
    from app.ingesta.cargar import cargar_muestra
    d = tmp_path / "data"
    d.mkdir()
    (d / "ds09_ipm.csv").write_text("anio_mes,columna_extra\n2026-01,1\n", encoding="utf-8")
    m = cargar_muestra(d)
    mensajes = [p.mensaje for p in m.problemas]
    assert any("columna_extra" in x and "variacion_mensual_pct" in x for x in mensajes)
    assert sum("No se encontró" in x for x in mensajes) == len(DATASETS) - 1


def test_especificacion_bien_formada():
    nombres = [d.nombre for d in DATASETS]
    assert len(nombres) == len(set(nombres)) == 11
    for d in DATASETS:
        cols = [c.nombre for c in d.columnas]
        assert len(cols) == len(set(cols))
        assert set(d.llave) <= set(cols)
        assert all(c.naturaleza in NATURALEZAS for c in d.columnas)


def test_diccionario_ausente(tmp_path):
    (p,) = verificar_contra_diccionario(tmp_path)
    assert "No se encontró" in p.mensaje


@pytest.mark.muestra
def test_especificacion_coincide_con_diccionario(data_dir_real):
    assert verificar_contra_diccionario(data_dir_real) == []


@pytest.mark.muestra
def test_muestra_real_carga_completa_sin_problemas(muestra_real):
    filas = {n: len(t.datos) for n, t in muestra_real.tablas.items()}
    # Cobertura de la hoja Léame: 20 EPS, 53 localidades, 481 expedientes con 1825 hitos.
    assert filas["ds01_catalogo_eps"] == 20
    assert filas["ds01_localidades_eps"] == 53
    assert filas["ds02_procedimientos"] == 481
    assert filas["ds02_hitos_procedimientos"] == 1825
    assert len(filas) == 11
    assert muestra_real.problemas == []
