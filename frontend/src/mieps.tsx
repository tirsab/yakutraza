import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { pedir } from "./api";
import { plazoEnPalabras } from "./bandeja";
import { fecha } from "./componentes";
import { soles } from "./dinero";
import { humanizar, t } from "./etiquetas";
import { useSesion } from "./sesion";
import { BarraPasos, ChipFuente, Dialogo, Pildora, irA, useToast, type Pasos } from "./ui";

interface Pendiente {
  id_expediente: string; tipo_procedimiento: string; hito: string; accion: string; fecha_limite: string | null;
  dias_restantes: number | null; estado: string; detalle: string; documento: string | null; fuente: string;
  suspende_plazo?: boolean;
}

interface MiEpsDatos {
  cod_eps: string; fecha_corte: string;
  siguiente_accion: Pendiente | null; pendientes: Pendiente[];
  tramites: { id_expediente: string; tipo_procedimiento: string; fecha_inicio: string; hito_al_corte: string | null;
    le_toca_a_la_eps: boolean; en_que_va: string; pasos?: Pasos | null }[];
  concluidos: { id_expediente: string; tipo_procedimiento: string; fecha_conclusion: string; resultado?: string | null;
    pasos?: Pasos | null }[];
  fondo: { fondo: string; deposito_programado: number; deposito_efectuado: number; saldo_final: number | null;
    saldo_al: string | null }[];
  usos_autorizados: { id_expediente: string; estado: string; monto_autorizado: number | null; fondo: string[] | string | null }[];
  resumen_fondo?: { programado: number; depositado: number; autorizado: number; usado: number; aviso: string;
    definiciones: Record<string, string>; fuente: string; hasta: string | null };
  proyectos?: { cod_proyecto: string; nombre_proyecto: string }[];
  aviso_correo: { asunto: string; cuerpo: string; aviso: string };
  fuente: string;
}

// Portal EPS: una acción principal por pantalla; lo demás, en secciones.
export function MiEps() {
  const { usuario, corte, config } = useSesion();
  const toast = useToast();
  const { hash } = useLocation();
  const [d, setD] = useState<MiEpsDatos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [respondiendo, setRespondiendo] = useState<Pendiente | null>(null);
  const cargar = useCallback(() => {
    pedir<MiEpsDatos>(`/mi-eps?fecha_corte=${corte}`).then(setD).catch((e) => setError(e.message));
  }, [corte]);
  useEffect(cargar, [cargar]);
  useEffect(() => { if (d && hash) irA(document.getElementById(hash.slice(1))); }, [hash, d]);

  if (error) return <p className="mensaje mensaje-error" role="alert">No se pudo cargar su información: {error}</p>;
  if (!d) return <p className="cargando">Cargando su información…</p>;
  const nombre = (config.eps.find((e) => e.cod_eps === usuario.cod_eps)?.nombre_eps ?? d.cod_eps).replace(/^EPS\s+/, "").replace(/\s+S\.A\.?$/, "");
  return (
    <>
      <section id="inicio" aria-labelledby="saludo">
        <h1 id="saludo">Hola, equipo de {nombre}.</h1>
        <p className="sub">Aquí ves en qué va cada pedido que hiciste a Sunass, qué te piden y hasta cuándo.{" "}
          <span className="rotulo rotulo-sintetico">Dato sintético</span></p>
      </section>
      <div className="eps-grid" style={{ marginTop: 14 }}>
        <div>
          <Pedido p={d.siguiente_accion} otros={d.pendientes.length - 1} onResponder={setRespondiendo} correo={d.aviso_correo} />
          <RevisarVia codEps={d.cod_eps} proyectos={d.proyectos ?? []} />
        </div>
        <div>
          <MisTramites d={d} />
          <MiFondo d={d} />
        </div>
      </div>
      {respondiendo && (
        <Responder p={respondiendo} usuarioId={usuario.id} onCerrar={() => setRespondiendo(null)}
                   onListo={() => { setRespondiendo(null); toast("Tu respuesta quedó registrada como «propuesta». Sunass la revisará."); cargar(); }}
                   onError={(e) => toast(e, true)} />
      )}
    </>
  );
}

// ------------------------------------------------------------- Sunass te pidió algo
function Pedido({ p, otros, onResponder, correo }: {
  p: Pendiente | null; otros: number; onResponder: (p: Pendiente) => void; correo: MiEpsDatos["aviso_correo"];
}) {
  if (!p) {
    return (
      <section className="tarjeta" aria-labelledby="pedido-titulo">
        <Pildora tono="ok" icono="✓">Sin pedidos</Pildora>
        <h2 id="pedido-titulo">Sunass no te ha pedido nada pendiente</h2>
        <p className="detalle">A la fecha de corte, tu EPS no tiene respuestas pendientes ante Sunass.</p>
      </section>
    );
  }
  const vencido = (p.dias_restantes ?? 0) < 0;
  const sinPlazo = p.dias_restantes == null;
  return (
    <section className={`tarjeta pedido${vencido ? " vencido" : sinPlazo ? " sin_plazo" : ""}`} aria-labelledby="pedido-titulo">
      <div className="fila" style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <Pildora tono={vencido ? "bad" : sinPlazo ? "vio" : "warn"} icono="✉">Sunass te pidió algo</Pildora>
        {p.documento && <ChipFuente texto={p.documento} detalle={humanizar(p.fuente)} />}
      </div>
      <h2 id="pedido-titulo" style={{ marginTop: 10 }}>{p.accion.replace(/\.$/, "")}</h2>
      <p className="detalle">Trámite {p.id_expediente} · {t("tipo_procedimiento", p.tipo_procedimiento)}</p>
      <div className="pedido-cuerpo">
        <div className={`contador-dh${vencido ? " vencido" : sinPlazo ? " sin_plazo" : ""}`}>
          <strong>{sinPlazo ? "?" : Math.abs(p.dias_restantes!)}</strong>
          <span>{sinPlazo ? "sin plazo registrado" : vencido ? "días hábiles de atraso" : "días hábiles"}</span>
        </div>
        <div>
          {p.fecha_limite ? <p>{vencido ? "Venció el" : "Tienes hasta el"} <strong>{fecha(p.fecha_limite)}</strong> ({plazoEnPalabras(p.dias_restantes)}).</p>
            : <p>No hay un plazo registrado para esta respuesta.</p>}
          {p.suspende_plazo && <p className="detalle">Mientras no respondas, el plazo de Sunass está en pausa.</p>}
        </div>
      </div>
      <div className="acciones">
        <button type="button" onClick={() => onResponder(p)}>Responder</button>
      </div>
      {otros > 0 && <p className="meta">Tienes {otros} {otros === 1 ? "pedido más" : "pedidos más"} en «Mis trámites».</p>}
      <details>
        <summary>Vista previa del aviso por correo</summary>
        <div className="aviso"><strong>Asunto:</strong> {correo.asunto}<br />{correo.cuerpo}</div>
        <p className="meta">{correo.aviso}</p>
      </details>
    </section>
  );
}

function Responder({ p, usuarioId, onCerrar, onListo, onError }: {
  p: Pendiente; usuarioId: string; onCerrar: () => void; onListo: () => void; onError: (t: string) => void;
}) {
  const [numero, setNumero] = useState("");
  const [fechaR, setFechaR] = useState("");
  const [canal, setCanal] = useState("mesa_partes");
  const [enlace, setEnlace] = useState("");
  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await pedir(`/expedientes/${encodeURIComponent(p.id_expediente)}/documentos`, { method: "POST", body: JSON.stringify({
        tipo: "OF", canal, numero: numero || undefined, hito: p.hito, fecha_recepcion: fechaR || undefined,
        referencia: enlace || undefined }) }, usuarioId);
      onListo();
    } catch (err) {
      onError((err as Error).message);
    }
  };
  return (
    <Dialogo titulo={`Responder: ${t("hito", p.hito)}`} onCerrar={onCerrar}>
      <p className="detalle">Tu respuesta entra como «propuesta»: el equipo de Sunass la revisa y la confirma.</p>
      <form onSubmit={enviar}>
        <label className="campo">Número de tu oficio o carta<input value={numero} onChange={(e) => setNumero(e.target.value)} required /></label>
        <label className="campo">Fecha de envío<input type="date" value={fechaR} onChange={(e) => setFechaR(e.target.value)} required /></label>
        <label className="campo">¿Por dónde lo enviaste?
          <select value={canal} onChange={(e) => setCanal(e.target.value)}>
            {["mesa_partes", "correo", "enlace_externo", "otro"].map((c) => <option key={c} value={c}>{t("canal", c)}</option>)}
          </select>
        </label>
        <label className="campo">Enlace o ubicación (opcional)<input value={enlace} onChange={(e) => setEnlace(e.target.value)} /></label>
        <div className="acciones">
          <button type="button" className="secundario" onClick={onCerrar}>Cancelar</button>
          <button type="submit">Enviar respuesta</button>
        </div>
      </form>
    </Dialogo>
  );
}

// ------------------------------------------------------------- ¿qué vía te corresponde?
const PREGUNTAS: { clave: string; texto: string; tipo?: string; sub?: string }[] = [
  { clave: "monto", texto: "¿Vas a aumentar el monto de una inversión del programa?", tipo: "incremento_monto" },
  { clave: "sustituye", texto: "¿Vas a reemplazar un proyecto por otro?", sub: "plan" },
  { clave: "liberados", texto: "¿Una donación o transferencia liberó recursos propios que quieres destinar a otra inversión?", tipo: "recursos_liberados_93_2" },
  { clave: "adelanto", texto: "¿Vas a adelantar la ejecución de una inversión prevista?", tipo: "adelanto_94_2" },
  { clave: "reprograma", texto: "¿Vas a reprogramar dos o más inversiones sin cambiar los montos anuales?", tipo: "reprogramacion_94_4" },
  { clave: "nombre", texto: "¿Solo cambia el nombre de una inversión aprobada en el SNPMGI?", tipo: "cambio_nombre_94_5" },
];

interface ResultadoVia {
  ruta: string; titulo: string; regla_aplicada: string; explicacion: string; texto_citado: { ubicacion: string; texto: string }[];
  advertencias: string[]; faltantes: string[]; supuestos: string[]; documentos: { texto: string; fuente: string }[];
  documentos_pendientes?: { texto: string; pregunta_dre: string } | null; decision: string;
}

export function RevisarVia({ codEps, proyectos }: { codEps: string; proyectos: { cod_proyecto: string; nombre_proyecto: string }[] }) {
  const [resp, setResp] = useState<Record<string, boolean>>({});
  const [plan, setPlan] = useState<boolean | null>(null);
  const [proyecto, setProyecto] = useState("");
  const [monto, setMonto] = useState("");
  const [costo, setCosto] = useState("");
  const [res, setRes] = useState<ResultadoVia | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hechos, setHechos] = useState<Record<string, boolean>>({});

  // Primera pregunta con «Sí» decide el tipo de cambio; si todas son «No», es otro caso del párrafo 93.1.
  let tipo: string | null = null;
  let siguiente = PREGUNTAS.length;
  for (let i = 0; i < PREGUNTAS.length; i++) {
    const q = PREGUNTAS[i];
    if (resp[q.clave] === undefined) { siguiente = i; break; }
    if (resp[q.clave]) {
      if (q.sub) tipo = plan === null ? null : plan ? "sustitucion_93_1_4" : "sustitucion_93_1_3";
      else tipo = q.tipo!;
      siguiente = i;
      break;
    }
  }
  if (!tipo && siguiente === PREGUNTAS.length && PREGUNTAS.every((q) => resp[q.clave] === false)) tipo = "otro_93_1";
  const necesitaProyecto = tipo === "incremento_monto" || tipo?.startsWith("sustitucion");
  const responder = (clave: string, v: boolean) => {
    const i = PREGUNTAS.findIndex((q) => q.clave === clave);
    const nuevas: Record<string, boolean> = {};
    PREGUNTAS.slice(0, i).forEach((q) => { if (resp[q.clave] !== undefined) nuevas[q.clave] = resp[q.clave]; });
    nuevas[clave] = v;
    setResp(nuevas);
    setRes(null);
    if (clave === "sustituye") setPlan(null);
  };
  const consultar = async () => {
    try {
      setRes(await pedir<ResultadoVia>("/prechequeo/programa-inversiones", { method: "POST", body: JSON.stringify({
        cod_eps: codEps, tipo_cambio: tipo, anio_solicitud: new Date().getFullYear(), cod_proyecto: proyecto || null,
        monto_nuevo_pendiente: monto ? Number(monto) : null, costo_proyecto_sustituto: costo ? Number(costo) : null }) }));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const SiNo = ({ clave, valor, onSi, onNo }: { clave: string; valor: boolean | undefined; onSi: () => void; onNo: () => void }) => (
    <span className="si-no" role="group" aria-label={`Respuesta a ${clave}`}>
      <button type="button" aria-pressed={valor === true} onClick={onSi}>Sí</button>
      <button type="button" aria-pressed={valor === false} onClick={onNo}>No</button>
    </span>
  );
  const visibles = PREGUNTAS.slice(0, Math.min(siguiente + 1, PREGUNTAS.length));
  return (
    <section className="tarjeta" id="via" aria-labelledby="via-titulo">
      <span className="pildora pil-info">Antes de presentar</span>
      <h2 id="via-titulo" style={{ marginTop: 8 }}>¿Qué vía te corresponde?</h2>
      <p className="detalle">Responde Sí o No. Te orientamos según los arts. 93 y 94 del RGT y te decimos qué documentos menciona la norma.</p>
      {visibles.map((q, i) => (
        <div key={q.clave}>
          <div className="pregunta"><span>{i + 1} · {q.texto}</span>
            <SiNo clave={q.texto} valor={resp[q.clave]} onSi={() => responder(q.clave, true)} onNo={() => responder(q.clave, false)} /></div>
          {q.sub && resp[q.clave] && (
            <div className="pregunta"><span>¿El nuevo proyecto es del Plan de Acciones de Urgencia o del Plan de Reflotamiento?</span>
              <SiNo clave="plan" valor={plan ?? undefined} onSi={() => { setPlan(true); setRes(null); }} onNo={() => { setPlan(false); setRes(null); }} /></div>
          )}
        </div>
      ))}
      {tipo && (
        <div className="via-resultado">
          <p><strong>Tu caso:</strong> {t("tipo_cambio", tipo)}</p>
          {necesitaProyecto && (
            <div className="filtros-linea" style={{ margin: "6px 0" }}>
              <label>Proyecto
                <select value={proyecto} onChange={(e) => setProyecto(e.target.value)}>
                  <option value="">Elegir…</option>
                  {proyectos.map((p) => <option key={p.cod_proyecto} value={p.cod_proyecto}>{p.cod_proyecto} · {p.nombre_proyecto}</option>)}
                </select>
              </label>
              {tipo === "incremento_monto" ? (
                <label>Nuevo monto pendiente (S/)<input type="number" min={0} value={monto} onChange={(e) => setMonto(e.target.value)} /></label>
              ) : (
                <label>Costo del proyecto nuevo (S/)<input type="number" min={0} value={costo} onChange={(e) => setCosto(e.target.value)} /></label>
              )}
            </div>
          )}
          <button type="button" onClick={consultar}>Ver la vía sugerida</button>
        </div>
      )}
      {error && <p className="mensaje mensaje-error" role="alert">{error}</p>}
      {res && (
        <div role="status" aria-live="polite">
          <p className="mensaje mensaje-ok"><strong>{res.titulo}.</strong> {humanizar(res.explicacion)}</p>
          <p className="meta">Regla aplicada: <ChipFuente texto={res.regla_aplicada} /></p>
          {res.texto_citado.slice(0, 2).map((x) => <blockquote key={x.ubicacion} className="cita">«{x.texto}» ({x.ubicacion})</blockquote>)}
          {res.advertencias.map((a) => <p key={a} className="aviso">⚠ {humanizar(a)}</p>)}
          {res.faltantes.length > 0 && <p className="detalle">Falta: {humanizar(res.faltantes.join("; "))}.</p>}
          <h3>Documentos que menciona la norma</h3>
          <ul className="lista-docs">
            {res.documentos.map((x) => (
              <li key={x.texto}><label><input type="checkbox" checked={!!hechos[x.texto]}
                onChange={(e) => setHechos({ ...hechos, [x.texto]: e.target.checked })} /> <span>{x.texto} <ChipFuente texto={x.fuente} /></span></label></li>
            ))}
            {res.documentos.length === 0 && <li>La norma citada no menciona documentos para este caso.</li>}
          </ul>
          {res.documentos_pendientes && <p className="detalle">{res.documentos_pendientes.texto}</p>}
          <p><strong>{res.decision}</strong></p>
        </div>
      )}
      {!res && <p className="meta">Es una orientación. La decisión final siempre es de Sunass.</p>}
    </section>
  );
}

// ------------------------------------------------------------- mis trámites
function MisTramites({ d }: { d: MiEpsDatos }) {
  return (
    <section className="tarjeta" id="tramites" aria-labelledby="tramites-titulo">
      <h2 id="tramites-titulo">Mis trámites</h2>
      {d.tramites.length === 0 && <p className="detalle">No tienes trámites en curso a la fecha de corte.</p>}
      {d.tramites.map((x) => (
        <div key={x.id_expediente} className="tramite">
          <div className="fila">
            <strong><Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link> · {t("tipo_procedimiento", x.tipo_procedimiento)}</strong>
            {x.le_toca_a_la_eps ? <Pildora tono="warn" icono="✋">Te toca a ti</Pildora> : <Pildora tono="info" icono="◷">Sunass evalúa</Pildora>}
          </div>
          <BarraPasos p={x.pasos} compacto />
          <p className="meta">{x.pasos ? `Paso ${x.pasos.actual + 1} de ${x.pasos.n} (${x.pasos.pasos[x.pasos.actual]?.nombre}) · ` : ""}{x.en_que_va}</p>
        </div>
      ))}
      {d.concluidos.slice(0, 3).map((x) => (
        <div key={x.id_expediente} className="tramite">
          <div className="fila">
            <strong><Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link> · {t("tipo_procedimiento", x.tipo_procedimiento)}</strong>
            <Pildora tono="ok" icono="✓">{x.resultado ? t("resultado", x.resultado) : "Concluido"}</Pildora>
          </div>
          <BarraPasos p={x.pasos} compacto />
          <p className="meta">Concluido el {fecha(x.fecha_conclusion)}</p>
        </div>
      ))}
      <p className="meta">Ves el mismo recorrido que Sunass, sin sus documentos internos (informes y memorandos).</p>
    </section>
  );
}

// ------------------------------------------------------------- mi fondo
/** Monto abreviado para los recuadros («S/ 2,91 M»); el monto completo va en la etiqueta accesible. */
export function solesCorto(v: number): string {
  if (Math.abs(v) >= 1e6) return `S/ ${(v / 1e6).toFixed(2).replace(".", ",")} M`;
  if (Math.abs(v) >= 1e4) return `S/ ${Math.round(v / 1e3)} mil`;
  return soles(v);
}

function Recuadro({ titulo, valor, clase, def }: { titulo: string; valor: number; clase?: string; def: string }) {
  return (
    <div className={`recuadro${clase ? ` ${clase}` : ""}`} title={`${def}: ${soles(valor)}`} aria-label={`${titulo}: ${soles(valor)}`}>
      <span>{titulo}</span><strong aria-hidden="true">{solesCorto(valor)}</strong>
    </div>
  );
}

function MiFondo({ d }: { d: MiEpsDatos }) {
  const r = d.resumen_fondo;
  return (
    <section className="tarjeta" id="fondo" aria-labelledby="fondo-titulo">
      <h2 id="fondo-titulo">Mi fondo de inversiones</h2>
      <p className="detalle">Lo programado, lo depositado, lo autorizado por Sunass y lo que usaste{r?.hasta ? ` (hasta ${r.hasta})` : ""}.</p>
      {r && (
        <>
          <div className="cuatro-fondo">
            <Recuadro titulo="Programado" valor={r.programado} def={r.definiciones.programado} />
            <Recuadro titulo="Depositado" valor={r.depositado} def={r.definiciones.depositado} />
            <Recuadro titulo="Autorizado" valor={r.autorizado} clase="medio" def={r.definiciones.autorizado} />
            <Recuadro titulo="Usado" valor={r.usado} clase="oscuro" def={r.definiciones.usado} />
          </div>
          <p className="aviso">{r.aviso.replace(/(\d)\.(\d)/g, "$1,$2")}</p>
          <p className="meta"><ChipFuente texto={r.fuente} etiqueta="DS05 · DS02" /></p>
        </>
      )}
    </section>
  );
}
