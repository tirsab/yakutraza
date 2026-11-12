import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Bandeja } from "./bandeja";
import { VistaCiudadana } from "./ciudadana";
import { fecha } from "./componentes";
import { DetalleProyecto, TableroRutaDelDinero } from "./dinero";
import { t } from "./etiquetas";
import { MiEps } from "./mieps";
import { ExpedienteVivo, ListaExpedientes } from "./paginas";
import { Portada } from "./portada";
import { SesionProvider, useSesion } from "./sesion";
import { TableroGerencial } from "./tablero";

// Enlaces de la barra según las vistas del rol (rules/roles.yaml).
const ENLACES: { vista: string; ruta: string; texto: string }[] = [
  { vista: "bandeja", ruta: "/bandeja", texto: "Mi siguiente acción" },
  { vista: "tablero", ruta: "/tablero", texto: "Tablero gerencial" },
  { vista: "mi_eps", ruta: "/mi-eps", texto: "Mi EPS" },
  { vista: "expedientes", ruta: "/expedientes", texto: "Expedientes" },
  { vista: "ruta_dinero", ruta: "/ruta-del-dinero", texto: "Ruta del dinero" },
  { vista: "ciudadania", ruta: "/ciudadania", texto: "Vista ciudadana" },
];

function SelectorRol() {
  const { config, usuario, verComo } = useSesion();
  const [aviso, setAviso] = useState("");
  if (!config.modo_demo) return null;
  const cambiar = async (rol: string, codEps?: string) => {
    await verComo(rol, codEps);
    setAviso(`Ahora ves YakuTraza como: ${t("rol", rol)}${codEps ? ` (${codEps})` : ""}.`);
  };
  return (
    <div className="selector-rol" role="group" aria-label="Modo demo: ver como">
      <span className="modo-demo">Modo demo</span>
      <label htmlFor="ver-como">Ver como:</label>
      <select id="ver-como" value={usuario.rol} onChange={(e) => cambiar(e.target.value)}>
        {config.roles.map((r) => <option key={r.rol} value={r.rol}>{r.rol === "eps" ? "EPS (elegir cuál)" : r.nombre}</option>)}
      </select>
      {usuario.rol === "eps" && (
        <>
          <label htmlFor="ver-eps" className="oculto">EPS</label>
          <select id="ver-eps" value={usuario.cod_eps ?? ""} onChange={(e) => cambiar("eps", e.target.value)}>
            {config.eps.map((e) => <option key={e.cod_eps} value={e.cod_eps}>{e.cod_eps} · {e.nombre_eps}</option>)}
          </select>
        </>
      )}
      <span className="oculto" role="status" aria-live="polite">{aviso}</span>
    </div>
  );
}

function Barra() {
  const { config, usuario, corte, puedeVer } = useSesion();
  return (
    <header className="encabezado">
      <a className="saltar" href="#contenido">Saltar al contenido principal</a>
      <div className="pagina barra">
        <Link to="/" className="marca" aria-label="YakuTraza, ir a la portada">YakuTraza</Link>
        <nav aria-label="Secciones">
          <ul>
            {ENLACES.filter((e) => puedeVer(e.vista)).map((e) => (
              <li key={e.ruta}><NavLink to={e.ruta}>{e.texto}</NavLink></li>
            ))}
          </ul>
        </nav>
        <SelectorRol />
      </div>
      <div className="franja">
        <div className="pagina franja-contenido">
          <span>{config.rotulo}</span>
          <span>
            Viendo como: <strong>{usuario.rol === "eps" ? `EPS ${usuario.cod_eps}` : t("rol", usuario.rol)}</strong>
            {usuario.rol !== "ciudadania" && <> (usuario ficticio)</>}
            {" · "}Fecha de corte: <strong>{fecha(corte)}</strong>
            {corte !== config.fecha_corte_muestra && <> (la muestra llega al {fecha(config.fecha_corte_muestra)})</>}
          </span>
        </div>
      </div>
    </header>
  );
}

/** La vista solo se muestra si el rol la tiene; si no, explica por qué y ofrece cambiar de rol. */
function Vista({ nombre, children }: { nombre: string; children: ReactNode }) {
  const { puedeVer, usuario, config, verComo } = useSesion();
  if (puedeVer(nombre)) return <>{children}</>;
  const quien = config.roles.filter((r) => r.vistas.includes(nombre));
  return (
    <section className="panel" aria-labelledby="sin-permiso">
      <h1 id="sin-permiso">Esta vista no está disponible para {t("rol", usuario.rol)}</h1>
      <p>Los permisos se definen por rol en <code>rules/roles.yaml</code>.</p>
      {config.modo_demo && quien.length > 0 && (
        <p className="acciones">
          En el modo demo puede verla como:{" "}
          {quien.map((r) => (
            <button key={r.rol} type="button" className="secundario" onClick={() => verComo(r.rol)}>{r.nombre}</button>
          ))}
        </p>
      )}
      <p><Link to={usuario.inicio ?? "/"}>Ir a su vista de inicio</Link></p>
    </section>
  );
}

function Contenido() {
  const { usuario } = useSesion();
  const { pathname } = useLocation();
  const main = useRef<HTMLElement>(null);
  const primera = useRef(true);
  // Al cambiar de página, el foco va al contenido: la navegación funciona con teclado y lector de pantalla.
  useEffect(() => {
    if (primera.current) {
      primera.current = false;
      return;
    }
    main.current?.focus();
  }, [pathname]);
  return (
    <>
      <Barra />
      <main id="contenido" className="pagina" tabIndex={-1} ref={main} key={usuario.id}>
        <Routes>
          <Route path="/" element={<Portada />} />
          <Route path="/bandeja" element={<Vista nombre="bandeja"><Bandeja /></Vista>} />
          <Route path="/tablero" element={<Vista nombre="tablero"><TableroGerencial /></Vista>} />
          <Route path="/mi-eps" element={<Vista nombre="mi_eps"><MiEps /></Vista>} />
          <Route path="/expedientes" element={<Vista nombre="expedientes"><ListaExpedientes /></Vista>} />
          <Route path="/expedientes/:id" element={<Vista nombre="expedientes"><ExpedienteVivo usuario={usuario} /></Vista>} />
          <Route path="/ruta-del-dinero" element={<Vista nombre="ruta_dinero"><TableroRutaDelDinero /></Vista>} />
          <Route path="/proyectos/:cod" element={<Vista nombre="ruta_dinero"><DetalleProyecto /></Vista>} />
          <Route path="/ciudadania" element={<VistaCiudadana />} />
          <Route path="*" element={<section><h1>No encontramos esta página</h1><p><Link to="/">Volver a la portada</Link></p></section>} />
        </Routes>
      </main>
      <footer className="pie">
        <div className="pagina">
          Ninguna salida es una decisión regulatoria: las decisiones son de Sunass. Las reglas de plazo están «por validar».
          Datos sintéticos de la muestra del Hackathon Sunass «Lideresas por el Agua». Código abierto (MIT).
        </div>
      </footer>
    </>
  );
}

export default function App() {
  return (
    <SesionProvider>
      <Contenido />
    </SesionProvider>
  );
}
