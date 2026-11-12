import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, pedir, type Alerta, type Documento, type Evento, type Ficha, type Hito } from "./api";
import { FormularioDocumento, Rotulo, fecha } from "./componentes";
import { soles, type Peldano, type Proyecto, type RutaUso } from "./dinero";
import { humanizar, t } from "./etiquetas";
import { useSesion } from "./sesion";
import { BarraPasos, ChipFuente, Dialogo, PildoraPlazo, irA, useToast, type Pasos } from "./ui";

export interface ItemBandeja {
  id_expediente: string;
  cod_eps: string | null;
  empresa?: string;
  tipo_procedimiento: string;
  especialista: string;
  estado: string;
  hito_al_corte: string | null;
  responsable_al_corte: string | null;
  alerta: { reloj: string; estado: string; titulo: string; mensaje: string; dias_restantes: number | null;
    fecha_limite: string | null; fuente: string } | null;
  siguiente_paso: string;
  evidencia_faltante: { tipo: string; hito: string | null; texto: string }[];
  por_que_importa: string[];
  naturaleza: string;
  fuente: string;
  base_normativa?: string | null;
  te_toca?: boolean;
  en_pausa?: boolean;
  pasos?: Pasos | null;
  proyecto?: { cod_proyecto: string; nombre: string; localidad: string } | null;
}

interface RespuestaBandeja {
  fecha_corte: string;
  especialista: string | null;
  items: ItemBandeja[];
  resumen: Record<string, number>;
  rotulo_asignacion: string;
  orden: string;
}

export function plazoEnPalabras(d: number | null | undefined): string {
  if (d == null) return "sin plazo calculable";
  if (d < 0) return `vencido hace ${-d} ${-d === 1 ? "día hábil" : "días hábiles"}`;
  if (d === 0) return "vence hoy";
  return `quedan ${d} ${d === 1 ? "día hábil" : "días hábiles"}`;
}

const URGENTES = ["vencido", "no_calculable", "por_vencer"];

// ------------------------------------------------------------------ bandeja
export function Bandeja() {
  const { usuario, corte, config } = useSesion();
  const [esp, setEsp] = useState("");
  const [r, setR] = useState<RespuestaBandeja | null>(null);
  const [params] = useSearchParams();
  const [sel, setSel] = useState<string | null>(params.get("exp"));
  const [error, setError] = useState<string | null>(null);
  const detalle = useRef<HTMLDivElement>(null);
  const coordinacion = usuario.rol !== "especialista_srt";

  useEffect(() => {
    const q = new URLSearchParams({ fecha_corte: corte });
    if (esp) q.set("especialista", esp);
    pedir<RespuestaBandeja>(`/bandeja?${q}`).then((x) => {
      setR(x);
      setSel((s) => (s && x.items.some((i) => i.id_expediente === s) ? s : x.items[0]?.id_expediente ?? null));
    }).catch((e) => setError(e.message));
  }, [corte, esp]);

  if (error) return <p className="mensaje mensaje-error" role="alert">No se pudo cargar la bandeja: {error}</p>;
  if (!r) return <p className="cargando">Cargando su bandeja…</p>;
  const urgentes = URGENTES.reduce((n, e) => n + (r.resumen[e] ?? 0), 0);
  const item = r.items.find((x) => x.id_expediente === sel) ?? null;
  const nombre = usuario.nombre.replace(/\s*\(.*\)$/, "");

  return (
    <>
      <div className="saludo">
        <h1>Hola, {nombre}.</h1>
        <p className="sub" role="status">
          {urgentes === 0 ? "Hoy no tienes expedientes urgentes." : <>Hoy tienes <strong className="urgentes">{urgentes} {urgentes === 1 ? "expediente" : "expedientes"}</strong> que {urgentes === 1 ? "necesita" : "necesitan"} tu atención.</>}
          {" "}Empecemos por el más urgente. <span className="rotulo rotulo-supuesto">{r.rotulo_asignacion}</span>
        </p>
        {corte !== config.fecha_corte_muestra && (
          <p className="aviso">Está viendo la bandeja a una fecha anterior a la de la muestra: lo posterior aún no se conoce.</p>
        )}
      </div>
      {coordinacion && (
        <form className="filtros-linea" aria-label="Filtrar la bandeja" onSubmit={(e) => e.preventDefault()}>
          <label>Especialista (ficticio)
            <select value={esp} onChange={(e) => setEsp(e.target.value)}>
              <option value="">Todo el equipo</option>
              {["esp-srt-01", "esp-srt-02", "esp-srt-03"].map((x) => <option key={x}>{x}</option>)}
            </select>
          </label>
        </form>
      )}
      {r.items.length === 0 ? <p className="tarjeta">No tiene expedientes en trámite a esta fecha.</p> : (
        <div className="bandeja-grid">
          <section aria-labelledby="mi-bandeja">
            <h2 id="mi-bandeja" className="lista-exp-titulo">Mi bandeja · {r.items.length} expedientes · por plazo restante</h2>
            <ol className="lista-exp" aria-label="Expedientes ordenados por plazo restante">
              {r.items.map((x) => (
                <li key={x.id_expediente}>
                  <button type="button" className={`exp-item estado-${x.estado}`} aria-current={x.id_expediente === sel}
                          onClick={() => { setSel(x.id_expediente); if (window.innerWidth < 1100) irA(detalle.current); }}>
                    <span className="fila"><span className="cod">{x.id_expediente}</span>
                      <PildoraPlazo estado={x.estado} dias={x.alerta?.dias_restantes} enPausa={x.en_pausa} /></span>
                    <span className="detalle">{x.cod_eps ?? x.empresa} · {t("tipo_procedimiento", x.tipo_procedimiento)}</span>
                    <span className="prox">Próxima acción: <strong>{x.siguiente_paso.replace(/\.$/, "")}</strong></span>
                    {coordinacion && <span className="meta">{x.especialista} (ficticio)</span>}
                  </button>
                </li>
              ))}
            </ol>
          </section>
          <div ref={detalle}>{item && <DetalleExpediente key={item.id_expediente} x={item} />}</div>
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------- detalle
function DetalleExpediente({ x }: { x: ItemBandeja }) {
  const { corte, puede, usuario } = useSesion();
  const toast = useToast();
  const [f, setF] = useState<Ficha | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [registrar, setRegistrar] = useState(false);
  const cargar = useCallback(() => {
    api.ficha(x.id_expediente, corte).then(setF).catch((e) => setError(e.message));
  }, [x.id_expediente, corte]);
  useEffect(cargar, [cargar]);

  const a = x.alerta;
  const p = x.pasos;
  const etq = x.te_toca ? "te toca a ti" : x.en_pausa ? "esperando a la EP" : `está en ${t("responsable", x.responsable_al_corte)}`;
  return (
    <div className="detalle-col" aria-label={`Detalle de ${x.id_expediente}`}>
      <section className="prox-accion" aria-labelledby="prox-titulo">
        <span className="etq">Próxima acción · {etq}</span>
        <h2 id="prox-titulo">{x.siguiente_paso.replace(/\.$/, "")} · {x.id_expediente}</h2>
        <p>
          {x.cod_eps ?? x.empresa} · {t("tipo_procedimiento", x.tipo_procedimiento)}
          {x.base_normativa && <> · {x.base_normativa}</>}
          {p && <> · paso {p.actual + 1} de {p.n} ({p.pasos[p.actual]?.nombre})</>}
          {x.proyecto && <> · Proyecto: {x.proyecto.nombre} ({x.proyecto.localidad})</>}
        </p>
        <div className="tres-respuestas-mini">
          <p><strong>¿Qué requiere acción?</strong> {a ? `${t("reloj", a.reloj)}: ${plazoEnPalabras(a.dias_restantes)}${a.fecha_limite ? ` (vence el ${fecha(a.fecha_limite)})` : ""}.` : "Sin plazo abierto."}</p>
          <p><strong>¿Qué falta?</strong> {x.evidencia_faltante.length === 0 ? "No falta evidencia registrada." :
            `${x.evidencia_faltante.length} ${x.evidencia_faltante.length === 1 ? "evidencia" : "evidencias"}: ${humanizar(x.evidencia_faltante[0].texto)}${x.evidencia_faltante.length > 1 ? " …" : ""}`}</p>
          <p><strong>¿Por qué importa?</strong> {x.por_que_importa.map(humanizar).join(" ")}</p>
        </div>
        <div className="acciones">
          {puede("registrar_documento") && <button type="button" className="claro" onClick={() => setRegistrar(true)}>Registrar documento o avance</button>}
          <Link className="boton fantasma" to={`/expedientes/${x.id_expediente}`}>Abrir expediente completo</Link>
        </div>
      </section>

      {p && (
        <section className="tarjeta" aria-label="Pasos del procedimiento">
          <BarraPasos p={p} />
          <p className="meta">Pasos agrupados a partir de los hitos del diccionario <span className="rotulo rotulo-supuesto">Supuesto de presentación</span></p>
        </section>
      )}

      {error && <p className="mensaje mensaje-error" role="alert">No se pudo abrir el detalle: {error}</p>}
      {!f ? <p className="cargando">Cargando el detalle…</p> : (
        <>
          <TresRelojes relojes={f.relojes} />
          <div className="dos-col">
            <div><LineaCompacta hitos={f.linea_de_tiempo} docs={f.documentos} /></div>
            <div>
              <TarjetaIA f={f} puedeConfirmar={puede("confirmar_registro")} usuarioId={usuario.id}
                         onCambio={(texto) => { toast(texto); cargar(); }} onError={(e) => toast(e, true)} />
              <MiniRuta f={f} />
            </div>
          </div>
        </>
      )}
      {registrar && f && (
        <Dialogo titulo={`Registrar en ${x.id_expediente}`} onCerrar={() => setRegistrar(false)}>
          <FormularioDocumento hitos={f.linea_de_tiempo.map((h) => h.hito)} deshabilitado={false}
            onEnviar={async (datos) => {
              try {
                await api.registrarDocumento(x.id_expediente, datos, usuario.id);
                setRegistrar(false);
                toast("Documento registrado; quedó en la bitácora.");
                cargar();
              } catch (e) {
                toast((e as Error).message, true);
              }
            }} />
          <p className="acciones" style={{ marginTop: 10 }}><button type="button" className="secundario" onClick={() => setRegistrar(false)}>Cancelar</button></p>
        </Dialogo>
      )}
    </div>
  );
}

// ------------------------------------------------------------- tres relojes
const RELOJES = [
  { clave: "normativo", titulo: "Plazo normativo" },
  { clave: "interno", titulo: "Plazo interno" },
  { clave: "oficio", titulo: "Plazo del oficio" },
];

function elegir(relojes: Alerta[], reloj: string): Alerta | undefined {
  const abiertos = relojes.filter((r) => r.reloj === reloj && ["vencido", "por_vencer", "en_plazo", "no_calculable"].includes(r.estado));
  const orden = ["vencido", "no_calculable", "por_vencer", "en_plazo"];
  return abiertos.sort((a, b) => orden.indexOf(a.estado) - orden.indexOf(b.estado))[0]
    ?? [...relojes].reverse().find((r) => r.reloj === reloj);
}

export function TresRelojes({ relojes }: { relojes: Alerta[] }) {
  return (
    <section className="tarjeta tres-relojes" aria-label="Tres relojes">
      {RELOJES.map(({ clave, titulo }) => {
        const a = elegir(relojes, clave);
        return (
          <div key={clave} className="reloj-col" aria-label={titulo}>
            <div className="tit">{titulo}{a && <PildoraPlazo estado={a.estado} dias={a.dias_restantes} />}</div>
            {!a ? <p className="detalle">{clave === "oficio" ? "No hay un plazo de oficio registrado." : "Sin plazo para este expediente."}</p>
              : a.estado === "no_calculable" ? (
                <p><strong>No puedo calcular:</strong> {humanizar(a.mensaje).replace(/^No puedo calcular( todavía)?:\s*/i, "")}</p>
              ) : (
                <>
                  <span className="fecha-g">{a.fecha_limite ? fecha(a.fecha_limite) : a.dias_restantes != null ? `${Math.abs(a.dias_restantes)} DH` : "—"}</span>
                  <span className="detalle">{a.dias_restantes != null ? plazoEnPalabras(a.dias_restantes) : t("estado_reloj", a.estado)} · {humanizar(a.titulo)}</span>
                </>
              )}
            {a && <span><ChipFuente texto={a.fuente} detalle={<>Regla {a.regla_id ?? "—"} ({a.estado_validacion}). {humanizar(a.mensaje)}</>} /></span>}
          </div>
        );
      })}
    </section>
  );
}

// ------------------------------------------------------------- línea de tiempo
const EVIDENCIA: Record<string, string> = {
  "documento registrado": "evidencia-registrado",
  "registro propuesto, falta confirmar": "evidencia-propuesto",
  "código en DS02, sin archivo": "evidencia-codigo",
  "declarado, no verificado": "evidencia-declarado",
};

const VISIBLES = 4;

export function LineaCompacta({ hitos, docs }: { hitos: Hito[]; docs: Documento[] }) {
  const iniciados = hitos.filter((h) => h.estado !== "no iniciado");
  const corte = Math.max(0, iniciados.length - VISIBLES);
  const anteriores = hitos.slice(0, corte);
  const recientes = hitos.slice(corte);
  const item = (h: Hito) => {
    const doc = docs.find((d) => h.evidencia.documentos.includes(d.id));
    return (
      <li key={h.nro} className={h.estado === "en curso" ? "en-curso" : h.estado === "no iniciado" ? "no-iniciado" : ""}>
        <div className="titulo-hito">{t("hito", h.hito)}</div>
        <div className="detalle">
          {t("responsable", h.responsable)} · {fecha(h.fecha_inicio)}{h.fecha_fin ? ` → ${fecha(h.fecha_fin)}` : h.estado === "en curso" ? " · en curso" : ""}
          {h.cuenta_plazo === false && " · a cargo de la EP: pausa el plazo de Sunass"}
        </div>
        <div>
          <span className={`evidencia ${EVIDENCIA[h.evidencia.estado] ?? ""}`}>{h.evidencia.estado}</span>{" "}
          {h.evidencia.referencia && (
            <ChipFuente texto={`${h.evidencia.referencia}${doc?.pagina ? `, pág. ${doc.pagina}` : ""}`}
                        detalle={doc?.fuente ? humanizar(doc.fuente) : h.fila_ds02 != null ? `DS02 fila ${h.fila_ds02} (sintético)` : undefined} />
          )}
        </div>
      </li>
    );
  };
  const sinDoc = hitos.filter((h) => h.evidencia.estado === "declarado, no verificado" && h.estado !== "no iniciado").length;
  return (
    <section className="tarjeta" aria-labelledby="linea-titulo">
      <h3 id="linea-titulo" style={{ marginTop: 0 }}>Línea de tiempo con evidencia</h3>
      <p className="detalle">Cada paso, su documento. {sinDoc > 0 ? `${sinDoc} ${sinDoc === 1 ? "hito figura" : "hitos figuran"} «declarado, no verificado» (sin documento).` : "Todos los hitos iniciados tienen evidencia."}</p>
      {anteriores.length > 0 && (
        <details>
          <summary>Ver {anteriores.length} {anteriores.length === 1 ? "hito anterior" : "hitos anteriores"}</summary>
          <ol className="linea" aria-label="Hitos anteriores">{anteriores.map(item)}</ol>
        </details>
      )}
      <ol className="linea" aria-label="Línea de tiempo del expediente">{recientes.map(item)}</ol>
    </section>
  );
}

// ------------------------------------------------------------- la IA leyó
type Registro = (Documento & { clase: "documento" }) | (Evento & { clase: "evento"; origen?: string });

export function TarjetaIA({ f, puedeConfirmar, usuarioId, onCambio, onError }: {
  f: Ficha; puedeConfirmar: boolean; usuarioId: string; onCambio: (texto: string) => void; onError: (texto: string) => void;
}) {
  const [corrigiendo, setCorrigiendo] = useState<Registro | null>(null);
  // Primero los plazos y prórrogas (son los que cambian los relojes), luego los documentos.
  const transcritos: Registro[] = [
    ...f.eventos.filter((e) => ["transcrito_ia", "corregido"].includes((e as Evento & { origen?: string }).origen ?? "") && e.estado_registro === "propuesto")
      .map((e) => ({ ...e, clase: "evento" as const })),
    ...f.documentos.filter((d) => ["transcrito_ia", "corregido"].includes(d.origen) && d.estado_registro === "propuesto")
      .map((d) => ({ ...d, clase: "documento" as const })),
  ];
  const confirmar = async (r: Registro) => {
    try {
      if (r.clase === "documento") await api.confirmarDocumento(r.id, usuarioId);
      else await api.confirmarEvento(r.id, usuarioId);
      onCambio("Confirmado. Quedó en la bitácora.");
    } catch (e) {
      onError((e as Error).message);
    }
  };
  return (
    <section className="tarjeta ia-tarjeta" aria-labelledby="ia-titulo">
      <div className="fila" style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <h3 id="ia-titulo" style={{ margin: 0 }}>La IA leyó el documento</h3>
        {transcritos.length > 0 && <span className="pildora pil-vio">Por confirmar ({transcritos.length})</span>}
      </div>
      {transcritos.length === 0 ? (
        <p className="detalle">No hay transcripciones por confirmar en este expediente. La extracción asistida con IA llega en la Fase 6;
          hoy solo se muestran los registros de los casos reales transcritos con asistencia de IA.</p>
      ) : (
        <>
          <p className="detalle">Transcrito con asistencia de IA. Nada cambia los plazos hasta que una persona lo confirme.</p>
          {transcritos.slice(0, 4).map((r) => (
            <div key={`${r.clase}${r.id}`} className="ia-item">
              <strong>{r.clase === "documento" ? (r.numero && r.numero.toLowerCase().startsWith(t("tipo_documento", r.tipo).toLowerCase())
                ? r.numero : `${t("tipo_documento", r.tipo)} ${r.numero ?? ""}`) :
                `${r.tipo === "prorroga" ? "Prórroga" : "Plazo del oficio"}: ${r.dias_dh != null ? `${r.dias_dh} DH` : "plazo no indicado"}`}</strong>
              <span className="detalle"> · {t("hito", r.hito)}{r.origen === "corregido" ? " · corregido por una persona" : ""}</span>
              {r.cita && <blockquote className="cita-bloque">«{r.cita}»</blockquote>}
              {r.fuente && <ChipFuente texto={r.fuente} />}
              {puedeConfirmar && (
                <div className="acciones" style={{ marginTop: 8 }}>
                  <button type="button" className="secundario" onClick={() => setCorrigiendo(r)}>Corregir</button>
                  <button type="button" onClick={() => confirmar(r)}>Confirmar</button>
                </div>
              )}
            </div>
          ))}
          {transcritos.length > 4 && <p className="meta">Y {transcritos.length - 4} más en el expediente completo.</p>}
        </>
      )}
      {corrigiendo && (
        <Correccion r={corrigiendo} usuarioId={usuarioId} onCerrar={() => setCorrigiendo(null)}
                    onListo={() => { setCorrigiendo(null); onCambio("Corrección registrada con su motivo. Falta confirmar."); }}
                    onError={onError} />
      )}
    </section>
  );
}

function Correccion({ r, usuarioId, onCerrar, onListo, onError }: {
  r: Registro; usuarioId: string; onCerrar: () => void; onListo: () => void; onError: (t: string) => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [valor, setValor] = useState(r.clase === "documento" ? r.numero ?? "" : String(r.dias_dh ?? ""));
  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    const cuerpo = r.clase === "documento" ? { motivo, numero: valor } : { motivo, dias_dh: valor === "" ? null : Number(valor) };
    try {
      await pedir(`/${r.clase === "documento" ? "documentos" : "eventos"}/${r.id}/corregir`,
                  { method: "POST", body: JSON.stringify(cuerpo) }, usuarioId);
      onListo();
    } catch (err) {
      onError((err as Error).message);
    }
  };
  return (
    <Dialogo titulo="Corregir la transcripción" onCerrar={onCerrar}>
      <form onSubmit={enviar}>
        <label className="campo">{r.clase === "documento" ? "Número del documento" : "Días hábiles del plazo"}
          <input value={valor} onChange={(e) => setValor(e.target.value)} type={r.clase === "documento" ? "text" : "number"} min={0} />
        </label>
        <label className="campo">Motivo de la corrección (queda en la bitácora)
          <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} required minLength={5} />
        </label>
        <div className="acciones">
          <button type="button" className="secundario" onClick={onCerrar}>Cancelar</button>
          <button type="submit">Guardar corrección</button>
        </div>
      </form>
    </Dialogo>
  );
}

// ------------------------------------------------------------- mini ruta del dinero
function Fila({ nombre, valor, max, clase, fuente, pendiente }: {
  nombre: string; valor: number | null | undefined; max: number; clase: string; fuente?: string; pendiente?: string;
}) {
  const ancho = valor != null && max > 0 ? Math.min(100, (valor / max) * 100) : 0;
  return (
    <>
      <dt>{nombre}</dt>
      <dd style={{ textAlign: "left" }}>
        <div className={`barrita ${clase}`} aria-hidden="true"><span style={{ width: `${ancho}%` }} /></div>
        {fuente && <ChipFuente texto={fuente} />}
      </dd>
      <dd>{valor != null ? soles(valor) : (pendiente ?? "Sin dato")}</dd>
    </>
  );
}

export function MiniRuta({ f }: { f: Ficha }) {
  const e = f.expediente as Record<string, unknown>;
  const rd = f.ruta_dinero;
  const escalera = rd && "escalera" in rd ? (rd as RutaUso).escalera : null;
  const proy = rd && "proyectos" in rd ? (rd as { proyectos: Proyecto[] }).proyectos[0] : null;
  const pel = (k: string) => escalera?.find((x: Peldano) => x.peldano === k);
  const enTramite = e.estado === "en_tramite" || e.estado === "en trámite";
  const programado = proy?.monto_programado_vigente ?? null;
  const solicitado = (e.monto_solicitado as number | null) ?? pel("solicitado")?.monto ?? null;
  const autorizado = enTramite ? null : ((e.monto_aprobado as number | null) ?? pel("autorizado")?.monto ?? null);
  const usado = proy ? proy.ejecucion_financiera : pel("usado")?.monto ?? null;
  const max = Math.max(1, ...[programado, solicitado, autorizado, usado].map((v) => Number(v ?? 0)));
  if (programado == null && solicitado == null && usado == null && !escalera) {
    return (
      <section className="tarjeta mini-ruta" aria-labelledby="ruta-mini">
        <h3 id="ruta-mini" style={{ marginTop: 0 }}>Ruta del dinero</h3>
        <p className="detalle">Este trámite no tiene montos de inversión asociados en la muestra (DS02 no registra monto solicitado ni proyecto).</p>
      </section>
    );
  }
  return (
    <section className="tarjeta mini-ruta" aria-labelledby="ruta-mini">
      <h3 id="ruta-mini" style={{ marginTop: 0 }}>Ruta del dinero</h3>
      <p className="detalle">Lo programado, lo que pide la EPS, lo autorizado y lo usado. Pendiente nunca es cero.</p>
      <dl>
        <Fila nombre="Programado" valor={programado} max={max} clase="b-clara" fuente={proy ? "DS03 programa de inversiones (vigente)" : undefined}
              pendiente="No aplica" />
        <Fila nombre="Solicitado" valor={solicitado} max={max} clase="" fuente={solicitado != null ? (escalera ? pel("solicitado")?.fuente : "DS02 monto solicitado") : undefined} />
        <Fila nombre="Autorizado" valor={autorizado} max={max} clase="b-oscura" fuente={autorizado != null ? (escalera ? pel("autorizado")?.fuente : "DS02 monto aprobado") : undefined}
              pendiente={enTramite ? "Pendiente" : "Sin dato"} />
        <Fila nombre={proy ? "Ejecutado" : "Usado"} valor={usado} max={max} clase="b-ok"
              fuente={usado != null ? (proy ? `DS04 ejecución acumulada (${proy.ultimo_trimestre ?? "—"})` : pel("usado")?.fuente) : undefined}
              pendiente={proy?.aviso_ejecucion ? "No puedo determinar" : "Sin dato"} />
      </dl>
      {proy && <p className="meta">Proyecto {proy.cod_proyecto} · avance financiero {proy.avance_financiero ?? "—"} % sobre programado vigente <Rotulo naturaleza="sintético" /></p>}
    </section>
  );
}
