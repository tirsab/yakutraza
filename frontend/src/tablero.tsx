import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { pedir } from "./api";
import { EstadoAlerta, fecha } from "./componentes";
import { humanizar, t } from "./etiquetas";
import { useSesion } from "./sesion";

// ------------------------------------------------------------------ tipos
type Ids = { n: number; ids: string[] };
interface Grupo { superan: number; calculables: number; no_calculables: number; porcentaje: number | null;
  ids_superan: string[]; en_tramite_superan: number }
interface Cuello { clave: string; n: number; mediana_dh: number | null; p90_dh: number | null; max_dh: number;
  en_curso: number; ids_en_curso: string[]; supera_referencial: number; con_referencial: number;
  plazo_referencial_dh: number[]; responsables: string[] }
interface FilaExp { id_expediente: string; cod_eps: string; tipo_procedimiento: string; especialista: string;
  estado: string; hito_al_corte: string | null; responsable_al_corte: string | null;
  alerta: { reloj: string; titulo: string; dias_restantes: number | null; fecha_limite: string | null } | null }
interface Tablero {
  fecha_corte: string; fecha_corte_muestra: string; corte_min: string;
  opciones: Record<string, string[]>;
  indicadores: Record<string, Ids>;
  expedientes: FilaExp[];
  supera_plazo: { rotulo: string; total: Grupo; por_tipo: Record<string, Grupo>; por_eps: Record<string, Grupo>;
    formula: string; nota: string; fuente: string; a_la_fecha: string };
  cuellos: { por_hito: Cuello[]; por_responsable: Cuello[]; fechas_inconsistentes: unknown[]; nota: string; fuente: string };
  embudo: { etapas: { clave: string; nombre: string; llegaron: number; en_curso: number; ids_en_curso: string[];
    mediana_dh: number | null; p90_dh: number | null }[]; sustento: string; fuente: string };
  carga: { actual: { especialista: string; n: number; carga: number; vencidos: number; por_vencer: number;
    no_calculable: number }[]; propuesta: { especialista: string; carga: number }[];
    movimientos: { id_expediente: string; tipo_procedimiento: string; de: string; a: string; peso: number }[];
    desbalance_actual: number; desbalance_propuesto: number; pesos: Record<string, number>;
    sustento_pesos: string; pregunta_dre: string; rotulo: string; aviso: string };
  calidad: { total: number; por_severidad: Record<string, number>; por_tipo: Record<string, number>;
    reglas: { regla_id: string; titulo: string; severidad: string; n: number }[]; reporte: string; nota: string };
}

const INDICADORES: { clave: string; titulo: string; estado?: string }[] = [
  { clave: "en_tramite", titulo: "En trámite" },
  { clave: "vencido", titulo: "Vencidos", estado: "vencido" },
  { clave: "por_vencer", titulo: "Por vencer", estado: "por_vencer" },
  { clave: "no_calculable", titulo: "No puedo calcular", estado: "no_calculable" },
  { clave: "en_plazo", titulo: "En plazo", estado: "en_plazo" },
];

// ------------------------------------------------------------- utilidades
const DIA = 86400000;
const aFecha = (s: string) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
const aTexto = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const uno = (v: number | null | undefined) => (v == null ? "—" : v.toLocaleString("es-PE", { maximumFractionDigits: 1 }).replace(".", ","));

function Barra({ valor, maximo, etiqueta }: { valor: number; maximo: number; etiqueta: string }) {
  const id = useId().replace(/:/g, "");
  const ancho = maximo > 0 ? Math.max(0, (valor / maximo) * 100) : 0;
  return (
    <svg className="barra-svg" width="160" height="14" role="img" aria-label={etiqueta}>
      <defs>
        <pattern id={`p${id}`} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="2" height="4" fill="var(--yt-blue-600)" />
        </pattern>
      </defs>
      <rect x="0" y="1" width="100%" height="12" fill="var(--yt-ice-50)" stroke="var(--yt-borde)" />
      <rect x="0" y="1" width={`${ancho}%`} height="12" fill={`url(#p${id})`} stroke="var(--yt-blue-600)" />
    </svg>
  );
}

// ------------------------------------------------------ selector de fecha
export function SelectorFecha() {
  const { corte, setCorte, config } = useSesion();
  const min = aFecha(config.corte_min);
  const max = aFecha(config.corte_max);
  const [texto, setTexto] = useState(corte);
  useEffect(() => setTexto(corte), [corte]);
  const mover = (dias: number) => setCorte(aTexto(Math.min(max, Math.max(min, aFecha(corte) + dias * DIA))));
  const valido = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s) && aFecha(s) >= min && aFecha(s) <= max;
  return (
    <section className="panel-fecha" aria-labelledby="fecha-titulo">
      <div className="panel-fecha-cabecera">
        <h2 id="fecha-titulo">Fecha de corte</h2>
        <p className="fecha-grande" aria-live="polite">{fecha(corte)}</p>
      </div>
      <p className="sub" id="fecha-ayuda">
        Mueva la fecha para ver cómo cada expediente pasa de «en plazo» a «por vencer» y a «vencido». Los hechos
        posteriores a la fecha elegida aún no se conocen. La muestra llega al {fecha(config.corte_max)}.
      </p>
      <div className="fecha-controles">
        <label htmlFor="fecha-corte">Fecha</label>
        <input id="fecha-corte" type="date" min={config.corte_min} max={config.corte_max} value={texto}
               aria-describedby="fecha-ayuda"
               onChange={(e) => { setTexto(e.target.value); if (valido(e.target.value)) setCorte(e.target.value); }} />
        <button type="button" className="secundario" onClick={() => mover(-7)}>− 1 semana</button>
        <button type="button" className="secundario" onClick={() => mover(-1)}>− 1 día</button>
        <button type="button" className="secundario" onClick={() => mover(1)}>+ 1 día</button>
        <button type="button" className="secundario" onClick={() => mover(7)}>+ 1 semana</button>
        <button type="button" onClick={() => setCorte(config.fecha_corte_muestra)}
                disabled={corte === config.fecha_corte_muestra}>Volver a la fecha de la muestra</button>
      </div>
      <label htmlFor="fecha-deslizador" className="oculto">Deslizar la fecha de corte</label>
      <input id="fecha-deslizador" className="deslizador" type="range" min={0} max={Math.round((max - min) / DIA)}
             value={Math.round((aFecha(corte) - min) / DIA)} aria-valuetext={fecha(corte)}
             onChange={(e) => setCorte(aTexto(min + Number(e.target.value) * DIA))} />
    </section>
  );
}

// ------------------------------------------------------------- tablero
export function TableroGerencial() {
  const { corte, usuario } = useSesion();
  const [filtros, setFiltros] = useState({ tipo: "", cod_eps: "", responsable: "", especialista: "", estado: "" });
  const [d, setD] = useState<Tablero | null>(null);
  const [error, setError] = useState<string | null>(null);
  const previo = useRef<Record<string, Ids> | null>(null);
  const [cambios, setCambios] = useState<Record<string, number>>({});
  const lista = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const q = new URLSearchParams({ fecha_corte: corte });
    Object.entries(filtros).forEach(([k, v]) => v && q.set(k, v));
    pedir<Tablero>(`/tablero?${q}`).then((r) => {
      if (previo.current) {
        const dif: Record<string, number> = {};
        for (const i of INDICADORES) dif[i.clave] = r.indicadores[i.clave].n - (previo.current[i.clave]?.n ?? 0);
        setCambios(dif);
      }
      previo.current = r.indicadores;
      setD(r);
      setError(null);
    }).catch((e) => setError(e.message));
  }, [corte, filtros]);

  const elegir = (estado: string) => {
    setFiltros({ ...filtros, estado: filtros.estado === estado ? "" : estado });
    setTimeout(() => lista.current?.focus(), 0);
  };
  const cambiar = (k: keyof typeof filtros) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    setFiltros({ ...filtros, [k]: e.target.value });

  return (
    <>
      <h1>Tablero gerencial de la DRE</h1>
      <p className="sub">
        Expedientes en trámite, plazos, cuellos de botella, carga del equipo y calidad de datos.{" "}
        <span className="rotulo rotulo-sintetico">Dato sintético</span>
      </p>
      <SelectorFecha />
      {error && <p className="mensaje mensaje-error" role="alert">No se pudo cargar el tablero: {error}</p>}
      {!d ? <p className="cargando">Cargando el tablero…</p> : (
        <>
          <form className="filtros-linea" aria-label="Filtros del tablero" onSubmit={(e) => e.preventDefault()}>
            <label>Tipo de trámite
              <select value={filtros.tipo} onChange={cambiar("tipo")}>
                <option value="">Todos</option>
                {d.opciones.tipo.map((x) => <option key={x} value={x}>{t("tipo_procedimiento", x)}</option>)}
              </select>
            </label>
            <label>EPS
              <select value={filtros.cod_eps} onChange={cambiar("cod_eps")}>
                <option value="">Todas</option>
                {d.opciones.cod_eps.map((x) => <option key={x}>{x}</option>)}
              </select>
            </label>
            <label>Responsable actual
              <select value={filtros.responsable} onChange={cambiar("responsable")}>
                <option value="">Todos</option>
                {d.opciones.responsable.map((x) => <option key={x} value={x}>{t("responsable", x)}</option>)}
              </select>
            </label>
            <label>Especialista (ficticio)
              <select value={filtros.especialista} onChange={cambiar("especialista")}>
                <option value="">Todos</option>
                {d.opciones.especialista.map((x) => <option key={x}>{x}</option>)}
              </select>
            </label>
            {Object.values(filtros).some(Boolean) && (
              <button type="button" className="secundario"
                      onClick={() => setFiltros({ tipo: "", cod_eps: "", responsable: "", especialista: "", estado: "" })}>
                Quitar filtros
              </button>
            )}
          </form>

          <section aria-labelledby="ind-titulo">
            <h2 id="ind-titulo">¿Qué requiere acción? Indicadores al {fecha(d.fecha_corte)}</h2>
            <p className="sub">Elija un indicador para ver sus expedientes y llegar hasta cada uno.</p>
            <div className="indicadores">
              {INDICADORES.map((i) => {
                const delta = cambios[i.clave];
                const activo = (i.estado ?? "") === filtros.estado;
                return (
                  <button key={i.clave} type="button" className={`indicador ind-${i.clave}${activo ? " activo" : ""}`}
                          aria-pressed={activo} onClick={() => elegir(i.estado ?? "")}>
                    <span className="ind-titulo">{i.estado ? <EstadoAlerta estado={i.estado} /> : i.titulo}</span>
                    <span className="ind-valor">{d.indicadores[i.clave].n}</span>
                    {delta ? <span className="ind-delta">{delta > 0 ? `+${delta}` : delta} desde la fecha anterior</span> : null}
                  </button>
                );
              })}
            </div>
          </section>

          <section aria-labelledby="lista-titulo">
            <h2 id="lista-titulo" ref={lista} tabIndex={-1}>
              Expedientes {filtros.estado ? `— ${t("estado_reloj", filtros.estado).toLowerCase()}` : "en trámite"} ({d.expedientes.length})
            </h2>
            <div className="tabla-wrap">
              <table>
                <thead><tr><th>Expediente</th><th>Estado</th><th>Plazo</th><th>Está en</th><th>EPS</th><th>Tipo</th><th>Especialista</th></tr></thead>
                <tbody>
                  {d.expedientes.map((x) => (
                    <tr key={x.id_expediente}>
                      <td><Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link></td>
                      <td><EstadoAlerta estado={x.estado} /></td>
                      <td>{x.alerta ? <>{t("reloj", x.alerta.reloj)}: {x.alerta.dias_restantes == null ? "—" :
                        x.alerta.dias_restantes < 0 ? `vencido hace ${-x.alerta.dias_restantes} DH` : `quedan ${x.alerta.dias_restantes} DH`}</> : "—"}</td>
                      <td>{x.hito_al_corte ? <>{t("hito", x.hito_al_corte)}<div className="detalle">{t("responsable", x.responsable_al_corte)}</div></> : "—"}</td>
                      <td>{x.cod_eps}</td>
                      <td>{t("tipo_procedimiento", x.tipo_procedimiento)}</td>
                      <td>{x.especialista}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <SuperaPlazo s={d.supera_plazo} />
          <Cuellos c={d.cuellos} />
          <Embudo e={d.embudo} />
          <Carga c={d.carga} />
          <Calidad q={d.calidad} />
          {usuario.vistas?.includes("simulador") && <Simulador filtros={filtros} />}
        </>
      )}
    </>
  );
}

function SuperaPlazo({ s }: { s: Tablero["supera_plazo"] }) {
  const filas = (g: Record<string, Grupo>, cat: string | null) => Object.entries(g).map(([k, v]) => (
    <tr key={k}>
      <th scope="row">{cat ? t(cat, k) : k}</th>
      <td>{v.porcentaje == null ? "No calculable" : `${uno(v.porcentaje)} %`}</td>
      <td>{v.superan} de {v.calculables}</td>
      <td>{v.no_calculables}</td>
      <td>{v.ids_superan.map((id) => <Link key={id} to={`/expedientes/${id}`} className="enlace-lista">{id}</Link>)}</td>
    </tr>
  ));
  return (
    <section aria-labelledby="sp-titulo">
      <h2 id="sp-titulo">Expedientes que superan el plazo máximo <span className="rotulo rotulo-supuesto">{s.rotulo}</span></h2>
      <p className="cifra-grande">
        {s.total.porcentaje == null ? "No calculable" : `${uno(s.total.porcentaje)} %`}
        <span className="sub"> ({s.total.superan} de {s.total.calculables} con datos; {s.total.en_tramite_superan} siguen en trámite)</span>
      </p>
      <p className="sub">{humanizar(s.formula)}. {humanizar(s.nota)}</p>
      <div className="tabla-wrap">
        <table>
          <caption>Por tipo de trámite</caption>
          <thead><tr><th>Tipo</th><th>Superan</th><th>Casos</th><th>No calculables</th><th>Expedientes</th></tr></thead>
          <tbody>{filas(s.por_tipo, "tipo_procedimiento")}</tbody>
        </table>
      </div>
      <details>
        <summary>Ver por EPS</summary>
        <div className="tabla-wrap">
          <table>
            <caption>Por EPS</caption>
            <thead><tr><th>EPS</th><th>Superan</th><th>Casos</th><th>No calculables</th><th>Expedientes</th></tr></thead>
            <tbody>{filas(s.por_eps, null)}</tbody>
          </table>
        </div>
      </details>
      <p className="meta">Fuente: {humanizar(s.fuente)}</p>
    </section>
  );
}

function Cuellos({ c }: { c: Tablero["cuellos"] }) {
  const tabla = (xs: Cuello[], cat: string, titulo: string) => {
    const max = Math.max(1, ...xs.map((x) => x.mediana_dh ?? 0));
    return (
      <div className="tabla-wrap">
        <table>
          <caption>{titulo}</caption>
          <thead><tr><th>{cat === "hito" ? "Hito" : "Responsable"}</th><th>Mediana (DH)</th><th>Demora</th><th>P90 (DH)</th><th>Casos</th><th>En curso ahora</th>{cat === "hito" && <th>Superan su plazo referencial</th>}</tr></thead>
          <tbody>
            {xs.slice(0, 10).map((x) => (
              <tr key={x.clave}>
                <th scope="row">{t(cat, x.clave)}</th>
                <td>{uno(x.mediana_dh)}</td>
                <td><Barra valor={x.mediana_dh ?? 0} maximo={max} etiqueta={`Mediana ${uno(x.mediana_dh)} días hábiles`} /></td>
                <td>{x.p90_dh ?? "—"}</td>
                <td>{x.n}</td>
                <td>{x.en_curso === 0 ? "0" : (
                  <details><summary>{x.en_curso}</summary>{x.ids_en_curso.map((id) => <Link key={id} to={`/expedientes/${id}`} className="enlace-lista">{id}</Link>)}</details>
                )}</td>
                {cat === "hito" && <td>{x.con_referencial ? `${x.supera_referencial} de ${x.con_referencial}` : "sin plazo referencial"}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  return (
    <section aria-labelledby="cb-titulo">
      <h2 id="cb-titulo">Cuellos de botella</h2>
      <p className="sub">{humanizar(c.nota)}</p>
      {tabla(c.por_responsable, "responsable", "Demora por responsable")}
      {tabla(c.por_hito, "hito", "Demora por hito (los 10 más lentos)")}
      <p className="meta">Fuente: {humanizar(c.fuente)}</p>
    </section>
  );
}

function Embudo({ e }: { e: Tablero["embudo"] }) {
  const max = Math.max(1, ...e.etapas.map((x) => x.llegaron));
  return (
    <section aria-labelledby="em-titulo">
      <h2 id="em-titulo">Embudo de firmas <span className="rotulo rotulo-supuesto">Supuesto de agrupación</span></h2>
      <p className="sub">{e.sustento}</p>
      <ol className="embudo">
        {e.etapas.map((x) => (
          <li key={x.clave}>
            <div className="embudo-barra" style={{ width: `${Math.max(12, (x.llegaron / max) * 100)}%` }}>
              <strong>{x.nombre}</strong>
            </div>
            <p>
              Llegaron {x.llegaron} · mediana {uno(x.mediana_dh)} DH · ahora en esta etapa: {x.en_curso}
              {x.ids_en_curso.map((id) => <Link key={id} to={`/expedientes/${id}`} className="enlace-lista">{id}</Link>)}
            </p>
          </li>
        ))}
      </ol>
      <p className="meta">Fuente: {humanizar(e.fuente)}</p>
    </section>
  );
}

function Carga({ c }: { c: Tablero["carga"] }) {
  const max = Math.max(1, ...c.actual.map((a) => a.carga), ...c.propuesta.map((p) => p.carga));
  const prop = Object.fromEntries(c.propuesta.map((p) => [p.especialista, p.carga]));
  return (
    <section aria-labelledby="ca-titulo">
      <h2 id="ca-titulo">Carga por especialista <span className="rotulo rotulo-supuesto">{c.rotulo}</span></h2>
      <p className="sub">{c.aviso} Pesos por tipo de trámite (supuesto, {c.pregunta_dre}): {Object.entries(c.pesos)
        .map(([k, v]) => `${t("tipo_procedimiento", k)} ${v}`).join(" · ")}.</p>
      <div className="tabla-wrap">
        <table>
          <thead><tr><th>Especialista</th><th>Expedientes</th><th>Carga actual</th><th></th><th>Vencidos</th><th>Por vencer</th><th>Carga propuesta</th></tr></thead>
          <tbody>
            {c.actual.map((a) => (
              <tr key={a.especialista}>
                <th scope="row">{a.especialista}</th>
                <td>{a.n}</td>
                <td>{a.carga}</td>
                <td><Barra valor={a.carga} maximo={max} etiqueta={`Carga ${a.carga}`} /></td>
                <td>{a.vencidos}</td>
                <td>{a.por_vencer}</td>
                <td>{prop[a.especialista] ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>Diferencia entre la mayor y la menor carga: hoy <strong>{c.desbalance_actual}</strong>; con la propuesta <strong>{c.desbalance_propuesto}</strong>.</p>
      {c.movimientos.length > 0 && (
        <details>
          <summary>Propuesta de asignación: {c.movimientos.length} {c.movimientos.length === 1 ? "cambio" : "cambios"}</summary>
          <ul>
            {c.movimientos.map((m) => (
              <li key={m.id_expediente}>
                <Link to={`/expedientes/${m.id_expediente}`}>{m.id_expediente}</Link> ({t("tipo_procedimiento", m.tipo_procedimiento)}, peso {m.peso}): de {m.de} a {m.a}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function Calidad({ q }: { q: Tablero["calidad"] }) {
  return (
    <section aria-labelledby="cq-titulo">
      <h2 id="cq-titulo">Calidad de datos</h2>
      <p>
        <strong>{q.total}</strong> hallazgos en la muestra:{" "}
        {Object.entries(q.por_severidad).map(([k, v]) => `${v} de severidad ${t("severidad", k).toLowerCase()}`).join(", ")}.
      </p>
      <div className="tabla-wrap">
        <table>
          <caption>Reglas con más hallazgos</caption>
          <thead><tr><th>Regla</th><th>Qué revisa</th><th>Severidad</th><th>Hallazgos</th></tr></thead>
          <tbody>{q.reglas.map((r) => (
            <tr key={r.regla_id}><td>{r.regla_id}</td><td>{humanizar(r.titulo)}</td><td>{t("severidad", r.severidad)}</td><td>{r.n}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="sub">{q.nota} <a href={`/api${q.reporte}`}>Abrir el reporte completo de calidad</a></p>
    </section>
  );
}

interface Escenario {
  parametros: { fecha_corte: string; fecha_escenario: string; dias_sin_accion: number };
  base: Record<string, Ids>; escenario: Record<string, Ids>;
  cambios: { id_expediente: string; antes: string | null; despues: string }[];
  carga_base: { desbalance: number }; carga_escenario: { desbalance: number };
  rotulo: string; supuestos: string[];
}

function Simulador({ filtros }: { filtros: { tipo: string; cod_eps: string } }) {
  const { corte } = useSesion();
  const [p, setP] = useState({ dias_sin_accion: "10", umbral_por_vencer_dh: "", especialistas_adicionales: "0" });
  const [r, setR] = useState<Escenario | null>(null);
  const [error, setError] = useState<string | null>(null);
  const simular = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setR(await pedir<Escenario>("/simulador", { method: "POST", body: JSON.stringify({
        fecha_corte: corte, dias_sin_accion: Number(p.dias_sin_accion || 0),
        umbral_por_vencer_dh: p.umbral_por_vencer_dh === "" ? null : Number(p.umbral_por_vencer_dh),
        especialistas_adicionales: Number(p.especialistas_adicionales || 0),
        tipo: filtros.tipo || null, cod_eps: filtros.cod_eps || null }) }));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <section aria-labelledby="sim-titulo" className="panel">
      <h2 id="sim-titulo">Simulador de escenarios</h2>
      <p className="aviso">Escenario simulado: calcula en memoria y nunca modifica los datos reales.</p>
      <form className="formulario" onSubmit={simular} aria-label="Parámetros del escenario">
        <label>Días hábiles sin acción desde la fecha de corte
          <input type="number" min={0} max={120} value={p.dias_sin_accion} onChange={(e) => setP({ ...p, dias_sin_accion: e.target.value })} />
        </label>
        <label>Umbral «por vencer» (DH; vacío = el del catálogo)
          <input type="number" min={0} max={30} value={p.umbral_por_vencer_dh} onChange={(e) => setP({ ...p, umbral_por_vencer_dh: e.target.value })} />
        </label>
        <label>Especialistas adicionales (ficticios)
          <input type="number" min={0} max={10} value={p.especialistas_adicionales} onChange={(e) => setP({ ...p, especialistas_adicionales: e.target.value })} />
        </label>
        <button type="submit">Simular</button>
      </form>
      {error && <p className="mensaje mensaje-error" role="alert">{error}</p>}
      {r && (
        <div role="status" aria-live="polite">
          <p><strong>{r.rotulo}.</strong> Del {fecha(r.parametros.fecha_corte)} al {fecha(r.parametros.fecha_escenario)}.</p>
          <div className="tabla-wrap">
            <table>
              <caption>Antes y después</caption>
              <thead><tr><th>Indicador</th><th>Hoy</th><th>Escenario</th></tr></thead>
              <tbody>
                {INDICADORES.map((i) => (
                  <tr key={i.clave}><th scope="row">{i.titulo}</th><td>{r.base[i.clave].n}</td><td>{r.escenario[i.clave].n}</td></tr>
                ))}
                <tr><th scope="row">Diferencia de carga entre especialistas</th><td>{r.carga_base.desbalance}</td><td>{r.carga_escenario.desbalance}</td></tr>
              </tbody>
            </table>
          </div>
          {r.cambios.length > 0 && (
            <ul>
              {r.cambios.map((c) => (
                <li key={c.id_expediente}>
                  <Link to={`/expedientes/${c.id_expediente}`}>{c.id_expediente}</Link>: {t("estado_reloj", c.antes ?? "")} → {t("estado_reloj", c.despues)}
                </li>
              ))}
            </ul>
          )}
          <details><summary>Supuestos del escenario</summary><ul>{r.supuestos.map((s) => <li key={s}>{s}</li>)}</ul></details>
        </div>
      )}
    </section>
  );
}
