import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Ficha, type FilaExpediente, type UsuarioDemo } from "./api";
import {
  AlertaReloj, Bitacora, fecha, FormularioDocumento, LineaDeTiempo, PanelPrechequeo, Rotulo, TablaDocumentos,
} from "./componentes";
import { pct, RutaDeUso, soles } from "./dinero";

const TIPOS: Record<string, string> = {
  cambio_programa_inversiones: "Cambio al programa de inversiones",
  uso_excepcional_fondo: "Uso excepcional del fondo",
  revision_periodica: "Revisión periódica",
  reajuste_ipm: "Reajuste por IPM",
  reporte_periodico: "Reporte periódico",
  verificacion_incremento: "Verificación de incrementos",
};

export function ListaExpedientes() {
  const [filas, setFilas] = useState<FilaExpediente[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tipo, setTipo] = useState("cambio_programa_inversiones");
  useEffect(() => {
    api.expedientes().then(setFilas).catch((e) => setError(e.message));
  }, []);
  if (error) return <p className="mensaje mensaje-error">No se pudo cargar la lista: {error}</p>;
  if (!filas) return <p>Cargando expedientes…</p>;
  const visibles = filas.filter((f) => !tipo || f.tipo_procedimiento === tipo);
  return (
    <>
      <h1>Expedientes</h1>
      <p className="sub">La bandeja priorizada por plazo llega en la Fase 5. Aquí se abre cada expediente vivo.</p>
      <label>Tipo de procedimiento{" "}
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos</option>
          {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </label>
      <div className="tabla-wrap" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>Expediente</th><th>EPS</th><th>Tipo</th><th>Estado</th><th>Inicio</th><th>Quién lo tiene</th><th>Dato</th></tr></thead>
          <tbody>
            {visibles.map((f) => (
              <tr key={f.id_expediente}>
                <td><Link to={`/expedientes/${f.id_expediente}`}>{f.id_expediente}</Link></td>
                <td>{f.cod_eps ?? f.empresa}</td>
                <td>{TIPOS[f.tipo_procedimiento] ?? f.tipo_procedimiento}</td>
                <td>{f.estado}</td>
                <td>{fecha(f.fecha_inicio)}</td>
                <td>{f.responsable_actual ? `${f.responsable_actual} (${f.hito_actual})` : "—"}</td>
                <td><Rotulo naturaleza={f.naturaleza} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

const ORDEN = ["vencido", "no_calculable", "por_vencer", "en_plazo", "incumplido", "cumplido"];

export function ExpedienteVivo({ usuario }: { usuario: UsuarioDemo | null }) {
  const { id = "" } = useParams();
  const [f, setF] = useState<Ficha | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null);

  const cargar = useCallback(() => {
    api.ficha(id).then(setF).catch((e) => setError(e.message));
  }, [id]);
  useEffect(cargar, [cargar]);

  const accion = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      setAviso({ ok: true, texto: ok });
      cargar();
    } catch (e) {
      setAviso({ ok: false, texto: (e as Error).message });
    }
  };

  if (error) return <p className="mensaje mensaje-error">No se pudo abrir el expediente {id}: {error}</p>;
  if (!f) return <p>Cargando expediente {id}…</p>;
  const e = f.expediente;
  const relojes = [...f.relojes].sort((a, b) => ORDEN.indexOf(a.estado) - ORDEN.indexOf(b.estado));
  const enCurso = relojes.filter((a) => ["vencido", "por_vencer", "en_plazo", "no_calculable"].includes(a.estado));
  const historial = relojes.filter((a) => !enCurso.includes(a));
  const puedeConfirmar = !!usuario?.permisos.includes("confirmar_registro");
  const puedeRegistrar = !!usuario?.permisos.includes("registrar_documento");

  return (
    <>
      <p><Link to="/">← Expedientes</Link></p>
      <h1>Expediente {e.id_expediente}</h1>
      <p className="sub">
        {TIPOS[e.tipo_procedimiento] ?? e.tipo_procedimiento} · {String(e.cod_eps ?? e.empresa ?? "")} · estado: {String(e.estado)}
        {" "}<Rotulo naturaleza={e.naturaleza} />
      </p>
      {"aviso" in e && e.aviso ? <div className="aviso">{String(e.aviso)}</div> : null}
      <dl className="ficha-datos">
        <div><dt>Inicio</dt><dd>{fecha(e.fecha_inicio as string)}</dd></div>
        <div><dt>Conclusión</dt><dd>{e.fecha_conclusion ? fecha(e.fecha_conclusion as string) : "en trámite"}</dd></div>
        <div><dt>Plazo máximo</dt><dd>{e.plazo_maximo_dh != null ? `${e.plazo_maximo_dh} DH` : "sin plazo en DH"}</dd></div>
        <div><dt>Base normativa</dt><dd>{typeof e.base_normativa === "string" ? e.base_normativa : (e.base_normativa as { articulo?: string })?.articulo ?? "—"}</dd></div>
        <div><dt>Fuente</dt><dd>{String(e.fuente ?? "")}</dd></div>
        <div><dt>Fecha de corte («hoy»)</dt><dd>{fecha(f.fecha_corte)}</dd></div>
      </dl>

      <h2>¿Qué requiere acción? Tres relojes</h2>
      {enCurso.length === 0 && <p>No hay plazos abiertos en este expediente.</p>}
      <div className="relojes">{enCurso.map((a, i) => <AlertaReloj key={`c${i}`} a={a} />)}</div>
      {historial.length > 0 && (
        <details>
          <summary>Plazos ya cerrados ({historial.length})</summary>
          <div className="relojes">{historial.map((a, i) => <AlertaReloj key={`h${i}`} a={a} />)}</div>
        </details>
      )}

      <h2>Línea de tiempo y pasaporte de evidencia</h2>
      <p className="sub">Un hito sin documento figura como «declarado, no verificado».</p>
      <LineaDeTiempo hitos={f.linea_de_tiempo} />

      <h2>Documentos registrados</h2>
      {aviso && <p className={`mensaje ${aviso.ok ? "mensaje-ok" : "mensaje-error"}`} role="status">{aviso.texto}</p>}
      <TablaDocumentos
        docs={f.documentos} eventos={f.eventos} puedeConfirmar={puedeConfirmar}
        onConfirmarDoc={(d) => accion(() => api.confirmarDocumento(d, usuario?.id), "Documento confirmado.")}
        onConfirmarEvento={(ev) => accion(() => api.confirmarEvento(ev, usuario?.id), "Evento confirmado.")}
      />
      <h3>Registrar un documento (incluye canales informales: correo, enlace externo)</h3>
      {!puedeRegistrar && <p className="sub">Elija un usuario de demostración con permiso para registrar.</p>}
      <FormularioDocumento
        hitos={f.linea_de_tiempo.map((h) => h.hito)} deshabilitado={!puedeRegistrar}
        onEnviar={(datos) => accion(() => api.registrarDocumento(id, datos, usuario?.id), "Documento registrado; quedó en la bitácora.")}
      />

      {f.proyectos.length > 0 && (
        <>
          <h2>Proyectos afectados</h2>
          {f.proyectos.map((p) => (
            <p key={String(p.cod_proyecto)}>
              <strong>{String(p.cod_proyecto)}</strong> · {String(p.nombre)} · {String(p.localidad)} · meta asociada: {String(p.meta_asociada ?? "ninguna")}
              {" "}· población beneficiaria {String(p.poblacion_beneficiaria ?? "—")} <Rotulo naturaleza="estimado" /> <Rotulo naturaleza="sintético" />
            </p>
          ))}
        </>
      )}

      {f.ruta_dinero && (
        <>
          <h2>Ruta del dinero</h2>
          {"proyectos" in f.ruta_dinero ? (
            <div className="tabla-wrap"><table aria-label="Ruta del dinero de los proyectos afectados">
              <thead><tr><th>Proyecto</th><th>Programado vigente</th><th>Ejecutado</th><th>Avance financiero (base)</th><th>Avance físico</th><th>Etapa</th></tr></thead>
              <tbody>{f.ruta_dinero.proyectos.map((p) => (
                <tr key={p.cod_proyecto}>
                  <td><Link to={`/proyectos/${p.cod_proyecto}`}>{p.cod_proyecto}</Link></td>
                  <td>{soles(p.monto_programado_vigente)}{p.modificado && <div className="detalle">original: {soles(p.monto_programado_original)}</div>}</td>
                  <td>{p.aviso_ejecucion ?? soles(p.ejecucion_financiera)}</td>
                  <td>{pct(p.avance_financiero)} sobre programado vigente
                    {p.avance_financiero_original != null && <div className="detalle">{pct(p.avance_financiero_original)} sobre el original</div>}</td>
                  <td>{pct(p.avance_fisico)}</td>
                  <td>{p.etapa_escalera}{p.senal_revision && ` · ⚠ señal para revisión (${p.diferencia_pp} pp)`}</td>
                </tr>
              ))}</tbody>
            </table></div>
          ) : (
            <RutaDeUso r={f.ruta_dinero} />
          )}
          <p className="sub"><Link to="/ruta-del-dinero">Ver el tablero de la ruta del dinero</Link></p>
        </>
      )}

      {f.prechequeo && (
        <>
          <h2>Pre-chequeo art. 93/94</h2>
          <PanelPrechequeo p={f.prechequeo} />
        </>
      )}

      <h2>Bitácora de cambios</h2>
      <p className="sub">Solo se agregan entradas; cada una encadena el hash de la anterior.</p>
      <Bitacora entradas={f.bitacora} />
    </>
  );
}
