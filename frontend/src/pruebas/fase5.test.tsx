import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { Bandeja } from "../bandeja";
import { VistaCiudadana } from "../ciudadana";
import { MiEps } from "../mieps";
import { Portada } from "../portada";
import { TableroGerencial } from "../tablero";
import { readFileSync } from "node:fs";
import { CATEGORIAS } from "./etiquetasPrueba";
import { configPrueba, ConSesion, respuesta, sesionPrueba, usuarioPrueba } from "./sesion";

// Vitest no entrega el CSS como texto: se lee del disco (ruta relativa a frontend/).
const css = readFileSync("src/estilos.css", "utf-8");
const SIN_CODIGOS = /\b[a-z0-9]+(?:_[a-z0-9]+)+\b/;

afterEach(() => {
  vi.restoreAllMocks();
  try { window.localStorage.clear(); } catch { /* sin almacenamiento */ }
});

// ------------------------------------------------------------------ datos
const itemVencido = {
  id_expediente: "RP-2026-0001", cod_eps: "EPS01", tipo_procedimiento: "revision_periodica", especialista: "esp-srt-01",
  estado: "vencido", hito_al_corte: "resolucion_difusion", responsable_al_corte: "CD",
  alerta: { reloj: "normativo", estado: "vencido", titulo: "Etapa 2_evaluacion", mensaje: "Etapa 2_evaluacion en curso desde el 2026-06-15: vencida hace 4 días hábiles.",
    dias_restantes: -4, fecha_limite: "2026-09-24", fuente: "RGT art. 47" },
  siguiente_paso: "Hacer seguimiento: está en Consejo Directivo (CD) (Resolución que dispone la difusión).",
  evidencia_faltante: [1, 2, 3, 4, 5].map((n) => ({ tipo: "sin_documento", hito: "solicitud", texto: `Hito ${n}: declarado, no verificado (sin documento).` })),
  por_que_importa: ["Vencido hace 4 días hábiles (etapa 2_evaluacion).", "Monto solicitado: S/ 159 441,32."],
  naturaleza: "sintético", fuente: "DS02 fila 23 (sintético)",
};
const itemEnPlazo = { ...itemVencido, id_expediente: "CPI-2026-0003", estado: "en_plazo", tipo_procedimiento: "cambio_programa_inversiones",
  alerta: { ...itemVencido.alerta, estado: "en_plazo", dias_restantes: 12 }, evidencia_faltante: [], por_que_importa: ["Quedan 12 días hábiles."] };
const bandeja = { fecha_corte: "2026-09-30", especialista: "esp-srt-01", items: [itemVencido, itemEnPlazo],
  resumen: { vencido: 1, no_calculable: 0, por_vencer: 0, en_plazo: 1 }, rotulo_asignacion: "Asignación ficticia de demostración",
  orden: "Por plazo restante: vencidos primero." };

const ind = (n: number, ids: string[] = []) => ({ n, ids });
function tablero(corte: string, vencidos: number) {
  return {
    fecha_corte: corte, fecha_corte_muestra: "2026-09-30", corte_min: "2022-01-19",
    opciones: { tipo: ["cambio_programa_inversiones"], cod_eps: ["EPS01"], responsable: ["CD", "EP"], especialista: ["esp-srt-01"], estado: [] },
    indicadores: { en_tramite: ind(3), vencido: ind(vencidos, ["RP-2026-0001"]), por_vencer: ind(0), no_calculable: ind(0), en_plazo: ind(3 - vencidos) },
    expedientes: [{ id_expediente: "RP-2026-0001", cod_eps: "EPS01", tipo_procedimiento: "revision_periodica", especialista: "esp-srt-01",
      estado: "vencido", hito_al_corte: "resolucion_difusion", responsable_al_corte: "CD",
      alerta: { reloj: "normativo", titulo: "x", dias_restantes: -4, fecha_limite: "2026-09-24" } }],
    supera_plazo: { rotulo: "muestra simulada", total: { superan: 12, calculables: 65, no_calculables: 416, porcentaje: 18.5, ids_superan: [], en_tramite_superan: 3 },
      por_tipo: { revision_periodica: { superan: 10, calculables: 20, no_calculables: 0, porcentaje: 50, ids_superan: ["RP-2024-0002"], en_tramite_superan: 2 } },
      por_eps: {}, formula: "DS02 dias_habiles_sunass > DS02 plazo_maximo_dh", nota: "Nota.", fuente: "DS02", a_la_fecha: "2026-09-30" },
    cuellos: { por_hito: [{ clave: "memo_gg", n: 3, mediana_dh: 2, p90_dh: 4, max_dh: 5, en_curso: 1, ids_en_curso: ["CPI-2026-0003"],
      supera_referencial: 0, con_referencial: 0, plazo_referencial_dh: [], responsables: ["DRE"] }],
      por_responsable: [{ clave: "CD", n: 4, mediana_dh: 4, p90_dh: 6, max_dh: 9, en_curso: 1, ids_en_curso: ["RP-2026-0001"],
        supera_referencial: 0, con_referencial: 0, plazo_referencial_dh: [], responsables: ["CD"] }],
      fechas_inconsistentes: [], nota: "Días hábiles.", fuente: "DS02" },
    embudo: { etapas: [{ clave: "memo_gg", nombre: "Memorándum a la Gerencia General", llegaron: 32, en_curso: 2, ids_en_curso: ["CPI-2026-0003"], mediana_dh: 1, p90_dh: 3 }],
      sustento: "Agrupación.", fuente: "DS02" },
    carga: { actual: [{ especialista: "esp-srt-01", n: 5, carga: 11, vencidos: 1, por_vencer: 0, no_calculable: 0 }],
      propuesta: [{ especialista: "esp-srt-01", carga: 15 }], movimientos: [{ id_expediente: "CPI-2026-0003", tipo_procedimiento: "cambio_programa_inversiones", de: "esp-srt-02", a: "esp-srt-01", peso: 3 }],
      desbalance_actual: 11, desbalance_propuesto: 1, pesos: { revision_periodica: 5 }, sustento_pesos: "s", pregunta_dre: "DRE-26",
      rotulo: "Asignación ficticia de demostración", aviso: "Propuesta orientativa: no reasigna nada." },
    calidad: { total: 202, por_severidad: { informativa: 129, alta: 10 }, por_tipo: {}, reglas: [{ regla_id: "CAL-MEF-02", titulo: "Desfase", severidad: "informativa", n: 121 }],
      reporte: "/calidad/reporte.html", nota: "Sin correcciones silenciosas." },
  };
}

function apiDeApp(rolPorUsuario: Record<string, string> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url, init) => {
    const u = String(url);
    const quien = (init?.headers as Record<string, string> | undefined)?.["X-Usuario"];
    if (u.endsWith("/config")) return respuesta(configPrueba);
    if (u.endsWith("/etiquetas")) return respuesta({ categorias: CATEGORIAS });
    if (u.endsWith("/sesion")) {
      const rol = quien ? rolPorUsuario[quien] ?? (quien.startsWith("eps-") ? "eps" : "especialista_srt") : "ciudadania";
      return respuesta(usuarioPrueba(rol, quien?.startsWith("eps-") ? { id: quien, cod_eps: quien.slice(4) } : {}));
    }
    if (u.includes("/bandeja")) return respuesta(bandeja);
    if (u.includes("/tablero")) return respuesta(tablero("2026-09-30", 1));
    if (u.includes("/mi-eps")) return respuesta(miEps);
    return respuesta({ detail: "no encontrado" }, 404);
  });
}

// ================================================================== portada
describe("Portada", () => {
  it("muestra nombre, frase, las tres preguntas, accesos y el rótulo de datos sintéticos", () => {
    render(<ConSesion sesion={sesionPrueba()}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    expect(screen.getByRole("heading", { level: 1, name: "YakuTraza" })).toBeInTheDocument();
    expect(screen.getByText("Seguimiento verificable de trámites y recursos de inversión de las EPS")).toBeInTheDocument();
    for (const p of ["¿Qué requiere acción?", "¿Qué falta?", "¿Por qué importa?"]) expect(screen.getByText(p)).toBeInTheDocument();
    expect(screen.getByText("Prototipo con datos sintéticos de la muestra del Hackathon Sunass")).toBeInTheDocument();
    const botones = screen.getAllByRole("button", { name: /^Entrar como/ });
    expect(botones.map((b) => b.textContent)).toEqual(["Entrar como Especialista SRT", "Entrar como Coordinación SRT",
      "Entrar como Dirección DRE", "Entrar como Otras áreas", "Entrar como Empresa prestadora (EPS)", "Entrar como Ciudadanía"]);
  });

  it("cada acceso cambia de rol", async () => {
    const verComo = vi.fn(async () => {});
    render(<ConSesion sesion={sesionPrueba("especialista_srt", { verComo })}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    await userEvent.click(screen.getByRole("button", { name: "Entrar como Dirección DRE" }));
    expect(verComo).toHaveBeenCalledWith("direccion_dre");
  });

  it("sin modo demo solo ofrece la vista ciudadana", () => {
    const s = sesionPrueba("ciudadania", { config: { ...configPrueba, modo_demo: false } });
    render(<ConSesion sesion={s}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByRole("link", { name: "Abrir la vista ciudadana" })).toHaveAttribute("href", "/ciudadania");
  });
});

// ======================================================== selector de rol
describe("Selector «Ver como» (modo demo)", () => {
  it("cambia de vista y de permisos sin recargar", async () => {
    const f = apiDeApp({ "coord-srt-01": "coordinacion_srt" });
    render(<MemoryRouter initialEntries={["/bandeja"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { level: 1, name: "Mi siguiente acción" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Secciones" });
    expect(within(nav).queryByRole("link", { name: "Tablero gerencial" })).not.toBeInTheDocument();
    expect(screen.getByText("Modo demo")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Ver como:"), "coordinacion_srt");
    expect(await screen.findByRole("heading", { level: 1, name: "Tablero gerencial de la DRE" })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: "Tablero gerencial" })).toBeInTheDocument();
    const pedidoTablero = f.mock.calls.find(([u]) => String(u).includes("/tablero"));
    expect((pedidoTablero?.[1]?.headers as Record<string, string>)["X-Usuario"]).toBe("coord-srt-01");
  });

  it("al elegir EPS aparece la lista de empresas", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    await userEvent.selectOptions(await screen.findByLabelText("Ver como:"), "eps");
    expect(await screen.findByRole("heading", { level: 1, name: "EPS Manantial S.A." })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("EPS"), "EPS07");
    await waitFor(() => expect(screen.getByText("EPS EPS07")).toBeInTheDocument());
  });

  it("una vista sin permiso lo explica y ofrece cambiar de rol", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/tablero"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Esta vista no está disponible para Especialista SRT" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Coordinación SRT" })).toBeInTheDocument();
  });

  it("sin modo demo no hay selector", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.endsWith("/config")) return respuesta({ ...configPrueba, modo_demo: false, roles: [configPrueba.roles[5]], eps: [] });
      if (u.endsWith("/etiquetas")) return respuesta({ categorias: CATEGORIAS });
      if (u.endsWith("/sesion")) return respuesta(usuarioPrueba("ciudadania"));
      return respuesta({}, 404);
    });
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { level: 1, name: "YakuTraza" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Ver como:")).not.toBeInTheDocument();
  });

  it("se navega con teclado: primero el enlace para saltar al contenido", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/bandeja"]}><App /></MemoryRouter>);
    await screen.findByRole("heading", { level: 1, name: "Mi siguiente acción" });
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Saltar al contenido principal" })).toHaveFocus();
    expect(screen.getByRole("link", { name: "Saltar al contenido principal" })).toHaveAttribute("href", "#contenido");
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "YakuTraza, ir a la portada" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Mi siguiente acción" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(document.getElementById("contenido")).toHaveAttribute("tabindex", "-1");
  });
});

// ================================================== bandeja: prueba memorable
describe("Bandeja «mi siguiente acción»", () => {
  it("la primera tarjeta responde qué requiere acción, qué falta y por qué importa", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(bandeja));
    render(<ConSesion sesion={sesionPrueba()}><MemoryRouter><Bandeja /></MemoryRouter></ConSesion>);
    const lista = await screen.findByRole("list", { name: "Expedientes ordenados por plazo restante" });
    const primera = within(lista).getAllByRole("article")[0];
    expect(within(primera).getByRole("link", { name: "RP-2026-0001" })).toHaveAttribute("href", "/expedientes/RP-2026-0001");
    expect(primera).toHaveTextContent("Vencido");
    expect(primera).toHaveTextContent("vencido hace 4 días hábiles");
    const [accion, falta, importa] = within(primera).getAllByRole("heading", { level: 4 }).map((h) => h.parentElement!);
    expect(accion).toHaveTextContent("¿Qué requiere acción?");
    expect(accion).toHaveTextContent("Consejo Directivo");
    expect(accion).toHaveTextContent("15/06/2026");
    expect(falta).toHaveTextContent("5 pendientes");
    expect(within(falta).getByText("Ver 2 más")).toBeInTheDocument();
    expect(importa).toHaveTextContent("S/ 159 441,32");
    expect(importa).toHaveTextContent("etapa 2. Evaluación");
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
    expect(screen.getByRole("status")).toHaveTextContent("1 expediente requiere atención");
  });

  it("pide la bandeja a la fecha de corte de la sesión", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(bandeja));
    render(<ConSesion sesion={sesionPrueba("especialista_srt", { corte: "2026-09-10" })}><MemoryRouter><Bandeja /></MemoryRouter></ConSesion>);
    await screen.findAllByRole("article");
    expect(String(f.mock.calls[0][0])).toContain("fecha_corte=2026-09-10");
    expect(screen.getByText(/fecha anterior a la de la muestra/)).toBeInTheDocument();
  });
});

// ================================================================== tablero
function TableroConFecha() {
  const [corte, setCorte] = useState("2026-09-30");
  return (
    <ConSesion sesion={sesionPrueba("coordinacion_srt", { corte, setCorte })}>
      <MemoryRouter><TableroGerencial /></MemoryRouter>
    </ConSesion>
  );
}

describe("Tablero gerencial", () => {
  it("la fecha de corte mueve los indicadores y muestra el cambio", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      return respuesta(u.includes("fecha_corte=2026-09-23") ? tablero("2026-09-23", 0) : tablero("2026-09-30", 1));
    });
    render(<TableroConFecha />);
    const panel = await screen.findByRole("region", { name: "Fecha de corte" });
    expect(within(panel).getByText("30/09/2026")).toBeInTheDocument();
    await screen.findByRole("button", { name: /Vencido\s*1/ });
    await userEvent.click(within(panel).getByRole("button", { name: "− 1 semana" }));
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("fecha_corte=2026-09-23"))).toBe(true));
    expect(await screen.findByText("-1 desde la fecha anterior")).toBeInTheDocument();
    expect(within(panel).getByText("23/09/2026")).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: "Volver a la fecha de la muestra" }));
    expect(within(panel).getByText("30/09/2026")).toBeInTheDocument();
    expect(within(panel).getByLabelText("Deslizar la fecha de corte")).toHaveAttribute("type", "range");
  });

  it("cada indicador filtra la lista y lleva hasta el expediente", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    const boton = await screen.findByRole("button", { name: /Vencido\s*1/ });
    await userEvent.click(boton);
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("estado=vencido"))).toBe(true));
    expect(boton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: /Expedientes — vencido/ })).toHaveFocus();
    expect(screen.getAllByRole("link", { name: "RP-2026-0001" })[0]).toHaveAttribute("href", "/expedientes/RP-2026-0001");
  });

  it("muestra línea base, cuellos, embudo, carga, calidad y el simulador, sin códigos", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) => String(url).includes("/simulador")
      ? respuesta({ parametros: { fecha_corte: "2026-09-30", fecha_escenario: "2026-10-14", dias_sin_accion: 10 },
          base: tablero("2026-09-30", 1).indicadores, escenario: tablero("2026-09-30", 3).indicadores,
          cambios: [{ id_expediente: "CPI-2026-0003", antes: "en_plazo", despues: "vencido" }],
          carga_base: { desbalance: 11 }, carga_escenario: { desbalance: 2 },
          rotulo: "Escenario simulado: no modifica los datos reales", supuestos: ["s"] })
      : respuesta(tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    expect(await screen.findByText("18,5 %")).toBeInTheDocument();
    expect(screen.getAllByText("muestra simulada")[0]).toBeInTheDocument();
    expect(screen.getByText("Memorándum a la Gerencia General", { selector: "th" })).toBeInTheDocument();
    expect(screen.getByText("Consejo Directivo (CD)", { selector: "th" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir el reporte completo de calidad" })).toHaveAttribute("href", "/api/calidad/reporte.html");
    expect(screen.getByText(/Propuesta de asignación: 1 cambio/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
    await userEvent.click(screen.getByRole("button", { name: "Simular" }));
    expect(await screen.findByText(/Escenario simulado: no modifica los datos reales/)).toBeInTheDocument();
    expect(screen.getByText(/En plazo → Vencido/)).toBeInTheDocument();
    const [, init] = f.mock.calls.find(([u]) => String(u).includes("/simulador"))!;
    expect(JSON.parse(String(init?.body))).toMatchObject({ fecha_corte: "2026-09-30", dias_sin_accion: 10 });
  });
});

// ================================================================ vista EPS
const miEps = {
  cod_eps: "EPS02", fecha_corte: "2026-09-30",
  siguiente_accion: { id_expediente: "CPI-2026-0005", tipo_procedimiento: "cambio_programa_inversiones", hito: "informacion_ep",
    accion: "Enviar a la Sunass: Información adicional de la EP.", fecha_limite: "2026-09-28", dias_restantes: -2, estado: "vencido",
    detalle: "", documento: "OF-2026-0030", fuente: "RGT" },
  pendientes: [], tramites: [{ id_expediente: "CPI-2026-0005", tipo_procedimiento: "cambio_programa_inversiones", fecha_inicio: "2026-08-31",
    hito_al_corte: "informacion_ep", le_toca_a_la_eps: true, en_que_va: "Le toca a su EPS." }],
  concluidos: [], fondo: [{ fondo: "fondo_inversiones", deposito_programado: 100, deposito_efectuado: 80, saldo_final: 500, saldo_al: "2026-08",
    uso_ordinario: 0, uso_excepcional_art_89: 0, uso_emergencia_art_90: 0 }], usos_autorizados: [],
  aviso_correo: { asunto: "Pendiente: Información adicional de la EP (CPI-2026-0005)", cuerpo: "Estimado equipo…",
    aviso: "Vista previa: este aviso no se envía." },
  fuente: "DS02",
};

describe("Vista EPS", () => {
  it("muestra una sola acción principal, hasta cuándo, y el aviso como vista previa", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(miEps));
    render(<ConSesion sesion={sesionPrueba("eps")}><MemoryRouter><MiEps /></MemoryRouter></ConSesion>);
    const accion = await screen.findByRole("region", { name: "Su siguiente acción" });
    expect(accion).toHaveTextContent("Enviar a la Sunass: Información adicional de la EP.");
    expect(accion).toHaveTextContent("28/09/2026");
    expect(accion).toHaveTextContent("vencido hace 2 días hábiles");
    expect(within(accion).getAllByRole("link")).toHaveLength(1);
    expect(screen.getByText("Vista previa: este aviso no se envía.")).toBeInTheDocument();
    expect(screen.getByText("Fondo de inversiones")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });
});

// =========================================================== vista ciudadana
describe("Vista ciudadana", () => {
  it("busca la localidad y muestra proyectos, audiencias y el resumen en quechua pendiente", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.includes("/publico/localidades?q=")) return respuesta([{ localidad: "Belén", ubigeo: "160112", departamento: "LORETO",
        provincia: "MAYNAS", distrito: "BELEN", cod_eps: "EPS06", nombre_eps: "EPS Fuente Clara S.A." }]);
      return respuesta({
        localidad: { localidad: "Belén", ubigeo: "160112", departamento: "LORETO", provincia: "MAYNAS", distrito: "BELEN",
          cod_eps: "EPS06", nombre_eps: "EPS Fuente Clara S.A.", poblacion_servida: 71421 },
        fecha_corte: "2026-09-30", agregados: { proyectos: 1, por_etapa: { en_ejecucion: 1 }, monto_programado_original: 2322000 },
        proyectos: [{ cod_proyecto: "EPS06-P002", nombre_proyecto: "Rehabilitación de cámara de bombeo", componente: "alcantarillado",
          etapa_escalera: "en_ejecucion", poblacion_beneficiaria: 6962, monto_programado_original: 2322000, meta_asociada: "MG02",
          decisiones: [{ id_expediente: "CPI-2025-0009", documento_final: "RCD-2025-0101", resultado: "aprobado", fecha_conclusion: "2025-04-10" }] }],
        audiencias: [{ id_expediente: "RP-2025-0001", hito: "audiencia_publica", fecha_inicio: "2026-04-09", fecha_fin: "2026-05-11",
          estado: "realizada", plazo_referencial_dh: 30 }],
        resumen_quechua: null, avisos: ["La población beneficiaria es una estimación."], fuente: "DS01",
      });
    });
    render(<ConSesion sesion={sesionPrueba("ciudadania")}><MemoryRouter><VistaCiudadana /></MemoryRouter></ConSesion>);
    await userEvent.type(screen.getByLabelText("Localidad, distrito o código de ubigeo"), "belen");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await userEvent.click(await screen.findByRole("button", { name: "Belén" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Belén" })).toBeInTheDocument();
    expect(screen.getByText(/Etapa:/).parentElement).toHaveTextContent("En ejecución");
    expect(screen.getByText(/6\D?962 personas beneficiarias/)).toBeInTheDocument();
    expect(screen.getByText(/RCD-2025-0101/)).toHaveTextContent("Aprobado");
    expect(screen.getByText("Audiencia pública")).toBeInTheDocument();
    expect(screen.getByText(/Pendiente: una persona debe escribirlo y otra validarlo/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });

  it("pide al menos dos caracteres", async () => {
    render(<ConSesion sesion={sesionPrueba("ciudadania")}><MemoryRouter><VistaCiudadana /></MemoryRouter></ConSesion>);
    await userEvent.type(screen.getByLabelText("Localidad, distrito o código de ubigeo"), "b");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("al menos dos");
  });
});

// ======================================================= contraste WCAG AA
function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
}
const token = (n: string) => css.match(new RegExp(`--yt-${n}:\\s*(#[0-9A-Fa-f]{6})`))![1];

describe("Contraste WCAG AA de la paleta", () => {
  it("cada par de texto usado cumple 4,5:1", () => {
    const blanco = "#FFFFFF";
    const pares: [string, string][] = [
      [token("navy-900"), blanco], [token("blue-600"), blanco], [token("slate-600"), blanco], [token("violet-600"), blanco],
      [token("navy-700"), blanco], [token("slate-600"), token("ice-100")], [token("slate-600"), token("ice-50")],
      [token("blue-600"), token("ice-100")], [token("navy-900"), token("lilac-300")], [token("navy-900"), token("ice-100")],
      [blanco, token("navy-700")], [token("violet-600"), token("ice-50")],
    ];
    for (const [a, b] of pares) expect(contraste(a, b), `${a} sobre ${b}`).toBeGreaterThanOrEqual(4.5);
  });

  it("el teal no se usa como color de texto normal (4,05:1)", () => {
    expect(contraste(token("teal-500"), "#FFFFFF")).toBeLessThan(4.5);
    expect(contraste(token("teal-500"), "#FFFFFF")).toBeGreaterThanOrEqual(3);
    expect(css).not.toMatch(/(^|[^-])color:\s*var\(--yt-teal-500\)/m);
  });

  it("usa Noto Sans con respaldo Arial", () => {
    expect(css).toMatch(/font-family:\s*"Noto Sans", Arial, sans-serif/);
  });
});
