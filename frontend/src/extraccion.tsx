import { useEffect, useState } from "react";
import { pedir } from "./api";
import { t } from "./etiquetas";
import { Icono } from "./iconos";
import { ChipFuente, Pildora } from "./ui";

// Fase 6: leer un documento real con IA. Todo lo que devuelve es una PROPUESTA con su cita y su página;
// recién entra al expediente cuando una persona lo confirma (o lo corrige con motivo y lo confirma).

interface Estado { proveedor: string; modelo: string | null; disponible: boolean; detalle: string; parte_privada: boolean;
  lista_privada: boolean }
interface DocAlias { alias: string; id_expediente: string; huella: string; procesado: boolean; publicado?: boolean }
interface Campo { valor: string; cita: string; pagina: number }
interface Resultado {
  alias: string; proveedor: string; modelo: string; segundos: number;
  campos: { numero_documento: Campo | null; fecha: Campo | null; remitente: Campo | null;
    plazo: { dias_habiles: number; tipo: string | null; cita: string; pagina: number } | null;
    requerimientos: { texto: string; cita: string; pagina: number }[] };
  descartados: { campo: string; motivo: string }[];
  reemplazos: Record<string, number>;
  aviso: string;
}

const NOMBRES: Record<string, string> = { numero_documento: "Número del documento", fecha: "Fecha", remitente: "Remitente" };

export function LeerConIA({ idExpediente, hitos, usuarioId, onConfirmado, onError }: {
  idExpediente: string; hitos: string[]; usuarioId: string; onConfirmado: (texto: string) => void; onError: (texto: string) => void;
}) {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [docs, setDocs] = useState<DocAlias[]>([]);
  const [alias, setAlias] = useState("");
  const [leyendo, setLeyendo] = useState(false);
  const [r, setR] = useState<Resultado | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [hito, setHito] = useState(hitos.includes("informacion_ep") ? "informacion_ep" : hitos[0] ?? "");
  const [motivo, setMotivo] = useState("");

  useEffect(() => {
    pedir<Estado>("/extraccion/estado", {}, usuarioId).then(setEstado).catch(() => setEstado(null));
    pedir<DocAlias[]>(`/extraccion/documentos?id_expediente=${encodeURIComponent(idExpediente)}`, {}, usuarioId)
      .then((d) => { setDocs(d); setAlias(d[0]?.alias ?? ""); }).catch(() => setDocs([]));
  }, [idExpediente, usuarioId]);

  const cargar = (x: Resultado) => {
    setR(x);
    setValores({ numero_documento: x.campos.numero_documento?.valor ?? "", fecha: x.campos.fecha?.valor ?? "",
      remitente: x.campos.remitente?.valor ?? "", plazo: x.campos.plazo ? String(x.campos.plazo.dias_habiles) : "",
      tipo: x.campos.plazo?.tipo ?? "" });
  };
  const leer = async () => {
    setLeyendo(true);
    try {
      cargar(await pedir<Resultado>(`/extraccion/documentos/${alias}`, { method: "POST" }, usuarioId));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setLeyendo(false);
    }
  };
  const propuesto = (k: string) => k === "plazo" ? (r?.campos.plazo ? String(r.campos.plazo.dias_habiles) : "")
    : k === "tipo" ? r?.campos.plazo?.tipo ?? "" : (r?.campos[k as "fecha"]?.valor ?? "");
  const corregidos = r ? ["numero_documento", "fecha", "remitente", "plazo"].filter((k) => (valores[k] ?? "") !== propuesto(k)) : [];
  const confirmar = async () => {
    try {
      await pedir(`/extraccion/documentos/${alias}/confirmar`, { method: "POST", body: JSON.stringify({
        hito, numero_documento: valores.numero_documento || null, fecha: valores.fecha || null, remitente: valores.remitente || null,
        plazo: valores.plazo ? { dias_habiles: Number(valores.plazo), tipo: valores.tipo || null } : null,
        motivo_correccion: corregidos.length ? motivo : null }) }, usuarioId);
      setR(null);
      onConfirmado(corregidos.length ? "Confirmado con correcciones. Quedó en la bitácora con su motivo." : "Confirmado. Ya entra al expediente y quedó en la bitácora.");
    } catch (e) {
      onError((e as Error).message);
    }
  };

  if (!estado || docs.length === 0) return null;
  return (
    <section className="tarjeta ia-tarjeta leer-ia" aria-labelledby="leer-ia">
      <h3 id="leer-ia" className="con-icono"><Icono nombre="documento" /> Leer un documento con IA</h3>
      <p className="detalle">La IA propone cada dato con su cita y su página; nada entra al expediente hasta que una persona lo confirme.</p>
      {!estado.disponible && <p className="aviso">{estado.detalle}</p>}
      <div className="filtros-linea leer-ia-controles">
        <label>Documento del caso
          <select value={alias} onChange={(e) => { setAlias(e.target.value); setR(null); }}>
            {docs.map((d) => {
              // La API de Anthropic solo recibe documentos publicados; los demás se leen con el modelo local.
              const bloqueado = estado.proveedor === "anthropic" && !d.publicado;
              return <option key={d.alias} value={d.alias} disabled={bloqueado}>{d.alias}{d.procesado ? " · leído" : ""}{bloqueado ? " · solo con el modelo local" : ""}</option>;
            })}
          </select>
        </label>
        <button type="button" onClick={leer} disabled={!estado.disponible || leyendo || !alias}>{leyendo ? "Leyendo…" : "Leer con IA"}</button>
      </div>
      {leyendo && <p className="detalle" role="status">Leyendo con {estado.proveedor === "ollama" ? `el modelo local (${estado.modelo}): puede tardar 1 a 2 minutos` : estado.modelo}. Se anonimiza antes de enviar.</p>}
      <p className="meta">Los documentos se identifican por alias; sus nombres de archivo no se muestran.{estado.lista_privada ? "" : " Falta la lista privada de nombres a ocultar (ver README)."}</p>
      {r && (
        <div role="status" aria-live="polite">
          <p><Pildora tono="vio" icono="IA">Propuesto por IA</Pildora> <span className="detalle">{r.proveedor} · {r.modelo} · {r.segundos} s</span></p>
          {(["numero_documento", "fecha", "remitente"] as const).map((k) => (
            <div key={k} className="ia-campo">
              <label className="campo">{NOMBRES[k]}<input value={valores[k] ?? ""} onChange={(e) => setValores({ ...valores, [k]: e.target.value })} /></label>
              {r.campos[k] ? <blockquote className="cita-bloque">«{r.campos[k]!.cita}» <ChipFuente texto={`${r.alias}, pág. ${r.campos[k]!.pagina}`} soloIcono /></blockquote>
                : <p className="meta">Vacío: el modelo no dio una cita válida.</p>}
            </div>
          ))}
          <div className="ia-campo">
            <label className="campo">Plazo en días hábiles<input type="number" min={0} value={valores.plazo ?? ""} onChange={(e) => setValores({ ...valores, plazo: e.target.value })} /></label>
            <label className="campo">Tipo de plazo
              <select value={valores.tipo ?? ""} onChange={(e) => setValores({ ...valores, tipo: e.target.value })}>
                <option value="">Sin plazo</option><option value="otorgado">Otorgado</option><option value="prorroga">Prórroga</option><option value="solicitado">Solicitado</option>
              </select>
            </label>
            {r.campos.plazo ? <blockquote className="cita-bloque">«{r.campos.plazo.cita}» <ChipFuente texto={`${r.alias}, pág. ${r.campos.plazo.pagina}`} soloIcono /></blockquote>
              : <p className="meta">Vacío: el modelo no dio una cita válida.</p>}
          </div>
          {r.campos.requerimientos.length > 0 && (
            <details><summary>Requerimientos ({r.campos.requerimientos.length})</summary>
              <ul>{r.campos.requerimientos.map((x, i) => <li key={i}>{x.texto} <span className="meta">(pág. {x.pagina})</span></li>)}</ul></details>
          )}
          {r.descartados.length > 0 && (
            <p className="meta">Descartados por la validación: {r.descartados.map((d) => `${NOMBRES[d.campo] ?? d.campo} (${d.motivo})`).join("; ")}.</p>
          )}
          <label className="campo">Hito del expediente
            <select value={hito} onChange={(e) => setHito(e.target.value)}>
              {hitos.map((h) => <option key={h} value={h}>{t("hito", h)}</option>)}
            </select>
          </label>
          {corregidos.length > 0 && (
            <label className="campo">Motivo de la corrección (queda en la bitácora)
              <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </label>
          )}
          <p className="detalle">{r.aviso}</p>
          <div className="acciones">
            <button type="button" onClick={confirmar} disabled={corregidos.length > 0 && motivo.trim().length < 5}>
              {corregidos.length ? "Corregir y confirmar" : "Confirmar"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
