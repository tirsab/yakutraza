import { useState } from "react";
import type { Alerta, Documento, EntradaBitacora, Evento, Hito, Prechequeo } from "./api";
import { humanizar, t } from "./etiquetas";

// ---------------------------------------------------------------- rótulos
const NATURALEZAS: Record<string, { texto: string; clase: string }> = {
  real: { texto: "Dato real", clase: "rotulo-real" },
  "sintético": { texto: "Dato sintético", clase: "rotulo-sintetico" },
  sintetico: { texto: "Dato sintético", clase: "rotulo-sintetico" },
  estimado: { texto: "Estimado", clase: "rotulo-estimado" },
  supuesto: { texto: "Supuesto", clase: "rotulo-supuesto" },
  registrado_demo: { texto: "Registrado en la demo", clase: "rotulo-sintetico" },
};

export function Rotulo({ naturaleza }: { naturaleza: string }) {
  const n = NATURALEZAS[naturaleza] ?? { texto: naturaleza, clase: "rotulo-sintetico" };
  return <span className={`rotulo ${n.clase}`}>{n.texto}</span>;
}

export function fecha(f: string | null | undefined): string {
  if (!f) return "sin fecha";
  const [a, m, d] = f.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

// ---------------------------------------------------------------- estados
// Ícono + texto: el estado nunca depende solo del color.
export const ESTADOS: Record<string, { icono: string; texto: string }> = {
  vencido: { icono: "⛔", texto: "Vencido" },
  por_vencer: { icono: "⚠", texto: "Por vencer" },
  en_plazo: { icono: "◷", texto: "En plazo" },
  no_calculable: { icono: "?", texto: "No puedo calcular" },
  cumplido: { icono: "✓", texto: "Cumplido" },
  incumplido: { icono: "✗", texto: "Fuera de plazo" },
};

const RELOJES: Record<string, string> = {
  normativo: "Plazo de la norma",
  interno: "Meta interna",
  oficio: "Plazo del oficio",
};

export function EstadoAlerta({ estado }: { estado: string }) {
  const e = ESTADOS[estado] ?? { icono: "•", texto: estado };
  return (
    <span className="estado">
      <span aria-hidden="true">{e.icono}</span>
      {e.texto}
    </span>
  );
}

export function AlertaReloj({ a }: { a: Alerta }) {
  return (
    <article className={`alerta alerta-${a.estado}`} aria-label={`${RELOJES[a.reloj]}: ${ESTADOS[a.estado]?.texto ?? a.estado}`}>
      <div>
        <EstadoAlerta estado={a.estado} /> · <strong>{RELOJES[a.reloj]}</strong> · {humanizar(a.titulo)}
      </div>
      <p style={{ margin: "4px 0" }}>{humanizar(a.mensaje)}</p>
      <div className="meta">
        Regla: {a.regla_id ?? "—"} ({a.estado_validacion}) · Fuente: {humanizar(a.fuente) || "—"}
        {a.documento_estado && (
          <>
            {" "}
            · Documento que inició el conteo: {a.documento_inicio ?? "ninguno"} ({a.documento_estado})
          </>
        )}
      </div>
      {a.discrepancia && (
        <div className="discrepancia">
          <strong>Discrepancia</strong> ({humanizar(a.discrepancia.fuente)}: {humanizar(a.discrepancia.valor)}): {humanizar(a.discrepancia.descripcion)}
        </div>
      )}
    </article>
  );
}

// ------------------------------------------------------- pasaporte de evidencia
const EVIDENCIA: Record<string, string> = {
  "documento registrado": "evidencia-registrado",
  "registro propuesto, falta confirmar": "evidencia-propuesto",
  "código en DS02, sin archivo": "evidencia-codigo",
  "declarado, no verificado": "evidencia-declarado",
};

export function Evidencia({ h }: { h: Hito }) {
  const e = h.evidencia;
  return (
    <span className={`evidencia ${EVIDENCIA[e.estado] ?? ""}`}>
      {e.estado}
      {e.referencia ? ` · ${e.referencia}${e.tipo ? ` (${t("tipo_documento", e.tipo)})` : ""}` : ""}
    </span>
  );
}

export function LineaDeTiempo({ hitos }: { hitos: Hito[] }) {
  return (
    <ol className="linea" aria-label="Línea de tiempo del expediente">
      {hitos.map((h) => (
        <li key={h.nro} className={h.estado === "en curso" ? "en-curso" : ""}>
          <div className="titulo-hito">
            {h.nro}. {t("hito", h.hito)} <Evidencia h={h} />
          </div>
          <div className="detalle">
            {h.responsable ? t("responsable", h.responsable) : "responsable no indicado"} · {fecha(h.fecha_inicio)} → {h.fecha_fin ? fecha(h.fecha_fin) : "en curso"}
            {" · "}estado: {t("estado_hito", h.estado).toLowerCase()}
            {h.plazo_referencial_dh != null && ` · plazo referencial: ${h.plazo_referencial_dh} DH`}
            {h.cuenta_plazo === false && " · a cargo de la EP: suspende el plazo de Sunass"}
            {h.fila_ds02 != null && ` · DS02 fila ${h.fila_ds02}`}
          </div>
          {h.descripcion && <div className="detalle">{humanizar(h.descripcion)}</div>}
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------- documentos
const CANALES: Record<string, string> = {
  mesa_partes: "Mesa de partes",
  correo: "Correo electrónico",
  enlace_externo: "Enlace externo (p. ej. Drive)",
  tramite: "Trámite interno",
  no_indicado: "No indicado",
  otro: "Otro",
};

export function TablaDocumentos({ docs, eventos, puedeConfirmar, onConfirmarDoc, onConfirmarEvento }: {
  docs: Documento[];
  eventos: Evento[];
  puedeConfirmar: boolean;
  onConfirmarDoc: (id: number) => void;
  onConfirmarEvento: (id: number) => void;
}) {
  if (!docs.length && !eventos.length) return <p>No hay documentos registrados además de los códigos de DS02.</p>;
  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr>
            <th>Documento</th><th>Hito</th><th>Canal</th><th>Fecha</th><th>Naturaleza</th><th>Estado</th><th>Fuente</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={`d${d.id}`}>
              <td>{t("tipo_documento", d.tipo)} · {d.numero ?? "sin número"}</td>
              <td>{t("hito", d.hito)}</td>
              <td>{CANALES[d.canal] ?? d.canal}</td>
              <td>{fecha(d.fecha_notificacion ?? d.fecha_recepcion ?? d.fecha_emision)}</td>
              <td><Rotulo naturaleza={d.naturaleza} /> {d.origen === "transcrito_ia" && "Transcrito con asistencia de IA"}</td>
              <td>
                {d.estado_registro === "confirmado" ? `✓ Confirmado por ${d.confirmado_por}` : "Propuesto"}
                {d.estado_registro === "propuesto" && puedeConfirmar && (
                  <> <button className="secundario" onClick={() => onConfirmarDoc(d.id)}>Confirmar</button></>
                )}
              </td>
              <td>{humanizar(d.fuente)}{d.cita && <div className="cita">«{d.cita}»</div>}</td>
            </tr>
          ))}
          {eventos.map((e) => (
            <tr key={`e${e.id}`}>
              <td>{e.tipo === "prorroga" ? "Prórroga" : "Plazo fijado por oficio"}: {e.dias_dh != null ? `${e.dias_dh} DH` : "plazo no indicado"}</td>
              <td>{t("hito", e.hito)}</td>
              <td>—</td>
              <td>—</td>
              <td><Rotulo naturaleza={e.naturaleza} /></td>
              <td>
                {e.estado_registro === "confirmado" ? "✓ Confirmado" : "Propuesto"}
                {e.estado_registro === "propuesto" && puedeConfirmar && (
                  <> <button className="secundario" onClick={() => onConfirmarEvento(e.id)}>Confirmar</button></>
                )}
              </td>
              <td>{humanizar(e.fuente)}{e.cita && <div className="cita">«{e.cita}»</div>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FormularioDocumento({ hitos, onEnviar, deshabilitado }: {
  hitos: string[];
  onEnviar: (datos: Record<string, unknown>) => Promise<void>;
  deshabilitado: boolean;
}) {
  const [datos, setDatos] = useState<Record<string, string>>({ tipo: "OF", canal: "correo", hito: hitos[0] ?? "" });
  const cambiar = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setDatos({ ...datos, [k]: e.target.value });
  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    const limpio: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(datos)) if (v !== "") limpio[k] = k === "plazo_otorgado_dh" ? Number(v) : v;
    await onEnviar(limpio);
  };
  return (
    <form className="formulario" onSubmit={enviar} aria-label="Registrar un documento">
      <label>Tipo
        <select value={datos.tipo} onChange={cambiar("tipo")}>
          {["OF", "INF", "MEM", "RD", "RCD", "CARTA", "CORREO", "OTRO"].map((x) => <option key={x} value={x}>{t("tipo_documento", x)}</option>)}
        </select>
      </label>
      <label>Canal por el que llegó
        <select value={datos.canal} onChange={cambiar("canal")}>
          {Object.entries(CANALES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <label>Hito
        <select value={datos.hito} onChange={cambiar("hito")}>
          {hitos.map((h) => <option key={h} value={h}>{t("hito", h)}</option>)}
        </select>
      </label>
      <label>Número o descripción<input value={datos.numero ?? ""} onChange={cambiar("numero")} /></label>
      <label>Fecha de recepción<input type="date" value={datos.fecha_recepcion ?? ""} onChange={cambiar("fecha_recepcion")} /></label>
      <label>Plazo otorgado (DH, opcional)<input type="number" min={0} value={datos.plazo_otorgado_dh ?? ""} onChange={cambiar("plazo_otorgado_dh")} /></label>
      <label>Enlace o ubicación (opcional)<input value={datos.referencia ?? ""} onChange={cambiar("referencia")} /></label>
      <button type="submit" disabled={deshabilitado}>Registrar documento</button>
    </form>
  );
}

// ---------------------------------------------------------------- bitácora
export function Bitacora({ entradas }: { entradas: EntradaBitacora[] }) {
  if (!entradas.length) return <p>Sin cambios registrados para este expediente.</p>;
  return (
    <div className="tabla-wrap">
      <table>
        <thead><tr><th>Cuándo</th><th>Quién</th><th>Qué</th><th>Sobre</th><th>Motivo</th><th>Hash</th></tr></thead>
        <tbody>
          {entradas.map((b) => (
            <tr key={b.id}>
              <td>{b.cuando.replace("T", " ").slice(0, 19)}</td>
              <td>{b.usuario} ({t("rol", b.rol)})</td>
              <td>{humanizar(b.accion)}</td>
              <td>{humanizar(b.entidad)} {b.entidad_id}</td>
              <td>{b.motivo ?? "—"}</td>
              <td><code>{b.hash.slice(0, 10)}…</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------- pre-chequeo
const RUTAS: Record<string, string> = {
  solo_comunicacion_art_94: "Solo comunicación (art. 94)",
  aprobacion_cd_art_93: "Aprobación del Consejo Directivo (art. 93)",
  no_determinable: "No puedo determinar",
};

export function PanelPrechequeo({ p }: { p: Prechequeo }) {
  return (
    <section aria-label="Pre-chequeo art. 93/94">
      <div className="aviso">{p.aviso} Regla {p.estado_validacion}.</div>
      <p><strong>{RUTAS[p.ruta] ?? p.ruta}</strong>: {p.titulo}. Regla aplicada: {p.regla_aplicada}.</p>
      <p>{humanizar(p.explicacion)}</p>
      {p.texto_citado.map((t) => (
        <blockquote key={t.ubicacion} className="cita">«{t.texto}» ({t.ubicacion})</blockquote>
      ))}
      {p.advertencias.map((a) => <p key={a} className="mensaje mensaje-error">⚠ {humanizar(a)}</p>)}
      {p.faltantes.length > 0 && <p>Falta: {humanizar(p.faltantes.join("; "))}.</p>}
      {p.supuestos.length > 0 && (
        <details>
          <summary><span className="rotulo rotulo-supuesto">Supuesto</span> Supuestos usados</summary>
          <ul>{p.supuestos.map((s) => <li key={s}>{humanizar(s)}</li>)}</ul>
        </details>
      )}
    </section>
  );
}
