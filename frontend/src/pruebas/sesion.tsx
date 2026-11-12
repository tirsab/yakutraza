import type { ReactNode } from "react";
import type { Config, UsuarioDemo } from "../api";
import { ContextoSesion, type Sesion } from "../sesion";

export const configPrueba: Config = {
  modo_demo: true, fecha_corte_muestra: "2026-09-30", corte_min: "2022-01-19", corte_max: "2026-09-30",
  rotulo: "Prototipo con datos sintéticos de la muestra del Hackathon Sunass",
  roles: [
    { rol: "especialista_srt", nombre: "Especialista SRT", inicio: "/bandeja", vistas: ["bandeja", "expedientes", "ruta_dinero"], usuario: "esp-srt-01" },
    { rol: "coordinacion_srt", nombre: "Coordinación SRT", inicio: "/tablero", vistas: ["tablero", "simulador", "bandeja", "expedientes", "ruta_dinero"], usuario: "coord-srt-01" },
    { rol: "direccion_dre", nombre: "Dirección DRE", inicio: "/tablero", vistas: ["tablero", "simulador", "expedientes", "ruta_dinero"], usuario: "dir-dre-01" },
    { rol: "otras_areas", nombre: "Otras áreas (solo lectura)", inicio: "/expedientes", vistas: ["expedientes", "ruta_dinero"], usuario: "area-01" },
    { rol: "eps", nombre: "EPS", inicio: "/mi-eps", vistas: ["mi_eps", "expedientes"], usuario: null },
    { rol: "ciudadania", nombre: "Ciudadanía", inicio: "/ciudadania", vistas: ["ciudadania"], usuario: null },
  ],
  eps: [{ cod_eps: "EPS02", nombre_eps: "EPS Manantial S.A." }, { cod_eps: "EPS07", nombre_eps: "EPS Siete" }],
};

export function usuarioPrueba(rol: string, extra: Partial<UsuarioDemo> = {}): UsuarioDemo {
  const r = configPrueba.roles.find((x) => x.rol === rol)!;
  return { id: r.usuario ?? (rol === "eps" ? "eps-EPS02" : "ciudadania"), nombre: rol === "especialista_srt" ? "Especialista SRT (ficticia)" : `${r.nombre} (ficticio)`, rol,
    permisos: rol === "especialista_srt" || rol === "coordinacion_srt" ? ["registrar_documento", "confirmar_registro"] : [],
    cod_eps: rol === "eps" ? "EPS02" : null, rotulo: "Usuario ficticio de demostración", vistas: r.vistas, inicio: r.inicio, ...extra };
}

export function sesionPrueba(rol = "especialista_srt", extra: Partial<Sesion> = {}): Sesion {
  const usuario = usuarioPrueba(rol);
  return {
    config: configPrueba, usuario, corte: "2026-09-30", setCorte: () => {}, verComo: async () => {},
    puedeVer: (v) => v === "ciudadania" || (usuario.vistas ?? []).includes(v), puede: (p) => usuario.permisos.includes(p),
    ...extra,
  };
}

export function ConSesion({ sesion, children }: { sesion: Sesion; children: ReactNode }) {
  return <ContextoSesion.Provider value={sesion}>{children}</ContextoSesion.Provider>;
}

export function respuesta(cuerpo: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } }));
}
