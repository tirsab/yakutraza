import { useEffect, useId, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Rotulo } from "./componentes";

// ------------------------------------------------------------------ tipos
type Mapa = Record<string, string>;

export interface Peldano {
  peldano: string;
  estado: string;
  monto: number | null;
  fondo: string | string[] | null;
  area?: string | null;
  detalle: string;
  fuente: string;
}

export interface RutaUso {
  id_expediente: string;
  cod_eps: string | null;
  empresa?: string;
  naturaleza: string;
  articulo: string | null;
  escalera: Peldano[];
  senal: string | null;
}

interface FilaFondo {
  fondo: string;
  nombre: string;
  solicitado: number;
  autorizado: number;
  uso_ordinario: number;
  uso_excepcional_art_89: number;
  uso_emergencia_art_90: number;
  verificado: number | null;
  verificaciones_pendientes: number;
  deposito_programado: number;
  deposito_efectuado: number;
  saldo_final: number | null;
  saldo_al?: string | null;
  expedientes?: string[];
}

interface UsoEmergencia {
  cod_eps: string;
  anio_mes: string;
  tipo_fondo: string;
  monto: number;
  texto: string;
  informe: { estado: string; fecha_limite: string | null; mensaje: string };
  fuente: string;
}

interface Resumen {
  filas: FilaFondo[];
  total: FilaFondo;
  notas: string[];
  fuente: string;
  visibilidad: Mapa;
  usos_emergencia: UsoEmergencia[];
  expedientes_uso: RutaUso[];
  casos_reales: RutaUso[];
  filtros: { cod_eps: string[]; anios: number[]; fondos: Record<string, string> };
}

export interface Proyecto {
  cod_proyecto: string;
  cod_eps: string;
  nombre_proyecto: string;
  localidad: string;
  fuente_financiamiento: string;
  tipo_periodo: string;
  meta_asociada: string | null;
  poblacion_beneficiaria: number | null;
  monto_programado_original: number;
  monto_programado_vigente: number;
  modificado: boolean;
  expediente_modificacion: string[];
  ejecucion_financiera: number | null;
  ultimo_trimestre: string | null;
  estado_ejecucion: string | null;
  avance_fisico: number | null;
  avance_financiero: number | null;
  avance_financiero_original: number | null;
  base_avance_financiero: string;
  diferencia_pp: number | null;
  senal_revision: boolean;
  aviso_ejecucion: string | null;
  etapa_escalera: string;
  escalera: Peldano[];
  fuente: string;
  conciliacion_mef: Record<string, unknown> | null;
  anios?: { anio: number; original: number; vigente: number; id_expediente_modificacion: string | null; fila: number }[];
  trimestres?: { anio_trimestre: string; estado: string; ejecucion_trimestre: number; ejecucion_acumulada: number;
    avance_fisico: number | null; fila: number }[];
}

// ---------------------------------------------------------------- utilidades
// Mismo formato que el backend (app.calidad.reglas._util.soles): miles con espacio y decimales con coma.
function numero(v: number, decimales: number): string {
  const [ent, dec] = Math.abs(v).toFixed(decimales).split(".");
  const miles = ent.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${v < 0 ? "−" : ""}${miles}${dec ? `,${dec}` : ""}`;
}
export const soles = (v: number | null | undefined) => (v == null ? "—" : `S/ ${numero(v, 2)}`);
const uno = (v: number) => numero(v, 1).replace(/,0$/, "");
export const pct = (v: number | null | undefined) => (v == null ? "—" : `${uno(v)} %`);

async function obtener<T>(ruta: string): Promise<T> {
  const r = await fetch(`/api${ruta}`);
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new Error(typeof j.detail === "string" ? j.detail : `${r.status}`);
  }
  return r.json();
}

function Visible({ nivel }: { nivel?: string }) {
  if (!nivel) return null;
  return (
    <span className={`vis vis-${nivel}`} title="Visibilidad en la vista ciudadana">
      {nivel === "publico" ? "Público" : "Reservado"}
    </span>
  );
}

const PELDANOS: Record<string, string> = {
  solicitado: "Solicitado", autorizado: "Autorizado", usado: "Usado", verificacion_posterior: "Verificación posterior",
  devolucion: "Devolución o exoneración", programado: "Programado", aprobado: "Aprobado", financiado: "Financiado",
  en_ejecucion: "En ejecución", concluido: "Concluido", beneficio_verificado: "Beneficio verificado", paralizado: "Paralizado",
};
const ESTADO_PELDANO: Record<string, string> = {
  cumplido: "✓ Cumplido", pendiente: "◷ Pendiente", declarado: "✎ Declarado", paralizado: "⏸ Paralizado",
  no_aplica: "— No aplica", no_autorizado: "✗ No autorizado", sin_dato: "? Sin dato", exonerada: "✓ Exonerada",
  no_verificado: "? No verificado",
};

function textoFondo(f: Peldano["fondo"], fondos?: Record<string, string>) {
  if (!f) return null;
  const lista = Array.isArray(f) ? f : [f];
  return lista.map((x) => fondos?.[x] ?? x).join(", ");
}

// ---------------------------------------------------------------- escalera
export function Escalera({ pasos, fondos, titulo }: { pasos: Peldano[]; fondos?: Record<string, string>; titulo: string }) {
  return (
    <ol className="escalera" aria-label={titulo}>
      {pasos.map((p) => (
        <li key={p.peldano} className={`peldano peldano-${p.estado}`}>
          <strong>{PELDANOS[p.peldano] ?? p.peldano}</strong> · {ESTADO_PELDANO[p.estado] ?? p.estado}
          {p.monto != null && <> · {soles(p.monto)}</>}
          {p.fondo && <> · <span className="fondo">desde: {textoFondo(p.fondo, fondos)}</span></>}
          {p.area && <> · verifica: {p.area}</>}
          {p.detalle && <div className="detalle">{p.detalle}</div>}
          {p.fuente && p.fuente !== "—" && <div className="meta">Fuente: {p.fuente}</div>}
        </li>
      ))}
    </ol>
  );
}

export function RutaDeUso({ r, fondos }: { r: RutaUso; fondos?: Record<string, string> }) {
  return (
    <article className="alerta" aria-label={`Ruta del dinero de ${r.id_expediente}`}>
      <div>
        <Link to={`/expedientes/${r.id_expediente}`}>{r.id_expediente}</Link> · {r.cod_eps ?? r.empresa} · {r.articulo}
        {" "}<Rotulo naturaleza={r.naturaleza} />
      </div>
      {r.senal && <p className="mensaje mensaje-error">⚠ Señal para revisión: {r.senal}</p>}
      <Escalera pasos={r.escalera} fondos={fondos} titulo={`Escalera de ${r.id_expediente}`} />
    </article>
  );
}

// Barra accesible: programado vigente (contorno) frente a ejecutado (relleno con patrón).
function Barra({ programado, ejecutado }: { programado: number; ejecutado: number | null }) {
  const maximo = Math.max(programado, ejecutado ?? 0, 1);
  const anchoP = (programado / maximo) * 100;
  const anchoE = ((ejecutado ?? 0) / maximo) * 100;
  const patron = `rayas${useId().replace(/:/g, "")}`;
  return (
    <svg width="140" height="18" role="img" aria-label={`Programado ${soles(programado)}; ejecutado ${soles(ejecutado)}`}>
      <defs>
        <pattern id={patron} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="2" height="4" fill="var(--yt-blue-600)" />
        </pattern>
      </defs>
      <rect x="0" y="2" width={`${anchoP}%`} height="14" fill="none" stroke="var(--yt-navy-900)" strokeWidth="1.5" />
      <rect x="0" y="5" width={`${anchoE}%`} height="8" fill={`url(#${patron})`} />
    </svg>
  );
}

// ------------------------------------------------------------------ tablero
export function TableroRutaDelDinero() {
  const [filtro, setFiltro] = useState({ cod_eps: "", anio: "", fondo: "" });
  const [fp, setFp] = useState({ fuente: "", etapa: "", periodo: "vigente", solo_senales: false });
  const [res, setRes] = useState<Resumen | null>(null);
  const [proys, setProys] = useState<{ proyectos: Proyecto[]; visibilidad: Mapa; base_avance_financiero: string; umbral_senal_pp: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [limite, setLimite] = useState(50);

  useEffect(() => {
    const q = new URLSearchParams(Object.entries(filtro).filter(([, v]) => v));
    obtener<Resumen>(`/ruta-dinero/resumen?${q}`).then(setRes).catch((e) => setError(e.message));
  }, [filtro]);
  useEffect(() => {
    const q = new URLSearchParams();
    if (filtro.cod_eps) q.set("cod_eps", filtro.cod_eps);
    if (fp.fuente) q.set("fuente", fp.fuente);
    if (fp.etapa) q.set("etapa", fp.etapa);
    if (fp.periodo) q.set("periodo", fp.periodo);
    if (fp.solo_senales) q.set("solo_senales", "true");
    obtener<typeof proys>(`/ruta-dinero/proyectos?${q}`).then(setProys).catch((e) => setError(e.message));
  }, [filtro.cod_eps, fp]);

  const fondos = res?.filtros.fondos;
  const v = res?.visibilidad ?? {};
  const vp = proys?.visibilidad ?? {};
  const visibles = useMemo(() => proys?.proyectos.slice(0, limite) ?? [], [proys, limite]);

  if (error) return <p className="mensaje mensaje-error">No se pudo cargar la ruta del dinero: {error}</p>;
  if (!res) return <p>Cargando la ruta del dinero…</p>;
  const sel = (k: keyof typeof filtro) => (e: React.ChangeEvent<HTMLSelectElement>) => setFiltro({ ...filtro, [k]: e.target.value });

  return (
    <>
      <h1>Ruta del dinero</h1>
      <p className="sub">
        De qué fondo o reserva sale cada sol: solicitado, autorizado, usado y verificado. Aprobado no es ejecutado.{" "}
        <Rotulo naturaleza="sintético" /> Datos de muestra (DS02, DS03, DS04, DS05).
      </p>
      <form className="formulario" aria-label="Filtros de la ruta del dinero" onSubmit={(e) => e.preventDefault()}>
        <label>EPS
          <select value={filtro.cod_eps} onChange={sel("cod_eps")}>
            <option value="">Todas</option>
            {res.filtros.cod_eps.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Año (fondos)
          <select value={filtro.anio} onChange={sel("anio")}>
            <option value="">Todos</option>
            {res.filtros.anios.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Fondo o reserva
          <select value={filtro.fondo} onChange={sel("fondo")}>
            <option value="">Todos</option>
            {Object.entries(res.filtros.fondos).map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          </select>
        </label>
      </form>

      <h2>Totales por fondo o reserva</h2>
      <div className="tabla-wrap">
        <table aria-label="Totales por fondo o reserva">
          <thead>
            <tr>
              <th>Fondo o reserva</th>
              <th>Solicitado</th>
              <th>Autorizado <Visible nivel={v.uso_excepcional_autorizado} /></th>
              <th>Usado ordinario <Visible nivel={v.uso_ordinario} /></th>
              <th>Uso excepcional (art. 89)</th>
              <th>Uso por emergencia (art. 90) <Visible nivel={v.uso_emergencia_art_90} /></th>
              <th>Verificado</th>
              <th>Depósito programado</th>
              <th>Depósito efectuado <Visible nivel={v.deposito_efectuado} /></th>
              <th>Saldo final <Visible nivel={v.saldo_final} /></th>
            </tr>
          </thead>
          <tbody>
            {[...res.filas, res.total].map((f) => (
              <tr key={f.fondo} className={f.fondo === "total" ? "fila-total" : ""}>
                <th scope="row">
                  {f.nombre}
                  {f.expedientes && f.expedientes.length > 0 && (
                    <div className="detalle">
                      {f.expedientes.map((id) => <Link key={id} to={`/expedientes/${id}`} style={{ marginRight: 6 }}>{id}</Link>)}
                    </div>
                  )}
                </th>
                <td>{soles(f.solicitado)}</td>
                <td>{soles(f.autorizado)}</td>
                <td>{soles(f.uso_ordinario)}</td>
                <td>{soles(f.uso_excepcional_art_89)}</td>
                <td>{soles(f.uso_emergencia_art_90)}</td>
                <td>{f.verificado != null ? soles(f.verificado)
                  : f.verificaciones_pendientes ? `◷ Pendiente (${f.verificaciones_pendientes})` : "— sin usos que verificar"}</td>
                <td>{soles(f.deposito_programado)}</td>
                <td>{soles(f.deposito_efectuado)}</td>
                <td>{f.saldo_final == null ? "—" : `${soles(f.saldo_final)}${f.saldo_al ? ` (${f.saldo_al})` : ""}`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="sub">{res.notas.map((n) => <li key={n}>{n}</li>)}</ul>
      <p className="meta">Fuente: {res.fuente}</p>

      <h2>Usos por emergencia (art. 90, RCD 028-2026)</h2>
      {res.usos_emergencia.length === 0 ? (
        <p>
          La muestra no tiene usos por emergencia. La herramienta ya los contempla: un uso excepcional sin expediente se
          muestra como «uso que requiere informe mensual en 10 DH», no como error.
        </p>
      ) : (
        res.usos_emergencia.map((u) => (
          <article key={`${u.cod_eps}${u.anio_mes}${u.tipo_fondo}`} className="alerta alerta-por_vencer">
            <strong>{u.cod_eps} · {u.anio_mes} · {fondos?.[u.tipo_fondo] ?? u.tipo_fondo}</strong> · {soles(u.monto)}
            <p>{u.texto} {u.informe.mensaje}</p>
            <div className="meta">Fuente: {u.fuente}</div>
          </article>
        ))
      )}

      <h2>Usos excepcionales (art. 89): de dónde sale cada sol</h2>
      {res.casos_reales.map((r) => <RutaDeUso key={r.id_expediente} r={r} fondos={fondos} />)}
      {res.expedientes_uso.map((r) => <RutaDeUso key={r.id_expediente} r={r} fondos={fondos} />)}

      <h2>Programado frente a ejecutado por proyecto</h2>
      <p className="sub">
        Avance financiero = ejecución acumulada ÷ <strong>programado vigente</strong>; si hubo modificación se muestra también
        sobre el original. Señal para revisión: diferencia con el avance físico mayor a {proys?.umbral_senal_pp ?? 25} puntos
        <Rotulo naturaleza="supuesto" />.
      </p>
      <form className="formulario" aria-label="Filtros de proyectos" onSubmit={(e) => e.preventDefault()}>
        <label>Fuente de financiamiento
          <select value={fp.fuente} onChange={(e) => setFp({ ...fp, fuente: e.target.value })}>
            <option value="">Todas</option>
            {["fondo_inversiones", "transferencia_gobierno_nacional", "endeudamiento", "cooperacion"].map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Etapa
          <select value={fp.etapa} onChange={(e) => setFp({ ...fp, etapa: e.target.value })}>
            <option value="">Todas</option>
            {["financiado", "en_ejecucion", "paralizado", "concluido"].map((x) => <option key={x} value={x}>{PELDANOS[x]}</option>)}
          </select>
        </label>
        <label>Periodo
          <select value={fp.periodo} onChange={(e) => setFp({ ...fp, periodo: e.target.value })}>
            <option value="vigente">Vigente</option><option value="anterior">Anterior</option><option value="">Ambos</option>
          </select>
        </label>
        <label style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
          <input type="checkbox" checked={fp.solo_senales} onChange={(e) => setFp({ ...fp, solo_senales: e.target.checked })} />
          Solo señales para revisión
        </label>
      </form>
      {proys && (
        <>
          <p>{proys.proyectos.length} proyectos.</p>
          <div className="tabla-wrap">
            <table aria-label="Programado frente a ejecutado por proyecto">
              <thead>
                <tr>
                  <th>Proyecto</th><th>EPS</th><th>Fuente</th>
                  <th>Programado vigente <Visible nivel={vp.monto_programado_vigente} /></th>
                  <th>Ejecutado <Visible nivel={vp.ejecucion_financiera} /></th>
                  <th>Programado frente a ejecutado</th>
                  <th>Avance financiero (base)</th>
                  <th>Avance físico <Visible nivel={vp.avance_fisico} /></th>
                  <th>Etapa <Visible nivel={vp.etapa_escalera} /></th>
                  <th>Señal</th>
                </tr>
              </thead>
              <tbody>
                {visibles.map((p) => (
                  <tr key={p.cod_proyecto}>
                    <td><Link to={`/proyectos/${p.cod_proyecto}`}>{p.cod_proyecto}</Link><div className="detalle">{p.nombre_proyecto}</div></td>
                    <td>{p.cod_eps}</td>
                    <td>{p.fuente_financiamiento}</td>
                    <td>
                      {soles(p.monto_programado_vigente)}
                      {p.modificado && <div className="detalle">original: {soles(p.monto_programado_original)}</div>}
                    </td>
                    <td>{p.aviso_ejecucion ? <span className="detalle">{p.aviso_ejecucion}</span> : soles(p.ejecucion_financiera)}</td>
                    <td><Barra programado={p.monto_programado_vigente} ejecutado={p.ejecucion_financiera} /></td>
                    <td>
                      {pct(p.avance_financiero)} <span className="detalle">sobre programado vigente</span>
                      {p.avance_financiero_original != null && <div className="detalle">{pct(p.avance_financiero_original)} sobre el original</div>}
                    </td>
                    <td>{pct(p.avance_fisico)}</td>
                    <td>{PELDANOS[p.etapa_escalera] ?? p.etapa_escalera}</td>
                    <td>{p.senal_revision && p.diferencia_pp != null ? `⚠ ${uno(p.diferencia_pp)} pp` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {proys.proyectos.length > limite && (
            <button className="secundario" onClick={() => setLimite(limite + 100)}>Ver más proyectos</button>
          )}
        </>
      )}
    </>
  );
}

// --------------------------------------------------------------- proyecto
export function DetalleProyecto() {
  const { cod = "" } = useParams();
  const [p, setP] = useState<(Proyecto & { visibilidad: Mapa }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    obtener<Proyecto & { visibilidad: Mapa }>(`/ruta-dinero/proyectos/${encodeURIComponent(cod)}`).then(setP).catch((e) => setError(e.message));
  }, [cod]);
  if (error) return <p className="mensaje mensaje-error">No se pudo abrir el proyecto {cod}: {error}</p>;
  if (!p) return <p>Cargando proyecto {cod}…</p>;
  return (
    <>
      <p><Link to="/ruta-del-dinero">← Ruta del dinero</Link></p>
      <h1>{p.cod_proyecto} · {p.nombre_proyecto}</h1>
      <p className="sub">
        {p.cod_eps} · {p.localidad} · fuente: {p.fuente_financiamiento} · meta asociada: {p.meta_asociada ?? "ninguna"} ·
        población beneficiaria {p.poblacion_beneficiaria ?? "—"} <Rotulo naturaleza="estimado" /> <Rotulo naturaleza="sintético" />
      </p>
      <dl className="ficha-datos">
        <div><dt>Programado vigente</dt><dd>{soles(p.monto_programado_vigente)}</dd></div>
        {p.modificado && <div><dt>Programado original</dt><dd>{soles(p.monto_programado_original)}</dd></div>}
        <div><dt>Ejecutado acumulado ({p.ultimo_trimestre ?? "sin reporte"})</dt><dd>{p.aviso_ejecucion ?? soles(p.ejecucion_financiera)}</dd></div>
        <div><dt>Avance financiero</dt><dd>{pct(p.avance_financiero)} sobre programado vigente{p.avance_financiero_original != null && ` · ${pct(p.avance_financiero_original)} sobre el original`}</dd></div>
        <div><dt>Avance físico</dt><dd>{pct(p.avance_fisico)}</dd></div>
        <div><dt>Base del cálculo</dt><dd>{p.base_avance_financiero}</dd></div>
      </dl>
      {p.senal_revision && <p className="mensaje mensaje-error">⚠ Señal para revisión: el avance financiero y el físico difieren {p.diferencia_pp != null ? uno(p.diferencia_pp) : "—"} puntos. No es un problema confirmado.</p>}
      {p.expediente_modificacion.length > 0 && (
        <p>Modificado por: {p.expediente_modificacion.map((id) => <Link key={id} to={`/expedientes/${id}`} style={{ marginRight: 6 }}>{id}</Link>)}</p>
      )}
      <h2>Escalera</h2>
      <Escalera pasos={p.escalera} titulo={`Escalera del proyecto ${p.cod_proyecto}`} />
      <h2>Programado por año</h2>
      <div className="tabla-wrap"><table>
        <thead><tr><th>Año</th><th>Original</th><th>Vigente</th><th>Cambio</th><th>DS03 fila</th></tr></thead>
        <tbody>{p.anios?.map((a) => (
          <tr key={a.fila}><td>{a.anio}</td><td>{soles(a.original)}</td><td>{soles(a.vigente)}</td>
            <td>{a.id_expediente_modificacion ? <Link to={`/expedientes/${a.id_expediente_modificacion}`}>{a.id_expediente_modificacion}</Link> : "—"}</td><td>{a.fila}</td></tr>
        ))}</tbody>
      </table></div>
      <h2>Ejecución por trimestre</h2>
      <div className="tabla-wrap"><table>
        <thead><tr><th>Trimestre</th><th>Estado</th><th>Ejecutado en el trimestre</th><th>Acumulado</th><th>Avance físico</th><th>DS04 fila</th></tr></thead>
        <tbody>{p.trimestres?.map((q) => (
          <tr key={q.fila}><td>{q.anio_trimestre}</td><td>{q.estado}</td><td>{soles(q.ejecucion_trimestre)}</td><td>{soles(q.ejecucion_acumulada)}</td><td>{pct(q.avance_fisico)}</td><td>{q.fila}</td></tr>
        ))}</tbody>
      </table></div>
      {p.conciliacion_mef && (
        <>
          <h2>Registro del MEF (simulado)</h2>
          <p>{Object.entries(p.conciliacion_mef).map(([k, val]) => `${k}: ${val ?? "—"}`).join(" · ")}</p>
        </>
      )}
      <p className="meta">Fuente: {p.fuente}</p>
    </>
  );
}
