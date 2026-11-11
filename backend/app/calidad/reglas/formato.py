"""CAL-FMT-01: problemas de formato y de esquema detectados durante la carga."""

from __future__ import annotations

from app.calidad.base import nuevo
from app.calidad.reglas import regla


@regla("CAL-FMT-01")
def problemas_de_formato(m, cfg, ctx):
    res = []
    for p in m.problemas:
        llave = p.columna
        res.append(nuevo(cfg, p.dataset, p.fila, llave, p.mensaje, observado=p.valor))
    return res
