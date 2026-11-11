"""CAL-UNI-01: montos en una escala distinta al resto de su serie."""

from __future__ import annotations

import math
from statistics import median

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import dec, llave as texto_llave
from app.calidad.reglas._util import num


def _potencia_mil(ratio: float) -> str:
    """Describe el factor en potencias de 1000 si se parece a una."""
    exp = round(math.log10(ratio) / 3)
    if exp != 0 and abs(math.log10(ratio) - 3 * exp) < 0.5:
        return "miles" if exp < 0 else "milésimas"
    return ""


@regla("CAL-UNI-01")
def escala_distinta(m, cfg, ctx):
    factor = float(cfg.param("factor"))
    minimo = int(cfg.param("minimo_valores_en_serie"))
    res = []
    for serie in cfg.param("series", []):
        nombre = serie["dataset"]
        if nombre not in m.tablas:
            continue
        df = m[nombre]
        grupo_cols = serie["agrupar_por"]
        marcas: dict[int, list[str]] = {}
        for _, g in df.groupby(grupo_cols, sort=False):
            for col in serie["columnas"]:
                valores = {int(f): float(v) for f, v in zip(g["_fila"], g[col]) if v is not None and v > 0}
                if len(valores) < minimo:
                    continue
                for fila, v in valores.items():
                    otros = [x for f, x in valores.items() if f != fila]
                    med = median(otros)
                    ratio = v / med
                    if ratio <= 1 / factor or ratio >= factor:
                        escala = _potencia_mil(ratio)
                        pista = f" Parece expresado en {escala} de soles." if escala == "miles" else ""
                        veces = f"1/{dec(med / v, 0)}" if ratio < 1 else f"{dec(ratio, 0)}"
                        marcas.setdefault(fila, []).append(
                            f"{col} = {num(v)} es {veces} veces la mediana del resto de su serie "
                            f"({num(round(med, 2))}).{pista}"
                        )
        for fila, textos in marcas.items():
            r = df.loc[fila]
            res.append(nuevo(
                cfg, nombre, fila, texto_llave(r, grupo_cols + [c for c in m.tablas[nombre].spec.llave if c not in grupo_cols]),
                f"Serie agrupada por {', '.join(grupo_cols)} en {nombre}: " + " ".join(textos)
                + f" Umbral: factor {factor:g} (supuesto). No se convierte el valor.",
                observado=f"{len(textos)} columna(s) fuera de escala",
                esperado=f"Valores dentro de un factor {factor:g} de la mediana",
                detalle={"columnas": textos},
            ))
    return res
