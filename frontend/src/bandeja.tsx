import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { pedir } from "./api";
import { EstadoAlerta, Rotulo, fecha } from "./componentes";
import { humanizar, t } from "./etiquetas";
import { useSesion } from "./sesion";

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

const MAX_EVIDENCIA = 3;

export function TarjetaBandeja({ x, conEspecialista }: { x: ItemBandeja; conEspecialista: boolean }) {
  const a = x.alerta;
  const resto = x.evidencia_faltante.length - MAX_EVIDENCIA;
  return (
    <article className={`tarjeta-accion estado-${x.estado}`} aria-labelledby={`t-${x.id_expediente}`}>
      <header className="tarjeta-cabecera">
        <EstadoAlerta estado={x.estado} />
        <span className="plazo">{plazoEnPalabras(a?.dias_restantes)}</span>
        <h3 id={`t-${x.id_expediente}`}>
          <Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link>
        </h3>
        <span className="tarjeta-sub">
          {t("tipo_procedimiento", x.tipo_procedimiento)} · {x.cod_eps ?? x.empresa}
          {conEspecialista && <> · {x.especialista} (ficticio)</>}
        </span>
        <Rotulo naturaleza={x.naturaleza} />
      </header>
      <div className="tres-respuestas">
        <section>
          <h4>¿Qué requiere acción?</h4>
          <p className="paso">{x.siguiente_paso}</p>
          {a && (
            <p className="detalle">
              {t("reloj", a.reloj)}: {humanizar(a.mensaje)}
            </p>
          )}
        </section>
        <section>
          <h4>¿Qué evidencia falta?</h4>
          {x.evidencia_faltante.length === 0 ? (
            <p>No falta evidencia registrada.</p>
          ) : (
            <>
              <p className="conteo">{x.evidencia_faltante.length} {x.evidencia_faltante.length === 1 ? "pendiente" : "pendientes"}</p>
              <ul>{x.evidencia_faltante.slice(0, MAX_EVIDENCIA).map((e, i) => <li key={i}>{humanizar(e.texto)}</li>)}</ul>
              {resto > 0 && (
                <details>
                  <summary>Ver {resto} más</summary>
                  <ul>{x.evidencia_faltante.slice(MAX_EVIDENCIA).map((e, i) => <li key={i}>{humanizar(e.texto)}</li>)}</ul>
                </details>
              )}
            </>
          )}
        </section>
        <section>
          <h4>¿Por qué importa?</h4>
          <ul>{x.por_que_importa.map((r) => <li key={r}>{humanizar(r)}</li>)}</ul>
        </section>
      </div>
      <footer className="meta">
        {x.hito_al_corte && <>Está en: {t("hito", x.hito_al_corte)} ({t("responsable", x.responsable_al_corte)}) · </>}
        {a?.fecha_limite && <>Fecha límite: {fecha(a.fecha_limite)} · </>}
        Fuente: {humanizar(x.fuente)}
      </footer>
    </article>
  );
}

export function Bandeja() {
  const { usuario, corte, config } = useSesion();
  const [esp, setEsp] = useState("");
  const [r, setR] = useState<RespuestaBandeja | null>(null);
  const [error, setError] = useState<string | null>(null);
  const coordinacion = usuario.rol !== "especialista_srt";

  useEffect(() => {
    const q = new URLSearchParams({ fecha_corte: corte });
    if (esp) q.set("especialista", esp);
    pedir<RespuestaBandeja>(`/bandeja?${q}`).then(setR).catch((e) => setError(e.message));
  }, [corte, esp]);

  if (error) return <p className="mensaje mensaje-error" role="alert">No se pudo cargar la bandeja: {error}</p>;
  if (!r) return <p className="cargando">Cargando su bandeja…</p>;
  const urgentes = (r.resumen.vencido ?? 0) + (r.resumen.no_calculable ?? 0) + (r.resumen.por_vencer ?? 0);
  return (
    <>
      <h1>Mi siguiente acción</h1>
      <p className="sub">
        {coordinacion ? "Bandeja del equipo" : `Bandeja de ${usuario.nombre}`} al {fecha(r.fecha_corte)}.{" "}
        {r.orden} <span className="rotulo rotulo-supuesto">{r.rotulo_asignacion}</span>
      </p>
      {corte !== config.fecha_corte_muestra && (
        <p className="aviso">Está viendo la bandeja a una fecha anterior a la de la muestra: lo posterior aún no se conoce.</p>
      )}
      <div className="resumen-bandeja" role="status">
        <strong>{urgentes === 0 ? "Nada urgente." : `${urgentes} ${urgentes === 1 ? "expediente requiere" : "expedientes requieren"} atención.`}</strong>
        {(["vencido", "no_calculable", "por_vencer", "en_plazo"] as const).map((e) => (
          <span key={e} className={`chip chip-${e}`}><EstadoAlerta estado={e} /> {r.resumen[e] ?? 0}</span>
        ))}
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
      {r.items.length === 0 ? (
        <p>No tiene expedientes en trámite a esta fecha.</p>
      ) : (
        <ol className="lista-bandeja" aria-label="Expedientes ordenados por plazo restante">
          {r.items.map((x) => <li key={x.id_expediente}><TarjetaBandeja x={x} conEspecialista={coordinacion} /></li>)}
        </ol>
      )}
    </>
  );
}
