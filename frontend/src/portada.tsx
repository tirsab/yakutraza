import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSesion } from "./sesion";

const PASOS = [
  { t: "La EPS revisa su vía y presenta", d: "Sabe si su pedido va por el art. 93 o el 94 del RGT antes de enviarlo." },
  { t: "Sunass sigue cada paso con evidencia", d: "Próxima acción, responsable y tres plazos: normativo, interno y del oficio." },
  { t: "Se sigue el dinero", d: "Lo programado, lo solicitado, lo autorizado y lo usado, con su fuente." },
  { t: "La ciudadanía ve su obra", d: "En lenguaje simple, con audio y fechas para participar." },
];

const PRINCIPIOS = [
  { i: "IA", t: "La IA propone, una persona confirma", d: "Lo transcrito con asistencia de IA entra como propuesta, con su cita. Nada cambia los plazos sin revisión humana." },
  { i: "§", t: "Cada alerta tiene su fuente", d: "Toda alerta muestra la regla (RGT, flujograma, oficio) o el documento que la origina." },
  { i: "✓", t: "Las decisiones son de Sunass", d: "YakuTraza ordena y avisa; las decisiones regulatorias siguen a cargo de Sunass." },
];

const ROLES_SUNASS = [
  { rol: "especialista_srt", nombre: "Especialista SRT" },
  { rol: "coordinacion_srt", nombre: "Coordinación SRT" },
  { rol: "direccion_dre", nombre: "Dirección DRE" },
  { rol: "otras_areas", nombre: "Otras áreas (solo lectura)" },
];

export function Portada() {
  const { config, verComo } = useSesion();
  const navegar = useNavigate();
  const [rolSunass, setRolSunass] = useState("especialista_srt");
  const [eps, setEps] = useState(config.eps[0]?.cod_eps ?? "");
  const demo = config.modo_demo;
  return (
    <div className="portada">
      <section className="hero" aria-labelledby="portada-titulo">
        <div className="pagina hero-nav">
          <span className="marca">YakuTraza</span>
          <nav aria-label="Portada">
            <a href="#como" style={{ color: "#fff", marginRight: 16 }}>Cómo funciona</a>
            <Link to="/ciudadania" style={{ color: "#fff" }}>Consulta ciudadana</Link>
          </nav>
        </div>
        <div className="pagina hero-cuerpo">
          <div>
            <span className="hero-etq">TRAZABILIDAD · AGUA Y SANEAMIENTO</span>
            <h1 id="portada-titulo">Cada trámite y cada sol, a la vista.</h1>
            <p>YakuTraza: seguimiento verificable de trámites y recursos de inversión de las EPS. Muestra la próxima acción,
              el documento que respalda cada paso, los plazos y por dónde se mueve el dinero, hasta la obra de tu distrito.</p>
            <div className="hero-botones">
              {demo && <button type="button" className="claro" onClick={() => verComo("especialista_srt")}>Ver vista Sunass</button>}
              <button type="button" className="fantasma" onClick={() => navegar("/ciudadania")}>Consultar obras de mi zona →</button>
            </div>
          </div>
          <section className="como-funciona" id="como" aria-labelledby="como-titulo">
            <h2 id="como-titulo">CÓMO FUNCIONA</h2>
            <ol>
              {PASOS.map((p, i) => (
                <li key={p.t}><span className="paso-num" aria-hidden="true">{i + 1}</span><span><strong>{p.t}</strong>{p.d}</span></li>
              ))}
            </ol>
          </section>
        </div>
      </section>

      <div className="pagina">
        <ul className="accesos" aria-label="Accesos por rol">
          <li className="tarjeta acceso elevable">
            <span className="icono" aria-hidden="true">⚖</span>
            <span className="pildora pil-info" style={{ alignSelf: "flex-start" }}>Acceso privado</span>
            <h3>Sunass</h3>
            <p className="detalle">Especialistas, coordinación y dirección de la DRE</p>
            <ul>
              <li>Bandeja con la próxima acción</li>
              <li>Línea de tiempo con documentos</li>
              <li>Alertas con su fuente</li>
              <li>Tablero de dirección</li>
            </ul>
            {demo ? (
              <>
                <label className="campo" htmlFor="rol-sunass">Rol (modo demo)
                  <select id="rol-sunass" value={rolSunass} onChange={(e) => setRolSunass(e.target.value)}>
                    {ROLES_SUNASS.map((r) => <option key={r.rol} value={r.rol}>{r.nombre}</option>)}
                  </select>
                </label>
                <button type="button" onClick={() => verComo(rolSunass)}>Ingresar como Sunass →</button>
              </>
            ) : <p className="detalle">Requiere acceso institucional: no está disponible en el enlace público.</p>}
          </li>
          <li className="tarjeta acceso elevable">
            <span className="icono" aria-hidden="true">🏢</span>
            <span className="pildora pil-info" style={{ alignSelf: "flex-start" }}>Acceso privado</span>
            <h3>EPS</h3>
            <p className="detalle">Empresas prestadoras de saneamiento</p>
            <ul>
              <li>Revisión previa de la vía (art. 93 o 94)</li>
              <li>Qué pidió Sunass y hasta cuándo</li>
              <li>Mis trámites paso a paso</li>
              <li>Mi fondo de inversiones</li>
            </ul>
            {demo ? (
              <>
                <label className="campo" htmlFor="eps-portada">Empresa (modo demo)
                  <select id="eps-portada" value={eps} onChange={(e) => setEps(e.target.value)}>
                    {config.eps.map((e) => <option key={e.cod_eps} value={e.cod_eps}>{e.cod_eps} · {e.nombre_eps}</option>)}
                  </select>
                </label>
                <button type="button" onClick={() => verComo("eps", eps)}>Ingresar como EPS →</button>
              </>
            ) : <p className="detalle">Requiere acceso institucional: no está disponible en el enlace público.</p>}
          </li>
          <li className="tarjeta acceso elevable">
            <span className="icono" aria-hidden="true">💧</span>
            <span className="pildora pil-ok" style={{ alignSelf: "flex-start" }}>Ingreso libre</span>
            <h3>Ciudadanía</h3>
            <p className="detalle">Cualquier persona, desde el celular</p>
            <ul>
              <li>Mapa esquemático de obras por distrito</li>
              <li>6 etapas en lenguaje simple</li>
              <li>Resumen en audio</li>
              <li>Fechas para participar</li>
            </ul>
            <button type="button" onClick={() => (demo ? verComo("ciudadania").then(() => navegar("/ciudadania")) : navegar("/ciudadania"))}>
              Consultar sin registrarme →
            </button>
          </li>
        </ul>

        <section className="principios" aria-label="Principios">
          {PRINCIPIOS.map((p) => (
            <div key={p.t} className="principio">
              <span className="icono" aria-hidden="true">{p.i}</span>
              <div><h3 style={{ marginTop: 0 }}>{p.t}</h3><p className="detalle">{p.d}</p></div>
            </div>
          ))}
        </section>

        <footer className="pie-sintetico">
          <strong>YakuTraza</strong> · Seguimiento verificable de trámites y recursos de inversión de las EPS · Prototipo.<br />
          <span className="rotulo-prototipo">{config.rotulo}</span>: las EPS, expedientes y montos de la muestra son sintéticos.
          Ninguna salida es una decisión regulatoria. Código abierto (MIT).
        </footer>
      </div>
    </div>
  );
}
