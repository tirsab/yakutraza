"""Línea de comandos: python -m app.cli {seed|calidad|reporte|verificar-diccionario}."""

from __future__ import annotations

import argparse
import sys

from app import servicio
from app.config import get_settings
from app.ingesta.diccionario import verificar_contra_diccionario


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.cli", description="Tareas de YakuTraza")
    p.add_argument("tarea", choices=["seed", "calidad", "reporte", "verificar-diccionario"])
    a = p.parse_args(argv)
    s = get_settings()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if a.tarea == "seed":
        r = servicio.seed(s)
        print(f"Carga n.° {r.lote_id} desde {s.data_dir} (fecha de corte {s.fecha_corte}).")
        for nombre, n in r.filas.items():
            print(f"  {nombre}: {n} filas")
        print(f"Hallazgos de calidad: {r.hallazgos}")
        print(f"Reporte: {r.reporte}")
    elif a.tarea == "calidad":
        n = servicio.recalcular_calidad(s)
        print(f"Hallazgos de calidad: {n}. Reporte actualizado en {s.reportes_dir}.")
    elif a.tarea == "reporte":
        print(f"Reporte: {servicio.generar_reporte(s)}")
    elif a.tarea == "verificar-diccionario":
        problemas = verificar_contra_diccionario(s.data_dir)
        for pr in problemas:
            print(f"- {pr.dataset}: {pr.mensaje}")
        print("La especificación coincide con el diccionario." if not problemas else f"{len(problemas)} diferencias.")
        return 1 if problemas else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
