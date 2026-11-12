import { Link } from "react-router-dom";
import { useSesion } from "./sesion";

const ACCESOS: { rol: string; vista: string; titulo: string; texto: string }[] = [
  { rol: "especialista_srt", vista: "Mi siguiente acción", titulo: "Especialista SRT",
    texto: "Su bandeja ordenada por plazo restante: qué expediente atender primero." },
  { rol: "coordinacion_srt", vista: "Tablero gerencial", titulo: "Coordinación SRT",
    texto: "Vencidos, cuellos de botella, carga del equipo y propuesta de asignación." },
  { rol: "direccion_dre", vista: "Tablero gerencial", titulo: "Dirección DRE",
    texto: "Línea base del plazo superado, embudo de firmas y simulador de escenarios." },
  { rol: "otras_areas", vista: "Expedientes", titulo: "Otras áreas",
    texto: "Consulta de expedientes y ruta del dinero, solo lectura." },
  { rol: "eps", vista: "Mi EPS", titulo: "Empresa prestadora (EPS)",
    texto: "Qué le falta entregar y hasta cuándo; su fondo y usos autorizados." },
  { rol: "ciudadania", vista: "Vista ciudadana", titulo: "Ciudadanía",
    texto: "Proyectos de su localidad, su etapa y las audiencias públicas." },
];

export function Portada() {
  const { config, verComo } = useSesion();
  const accesos = config.modo_demo ? ACCESOS : ACCESOS.filter((a) => a.rol === "ciudadania");
  return (
    <div className="portada">
      <section className="portada-cabecera" aria-labelledby="portada-titulo">
        <p className="rotulo-prototipo">{config.rotulo}</p>
        <h1 id="portada-titulo">YakuTraza</h1>
        <p className="lema">Seguimiento verificable de trámites y recursos de inversión de las EPS</p>
      </section>

      <section aria-labelledby="preguntas-titulo">
        <h2 id="preguntas-titulo">Responde tres preguntas en menos de un minuto</h2>
        <ol className="tres-preguntas">
          <li>
            <span className="numero" aria-hidden="true">1</span>
            <strong>¿Qué requiere acción?</strong>
            <span>El expediente con el plazo más urgente: vencido, por vencer o sin datos para calcular.</span>
          </li>
          <li>
            <span className="numero" aria-hidden="true">2</span>
            <strong>¿Qué falta?</strong>
            <span>La evidencia que no está: hitos declarados sin documento y registros sin confirmar.</span>
          </li>
          <li>
            <span className="numero" aria-hidden="true">3</span>
            <strong>¿Por qué importa?</strong>
            <span>Los días de atraso, el monto, el proyecto y la población que espera la decisión.</span>
          </li>
        </ol>
      </section>

      <section aria-labelledby="accesos-titulo">
        <h2 id="accesos-titulo">Entrar a cada vista</h2>
        {config.modo_demo && (
          <p className="sub">Modo demo: cada acceso cambia el rol y aplica sus permisos. Los usuarios son ficticios.</p>
        )}
        <ul className="accesos">
          {accesos.map((a) => (
            <li key={a.rol}>
              <h3>{a.titulo}</h3>
              <p>{a.texto}</p>
              <p className="meta">Abre: {a.vista}</p>
              {a.rol === "ciudadania" && !config.modo_demo ? (
                <Link className="boton" to="/ciudadania">Abrir la {a.vista.toLowerCase()}</Link>
              ) : (
                <button type="button" onClick={() => verComo(a.rol)}>Entrar como {a.titulo}</button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
