import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { pedir } from "./api";
import { Bandeja } from "./bandeja";
import { PaginaBitacora } from "./bitacora";
import { VistaCiudadana } from "./ciudadana";
import { fecha } from "./componentes";
import { DetalleProyecto, TableroRutaDelDinero } from "./dinero";
import { t } from "./etiquetas";
import { MiEps } from "./mieps";
import { ExpedienteVivo, ListaExpedientes } from "./paginas";
import { Portada } from "./portada";
import { SesionProvider, useSesion } from "./sesion";
import { TableroGerencial } from "./tablero";
import { Avatar, ToastProvider } from "./ui";

const ROLES_SUNASS = ["especialista_srt", "coordinacion_srt", "direccion_dre", "otras_areas"];

// ---------------------------------------------------------------- barra DEMO
function BarraDemo() {
  const { config, usuario, verComo, corte } = useSesion();
  const [aviso, setAviso] = useState("");
  const cambiar = async (rol: string, codEps?: string) => {
    await verComo(rol, codEps);
    setAviso(`Ahora ves YakuTraza como: ${t("rol", rol)}${codEps ? ` (${codEps})` : ""}.`);
  };
  return (
    <div className="demo-barra">
      <div className="pagina">
        <span className="demo-etq">{config.modo_demo ? "DEMO" : "PROTOTIPO"}</span>
        <span className="demo-largo">{config.rotulo} · Fecha de corte: {fecha(corte)} · Plazos en días hábiles (DH)</span>
        <span className="demo-corto">Datos sintéticos · Corte {fecha(corte)}</span>
        {config.modo_demo && (
          <div className="demo-sel" role="group" aria-label="Modo demo: ver como">
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
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- vista Sunass
function FechaCompacta() {
  const { corte, setCorte, config } = useSesion();
  return (
    <div className="corte-compacto">
      <label htmlFor="corte-compacto"><strong>Fecha de corte</strong></label>
      <input id="corte-compacto" type="date" value={corte} min={config.corte_min} max={config.corte_max}
             onChange={(e) => { if (e.target.value >= config.corte_min && e.target.value <= config.corte_max) setCorte(e.target.value); }} />
      {corte !== config.fecha_corte_muestra && (
        <button type="button" className="secundario" onClick={() => setCorte(config.fecha_corte_muestra)}>Volver al {fecha(config.fecha_corte_muestra)}</button>
      )}
    </div>
  );
}

function BarraLateral({ abierta, urgentes }: { abierta: boolean; urgentes: number | null }) {
  const { usuario, puedeVer, config, verComo } = useSesion();
  return (
    <aside className={`lateral${abierta ? " abierta" : ""}`} aria-label="Menú de Sunass">
      <Link to="/" className="marca" aria-label="YakuTraza, ir a la portada">YakuTraza<small>SUNASS · DRE</small></Link>
      <div className="usuario-tarjeta">
        <Avatar nombre={usuario.nombre} claro />
        <div><strong>{usuario.nombre}</strong><span>{t("rol", usuario.rol)} · usuario ficticio</span></div>
      </div>
      <nav aria-label="Trabajo">
        <h2>Trabajo</h2>
        <ul>
          {puedeVer("bandeja") && (
            <li><NavLink className="item" to="/bandeja">Mi bandeja
              {urgentes ? <span className="contador" aria-label={`${urgentes} urgentes`}>{urgentes}</span> : null}</NavLink></li>
          )}
          {puedeVer("tablero") && <li><NavLink className="item" to="/tablero">Tablero de dirección</NavLink></li>}
          {puedeVer("expedientes") && <li><NavLink className="item" to="/expedientes" end>Expedientes</NavLink></li>}
          {puedeVer("ruta_dinero") && <li><NavLink className="item" to="/ruta-del-dinero">Ruta del dinero</NavLink></li>}
          <li><NavLink className="item" to="/bitacora">Bitácora</NavLink></li>
        </ul>
      </nav>
      <nav aria-label="Otras vistas">
        <h2>Otras vistas</h2>
        <ul>
          {config.modo_demo && <li><button type="button" className="item" onClick={() => verComo("eps")}>Ver como EPS <span aria-hidden="true">→</span></button></li>}
          <li><NavLink className="item" to="/ciudadania">Ver vista pública <span aria-hidden="true">→</span></NavLink></li>
          <li><Link className="item" to="/">Salir a la portada</Link></li>
        </ul>
      </nav>
      <div className="recordatorio">
        <strong>Cada alerta tiene su fuente</strong>
        La IA propone, una persona confirma. Las decisiones son de Sunass.
      </div>
    </aside>
  );
}

function VistaSunass({ children }: { children: ReactNode }) {
  const { puedeVer, corte } = useSesion();
  const [abierta, setAbierta] = useState(false);
  const [urgentes, setUrgentes] = useState<number | null>(null);
  const { pathname } = useLocation();
  useEffect(() => setAbierta(false), [pathname]);
  useEffect(() => {
    if (!puedeVer("bandeja")) return;
    pedir<{ resumen: Record<string, number> }>(`/bandeja?fecha_corte=${corte}`)
      .then((r) => setUrgentes((r.resumen.vencido ?? 0) + (r.resumen.no_calculable ?? 0) + (r.resumen.por_vencer ?? 0)))
      .catch(() => setUrgentes(null));
  }, [corte, puedeVer]);
  return (
    <div className="sunass">
      <BarraLateral abierta={abierta} urgentes={urgentes} />
      <div className="sunass-cuerpo">
        <header className="sunass-cabecera">
          <button type="button" className="secundario menu-movil" aria-expanded={abierta} onClick={() => setAbierta(!abierta)}>
            {abierta ? "Cerrar menú" : "Menú"}
          </button>
          <FechaCompacta />
        </header>
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- portal EPS
function VistaEps({ children }: { children: ReactNode }) {
  const { usuario, config } = useSesion();
  const nombre = config.eps.find((e) => e.cod_eps === usuario.cod_eps)?.nombre_eps ?? usuario.cod_eps ?? "EPS";
  return (
    <>
      <header className="eps-barra">
        <div className="pagina">
          <Link to="/" className="marca" aria-label="YakuTraza, ir a la portada">YakuTraza<small>PORTAL EPS</small></Link>
          <nav aria-label="Portal EPS">
            <ul>
              <li><Link to="/mi-eps#inicio">Inicio</Link></li>
              <li><Link to="/mi-eps#via">Revisar mi vía</Link></li>
              <li><Link to="/mi-eps#tramites">Mis trámites</Link></li>
              <li><Link to="/mi-eps#fondo">Mi fondo</Link></li>
            </ul>
          </nav>
          <div className="eps-tarjeta">
            <Avatar nombre={nombre} claro />
            <div><strong>{nombre}</strong>{usuario.cod_eps} · usuario ficticio</div>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}

/** La vista solo se muestra si el rol la tiene; si no, explica por qué y ofrece cambiar de rol. */
function Vista({ nombre, children }: { nombre: string; children: ReactNode }) {
  const { puedeVer, usuario, config, verComo } = useSesion();
  if (puedeVer(nombre)) return <>{children}</>;
  const quien = config.roles.filter((r) => r.vistas.includes(nombre));
  return (
    <section className="tarjeta" aria-labelledby="sin-permiso">
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

function Rutas() {
  const { usuario } = useSesion();
  return (
    <Routes>
      <Route path="/bandeja" element={<Vista nombre="bandeja"><Bandeja /></Vista>} />
      <Route path="/tablero" element={<Vista nombre="tablero"><TableroGerencial /></Vista>} />
      <Route path="/mi-eps" element={<Vista nombre="mi_eps"><MiEps /></Vista>} />
      <Route path="/expedientes" element={<Vista nombre="expedientes"><ListaExpedientes /></Vista>} />
      <Route path="/expedientes/:id" element={<Vista nombre="expedientes"><ExpedienteVivo usuario={usuario} /></Vista>} />
      <Route path="/ruta-del-dinero" element={<Vista nombre="ruta_dinero"><TableroRutaDelDinero /></Vista>} />
      <Route path="/proyectos/:cod" element={<Vista nombre="ruta_dinero"><DetalleProyecto /></Vista>} />
      <Route path="/bitacora" element={<Vista nombre="expedientes"><PaginaBitacora /></Vista>} />
      <Route path="*" element={<section><h1>No encontramos esta página</h1><p><Link to="/">Volver a la portada</Link></p></section>} />
    </Routes>
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

  const portada = pathname === "/";
  const ciudadana = pathname.startsWith("/ciudadania");
  const esEps = usuario.rol === "eps";
  const esSunass = ROLES_SUNASS.includes(usuario.rol);
  const cuerpo = portada ? <Portada /> : ciudadana ? <VistaCiudadana /> : <Rutas />;
  const principal = (
    <main id="contenido" tabIndex={-1} ref={main} key={usuario.id}
          className={portada || ciudadana ? "" : esEps ? "pagina eps-contenido" : esSunass ? "sunass-contenido" : "pagina"}>
      {cuerpo}
    </main>
  );
  return (
    <>
      <a className="saltar" href="#contenido">Saltar al contenido principal</a>
      <BarraDemo />
      {portada || ciudadana ? principal : esEps ? <VistaEps>{principal}</VistaEps> : esSunass ? <VistaSunass>{principal}</VistaSunass> : principal}
      {!portada && !ciudadana && (
        <footer className="pie">
          Ninguna salida es una decisión regulatoria: las decisiones son de Sunass. Las reglas de plazo están «por validar».
          Datos sintéticos de la muestra del Hackathon Sunass «Lideresas por el Agua». Código abierto (MIT).
        </footer>
      )}
    </>
  );
}

export default function App() {
  return (
    <SesionProvider>
      <ToastProvider>
        <Contenido />
      </ToastProvider>
    </SesionProvider>
  );
}
