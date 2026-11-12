import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { fijarUsuario, pedir, type Config, type UsuarioDemo } from "./api";
import { cargarEtiquetas } from "./etiquetas";

// Sesión de la demo: quién mira (selector «Ver como») y a qué fecha de corte.
interface Sesion {
  config: Config;
  usuario: UsuarioDemo;
  corte: string;
  setCorte: (f: string) => void;
  verComo: (rol: string, codEps?: string) => Promise<void>;
  puedeVer: (vista: string) => boolean;
  puede: (permiso: string) => boolean;
}

const Contexto = createContext<Sesion | null>(null);
/** Solo para pruebas: permite montar una vista con una sesión fija. */
export const ContextoSesion = Contexto;
export type { Sesion };

export function useSesion(): Sesion {
  const s = useContext(Contexto);
  if (!s) throw new Error("useSesion fuera de SesionProvider");
  return s;
}

const CLAVE = "yakutraza.usuario";

function leerGuardado(): string | null {
  try {
    return window.localStorage.getItem(CLAVE);
  } catch {
    return null;
  }
}

function guardar(id: string | null) {
  try {
    if (id) window.localStorage.setItem(CLAVE, id);
    else window.localStorage.removeItem(CLAVE);
  } catch {
    /* sin almacenamiento: la sesión vive solo en memoria */
  }
}

export function idDeRol(config: Config, rol: string, codEps?: string): string | null {
  if (rol === "ciudadania") return null;
  if (rol === "eps") return `eps-${codEps ?? config.eps[0]?.cod_eps ?? "EPS01"}`;
  return config.roles.find((r) => r.rol === rol)?.usuario ?? null;
}

export function SesionProvider({ children }: { children: ReactNode }) {
  const navegar = useNavigate();
  const [config, setConfig] = useState<Config | null>(null);
  const [usuario, setUsuario] = useState<UsuarioDemo | null>(null);
  const [corte, setCorte] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const entrar = useCallback(async (id: string | null) => {
    fijarUsuario(id);
    const u = await pedir<UsuarioDemo>("/sesion");
    setUsuario(u);
    guardar(id);
    return u;
  }, []);

  const [intento, setIntento] = useState(0);
  useEffect(() => {
    (async () => {
      try {
        // La API puede estar arrancando (por ejemplo, justo después de levantar Docker): se reintenta unas veces.
        let ultimo: unknown = null;
        let datos: [Config, { categorias: Record<string, Record<string, string>> }] | null = null;
        for (let i = 0; i < 6 && !datos; i++) {
          try {
            datos = await Promise.all([
              pedir<Config>("/config"),
              pedir<{ categorias: Record<string, Record<string, string>> }>("/etiquetas"),
            ]);
          } catch (e) {
            ultimo = e;
            await new Promise((r) => setTimeout(r, 1500));
          }
        }
        if (!datos) throw ultimo;
        const [cfg, etq] = datos;
        cargarEtiquetas(etq.categorias);
        setConfig(cfg);
        // Enlaces de demo: ?como=<usuario ficticio> y ?corte=AAAA-MM-DD (solo en modo demo).
        const url = new URLSearchParams(window.location.search);
        const corteUrl = url.get("corte");
        setCorte(cfg.modo_demo && corteUrl && /^\d{4}-\d{2}-\d{2}$/.test(corteUrl) && corteUrl >= cfg.corte_min
                 && corteUrl <= cfg.corte_max ? corteUrl : cfg.fecha_corte_muestra);
        const comoUrl = cfg.modo_demo ? url.get("como") : null;
        const inicial = !cfg.modo_demo || comoUrl === "ciudadania" ? null
          : comoUrl ?? leerGuardado() ?? idDeRol(cfg, "especialista_srt");
        await entrar(inicial).catch(() => entrar(null));
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [entrar, intento]);

  const verComo = useCallback(async (rol: string, codEps?: string) => {
    if (!config) return;
    const u = await entrar(idDeRol(config, rol, codEps));
    navegar(u.inicio ?? "/");
  }, [config, entrar, navegar]);

  const valor = useMemo<Sesion | null>(() => {
    if (!config || !usuario) return null;
    return {
      config, usuario, corte, setCorte, verComo,
      puedeVer: (v: string) => v === "ciudadania" || (usuario.vistas ?? []).includes(v),
      puede: (p: string) => usuario.permisos.includes(p),
    };
  }, [config, usuario, corte, verComo]);

  if (error) {
    return (
      <div className="pagina" style={{ paddingTop: 24 }}>
        <p className="mensaje mensaje-error" role="alert">
          No se pudo conectar con el servidor de YakuTraza ({error}). Si acaba de iniciar Docker, espere unos segundos.
        </p>
        <button type="button" onClick={() => { setError(null); setIntento((n) => n + 1); }}>Reintentar</button>
      </div>
    );
  }
  if (!valor) return <p className="cargando">Cargando YakuTraza…</p>;
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}
