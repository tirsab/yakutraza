// Íconos de línea de YakuTraza: trazo de 1,8 px, puntas redondeadas y color del texto (currentColor).
// Sin `titulo` son decorativos (aria-hidden); con `titulo` se anuncian como imagen con ese nombre.

const TRAZOS: Record<string, string[]> = {
  reloj: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 7v5l3 2"],
  documento: ["M7 3h7l5 5v13H7z", "M14 3v5h5", "M10 13h6", "M10 17h6"],
  balanza: ["M12 4v16", "M8 20h8", "M5 7h14", "M5 7l-3 6a3 3 0 0 0 6 0Z", "M19 7l-3 6a3 3 0 0 0 6 0Z"],
  bandeja: ["M3 13h5l1.5 3h5L16 13h5", "M5.5 5h13L21 13v6H3v-6Z"],
  tablero: ["M4 20V10", "M10 20V4", "M16 20v-7", "M3 20h18"],
  carpeta: ["M3 7h6l2 2h10v10H3Z"],
  dinero: ["M3 7h18v10H3Z", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z", "M6 10v4", "M18 10v4"],
  bitacora: ["M5 4h14v16H5Z", "M9 8h6", "M9 12h6", "M9 16h4"],
  eps: ["M4 20V9l8-5 8 5v11", "M9 20v-6h6v6"],
  ojo: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"],
  salir: ["M14 4h5v16h-5", "M10 8l-4 4 4 4", "M6 12h10"],
  plegar: ["M15 6l-6 6 6 6"],
  desplegar: ["M9 6l6 6-6 6"],
  info: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 11v5", "M12 8h.01"],
  filtro: ["M4 5h16l-6 8v6l-4-2v-4Z"],
  calendario: ["M4 6h16v14H4Z", "M4 10h16", "M8 3v4", "M16 3v4"],
  cerrar: ["M6 6l12 12", "M18 6 6 18"],
  flecha: ["M5 12h14", "M13 6l6 6-6 6"],
  sonido: ["M4 10v4h4l5 4V6L8 10Z", "M16 9a4 4 0 0 1 0 6"],
  detener: ["M7 7h10v10H7Z"],
};

export type NombreIcono = keyof typeof TRAZOS;

export function Icono({ nombre, titulo, tam = 20, className }: { nombre: string; titulo?: string; tam?: number; className?: string }) {
  const trazos = TRAZOS[nombre] ?? [];
  const accesible = titulo ? { role: "img", "aria-label": titulo } : { "aria-hidden": true as const, focusable: "false" as const };
  return (
    <svg className={`icono${className ? ` ${className}` : ""}`} width={tam} height={tam} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" {...accesible}>
      {trazos.map((d) => <path key={d} d={d} />)}
    </svg>
  );
}
