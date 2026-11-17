"""Línea de comandos: python -m app.cli {seed|calidad|reporte|verificar-diccionario|indicadores}."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import servicio
from app.config import RAIZ_REPO, get_settings
from app.ingesta.diccionario import verificar_contra_diccionario


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.cli", description="Tareas de YakuTraza")
    p.add_argument("tarea", choices=["seed", "calidad", "reporte", "verificar-diccionario", "indicadores",
                                      "plantilla-evaluacion", "evaluar-extraccion", "verificar-privacidad"])
    p.add_argument("--revisar", action="store_true",
                   help="verificar-privacidad: muestra en la consola el texto de cada coincidencia y su huella.")
    p.add_argument("--salida", default=str(RAIZ_REPO / "docs" / "indicadores.md"),
                   help="Archivo de la línea base (solo para «indicadores»).")
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
        if r.casos_reales:
            cr = r.casos_reales
            print(f"Casos reales: {cr['casos']} ({cr['con_detalle_privado']} con detalle privado); registros "
                  f"insertados {cr['insertados']}, actualizados {cr['actualizados']}, confirmados intactos "
                  f"{cr['confirmados_intactos']}.")
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
    elif a.tarea == "indicadores":
        from app.db import get_engine
        from app.vistas import indicadores, tablero
        from app.vistas.etiquetas import catalogo
        ctx = tablero.contexto(get_engine(s.database_url), s)
        Path(a.salida).write_text(indicadores.markdown(ctx, catalogo(Path(s.rules_dir) / "etiquetas.yaml")),
                                  encoding="utf-8")
        print(f"Línea base escrita en {a.salida}.")
    elif a.tarea == "plantilla-evaluacion":
        from app.extraccion import evaluacion
        print(f"Plantilla vacía escrita en {evaluacion.plantilla(s)}. Llénela a mano y guárdela como anotaciones.yaml.")
    elif a.tarea == "evaluar-extraccion":
        from app.extraccion import evaluacion
        r = evaluacion.evaluar(s)
        for k, v in r["por_campo"].items():
            print(f"  {k}: precisión {v['precision']}, exhaustividad {v['exhaustividad']} (vp {v['vp']}, fp {v['fp']}, fn {v['fn']})")
        t = r["total"]
        print(f"Total ({r['documentos']} documentos): precisión {t['precision']}, exhaustividad {t['exhaustividad']}. "
              f"Detalle en {evaluacion.carpeta(s) / 'resultado.yaml'}.")
    elif a.tarea == "verificar-privacidad":
        from app.extraccion import privacidad
        hallazgos = privacidad.verificar(s)
        for h in hallazgos:
            print(f"- {h.archivo}: {h.tipo}")
            if a.revisar:
                for x in h.fragmentos:
                    print(f"    «{x}» sha256={privacidad.huella(x)}")
        print("Ningún texto de los oficios ni nombre privado en los archivos versionados." if not hallazgos
              else f"{len(hallazgos)} coincidencias: revíselas antes de hacer commit.")
        return 1 if hallazgos else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
