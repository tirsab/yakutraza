import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { pedir } from "./api";
import { fecha } from "./componentes";
import { entero, soles } from "./dinero";
import { t } from "./etiquetas";
import { useSesion } from "./sesion";

// Vista ciudadana pública: primero celular (máx. 460 px); solo lee campos públicos.

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

type Pestana = "inicio" | "mapa" | "participa" | "mas";

/** DS01 trae los nombres en mayúsculas: se muestran con mayúscula inicial (los datos no cambian). */
const nombre = (x: string | null | undefined) => (x ?? "").toLowerCase().replace(/(^|[\s-])(\p{L})/gu, (_, a, b) => a + b.toUpperCase());
type Filtro = "todas" | "en_obra" | "detenidas";

const ESTADO_OBRA: Record<string, { icono: string; tono: string }> = {
  programada: { icono: "○", tono: "neutral" }, aprobada: { icono: "◔", tono: "info" }, en_preparacion: { icono: "◑", tono: "info" },
  en_obra: { icono: "🔨", tono: "info" }, terminada: { icono: "✓", tono: "ok" }, beneficio_verificado: { icono: "★", tono: "ok" },
};

function EstadoObra({ e }: { e: Etapa }) {
  if (e.detenida) return <span className="pildora pil-bad"><span aria-hidden="true">⏸</span>Obra detenida</span>;
  const x = ESTADO_OBRA[e.clave] ?? { icono: "•", tono: "neutral" };
  return <span className={`pildora pil-${x.tono}`}><span aria-hidden="true">{x.icono}</span>{e.nombre}</span>;
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

/** Lectura en voz alta con la síntesis del navegador, solo en español. */
function useVoz() {
  const soporta = typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  const [aviso, setAviso] = useState<string | null>(null);
  const leer = (texto: string) => {
    if (!soporta) {
      setAviso("Tu navegador no permite la lectura en voz alta. Prueba con otro navegador.");
      return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "es-PE";
    window.speechSynthesis.speak(u);
    setAviso(null);
  };
  const parar = () => { if (soporta) window.speechSynthesis.cancel(); };
  return { soporta, aviso, leer, parar };
}

export function VistaCiudadana() {
  const { corte } = useSesion();
  const [params, setParams] = useSearchParams();
  const [ubic, setUbic] = useState<Ubicacion[] | null>(null);
  const [dep, setDep] = useState("");
  const [prov, setProv] = useState("");
  const [ubigeo, setUbigeo] = useState(params.get("ubigeo") ?? "");
  const [d, setD] = useState<DetalleLocalidad | null>(null);
  const [mapa, setMapa] = useState<Mapa | null>(null);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!ubigeo) return;
    setObraSel(null);
    pedir<DetalleLocalidad>(`/publico/localidades/${encodeURIComponent(ubigeo)}?fecha_corte=${corte}`)
      .then((r) => { setD(r); setError(null); }).catch((e) => setError(e.message));
  }, [ubigeo, corte]);
  useEffect(() => {
    if (pestana !== "mapa" || !dep || !prov) return;
    pedir<Mapa>(`/publico/mapa?${new URLSearchParams({ departamento: dep, provincia: prov })}`).then(setMapa).catch((e) => setError(e.message));
  }, [pestana, dep, prov]);

  const provincias = ubic?.find((x) => x.departamento === dep)?.provincias ?? [];
  const distritos = provincias.find((p) => p.provincia === prov)?.distritos ?? [];
  const elegirUbigeo = (u: string) => { setUbigeo(u); setParams({ ubigeo: u }); };
  const obras = useMemo(() => (d?.proyectos ?? []).filter((o) =>
    filtro === "todas" || (filtro === "detenidas" ? o.etapa_ciudadana.detenida : o.etapa_ciudadana.clave === "en_obra" && !o.etapa_ciudadana.detenida)), [d, filtro]);
  const obra = d?.proyectos.find((o) => o.cod_proyecto === obraSel) ?? null;
  const resumenLocalidad = d ? `En ${d.localidad.localidad}, ${nombre(d.localidad.provincia)}, hay ${d.agregados.proyectos} obras de agua y saneamiento a cargo de ${d.localidad.nombre_eps}. ` +
    Object.entries(d.agregados.por_etapa).map(([k, v]) => `${v} ${t("peldano", k).toLowerCase()}`).join(", ") + ". Datos de la muestra sintética." : "";

  return (
    <div className="ciudadana">
      <header className="ciu-cabecera">
        <div className="fila">
          <Link to="/" className="marca" aria-label="YakuTraza, ir a la portada">YakuTraza</Link>
          <div className="idioma" role="group" aria-label="Idioma">
            <button type="button" aria-pressed={idioma === "es"} onClick={() => setIdioma("es")}>Español</button>
            <button type="button" aria-pressed={idioma === "qu"} onClick={() => setIdioma("qu")} lang="qu">Runasimi</button>
          </div>
        </div>
        <h1>¿Qué obras de agua hay en tu distrito?</h1>
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
      </header>

      <div className="ciu-cuerpo">
        {error && <p className="mensaje mensaje-error" role="alert">{error}</p>}
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
            {pestana === "inicio" && !obra && (
              <>
                <div className="audio">
                  <button type="button" className="secundario" onClick={() => voz.leer(resumenLocalidad)}>▶ Escuchar resumen en español</button>
                  {voz.soporta && <button type="button" className="secundario" onClick={voz.parar}>■ Detener</button>}
                </div>
                {voz.aviso && <p className="aviso" role="alert">{voz.aviso}</p>}
                <div className="filtros-pil" role="group" aria-label="Filtrar obras">
                  {([["todas", `Todas (${d.proyectos.length})`], ["en_obra", "En obra"], ["detenidas", "Detenidas"]] as [Filtro, string][]).map(([k, txt]) => (
                    <button key={k} type="button" aria-pressed={filtro === k} onClick={() => setFiltro(k)}>{txt}</button>
                  ))}
                </div>
                {obras.length === 0 && <p className="tarjeta">No hay obras con este filtro en {d.localidad.localidad}.</p>}
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }} aria-label="Obras del distrito">
                  {obras.map((o) => (
                    <li key={o.cod_proyecto}>
                      <button type="button" className="obra" onClick={() => setObraSel(o.cod_proyecto)}>
                        <EstadoObra e={o.etapa_ciudadana} />
                        <h3>{o.nombre_proyecto}</h3>
                        <BarraEtapas e={o.etapa_ciudadana} />
                        <span className="pie-obra"><span>Etapa {o.etapa_ciudadana.n} de {o.etapa_ciudadana.de}</span>
                          {o.monto_programado_original != null && <span>{soles(o.monto_programado_original)}</span>}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                <section className="empresa" aria-label="Tu empresa de agua">
                  <span className="meta" style={{ color: "#fff" }}>TU EMPRESA DE AGUA</span>
                  <h3>{d.localidad.nombre_eps}</h3>
                  <p>Atiende {d.localidad.localidad}{d.localidad.poblacion_servida != null && <> · población servida {entero(d.localidad.poblacion_servida)} (estimada)</>}.</p>
                </section>
                <p className="meta">Las etapas están «por validar» con la DRE (E-2). Ninguna obra figura «en funcionamiento» sin verificación de Sunass.</p>
              </>
            )}
            {pestana === "inicio" && obra && <FichaObra o={obra} etapas={d.etapas} d={d} volver={() => setObraSel(null)} voz={voz} />}
            {pestana === "mapa" && <PestanaMapa mapa={mapa} actual={ubigeo} etapas={d.etapas} onElegir={(u) => { elegirUbigeo(u); setPestana("inicio"); }} />}
            {pestana === "participa" && <Participa d={d} />}
            {pestana === "mas" && <Mas d={d} />}
          </>
        )}
      </div>

      <nav className="pestanas" aria-label="Secciones de la vista ciudadana">
        {([["inicio", "⌂", "Inicio"], ["mapa", "◎", "Mapa"], ["participa", "◷", "Participa"], ["mas", "☰", "Más"]] as [Pestana, string, string][]).map(([k, i, txt]) => (
          <button key={k} type="button" aria-current={pestana === k ? "page" : undefined} onClick={() => { setPestana(k); setObraSel(null); }}>
            <span aria-hidden="true">{i}</span>{txt}
          </button>
        ))}
      </nav>
    </div>
  );
}

function FichaObra({ o, etapas, d, volver, voz }: { o: Obra; etapas: EtapaDef[]; d: DetalleLocalidad; volver: () => void; voz: ReturnType<typeof useVoz> }) {
  const e = o.etapa_ciudadana;
  const texto = `${o.nombre_proyecto}. Etapa ${e.n} de ${e.de}: ${e.detenida ? "obra detenida" : e.nombre}. ` +
    (o.monto_programado_original != null ? `Monto programado: ${soles(o.monto_programado_original)}. ` : "") +
    (o.decisiones.length ? `Sunass emitió la ${o.decisiones[0].documento_final ?? "resolución"} sobre esta obra.` : "");
  return (
    <article aria-labelledby="obra-titulo">
      <p><button type="button" className="enlace-boton" onClick={volver}>← Volver a las obras</button></p>
      <EstadoObra e={e} />
      <h2 id="obra-titulo" style={{ marginTop: 8 }}>{o.nombre_proyecto}</h2>
      <p className="detalle">{d.localidad.localidad} · {nombre(d.localidad.provincia)}, {nombre(d.localidad.departamento)} · {d.localidad.nombre_eps}</p>
      <div className="audio">
        <button type="button" onClick={() => voz.leer(texto)}>▶ Escuchar resumen</button>
        {voz.soporta && <button type="button" className="secundario" onClick={voz.parar}>■ Detener</button>}
      </div>
      {voz.aviso && <p className="aviso" role="alert">{voz.aviso}</p>}
      <section className="tarjeta" aria-labelledby="etapa-titulo">
        <h3 id="etapa-titulo" style={{ marginTop: 0 }}>¿En qué etapa está?</h3>
        <ol className="etapas-lista">
          {etapas.map((x) => (
            <li key={x.n} className={x.n < e.n ? "hecha" : x.n === e.n ? `actual${e.detenida ? " det" : ""}` : ""}
                aria-current={x.n === e.n ? "step" : undefined}>
              <span className="marca-e" aria-hidden="true">{x.n < e.n ? "✓" : x.n}</span>
              <span>{x.nombre}{x.n === e.n && e.detenida ? " · obra detenida" : ""}
                {x.n === e.n && <span className="detalle"><br />{e.detenida ? "La obra está detenida (paralizada, según el reporte de la EPS)." : x.detalle}</span>}</span>
            </li>
          ))}
        </ol>
        <p className="meta">Etapas por validar con la DRE (E-2).</p>
      </section>
      <section className="tarjeta">
        <h3 style={{ marginTop: 0 }}>Datos públicos de la obra</h3>
        <p>{t("componente", o.componente)}{o.monto_programado_original != null && <> · {soles(o.monto_programado_original)} programado en el estudio tarifario</>}</p>
        {o.poblacion_beneficiaria != null && <p>{entero(o.poblacion_beneficiaria)} personas beneficiarias <span className="rotulo rotulo-estimado">Estimado</span></p>}
        {o.meta_asociada && <p>Impulsa la meta de gestión {o.meta_asociada}.</p>}
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

function PestanaMapa({ mapa, actual, etapas, onElegir }: { mapa: Mapa | null; actual: string; etapas: EtapaDef[]; onElegir: (u: string) => void }) {
  if (!mapa) return <p className="cargando">Cargando el mapa…</p>;
  return (
    <section aria-labelledby="mapa-titulo">
      <h2 id="mapa-titulo" style={{ marginTop: 0 }}>Mapa esquemático</h2>
      <p className="aviso">{mapa.aviso}</p>
      <div className="mapa-esq">
        {mapa.distritos.map((x) => (
          <button key={x.ubigeo} type="button" className={`distrito-caja${x.ubigeo === actual ? " actual" : ""}`} onClick={() => onElegir(x.ubigeo)}
                  aria-label={`${x.distrito}: ${x.obras.length} obras`} style={{ textAlign: "left", color: "var(--ink)", display: "block", fontWeight: 400 }}>
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
      <p className="meta">Número = etapa de la obra: {etapas.map((e) => `${e.n} ${e.nombre}`).join(" · ")}. Rojo = obra detenida. Mapa referencial y esquemático.</p>
    </section>
  );
}

function Participa({ d }: { d: DetalleLocalidad }) {
  return (
    <section aria-labelledby="part-titulo">
      <h2 id="part-titulo" style={{ marginTop: 0 }}>Participa</h2>
      <p className="detalle">Audiencias públicas y plazos para comentar las tarifas de {d.localidad.nombre_eps.replace(/\.$/, "")}.</p>
      {d.audiencias.length === 0 ? <p className="tarjeta">No hay audiencias registradas para tu empresa de agua en la muestra.</p> : d.audiencias.map((a) => (
        <article key={a.id_expediente + a.hito} className="tarjeta">
          <span className={`pildora ${a.estado === "próxima" ? "pil-ok" : a.estado === "en curso" ? "pil-warn" : ""}`}>{a.estado}</span>
          <h3>{t("hito", a.hito)}</h3>
          <p>Desde el {fecha(a.fecha_inicio)}{a.fecha_fin ? ` hasta el ${fecha(a.fecha_fin)}` : ""}
            {a.plazo_referencial_dh ? ` · plazo de referencia: ${a.plazo_referencial_dh} días hábiles` : ""}</p>
          <p className="meta">Revisión de tarifas {a.id_expediente} · por validar (E-2)</p>
        </article>
      ))}
    </section>
  );
}

function Mas({ d }: { d: DetalleLocalidad }) {
  return (
    <section aria-labelledby="mas-titulo">
      <h2 id="mas-titulo" style={{ marginTop: 0 }}>Más</h2>
      <div className="tarjeta">
        <h3 style={{ marginTop: 0 }}>Sobre estos datos</h3>
        <ul>{d.avisos.map((a) => <li key={a}>{a}</li>)}</ul>
        <p className="meta">Fuente: {d.fuente}</p>
        <p>Solo se muestra información pública. Los datos que la EPS reporta a Sunass (avance de obra, gasto) están reservados hasta que la DRE confirme qué es público.</p>
      </div>
      <p><Link to="/">Volver a la portada de YakuTraza</Link></p>
    </section>
  );
}
