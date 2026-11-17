"""PDF mínimos con texto SINTÉTICO para las pruebas de la Fase 6 (nunca texto de oficios reales).

Cada página es una lista de líneas; se escriben con Helvetica y codificación WinAnsi (admite tildes y ñ).
"""

from __future__ import annotations

from pathlib import Path


def _escapar(linea: str) -> bytes:
    b = linea.encode("cp1252")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def escribir_pdf(ruta: Path, paginas: list[list[str]]) -> Path:
    objetos: list[bytes] = []
    n_pag = len(paginas)
    # 1: catálogo, 2: páginas, 3: fuente; luego por página: página y contenido.
    hijos = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pag))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{hijos}] /Count {n_pag} >>".encode())
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, lineas in enumerate(paginas):
        flujo = b"BT /F1 11 Tf 14 TL 72 760 Td " + b" ".join(b"(" + _escapar(ln) + b") '" for ln in lineas) + b" ET"
        objetos.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
                       f"/Contents {5 + 2 * i} 0 R >>".encode())
        objetos.append(f"<< /Length {len(flujo)} >>\nstream\n".encode() + flujo + b"\nendstream")
    salida = bytearray(b"%PDF-1.4\n")
    desplaz = []
    for n, obj in enumerate(objetos, 1):
        desplaz.append(len(salida))
        salida += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    salida += b"".join(f"{d:010d} 00000 n \n".encode() for d in desplaz)
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(bytes(salida))
    return ruta
