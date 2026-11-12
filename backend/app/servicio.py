"""Operaciones de alto nivel que usan la CLI y la API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.calidad.base import cargar_catalogo
from app.calidad.motor import evaluar
from app.calidad.reporte import construir_html, escribir_reporte
from app.config import Settings, dir_privado
from app.expediente.casos_reales import cargar_casos, sincronizar
from app.db import get_engine
from app.ingesta.cargar import cargar_muestra
from app.ingesta.diccionario import verificar_contra_diccionario
from app.persistencia import guardar_carga, leer_hallazgos, reemplazar_hallazgos, ultimo_lote


@dataclass
class ResultadoSeed:
    lote_id: int
    filas: dict[str, int]
    hallazgos: int
    reporte: Path
    casos_reales: dict | None = None


def _ruta_catalogo(s: Settings) -> Path:
    return Path(s.rules_dir) / "calidad.yaml"


def _muestra_verificada(s: Settings):
    muestra = cargar_muestra(s.data_dir)
    muestra.problemas.extend(verificar_contra_diccionario(s.data_dir))
    return muestra


def seed(s: Settings) -> ResultadoSeed:
    if not Path(s.data_dir).exists():
        raise FileNotFoundError(f"DATA_DIR no existe: {s.data_dir}. Define DATA_DIR con la carpeta de los CSV.")
    muestra = _muestra_verificada(s)
    hallazgos = evaluar(muestra, _ruta_catalogo(s), s.fecha_corte)
    engine = get_engine(s.database_url)
    lote_id = guardar_carga(engine, muestra, hallazgos, s.fecha_corte)
    casos = cargar_casos(Path(s.casos_reales_dir), dir_privado(s))
    sync = sincronizar(engine, casos)
    ruta = generar_reporte(s)
    return ResultadoSeed(lote_id, {n: len(t.datos) for n, t in muestra.tablas.items()}, len(hallazgos), ruta,
                         {"casos": len(casos), "con_detalle_privado": sum(c.con_detalle_privado for c in casos.values()),
                          **sync})


def recalcular_calidad(s: Settings) -> int:
    """Vuelve a evaluar las reglas (p. ej., tras editar el YAML) sobre la última carga."""
    engine = get_engine(s.database_url)
    lote = ultimo_lote(engine)
    if lote is None:
        raise RuntimeError("No hay cargas. Ejecuta primero `seed`.")
    muestra = _muestra_verificada(s)
    actuales = {n: t.sha256 for n, t in muestra.tablas.items()}
    cargados = {n: info["sha256"] for n, info in lote["archivos"].items()}
    if actuales != cargados:
        raise RuntimeError("Los CSV de DATA_DIR cambiaron desde la última carga. Ejecuta `seed` de nuevo.")
    hallazgos = evaluar(muestra, _ruta_catalogo(s), s.fecha_corte)
    reemplazar_hallazgos(engine, lote["id"], hallazgos)
    generar_reporte(s)
    return len(hallazgos)


def html_reporte(s: Settings) -> str:
    engine = get_engine(s.database_url)
    lote = ultimo_lote(engine)
    if lote is None:
        raise RuntimeError("No hay cargas. Ejecuta primero `seed`.")
    return construir_html(leer_hallazgos(engine, lote["id"]), lote, cargar_catalogo(_ruta_catalogo(s)))


def generar_reporte(s: Settings) -> Path:
    return escribir_reporte(html_reporte(s), Path(s.reportes_dir))
