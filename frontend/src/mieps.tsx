import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { pedir } from "./api";
import { plazoEnPalabras } from "./bandeja";
import { EstadoAlerta, fecha } from "./componentes";
import { soles } from "./dinero";
import { humanizar, t } from "./etiquetas";
import { useSesion } from "./sesion";

interface Pendiente {
  id_expediente: string; tipo_procedimiento: string; hito: string; accion: string; fecha_limite: string | null;
  dias_restantes: number | null; estado: string; detalle: string; documento: string | null; fuente: string;
}

interface MiEpsDatos {
  cod_eps: string; fecha_corte: string;
  siguiente_accion: Pendiente | null; pendientes: Pendiente[];
  tramites: { id_expediente: string; tipo_procedimiento: string; fecha_inicio: string; hito_al_corte: string | null;
    le_toca_a_la_eps: boolean; en_que_va: string }[];
  concluidos: { id_expediente: string; tipo_procedimiento: string; fecha_conclusion: string }[];
  fondo: { fondo: string; deposito_programado: number; deposito_efectuado: number; saldo_final: number | null;
    saldo_al: string | null; uso_ordinario: number; uso_excepcional_art_89: number; uso_emergencia_art_90: number }[];
  usos_autorizados: { id_expediente: string; estado: string; monto_autorizado: number | null; fondo: string[] | string | null }[];
  aviso_correo: { asunto: string; cuerpo: string; aviso: string };
  fuente: string;
}

// Vista EPS: diseñada primero para el celular. Una acción por pantalla; lo demás, plegado.
export function MiEps() {
  const { usuario, corte, config } = useSesion();
  const [d, setD] = useState<MiEpsDatos | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    pedir<MiEpsDatos>(`/mi-eps?fecha_corte=${corte}`).then(setD).catch((e) => setError(e.message));
  }, [corte]);
  if (error) return <p className="mensaje mensaje-error" role="alert">No se pudo cargar su información: {error}</p>;
  if (!d) return <p className="cargando">Cargando su información…</p>;
  const nombre = config.eps.find((e) => e.cod_eps === usuario.cod_eps)?.nombre_eps;
  const s = d.siguiente_accion;
  return (
    <div className="movil">
      <h1>{nombre ?? d.cod_eps}</h1>
      <p className="sub">{d.cod_eps} · al {fecha(d.fecha_corte)} · <span className="rotulo rotulo-sintetico">Dato sintético</span></p>

      <section className={`accion-unica estado-${s?.estado ?? "ninguna"}`} aria-labelledby="su-accion">
        <h2 id="su-accion">Su siguiente acción</h2>
        {s ? (
          <>
            <p className="accion-texto">{s.accion}</p>
            <p>
              <EstadoAlerta estado={s.estado === "sin_plazo" ? "no_calculable" : s.estado} />{" "}
              {s.fecha_limite ? <>Hasta el <strong>{fecha(s.fecha_limite)}</strong> ({plazoEnPalabras(s.dias_restantes)})</>
                : "Sin plazo registrado"}
            </p>
            <p className="detalle">Expediente {s.id_expediente} · {t("tipo_procedimiento", s.tipo_procedimiento)}</p>
            <Link className="boton" to={`/expedientes/${s.id_expediente}`}>Abrir el expediente y registrar la respuesta</Link>
          </>
        ) : (
          <p className="accion-texto">No tiene respuestas pendientes ante la Sunass.</p>
        )}
      </section>

      {d.pendientes.length > 1 && (
        <details>
          <summary>Otros pendientes ({d.pendientes.length - 1})</summary>
          <ul className="lista-simple">
            {d.pendientes.slice(1).map((p) => (
              <li key={p.id_expediente + p.hito}>
                <strong>{p.accion}</strong> {p.fecha_limite ? `Hasta el ${fecha(p.fecha_limite)}.` : "Sin plazo registrado."}{" "}
                <Link to={`/expedientes/${p.id_expediente}`}>{p.id_expediente}</Link>
              </li>
            ))}
          </ul>
        </details>
      )}

      <details>
        <summary>Sus trámites en curso ({d.tramites.length})</summary>
        <ul className="lista-simple">
          {d.tramites.map((x) => (
            <li key={x.id_expediente}>
              <Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link> · {t("tipo_procedimiento", x.tipo_procedimiento)}
              <div className="detalle">{x.hito_al_corte ? `${t("hito", x.hito_al_corte)}. ` : ""}{x.en_que_va}</div>
            </li>
          ))}
        </ul>
      </details>

      <details>
        <summary>Resueltos recientemente ({d.concluidos.length})</summary>
        <ul className="lista-simple">
          {d.concluidos.map((x) => (
            <li key={x.id_expediente}>
              <Link to={`/expedientes/${x.id_expediente}`}>{x.id_expediente}</Link> · {t("tipo_procedimiento", x.tipo_procedimiento)} · {fecha(x.fecha_conclusion)}
            </li>
          ))}
        </ul>
      </details>

      <details>
        <summary>Su fondo de inversiones y reservas</summary>
        <ul className="lista-simple">
          {d.fondo.map((f) => (
            <li key={f.fondo}>
              <strong>{t("fondo", f.fondo)}</strong>
              <div className="detalle">
                Depositado {soles(f.deposito_efectuado)} de {soles(f.deposito_programado)} programado · saldo {soles(f.saldo_final)}
                {f.saldo_al ? ` (${f.saldo_al})` : ""}
              </div>
            </li>
          ))}
        </ul>
        {d.usos_autorizados.length > 0 && (
          <>
            <h3>Usos excepcionales solicitados</h3>
            <ul className="lista-simple">
              {d.usos_autorizados.map((u) => (
                <li key={u.id_expediente}>
                  <Link to={`/expedientes/${u.id_expediente}`}>{u.id_expediente}</Link>: {t("estado_peldano", u.estado)}
                  {u.monto_autorizado != null && u.monto_autorizado > 0 && <> · {soles(u.monto_autorizado)}</>}
                  {u.fondo && <> · desde {(Array.isArray(u.fondo) ? u.fondo : [u.fondo]).map((f) => t("fondo", f)).join(", ")}</>}
                </li>
              ))}
            </ul>
          </>
        )}
      </details>

      <details>
        <summary>Vista previa del aviso por correo</summary>
        <div className="correo" aria-label="Vista previa del correo">
          <p><strong>Asunto:</strong> {d.aviso_correo.asunto}</p>
          <p>{d.aviso_correo.cuerpo}</p>
        </div>
        <p className="aviso">{d.aviso_correo.aviso}</p>
      </details>
      <p className="meta">Fuente: {humanizar(d.fuente)}</p>
    </div>
  );
}
