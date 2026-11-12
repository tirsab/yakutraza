// Etiquetas en lenguaje claro (rules/etiquetas.yaml vía GET /api/etiquetas).
// La interfaz nunca muestra un código con guion bajo: si falta la etiqueta, quita los guiones.

type Catalogo = Record<string, Record<string, string>>;
let CAT: Catalogo = {};

export function cargarEtiquetas(c: Catalogo) {
  CAT = c ?? {};
}

function sinGuiones(codigo: string): string {
  if (!codigo.includes("_")) return codigo; // texto libre (p. ej., un fondo transcrito de una resolución)
  const s = codigo.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Etiqueta de un código dentro de una categoría (hito, estado_reloj, fondo…). */
export function t(categoria: string, codigo: string | null | undefined): string {
  if (codigo == null || codigo === "") return "—";
  return CAT[categoria]?.[codigo] ?? sinGuiones(String(codigo));
}

const CODIGO = /\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g;
const FECHA_ISO = /\b(\d{4})-(\d{2})-(\d{2})\b/g;

/** Texto libre (mensajes del motor, fuentes): códigos con etiqueta y fechas en formato día/mes/año. */
export function humanizar(texto: string | null | undefined): string {
  if (!texto) return "";
  return texto.replace(FECHA_ISO, "$3/$2/$1").replace(CODIGO, (c) => {
    for (const cat of Object.values(CAT)) if (cat[c]) return cat[c].charAt(0).toLowerCase() + cat[c].slice(1);
    return c.replace(/_/g, " ");
  });
}
