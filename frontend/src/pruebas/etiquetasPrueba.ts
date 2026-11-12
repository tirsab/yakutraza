/// <reference types="vite/client" />
// Las pruebas usan las etiquetas reales (una sola fuente: rules/etiquetas.yaml).
import texto from "../../../rules/etiquetas.yaml?raw";

export function leerCategorias(yaml: string): Record<string, Record<string, string>> {
  const res: Record<string, Record<string, string>> = {};
  let dentro = false;
  let actual: Record<string, string> | null = null;
  for (const linea of yaml.split(/\r?\n/)) {
    if (/^categorias:\s*$/.test(linea)) { dentro = true; continue; }
    if (!dentro || /^\s*#/.test(linea) || !linea.trim()) continue;
    const cat = linea.match(/^ {2}([a-z_]+):\s*$/);
    if (cat) { actual = res[cat[1]] = {}; continue; }
    const par = linea.match(/^ {4}"?([^":]+?)"?:\s*"(.*)"\s*$/);
    if (par && actual) actual[par[1]] = par[2];
  }
  return res;
}

export const CATEGORIAS = leerCategorias(texto);
