import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { pedir } from "./api";
import { fecha } from "./componentes";
import { entero, soles } from "./dinero";
import { t } from "./etiquetas";
import { useSesion } from "./sesion";

interface Localidad { localidad: string; ubigeo: string; departamento: string; provincia: string; distrito: string;
  cod_eps: string; nombre_eps: string; poblacion_servida?: number }

interface DetalleLocalidad {
  localidad: Localidad; fecha_corte: string;
  agregados: { proyectos: number; por_etapa: Record<string, number>; monto_programado_original: number };
  proyectos: { cod_proyecto: string; nombre_proyecto: string; componente: string; etapa_escalera: string;
    poblacion_beneficiaria: number | null; monto_programado_original: number; meta_asociada: string | null;
    decisiones: { id_expediente: string; documento_final: string | null; resultado: string | null; fecha_conclusion: string | null }[] }[];
  audiencias: { id_expediente: string; hito: string; fecha_inicio: string | null; fecha_fin: string | null; estado: string;
    plazo_referencial_dh: number | null }[];
  resumen_quechua: { texto: string; estado: string } | null;
  avisos: string[];
  fuente: string;
}

const ICONO_ETAPA: Record<string, string> = {
  programado: "○", aprobado: "◔", financiado: "◑", en_ejecucion: "◕", concluido: "●", paralizado: "⏸",
};

// Vista ciudadana: diseñada primero para el celular; solo lee campos públicos.
export function VistaCiudadana() {
  const { corte } = useSesion();
  const [params, setParams] = useSearchParams();
  const ubigeo = params.get("ubigeo");
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState<Localidad[] | null>(null);
  const [d, setD] = useState<DetalleLocalidad | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ubigeo) {
      setD(null);
      return;
    }
    pedir<DetalleLocalidad>(`/publico/localidades/${encodeURIComponent(ubigeo)}?fecha_corte=${corte}`)
      .then((r) => { setD(r); setError(null); }).catch((e) => setError(e.message));
  }, [ubigeo, corte]);

  const buscar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (q.trim().length < 2) {
      setError("Escriba al menos dos letras o números.");
      return;
    }
    try {
      setResultados(await pedir<Localidad[]>(`/publico/localidades?q=${encodeURIComponent(q.trim())}`));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="movil">
      <h1>Agua y saneamiento en su localidad</h1>
      <p className="sub">Proyectos, su etapa y las audiencias públicas. Solo información pública.</p>
      <form className="buscador" role="search" onSubmit={buscar} aria-label="Buscar localidad">
        <label htmlFor="buscar-localidad">Localidad, distrito o código de ubigeo</label>
        <div className="buscador-fila">
          <input id="buscar-localidad" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Por ejemplo: Belén" />
          <button type="submit">Buscar</button>
        </div>
      </form>
      {error && <p className="mensaje mensaje-error" role="alert">{error}</p>}
      {resultados && !d && (
        <section aria-live="polite" aria-labelledby="res-titulo">
          <h2 id="res-titulo">{resultados.length === 0 ? "No encontramos esa localidad en la muestra" : "Elija su localidad"}</h2>
          <ul className="lista-simple">
            {resultados.map((r) => (
              <li key={r.ubigeo + r.cod_eps}>
                <button type="button" className="enlace-boton" onClick={() => setParams({ ubigeo: r.ubigeo })}>
                  {r.localidad}
                </button>
                <div className="detalle">{r.distrito}, {r.provincia}, {r.departamento} · {r.nombre_eps}</div>
              </li>
            ))}
          </ul>
        </section>
      )}
      {d && <Localidad d={d} volver={() => setParams({})} />}
    </div>
  );
}

function Localidad({ d, volver }: { d: DetalleLocalidad; volver: () => void }) {
  const l = d.localidad;
  return (
    <article aria-labelledby="loc-titulo">
      <p><button type="button" className="enlace-boton" onClick={volver}>← Buscar otra localidad</button></p>
      <h2 id="loc-titulo">{l.localidad}</h2>
      <p className="sub">
        {l.distrito}, {l.provincia}, {l.departamento} · atiende {l.nombre_eps}
        {l.poblacion_servida != null && <> · población servida {entero(l.poblacion_servida)} <span className="rotulo rotulo-estimado">Estimado</span></>}
      </p>

      <section aria-labelledby="pq-titulo">
        <h3 id="pq-titulo">Resumen en quechua</h3>
        {d.resumen_quechua ? <p lang="qu">{d.resumen_quechua.texto}</p>
          : <p className="sub">Pendiente: una persona debe escribirlo y otra validarlo. No se traduce automáticamente.</p>}
      </section>

      <section aria-labelledby="pr-titulo">
        <h3 id="pr-titulo">Proyectos ({d.agregados.proyectos})</h3>
        <p className="sub">
          Monto programado en el estudio tarifario: {soles(d.agregados.monto_programado_original)} ·{" "}
          {Object.entries(d.agregados.por_etapa).map(([k, v]) => `${v} ${t("peldano", k).toLowerCase()}`).join(", ")}
        </p>
        <ul className="tarjetas">
          {d.proyectos.map((p) => (
            <li key={p.cod_proyecto} className="tarjeta">
              <h4>{p.nombre_proyecto}</h4>
              <p className="etapa"><span aria-hidden="true">{ICONO_ETAPA[p.etapa_escalera] ?? "•"}</span> Etapa: <strong>{t("peldano", p.etapa_escalera)}</strong> <span className="rotulo rotulo-supuesto">Por validar</span></p>
              <p>{t("componente", p.componente)} · {soles(p.monto_programado_original)} programado</p>
              {p.poblacion_beneficiaria != null && (
                <p>{entero(p.poblacion_beneficiaria)} personas beneficiarias <span className="rotulo rotulo-estimado">Estimado</span></p>
              )}
              {p.decisiones.map((x) => (
                <p key={x.id_expediente} className="detalle">
                  Decisión de Sunass: {x.documento_final ?? "sin número"} ({t("resultado", x.resultado)}
                  {x.fecha_conclusion ? `, ${fecha(x.fecha_conclusion)}` : ""})
                </p>
              ))}
            </li>
          ))}
        </ul>
        {d.proyectos.length === 0 && <p>La muestra no registra proyectos para esta localidad.</p>}
      </section>

      <section aria-labelledby="au-titulo">
        <h3 id="au-titulo">Audiencias públicas y plazos para comentar</h3>
        {d.audiencias.length === 0 ? <p>No hay audiencias registradas para la empresa de esta localidad.</p> : (
          <ul className="lista-simple">
            {d.audiencias.map((a) => (
              <li key={a.id_expediente + a.hito}>
                <strong>{t("hito", a.hito)}</strong> · {a.estado}
                <div className="detalle">
                  Desde el {fecha(a.fecha_inicio)}{a.fecha_fin ? ` hasta el ${fecha(a.fecha_fin)}` : ""}
                  {a.plazo_referencial_dh ? ` · plazo de referencia ${a.plazo_referencial_dh} días hábiles` : ""} · revisión de tarifas {a.id_expediente}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <ul className="avisos">{d.avisos.map((a) => <li key={a}>{a}</li>)}</ul>
    </article>
  );
}
