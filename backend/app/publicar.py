"""Un solo proceso para publicar la demo (Render u otro servicio de un contenedor).

Sirve la API bajo /api (igual que nginx en docker-compose y el proxy de Vite) y la interfaz ya construida
(WEB_DIR) en el resto de las rutas, con respaldo a index.html para las rutas del navegador.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.main import app as api


def crear(web_dir: Path) -> FastAPI:
    web_dir = web_dir.resolve()
    sitio = FastAPI(title="YakuTraza (demo publicada)", docs_url=None, redoc_url=None, openapi_url=None)
    sitio.mount("/api", api)

    @sitio.get("/{ruta:path}", include_in_schema=False)
    def interfaz(ruta: str) -> FileResponse:
        archivo = (web_dir / ruta).resolve()
        if ruta and archivo.is_file() and archivo.is_relative_to(web_dir):
            return FileResponse(archivo)
        if Path(ruta).suffix:  # recurso que no existe (p. ej. /assets/x.js): 404, no la portada
            raise HTTPException(404)
        return FileResponse(web_dir / "index.html")

    return sitio


app = crear(Path(os.environ.get("WEB_DIR", "/web")))
