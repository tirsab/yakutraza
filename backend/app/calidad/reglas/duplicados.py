"""Duplicados: filas idénticas (CAL-DUP-01) y llaves repetidas (CAL-DUP-02)."""

from __future__ import annotations

from app.calidad.base import nuevo
from app.calidad.reglas import regla
from app.calidad.reglas._util import llave as texto_llave


@regla("CAL-DUP-01")
def filas_identicas(m, cfg, ctx):
    res = []
    for nombre, t in m.tablas.items():
        crudos = t.crudos
        repetidas = crudos[crudos.duplicated(keep=False)]
        if repetidas.empty:
            continue
        for _, grupo in repetidas.groupby(list(crudos.columns), sort=False, dropna=False):
            filas = sorted(int(i) for i in grupo.index)
            primera = filas[0]
            res.append(nuevo(
                cfg, nombre, primera, texto_llave(grupo.iloc[0], t.spec.llave),
                f"Las filas {', '.join(map(str, filas))} de {t.spec.archivo} son idénticas en todas sus columnas. "
                "No se elimina ninguna: confirmar con la EPS si es un envío duplicado.",
                observado=f"{len(filas)} filas iguales", esperado="1 fila",
                detalle={"filas": filas},
            ))
    return res


@regla("CAL-DUP-02")
def llaves_repetidas(m, cfg, ctx):
    res = []
    for nombre, t in m.tablas.items():
        crudos = t.crudos
        cols = list(t.spec.llave)
        rep = crudos[crudos.duplicated(cols, keep=False)]
        if rep.empty:
            continue
        for _, grupo in rep.groupby(cols, sort=False):
            if len(grupo.drop_duplicates()) == 1:
                continue  # filas idénticas: las reporta CAL-DUP-01
            filas = sorted(int(i) for i in grupo.index)
            distintas = [c for c in crudos.columns if c not in cols and grupo[c].nunique() > 1]
            valores = "; ".join(
                f"{c}: " + " vs ".join(f"«{v}» (fila {i})" for i, v in grupo[c].items()) for c in distintas
            )
            res.append(nuevo(
                cfg, nombre, filas[0], texto_llave(grupo.iloc[0], cols),
                f"La llave ({', '.join(cols)}) se repite en las filas {', '.join(map(str, filas))} de "
                f"{t.spec.archivo} con valores distintos. {valores}. No se elige cuál es la correcta.",
                observado=f"{len(filas)} filas con la misma llave", esperado="1 fila por llave",
                detalle={"filas": filas, "columnas_distintas": distintas},
            ))
    return res
