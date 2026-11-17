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

// Nombre legible de cada dataset del hackathon (diccionario de variables). La interfaz nunca muestra el nombre del archivo.
const DATASETS: Record<string, string> = {
  ds01_catalogo_eps: "Catálogo de EPS", ds01_localidades_eps: "Localidades de las EPS",
  ds02_procedimientos: "Procedimientos", ds02_hitos_procedimientos: "Hitos de los procedimientos",
  ds03_programa_inversiones: "Programa de inversiones", ds04_ejecucion_inversiones: "Ejecución de inversiones",
  ds05_fondo_inversiones_reservas: "Fondo de inversiones y reservas", ds06_estados_financieros: "Estados financieros",
  ds07_metas_gestion: "Metas de gestión", ds08_inversiones_mef: "Inversiones del MEF (simulado)",
  ds09_ipm: "Índice de precios al por mayor",
};
// Dataset principal de cada código, para las citas sin nombre de archivo («DS02 fila 12»).
const POR_CODIGO: Record<string, string> = {
  DS01: "ds01_catalogo_eps", DS02: "ds02_procedimientos", DS03: "ds03_programa_inversiones",
  DS04: "ds04_ejecucion_inversiones", DS05: "ds05_fondo_inversiones_reservas", DS06: "ds06_estados_financieros",
  DS07: "ds07_metas_gestion", DS08: "ds08_inversiones_mef", DS09: "ds09_ipm",
};
const DS_ARCHIVO = /\b(DS0\d)\s+(ds0\d_[a-z_]+)\b/g;
const DS_FILA = /\b(DS0\d)(\s+filas?\b)/g;
const ARCHIVO_SUELTO = /\bds0\d_[a-z_]+\b/g;

/** «DS05 ds05_fondo_inversiones_reservas, fila 12» → «DS05 · Fondo de inversiones y reservas, fila 12». */
export function datasetsLegibles(texto: string): string {
  return texto
    .replace(DS_ARCHIVO, (m, cod: string, arch: string) => (DATASETS[arch] ? `${cod} · ${DATASETS[arch]}` : m))
    .replace(DS_FILA, (_m, cod: string, resto: string) => (POR_CODIGO[cod] ? `${cod} · ${DATASETS[POR_CODIGO[cod]]},${resto}` : _m))
    .replace(ARCHIVO_SUELTO, (arch) => {
      const cod = arch.slice(0, 4).toUpperCase();
      return DATASETS[arch] ? `${cod} · ${DATASETS[arch]}` : arch;
    });
}

/** Texto libre (mensajes del motor, fuentes): datasets y códigos con etiqueta, y fechas en formato día/mes/año. */
export function humanizar(texto: string | null | undefined): string {
  if (!texto) return "";
  return datasetsLegibles(texto).replace(FECHA_ISO, "$3/$2/$1").replace(CODIGO, (c) => {
    for (const cat of Object.values(CAT)) if (cat[c]) return cat[c].charAt(0).toLowerCase() + cat[c].slice(1);
    return c.replace(/_/g, " ");
  });
}
