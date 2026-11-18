import { createContext, useContext, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { pedir } from "./api";
import { dh, fecha, plural } from "./componentes";
import { entero, soles } from "./dinero";
import { t } from "./etiquetas";
import { Icono } from "./iconos";
import { useSesion } from "./sesion";
import { Dialogo } from "./ui";

// Vista ciudadana pública: celular primero (hasta 640 px, barra inferior); en computadora (desde 1 024 px), menú
// superior, dos columnas y la ficha de obra en un panel lateral. Solo lee campos públicos.

interface Distrito { distrito: string; ubigeo: string; localidad: string }
interface Ubicacion { departamento: string; provincias: { provincia: string; distritos: Distrito[] }[] }
interface Etapa { n: number; de: number; clave: string; nombre: string; detenida: boolean }
interface EtapaDef { n: number; clave: string; nombre: string; detalle: string }
interface Obra {
  cod_proyecto: string; nombre_proyecto: string; componente: string; etapa_ciudadana: Etapa;
  poblacion_beneficiaria: number | null; monto_programado_original: number | null; meta_asociada: string | null;
  decisiones: { id_expediente: string; documento_final: string | null; resultado: string | null; fecha_conclusion: string | null }[];
}
interface DetalleLocalidad {
  localidad: { localidad: string; ubigeo: string; departamento: string; provincia: string; distrito: string;
    cod_eps: string; nombre_eps: string; poblacion_servida?: number };
  fecha_corte: string; etapas: EtapaDef[];
  agregados: { proyectos: number; por_etapa: Record<string, number>; monto_programado_original: number };
  proyectos: Obra[];
  audiencias: { id_expediente: string; hito: string; fecha_inicio: string | null; fecha_fin: string | null; estado: string;
    plazo_referencial_dh: number | null }[];
  resumen_quechua: { texto: string; estado: string } | null;
  avisos: string[];
  fuente: string;
}
interface Mapa { aviso: string; distritos: (Distrito & { obras: { cod_proyecto: string; nombre_proyecto: string; etapa_ciudadana: Etapa }[] })[] }
interface Explicacion { termino: string; texto: string; fuente: string }

type Pestana = "inicio" | "mapa" | "participa" | "mas";
type Filtro = "todas" | "en_obra" | "detenidas";

/** DS01 trae los nombres en mayúsculas: se muestran con mayúscula inicial (los datos no cambian). */
const nombre = (x: string | null | undefined) => (x ?? "").toLowerCase().replace(/(^|[\s-])(\p{L})/gu, (_, a, b) => a + b.toUpperCase());

const ESTADO_OBRA: Record<string, { icono: string; tono: string }> = {
  programada: { icono: "○", tono: "neutral" }, aprobada: { icono: "◔", tono: "info" }, en_preparacion: { icono: "◑", tono: "info" },
  en_obra: { icono: "🔨", tono: "info" }, terminada: { icono: "✓", tono: "ok" }, beneficio_verificado: { icono: "★", tono: "ok" },
};

// ---------------------------------------------------------------- adaptable
const ESCRITORIO = "(min-width: 1024px)";

function useEscritorio(): boolean {
  const consulta = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(ESCRITORIO).matches;
  const [es, setEs] = useState(consulta);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const m = window.matchMedia(ESCRITORIO);
    const cambio = () => setEs(m.matches);
    m.addEventListener?.("change", cambio);
    return () => m.removeEventListener?.("change", cambio);
  }, []);
  return es;
}

// ---------------------------------------------------------------- voz
/** Lectura en voz alta con la síntesis del navegador, solo en español. */
function useVoz() {
  const soporta = typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  const [aviso, setAviso] = useState<string | null>(null);
  // «Detener» solo aparece mientras suena el audio.
  const [hablando, setHablando] = useState(false);
  const leer = (texto: string) => {
    if (!soporta) {
      setAviso("Tu navegador no permite la lectura en voz alta. Prueba con otro navegador.");
      return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "es-PE";
    u.onend = () => setHablando(false);
    u.onerror = () => setHablando(false);
    window.speechSynthesis.speak(u);
    setHablando(true);
    setAviso(null);
  };
  const parar = () => {
    if (soporta) window.speechSynthesis.cancel();
    setHablando(false);
  };
  useEffect(() => () => { if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis?.cancel(); }, []);
  return { soporta, aviso, leer, parar, hablando };
}
type Voz = ReturnType<typeof useVoz>;

// ---------------------------------------------------------------- «¿Qué significa?»
const Ctx = createContext<{ ex: Record<string, Explicacion>; voz: Voz | null }>({ ex: {}, voz: null });

/** Ícono «¿Qué significa?» junto a un término. Al tocarlo muestra la explicación (editable en rules/explicaciones_ciudadanas.yaml). */
function QueSignifica({ clave }: { clave: string }) {
  const { ex, voz } = useContext(Ctx);
  const [abierto, setAbierto] = useState(false);
  const id = useId();
  const caja = useRef<HTMLSpanElement>(null);
  const pop = useRef<HTMLSpanElement>(null);
  const [lado, setLado] = useState<"" | "izq" | "der">("");
  // El recuadro se alinea para no salirse de la pantalla (ni del panel lateral).
  useLayoutEffect(() => {
    if (!abierto || !pop.current) return;
    const r = pop.current.getBoundingClientRect();
    const limite = (caja.current?.closest("[role='dialog']") as HTMLElement | null)?.getBoundingClientRect().right ?? window.innerWidth;
    setLado(r.right > limite - 8 ? "der" : r.left < 8 ? "izq" : "");
  }, [abierto]);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);
  const x = ex[clave];
  if (!x) return null;
  return (
    <span className="que-significa" ref={caja} onKeyDown={(e) => { if (e.key === "Escape") setAbierto(false); }}>
      <button type="button" className="qs-boton" aria-expanded={abierto} aria-controls={id} title="¿Qué significa?"
              aria-label={`¿Qué significa «${x.termino}»?`} onClick={() => { setLado(""); setAbierto(!abierto); }}>
        <Icono nombre="info" tam={16} />
      </button>
      {abierto && (
        <span className={`qs-pop${lado ? ` qs-${lado}` : ""}`} id={id} role="note" ref={pop}>
          <strong>{x.termino}</strong>
          <span>{x.texto}</span>
          <span className="meta">Fuente: {x.fuente} · por validar</span>
          {voz?.soporta && <button type="button" className="enlace-boton" onClick={() => voz.leer(`${x.termino}. ${x.texto}`)}>▶ Escuchar</button>}
        </span>
      )}
    </span>
  );
}

/** Explicación visible (no desplegable), para «Cómo funciona» y «Más». */
function Explicado({ clave }: { clave: string }) {
  const { ex } = useContext(Ctx);
  const x = ex[clave];
  if (!x) return null;
  return (
    <div className="explicado">
      <strong>{x.termino}</strong>
      <p>{x.texto}</p>
      <p className="meta">Fuente: {x.fuente}</p>
    </div>
  );
}

// ---------------------------------------------------------------- piezas
function EstadoObra({ e }: { e: Etapa }) {
  if (e.detenida) return <span className="pildora pil-bad"><span aria-hidden="true">⏸</span>Obra detenida</span>;
  const x = ESTADO_OBRA[e.clave] ?? { icono: "•", tono: "neutral" };
  return <span className={`pildora pil-${x.tono}`}><span aria-hidden="true">{x.icono}</span>{e.clave === "terminada" ? "Terminada, verificación pendiente" : e.nombre}</span>;
}

function BarraEtapas({ e }: { e: Etapa }) {
  return (
    <ol className={`pasos compacto${e.detenida ? " detenido" : ""}`} aria-label={`Etapa ${e.n} de ${e.de}: ${e.detenida ? "obra detenida" : e.nombre}`}>
      {Array.from({ length: e.de }, (_, i) => (
        <li key={i} className={i + 1 < e.n ? "hecho" : i + 1 === e.n ? "actual" : ""}>{i + 1}</li>
      ))}
    </ol>
  );
}

/** Leyenda de colores de la barra de etapas. */
function Leyenda() {
  return (
    <section className="leyenda-etapas" aria-labelledby="leyenda-titulo">
      <h3 id="leyenda-titulo">Colores de la barra de etapas <QueSignifica clave="colores_etapas" /></h3>
      <ul>
        <li><i className="l-hecho" aria-hidden="true" />Etapa cumplida</li>
        <li><i className="l-actual" aria-hidden="true" />Etapa actual</li>
        <li><i className="l-detenida" aria-hidden="true" />Obra detenida</li>
        <li><i className="l-pendiente" aria-hidden="true" />Etapa que falta</li>
      </ul>
    </section>
  );
}

function Empresa({ d }: { d: DetalleLocalidad }) {
  return (
    <section className="empresa" aria-label="Tu empresa de agua">
      <span className="meta" style={{ color: "#fff" }}>TU EMPRESA DE AGUA</span>
      <h3>{d.localidad.nombre_eps}</h3>
      <p>Atiende {d.localidad.localidad}{d.localidad.poblacion_servida != null && <> · población servida {entero(d.localidad.poblacion_servida)} (estimada)</>}.</p>
    </section>
  );
}

const PESTANAS: [Pestana, string, string][] = [["inicio", "⌂", "Inicio"], ["mapa", "◎", "Mapa"], ["participa", "◷", "Participa"], ["mas", "☰", "Más"]];

// ---------------------------------------------------------------- vista
export function VistaCiudadana() {
  const { corte } = useSesion();
  const [params, setParams] = useSearchParams();
  const escritorio = useEscritorio();
  const [ubic, setUbic] = useState<Ubicacion[] | null>(null);
  const [dep, setDep] = useState("");
  const [prov, setProv] = useState("");
  const [ubigeo, setUbigeo] = useState(params.get("ubigeo") ?? "");
  const [d, setD] = useState<DetalleLocalidad | null>(null);
  const [mapa, setMapa] = useState<Mapa | null>(null);
  const [ex, setEx] = useState<Record<string, Explicacion>>({});
  const [pestana, setPestana] = useState<Pestana>("inicio");
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [obraSel, setObraSel] = useState<string | null>(null);
  const [idioma, setIdioma] = useState<"es" | "qu">("es");
  const [error, setError] = useState<string | null>(null);
  const voz = useVoz();

  useEffect(() => {
    pedir<Ubicacion[]>("/publico/ubicaciones").then((u) => {
      setUbic(u);
      const buscado = params.get("ubigeo");
      for (const x of u) for (const p of x.provincias) for (const di of p.distritos) {
        if (buscado ? di.ubigeo === buscado : !dep) {
          setDep(x.departamento); setProv(p.provincia); setUbigeo(di.ubigeo);
          return;
        }
      }
    }).catch((e) => setError(e.message));
    pedir<{ explicaciones?: Record<string, Explicacion> }>("/publico/explicaciones")
      .then((r) => setEx(r && typeof r.explicaciones === "object" ? r.explicaciones : {})).catch(() => setEx({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!ubigeo) return;
    setObraSel(null);
    pedir<DetalleLocalidad>(`/publico/localidades/${encodeURIComponent(ubigeo)}?fecha_corte=${corte}`)
      .then((r) => { setD(r); setError(null); }).catch((e) => setError(e.message));
  }, [ubigeo, corte]);
  useEffect(() => {
    // En computadora el mapa va a la derecha del inicio; en celular, en su propia pestaña.
    if ((pestana !== "mapa" && !escritorio) || !dep || !prov) return;
    pedir<Mapa>(`/publico/mapa?${new URLSearchParams({ departamento: dep, provincia: prov })}`).then(setMapa).catch((e) => setError(e.message));
  }, [pestana, dep, prov, escritorio]);

  const provincias = ubic?.find((x) => x.departamento === dep)?.provincias ?? [];
  const distritos = provincias.find((p) => p.provincia === prov)?.distritos ?? [];
  const elegirUbigeo = (u: string) => { setUbigeo(u); setParams({ ubigeo: u }); };
  const obras = useMemo(() => (d?.proyectos ?? []).filter((o) =>
    filtro === "todas" || (filtro === "detenidas" ? o.etapa_ciudadana.detenida : o.etapa_ciudadana.clave === "en_obra" && !o.etapa_ciudadana.detenida)), [d, filtro]);
  const obra = d?.proyectos.find((o) => o.cod_proyecto === obraSel) ?? null;
  const resumenLocalidad = !d ? "" : d.proyectos.length === 0
    ? `En ${d.localidad.localidad}, ${nombre(d.localidad.provincia)}. ${ex.sin_obras?.texto ?? "La muestra no registra obras para este distrito."}`
    : `En ${d.localidad.localidad}, ${nombre(d.localidad.provincia)}, hay ${plural(d.agregados.proyectos, "obra", "obras")} de agua y saneamiento a cargo de ${d.localidad.nombre_eps}. ` +
      Object.entries(d.agregados.por_etapa).map(([k, v]) => `${v} ${t("peldano", k).toLowerCase()}`).join(", ") + ". Datos de la muestra sintética.";
  const irPestana = (k: Pestana) => { setPestana(k); setObraSel(null); };

  const nav = (arriba: boolean) => (
    <nav className={arriba ? "pestanas-sup" : "pestanas"} aria-label="Secciones de la vista ciudadana">
      {PESTANAS.map(([k, i, txt]) => (
        <button key={k} type="button" aria-current={pestana === k ? "page" : undefined} onClick={() => irPestana(k)}>
          <span aria-hidden="true">{i}</span>{txt}
        </button>
      ))}
    </nav>
  );

  return (
    <Ctx.Provider value={{ ex, voz }}>
      <div className={`ciudadana${escritorio ? " escritorio" : ""}`}>
        <header className="ciu-cabecera">
          <div className="ciu-interior">
            <div className="fila">
              <Link to="/" className="marca" aria-label="YakuTraza, ir a la portada">YakuTraza</Link>
              {escritorio && nav(true)}
              <div className="idioma" role="group" aria-label="Idioma">
                <button type="button" aria-pressed={idioma === "es"} onClick={() => setIdioma("es")}>Español</button>
                <button type="button" aria-pressed={idioma === "qu"} onClick={() => setIdioma("qu")} lang="qu">Runasimi</button>
              </div>
            </div>
            <h1>¿Qué obras de agua hay en tu distrito?</h1>
            <div className="ciu-fila-sel">
              <div className="selectores">
                <label>Departamento
                  <select value={dep} onChange={(e) => { const x = ubic?.find((u) => u.departamento === e.target.value);
                    setDep(e.target.value); setProv(x?.provincias[0]?.provincia ?? ""); if (x?.provincias[0]?.distritos[0]) elegirUbigeo(x.provincias[0].distritos[0].ubigeo); }}>
                    {ubic?.map((u) => <option key={u.departamento} value={u.departamento}>{nombre(u.departamento)}</option>)}
                  </select>
                </label>
                <label>Provincia
                  <select value={prov} onChange={(e) => { const p = provincias.find((x) => x.provincia === e.target.value);
                    setProv(e.target.value); if (p?.distritos[0]) elegirUbigeo(p.distritos[0].ubigeo); }}>
                    {provincias.map((p) => <option key={p.provincia} value={p.provincia}>{nombre(p.provincia)}</option>)}
                  </select>
                </label>
                <label>Distrito
                  <select value={ubigeo} onChange={(e) => elegirUbigeo(e.target.value)}>
                    {distritos.map((x) => <option key={x.ubigeo} value={x.ubigeo}>{nombre(x.distrito)}</option>)}
                  </select>
                </label>
              </div>
              {d && pestana === "inicio" && (!obra || escritorio) && (
                <div className="audio">
                  <button type="button" className="secundario" onClick={() => voz.leer(resumenLocalidad)}>▶ Escuchar resumen en español</button>
                  {voz.soporta && voz.hablando && <button type="button" className="secundario" onClick={voz.parar}>■ Detener</button>}
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="ciu-cuerpo">
          {error && <p className="mensaje mensaje-error" role="alert">{error}</p>}
          {voz.aviso && <p className="aviso" role="alert">{voz.aviso}</p>}
          {idioma === "qu" && (
            d?.resumen_quechua ? (
              <section className="tarjeta" lang="qu" aria-label="Resumen en quechua">
                <p>{d.resumen_quechua.texto}</p>
                <p className="meta" lang="es">Validado por una persona hablante.</p>
              </section>
            ) : (
              <p className="aviso" role="status">Resumen en quechua pendiente de validación. Mientras tanto, la información se muestra en español.</p>
            )
          )}
          {!d ? <p className="cargando">Cargando las obras…</p> : (
            <>
              {pestana === "inicio" && (!obra || escritorio) && (
                <div className="ciu-inicio">
                  <div className="ciu-principal">
                    {d.proyectos.length === 0 ? (
                      <section className="tarjeta sin-obras" aria-label="Sin obras en la muestra">
                        <h2>No hay obras de la muestra en {d.localidad.localidad}</h2>
                        <p>{ex.sin_obras?.texto ?? "La muestra no registra obras de agua y saneamiento para este distrito."}</p>
                        <p className="meta">Pruebe con otro distrito o abra el mapa de la provincia.</p>
                      </section>
                    ) : (
                      <>
                        <div className="filtros-pil" role="group" aria-label="Filtrar obras">
                          {([["todas", `Todas (${d.proyectos.length})`], ["en_obra", "En obra"], ["detenidas", "Detenidas"]] as [Filtro, string][]).map(([k, txt]) => (
                            <button key={k} type="button" aria-pressed={filtro === k} onClick={() => setFiltro(k)}>{txt}</button>
                          ))}
                        </div>
                        {obras.length === 0 && <p className="tarjeta">No hay obras con este filtro en {d.localidad.localidad}.</p>}
                        <ul className="obras-grilla" aria-label="Obras del distrito">
                          {obras.map((o) => (
                            <li key={o.cod_proyecto}>
                              <button type="button" className="obra" aria-haspopup={escritorio ? "dialog" : undefined}
                                      onClick={() => setObraSel(o.cod_proyecto)}>
                                <EstadoObra e={o.etapa_ciudadana} />
                                <h3>{o.nombre_proyecto}</h3>
                                <BarraEtapas e={o.etapa_ciudadana} />
                                <span className="pie-obra"><span>Etapa {o.etapa_ciudadana.n} de {o.etapa_ciudadana.de}</span>
                                  {o.monto_programado_original != null && <span>{soles(o.monto_programado_original)} previstos</span>}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                        <p className="meta">Los montos son lo previsto en el plan de inversiones, no lo gastado. <QueSignifica clave="monto" /></p>
                      </>
                    )}
                  </div>
                  <aside className="ciu-lateral" aria-label="Tu distrito">
                    {escritorio && <PestanaMapa mapa={mapa} actual={ubigeo} etapas={d.etapas} compacto onElegir={elegirUbigeo} />}
                    <Leyenda />
                    <Empresa d={d} />
                    <p className="meta">Las etapas están «por validar» con la DRE (E-2). Ninguna obra figura «en funcionamiento» sin verificación de Sunass.</p>
                  </aside>
                </div>
              )}
              {pestana === "inicio" && obra && !escritorio && <FichaObra o={obra} etapas={d.etapas} d={d} volver={() => setObraSel(null)} voz={voz} />}
              {pestana === "inicio" && obra && escritorio && (
                <Dialogo lateral titulo={obra.nombre_proyecto} onCerrar={() => setObraSel(null)}>
                  <FichaObra o={obra} etapas={d.etapas} d={d} volver={() => setObraSel(null)} voz={voz} enPanel />
                </Dialogo>
              )}
              {pestana === "mapa" && <PestanaMapa mapa={mapa} actual={ubigeo} etapas={d.etapas} onElegir={(u) => { elegirUbigeo(u); setPestana("inicio"); }} />}
              {pestana === "participa" && <Participa d={d} />}
              {pestana === "mas" && <Mas d={d} />}
            </>
          )}
        </div>

        {!escritorio && nav(false)}
      </div>
    </Ctx.Provider>
  );
}

// ---------------------------------------------------------------- ficha de obra
function FichaObra({ o, etapas, d, volver, voz, enPanel }: {
  o: Obra; etapas: EtapaDef[]; d: DetalleLocalidad; volver: () => void; voz: Voz; enPanel?: boolean;
}) {
  const { ex } = useContext(Ctx);
  const e = o.etapa_ciudadana;
  const explicacion = e.detenida ? ex.obra_detenida?.texto : ex[`etapa_${e.clave}`]?.texto;
  const texto = `${o.nombre_proyecto}. Etapa ${e.n} de ${e.de}: ${e.detenida ? "obra detenida" : e.nombre}. ` +
    (explicacion ? `${explicacion} ` : "") +
    (o.monto_programado_original != null ? `Monto previsto en el plan de inversiones: ${soles(o.monto_programado_original)}. ` : "") +
    (o.decisiones.length ? `Sunass emitió la ${o.decisiones[0].documento_final ?? "resolución"} sobre esta obra.` : "");
  return (
    <article aria-labelledby={enPanel ? undefined : "obra-titulo"} aria-label={enPanel ? o.nombre_proyecto : undefined}
             className={enPanel ? "ficha-panel" : undefined}>
      {!enPanel && <p><button type="button" className="enlace-boton" onClick={volver}>← Volver a las obras</button></p>}
      <EstadoObra e={e} />{e.detenida && <QueSignifica clave="obra_detenida" />}
      {!e.detenida && e.clave === "terminada" && <QueSignifica clave="terminada_verificacion_pendiente" />}
      {!enPanel && <h2 id="obra-titulo" style={{ marginTop: 8 }}>{o.nombre_proyecto}</h2>}
      <p className="detalle">{d.localidad.localidad} · {nombre(d.localidad.provincia)}, {nombre(d.localidad.departamento)} · {d.localidad.nombre_eps}</p>
      <div className="audio">
        <button type="button" onClick={() => voz.leer(texto)}>▶ Escuchar resumen</button>
        {voz.soporta && voz.hablando && <button type="button" className="secundario" onClick={voz.parar}>■ Detener</button>}
      </div>
      <section className="tarjeta" aria-labelledby="etapa-titulo">
        <h3 id="etapa-titulo" style={{ marginTop: 0 }}>¿En qué etapa está?</h3>
        <ol className={`etapas-lista${enPanel ? " horizontal" : ""}`}>
          {etapas.map((x) => (
            <li key={x.n} className={x.n < e.n ? "hecha" : x.n === e.n ? `actual${e.detenida ? " det" : ""}` : ""}
                aria-current={x.n === e.n ? "step" : undefined}>
              <span className="marca-e" aria-hidden="true">{x.n < e.n ? "✓" : x.n}</span>
              <span>{x.nombre}{x.n === e.n && e.detenida ? " · obra detenida" : ""} <QueSignifica clave={`etapa_${x.clave}`} />
                {x.n === e.n && <span className="detalle"><br />{e.detenida ? (ex.obra_detenida?.texto ?? "La obra está detenida.") : x.detalle}</span>}</span>
            </li>
          ))}
        </ol>
        <p className="meta">Etapas por validar con la DRE (E-2).</p>
      </section>
      <section className="tarjeta">
        <h3 style={{ marginTop: 0 }}>Datos públicos de la obra</h3>
        <p>{t("componente", o.componente)}{o.monto_programado_original != null && <> · {soles(o.monto_programado_original)} previstos en el plan de inversiones <QueSignifica clave="monto" /></>}</p>
        {o.poblacion_beneficiaria != null && <p>{entero(o.poblacion_beneficiaria)} personas beneficiarias <span className="rotulo rotulo-estimado">Estimado</span></p>}
        {o.meta_asociada && <p>Impulsa la meta de gestión {o.meta_asociada}.</p>}
        <p className="detalle">¿Por qué no veo cuánto se gastó? <QueSignifica clave="por_que_no_gasto" /></p>
      </section>
      <section className="tarjeta" style={{ background: "var(--vio-bg)" }}>
        <h3 style={{ marginTop: 0 }}>Sunass y esta obra</h3>
        {o.decisiones.length === 0 ? <p>La muestra no registra decisiones de Sunass sobre esta obra.</p> : o.decisiones.map((x) => (
          <p key={x.id_expediente}>{x.documento_final ?? "Resolución sin número"}: {t("resultado", x.resultado)}{x.fecha_conclusion ? ` (${fecha(x.fecha_conclusion)})` : ""}.</p>
        ))}
      </section>
      <p className="meta">Fuentes: programa de inversiones (DS03), reporte de la EPS (DS04) solo para la etapa, decisiones (DS02) · datos sintéticos.</p>
    </article>
  );
}

// ---------------------------------------------------------------- mapa
function PestanaMapa({ mapa, actual, etapas, onElegir, compacto }: {
  mapa: Mapa | null; actual: string; etapas: EtapaDef[]; onElegir: (u: string) => void; compacto?: boolean;
}) {
  if (!mapa) return <p className="cargando">Cargando el mapa…</p>;
  return (
    <section aria-labelledby={compacto ? "mapa-mini" : "mapa-titulo"} className={compacto ? "mapa-mini tarjeta" : undefined}>
      {compacto ? <h3 id="mapa-mini" style={{ marginTop: 0 }}>Mapa esquemático de la provincia</h3>
        : <h2 id="mapa-titulo" style={{ marginTop: 0 }}>Mapa esquemático</h2>}
      {!compacto && <p className="aviso">{mapa.aviso}</p>}
      <div className="mapa-esq">
        {mapa.distritos.map((x) => (
          <button key={x.ubigeo} type="button" className={`distrito-caja${x.ubigeo === actual ? " actual" : ""}`} onClick={() => onElegir(x.ubigeo)}
                  aria-label={`${x.distrito}: ${plural(x.obras.length, "obra", "obras")}`} aria-current={x.ubigeo === actual ? "true" : undefined}
                  style={{ textAlign: "left", color: "var(--ink)", display: "block", fontWeight: 400 }}>
            <strong>{nombre(x.distrito)}</strong>
            <span className="circulos">
              {x.obras.length === 0 ? <span className="detalle">Sin obras</span> : x.obras.map((o) => (
                <span key={o.cod_proyecto} title={o.nombre_proyecto}
                      className={`circulo e${o.etapa_ciudadana.n}${o.etapa_ciudadana.detenida ? " det" : ""}`}>{o.etapa_ciudadana.n}</span>
              ))}
            </span>
          </button>
        ))}
      </div>
      <p className="meta">Número = etapa de la obra: {etapas.map((e) => `${e.n} ${e.nombre}`).join(" · ")}. Rojo = obra detenida. Mapa referencial y esquemático{compacto ? `: ${mapa.aviso}` : "."}</p>
    </section>
  );
}

// ---------------------------------------------------------------- participa y más
function Participa({ d }: { d: DetalleLocalidad }) {
  return (
    <section aria-labelledby="part-titulo">
      <h2 id="part-titulo" style={{ marginTop: 0 }}>Participa</h2>
      <p className="detalle">Audiencias públicas y plazos para comentar las tarifas de {d.localidad.nombre_eps.replace(/\.$/, "")}.</p>
      <div className="ciu-dos">
        <div>
          {d.audiencias.length === 0 ? <p className="tarjeta">No hay audiencias registradas para tu empresa de agua en la muestra.</p> : d.audiencias.map((a) => (
            <article key={a.id_expediente + a.hito} className="tarjeta">
              <span className={`pildora ${a.estado === "próxima" ? "pil-ok" : a.estado === "en curso" ? "pil-warn" : ""}`}>{a.estado}</span>
              <h3>{t("hito", a.hito)}</h3>
              <p>Desde el {fecha(a.fecha_inicio)}{a.fecha_fin ? ` hasta el ${fecha(a.fecha_fin)}` : ""}
                {a.plazo_referencial_dh ? ` · plazo de referencia: ${dh(a.plazo_referencial_dh)}` : ""}</p>
              <p className="meta">Revisión de tarifas {a.id_expediente} · por validar (E-2)</p>
            </article>
          ))}
        </div>
        <Recuadro titulo="Cómo funciona" claves={["audiencia_que_es", "audiencia_quien", "audiencia_hasta_cuando", "audiencia_como"]} />
      </div>
    </section>
  );
}

function Recuadro({ titulo, claves }: { titulo: string; claves: string[] }) {
  const { ex } = useContext(Ctx);
  if (!claves.some((k) => ex[k])) return null;
  const id = `rec-${titulo.replace(/\W+/g, "-")}`;
  return (
    <section className="tarjeta recuadro-explica" aria-labelledby={id}>
      <h3 id={id} style={{ marginTop: 0 }}>{titulo}</h3>
      {claves.map((k) => <Explicado key={k} clave={k} />)}
      <p className="meta">Explicaciones por validar con la DRE (E-2).</p>
    </section>
  );
}

function Mas({ d }: { d: DetalleLocalidad }) {
  return (
    <section aria-labelledby="mas-titulo">
      <h2 id="mas-titulo" style={{ marginTop: 0 }}>Más</h2>
      <div className="ciu-dos">
        <Recuadro titulo="Para entender estos datos" claves={["que_es_sunass", "que_es_eps", "dato_sintetico", "por_que_no_gasto"]} />
        <div className="tarjeta">
          <h3 style={{ marginTop: 0 }}>Sobre estos datos</h3>
          <ul>{d.avisos.map((a) => <li key={a}>{a}</li>)}</ul>
          <p className="meta">Fuente: {d.fuente}</p>
          <p>Solo se muestra información pública. Los datos que la EPS reporta a Sunass (avance de obra, gasto) están reservados hasta que la DRE confirme qué es público.</p>
        </div>
      </div>
      <p><Link to="/">Volver a la portada de YakuTraza</Link></p>
    </section>
  );
}


