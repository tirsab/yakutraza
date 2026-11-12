import type { Proyecto, RutaUso } from "./dinero";
// Cliente de la API de YakuTraza. En desarrollo y en Docker, /api se redirige a FastAPI.

export type Estado = "vencido" | "por_vencer" | "en_plazo" | "no_calculable" | "cumplido" | "incumplido";

export interface Alerta {
  expediente: string;
  reloj: "normativo" | "interno" | "oficio";
  estado: Estado;
  titulo: string;
  mensaje: string;
  regla_id: string | null;
  fuente: string;
  estado_validacion: string;
  respaldo: string | null;
  hito: string | null;
  etapa: string | null;
  fecha_limite: string | null;
  dias_restantes: number | null;
  documento_inicio: string | null;
  documento_estado: string | null;
  discrepancia: { fuente: string; valor: string; descripcion: string } | null;
  detalle: Record<string, unknown>;
}

export interface Hito {
  nro: number;
  hito: string;
  descripcion: string | null;
  etapa: string | null;
  responsable: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  plazo_referencial_dh: number | null;
  cuenta_plazo: boolean | null;
  estado: string;
  fila_ds02: number | null;
  evidencia: { estado: string; referencia: string | null; codigo_ds02: string | null; tipo: string | null; documentos: number[] };
}

export interface Documento {
  id: number;
  clave: string;
  hito: string | null;
  tipo: string;
  numero: string | null;
  canal: string;
  fecha_emision: string | null;
  fecha_recepcion: string | null;
  fecha_notificacion: string | null;
  naturaleza: string;
  origen: string;
  estado_registro: "propuesto" | "confirmado";
  fuente: string | null;
  cita: string | null;
  pagina?: number | null;
  registrado_por: string;
  confirmado_por: string | null;
}

export interface Evento {
  id: number;
  origen?: string;
  hito: string;
  tipo: string;
  dias_dh: number | null;
  estado_registro: "propuesto" | "confirmado";
  naturaleza: string;
  fuente: string | null;
  cita: string | null;
}

export interface EntradaBitacora {
  id: number;
  cuando: string;
  usuario: string;
  rol: string;
  accion: string;
  entidad: string;
  entidad_id: string;
  motivo: string | null;
  hash: string;
}

export interface Prechequeo {
  ruta: string;
  titulo: string;
  regla_aplicada: string;
  texto_citado: { ubicacion: string; texto: string }[];
  explicacion: string;
  calculos: Record<string, unknown>;
  advertencias: string[];
  faltantes: string[];
  supuestos: string[];
  estado_validacion: string;
  aviso: string;
}

export interface Ficha {
  expediente: Record<string, unknown> & { id_expediente: string; naturaleza: string; tipo_procedimiento: string };
  fecha_corte: string;
  pasos?: import("./ui").Pasos | null;
  linea_de_tiempo: Hito[];
  relojes: Alerta[];
  documentos: Documento[];
  eventos: Evento[];
  proyectos: Record<string, unknown>[];
  prechequeo: Prechequeo | null;
  bitacora: EntradaBitacora[];
  ruta_dinero?: RutaUso | { proyectos: Proyecto[] } | null;
}

export interface FilaExpediente {
  id_expediente: string;
  cod_eps: string | null;
  tipo_procedimiento: string;
  estado: string;
  fecha_inicio: string | null;
  hito_actual: string | null;
  responsable_actual: string | null;
  naturaleza: string;
  empresa?: string;
}

export interface UsuarioDemo {
  id: string;
  nombre: string;
  rol: string;
  permisos: string[];
  cod_eps: string | null;
  rotulo: string;
  vistas?: string[];
  inicio?: string;
  alcance?: string;
}

export interface Config {
  modo_demo: boolean;
  fecha_corte_muestra: string;
  corte_min: string;
  corte_max: string;
  rotulo: string;
  roles: { rol: string; nombre: string; inicio: string; vistas: string[]; usuario: string | null }[];
  eps: { cod_eps: string; nombre_eps: string }[];
  privacidad?: { casos_reales_privados: boolean; rastros_privados: Record<string, number> | null };
}

// Usuario de demostración activo (selector «Ver como»). Se envía en cada pedido.
let usuarioActual: string | null = null;
export function fijarUsuario(id: string | null) {
  usuarioActual = id;
}

export async function pedir<T>(ruta: string, init: RequestInit = {}, usuario?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const quien = usuario ?? usuarioActual;
  if (quien) headers["X-Usuario"] = quien;
  const r = await fetch(`/api${ruta}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
  if (!r.ok) {
    let detalle = `${r.status}`;
    try {
      const j = await r.json();
      detalle = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detalle);
  }
  return r.json() as Promise<T>;
}

export const api = {
  usuarios: () => pedir<UsuarioDemo[]>("/usuarios-demo"),
  expedientes: () => pedir<FilaExpediente[]>("/expedientes"),
  ficha: (id: string, corte?: string) =>
    pedir<Ficha>(`/expedientes/${encodeURIComponent(id)}${corte ? `?fecha_corte=${corte}` : ""}`),
  registrarDocumento: (id: string, datos: Record<string, unknown>, usuario?: string) =>
    pedir<{ id: number }>(`/expedientes/${encodeURIComponent(id)}/documentos`, { method: "POST", body: JSON.stringify(datos) }, usuario),
  confirmarDocumento: (docId: number, usuario?: string) =>
    pedir<unknown>(`/documentos/${docId}/confirmar`, { method: "POST" }, usuario),
  confirmarEvento: (evId: number, usuario?: string) =>
    pedir<unknown>(`/eventos/${evId}/confirmar`, { method: "POST" }, usuario),
};
