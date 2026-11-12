// Declaración mínima para leer archivos en las pruebas (Vitest corre en Node) sin instalar @types/node.
declare module "node:fs" {
  export function readFileSync(ruta: string, codificacion: string): string;
}
