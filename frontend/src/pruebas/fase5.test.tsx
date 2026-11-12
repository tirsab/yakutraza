import { act, render, screen, waitFor, within } from "@testing-library/react";
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
import { ChipFuente, PildoraPlazo, ToastProvider, iniciales, irA, useToast } from "../ui";
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
const pasosCpi = { pasos: ["Recepción", "Requisitos TUPA", "Evaluación", "Informe", "Memorándum a la GG", "Consejo Directivo", "Resolución"]
  .map((nombre, i) => ({ clave: `p${i}`, nombre })), actual: 5, n: 7, terminado: false };
const itemVencido = {
  id_expediente: "CPI-2026-0004", cod_eps: "EPS02", tipo_procedimiento: "cambio_programa_inversiones", especialista: "esp-srt-01",
  estado: "vencido", hito_al_corte: "elevacion_cd", responsable_al_corte: "GG",
  alerta: { reloj: "normativo", estado: "vencido", titulo: "Plazo máximo", mensaje: "Vencido hace 7 días hábiles desde el 2026-09-21.",
    dias_restantes: -7, fecha_limite: "2026-09-21", fuente: "RGT (RCD 028-2021-SUNASS-CD), art. 93.8" },
  siguiente_paso: "Hacer seguimiento: está en Gerencia General (GG) (Elevación al Consejo Directivo).",
  evidencia_faltante: [1, 2, 3].map((n) => ({ tipo: "sin_documento", hito: "solicitud", texto: `Hito ${n}: declarado, no verificado (sin documento).` })),
  por_que_importa: ["Vencido hace 7 días hábiles (plazo máximo).", "Monto solicitado: S/ 159 441,32."],
  naturaleza: "sintético", fuente: "DS02 fila 2 (sintético)", base_normativa: "RGT art. 93", te_toca: false, en_pausa: false,
  pasos: pasosCpi, proyecto: { cod_proyecto: "EPS02-P014", nombre: "Medidores", localidad: "Tingo María" },
};
const itemPausa = { ...itemVencido, id_expediente: "CPI-2026-0005", estado: "en_plazo", en_pausa: true,
  alerta: { ...itemVencido.alerta, estado: "en_plazo", dias_restantes: 5 }, evidencia_faltante: [], por_que_importa: ["Quedan 5 días hábiles."] };
const bandeja = { fecha_corte: "2026-09-30", especialista: "esp-srt-01", items: [itemVencido, itemPausa],
  resumen: { vencido: 1, no_calculable: 0, por_vencer: 0, en_plazo: 1 }, rotulo_asignacion: "Asignación ficticia de demostración",
  orden: "Por plazo restante: vencidos primero." };

const ficha = {
  expediente: { id_expediente: "CPI-2026-0004", cod_eps: "EPS02", tipo_procedimiento: "cambio_programa_inversiones", naturaleza: "sintético",
    estado: "en_tramite", monto_solicitado: 159441.32, monto_aprobado: null },
  fecha_corte: "2026-09-30", pasos: pasosCpi,
  linea_de_tiempo: [
    { nro: 1, hito: "solicitud", descripcion: null, etapa: "unica", responsable: "EP", fecha_inicio: "2026-07-27", fecha_fin: "2026-07-27",
      plazo_referencial_dh: null, cuenta_plazo: true, estado: "concluido", fila_ds02: 10,
      evidencia: { estado: "declarado, no verificado", referencia: null, codigo_ds02: null, tipo: null, documentos: [] } },
    { nro: 2, hito: "elevacion_cd", descripcion: null, etapa: "unica", responsable: "GG", fecha_inicio: "2026-09-11", fecha_fin: null,
      plazo_referencial_dh: null, cuenta_plazo: true, estado: "en curso", fila_ds02: 20,
      evidencia: { estado: "código en DS02, sin archivo", referencia: "MEM-2026-0007", codigo_ds02: "MEM-2026-0007", tipo: "MEM", documentos: [] } },
  ],
  relojes: [
    { expediente: "CPI-2026-0004", reloj: "normativo", estado: "vencido", titulo: "Plazo máximo del procedimiento", mensaje: "Vencido hace 7 DH.",
      regla_id: "PLZ-N-CPI", fuente: "RGT (RCD 028-2021-SUNASS-CD), art. 93.8", estado_validacion: "por validar", respaldo: "norma_leida",
      hito: null, etapa: null, fecha_limite: "2026-09-21", dias_restantes: -7, documento_inicio: null, documento_estado: null, discrepancia: null, detalle: {} },
    { expediente: "CPI-2026-0004", reloj: "interno", estado: "no_calculable", titulo: "Meta interna", mensaje: "falta la fecha de inicio del hito 3.",
      regla_id: "PLZ-I", fuente: "Flujograma de la DRE", estado_validacion: "por validar", respaldo: null, hito: null, etapa: null,
      fecha_limite: null, dias_restantes: null, documento_inicio: null, documento_estado: null, discrepancia: null, detalle: {} },
  ],
  documentos: [{ id: 7, clave: "TACNA:OF-00162-2026", hito: "informacion_ep", tipo: "OF", numero: "Oficio N.° 00162-2026-SUNASS-DRE-SRT", canal: "tramite",
    fecha_emision: "2026-08-14", fecha_recepcion: null, fecha_notificacion: null, naturaleza: "real", origen: "transcrito_ia",
    estado_registro: "propuesto", fuente: "RCD 032-2026, pág. 2", cita: "se le concede una prórroga", pagina: 2, registrado_por: "sistema-carga", confirmado_por: null }],
  eventos: [{ id: 3, hito: "informacion_ep", tipo: "prorroga", dias_dh: 2, estado_registro: "propuesto", naturaleza: "real", origen: "transcrito_ia",
    fuente: "Oficio 162, pág. 1", cita: "dos (2) días hábiles adicionales" }],
  proyectos: [], prechequeo: null, bitacora: [],
  ruta_dinero: { proyectos: [{ cod_proyecto: "EPS02-P014", monto_programado_vigente: 139000, monto_programado_original: 139000, ejecucion_financiera: null,
    ultimo_trimestre: null, aviso_ejecucion: "Sin reportes de ejecución en DS04.", avance_financiero: null }] },
};

function apiBandeja() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    const u = String(url);
    if (u.includes("/bandeja")) return respuesta(bandeja);
    if (u.includes("/corregir")) return respuesta({ id: 3, origen: "corregido" });
    if (u.includes("/confirmar")) return respuesta({ estado_registro: "confirmado" });
    if (u.includes("/expedientes/")) return respuesta(ficha);
    return respuesta({ detail: "no encontrado" }, 404);
  });
}

const ind = (n: number, ids: string[] = []) => ({ n, ids });
function tablero(corte: string, vencidos: number) {
  return {
    fecha_corte: corte, fecha_corte_muestra: "2026-09-30", corte_min: "2022-01-19",
    opciones: { tipo: ["cambio_programa_inversiones"], cod_eps: ["EPS01"], responsable: ["CD", "EP"], especialista: ["esp-srt-01"],
      estado: ["vencido", "no_calculable", "por_vencer", "en_plazo"] },
    indicadores: { en_tramite: ind(3), vencido: ind(vencidos, ["CPI-2026-0004"]), por_vencer: ind(0), no_calculable: ind(0), en_plazo: ind(3 - vencidos) },
    expedientes: [{ id_expediente: "CPI-2026-0004", cod_eps: "EPS02", tipo_procedimiento: "cambio_programa_inversiones", especialista: "esp-srt-01",
      estado: "vencido", hito_al_corte: "elevacion_cd", responsable_al_corte: "GG",
      alerta: { reloj: "normativo", titulo: "x", dias_restantes: -7, fecha_limite: "2026-09-21", fuente: "RGT art. 93.8" } }],
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
    ruta_por_eps: { eps: [{ cod_eps: "EPS02", programado_vigente: 970000, ejecutado: 120000, proyectos: 2, sin_dato_ejecucion: 1,
      senales: [{ cod_proyecto: "EPS02-P001", diferencia_pp: 31.5, fuente: "DS03 filas [1]" }], uso_solicitado: 0, uso_autorizado: 0, uso_usado: 0,
      usos: [], estado: "vencido", expedientes_en_curso: 2 }], nota: "Los pedidos de cambio al programa no se suman como «solicitado».", fuente: "DS03", umbral_senal_pp: 25 },
    por_paso: { cambio_programa_inversiones: { total: 2, pasos: pasosCpi.pasos.map((p, i) => ({ ...p, n: i === 5 ? 2 : 0, ids: i === 5 ? ["CPI-2026-0004"] : [] })) } },
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
    if (u.includes("/expedientes/")) return respuesta(ficha);
    return respuesta({ detail: "no encontrado" }, 404);
  });
}

// ================================================================== portada
describe("Portada", () => {
  it("encabezado, cómo funciona, tres accesos, tres principios y rótulo sintético", () => {
    render(<ConSesion sesion={sesionPrueba()}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    expect(screen.getByRole("heading", { level: 1, name: "Cada trámite y cada sol, a la vista." })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "CÓMO FUNCIONA" })).getAllByRole("listitem")).toHaveLength(4);
    const accesos = within(screen.getByRole("list", { name: "Accesos por rol" }));
    expect(accesos.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Sunass", "EPS", "Ciudadanía"]);
    expect(accesos.getAllByText("Acceso privado")).toHaveLength(2);
    expect(accesos.getByText("Ingreso libre")).toBeInTheDocument();
    for (const p of ["La IA propone, una persona confirma", "Cada alerta tiene su fuente", "Las decisiones son de Sunass"]) {
      expect(screen.getByRole("heading", { name: p })).toBeInTheDocument();
    }
    expect(screen.getByText("Prototipo con datos sintéticos de la muestra del Hackathon Sunass")).toBeInTheDocument();
  });

  it("cada tarjeta entra con su rol (y su EPS)", async () => {
    const verComo = vi.fn(async () => {});
    render(<ConSesion sesion={sesionPrueba("especialista_srt", { verComo })}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    await userEvent.selectOptions(screen.getByLabelText("Rol (modo demo)"), "direccion_dre");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar como Sunass →" }));
    expect(verComo).toHaveBeenCalledWith("direccion_dre");
    await userEvent.selectOptions(screen.getByLabelText("Empresa (modo demo)"), "EPS07");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar como EPS →" }));
    expect(verComo).toHaveBeenCalledWith("eps", "EPS07");
  });

  it("sin modo demo, Sunass y EPS no tienen botón de ingreso", () => {
    const s = sesionPrueba("ciudadania", { config: { ...configPrueba, modo_demo: false } });
    render(<ConSesion sesion={s}><MemoryRouter><Portada /></MemoryRouter></ConSesion>);
    expect(screen.queryByRole("button", { name: /Ingresar como/ })).not.toBeInTheDocument();
    expect(screen.getAllByText(/Requiere acceso institucional/)).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Consultar sin registrarme →" })).toBeInTheDocument();
  });
});

// ======================================================== selector de rol
describe("Barra DEMO y vistas por rol", () => {
  it("cambia de vista y de permisos sin recargar", async () => {
    const f = apiDeApp({ "coord-srt-01": "coordinacion_srt" });
    render(<MemoryRouter initialEntries={["/bandeja"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { level: 1, name: "Hola, Especialista SRT." })).toBeInTheDocument();
    expect(screen.getByText("DEMO")).toBeInTheDocument();
    const trabajo = screen.getByRole("navigation", { name: "Trabajo" });
    expect(within(trabajo).queryByRole("link", { name: "Tablero de dirección" })).not.toBeInTheDocument();
    expect(within(trabajo).getByLabelText("1 urgentes")).toBeInTheDocument();
    expect(screen.getByLabelText("Fecha de corte")).toHaveValue("2026-09-30");
    await userEvent.selectOptions(screen.getByLabelText("Ver como:"), "coordinacion_srt");
    expect(await screen.findByRole("heading", { level: 1, name: "Tablero gerencial de la DRE" })).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Trabajo" })).getByRole("link", { name: "Tablero de dirección" })).toBeInTheDocument();
    const pedido = f.mock.calls.find(([u]) => String(u).includes("/tablero"));
    expect((pedido?.[1]?.headers as Record<string, string>)["X-Usuario"]).toBe("coord-srt-01");
  });

  it("al elegir EPS abre el portal EPS y la lista de empresas", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    await userEvent.selectOptions(await screen.findByLabelText("Ver como:"), "eps");
    expect(await screen.findByRole("heading", { level: 1, name: "Hola, equipo de Manantial." })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Portal EPS" })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("EPS"), "EPS07");
    await waitFor(() => expect(screen.getByText(/EPS07 · usuario ficticio/)).toBeInTheDocument());
  });

  it("una vista sin permiso lo explica y ofrece cambiar de rol", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/tablero"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Esta vista no está disponible para Especialista SRT" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Coordinación SRT" })).toBeInTheDocument();
  });

  it("sin modo demo no hay selector y la barra dice PROTOTIPO", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      const u = String(url);
      if (u.endsWith("/config")) return respuesta({ ...configPrueba, modo_demo: false, roles: [configPrueba.roles[5]], eps: [] });
      if (u.endsWith("/etiquetas")) return respuesta({ categorias: CATEGORIAS });
      if (u.endsWith("/sesion")) return respuesta(usuarioPrueba("ciudadania"));
      return respuesta({}, 404);
    });
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    expect(await screen.findByText("PROTOTIPO")).toBeInTheDocument();
    expect(screen.queryByLabelText("Ver como:")).not.toBeInTheDocument();
  });

  it("si la API tarda en arrancar, reintenta y ofrece «Reintentar»", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta({ detail: "502" }, 502));
      render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
      await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
      expect(await screen.findByRole("button", { name: "Reintentar" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveTextContent("No se pudo conectar con el servidor");
    } finally {
      vi.useRealTimers();
    }
  });

  it("se navega con teclado: primero el enlace para saltar al contenido", async () => {
    apiDeApp();
    render(<MemoryRouter initialEntries={["/bandeja"]}><App /></MemoryRouter>);
    await screen.findByRole("heading", { level: 1, name: "Hola, Especialista SRT." });
    await userEvent.tab();
    const saltar = screen.getByRole("link", { name: "Saltar al contenido principal" });
    expect(saltar).toHaveFocus();
    expect(saltar).toHaveAttribute("href", "#contenido");
    await userEvent.tab();
    expect(screen.getByLabelText("Ver como:")).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "YakuTraza, ir a la portada" })).toHaveFocus();
    expect(document.getElementById("contenido")).toHaveAttribute("tabindex", "-1");
  });
});

// ================================================== bandeja: prueba memorable
describe("Bandeja maestro-detalle", () => {
  it("el primer expediente se abre solo y responde las tres preguntas", async () => {
    apiBandeja();
    render(<ConSesion sesion={sesionPrueba()}><ToastProvider><MemoryRouter><Bandeja /></MemoryRouter></ToastProvider></ConSesion>);
    expect(await screen.findByRole("heading", { level: 1, name: "Hola, Especialista SRT." })).toBeInTheDocument();
    expect(screen.getByText(/Hoy tienes/).closest("p")).toHaveTextContent("Hoy tienes 1 expediente que necesita tu atención");
    const lista = screen.getByRole("list", { name: "Expedientes ordenados por plazo restante" });
    const [primero, segundo] = within(lista).getAllByRole("button");
    expect(primero).toHaveAttribute("aria-current", "true");
    expect(primero).toHaveTextContent("Vencido 7 DH");
    expect(segundo).toHaveTextContent("En pausa");
    const prox = screen.getByRole("region", { name: /Hacer seguimiento/ });
    expect(prox).toHaveTextContent("Próxima acción · está en Gerencia General (GG)");
    expect(prox).toHaveTextContent("paso 6 de 7 (Consejo Directivo)");
    expect(prox).toHaveTextContent("¿Qué requiere acción? Plazo normativo: vencido hace 7 días hábiles (vence el 21/09/2026).");
    expect(prox).toHaveTextContent("¿Qué falta? 3 evidencias");
    expect(prox).toHaveTextContent("¿Por qué importa? Vencido hace 7 días hábiles");
    expect(prox).toHaveTextContent("S/ 159 441,32");
    expect(screen.getByRole("list", { name: "Paso 6 de 7: Consejo Directivo" })).toBeInTheDocument();
    await screen.findByRole("region", { name: "Tres relojes" });
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });

  it("tres relojes con su fuente y «no puedo calcular: falta X»", async () => {
    apiBandeja();
    render(<ConSesion sesion={sesionPrueba()}><ToastProvider><MemoryRouter><Bandeja /></MemoryRouter></ToastProvider></ConSesion>);
    const relojes = await screen.findByRole("region", { name: "Tres relojes" });
    const normativo = within(relojes).getByLabelText("Plazo normativo");
    expect(normativo).toHaveTextContent("21/09/2026");
    expect(within(relojes).getByLabelText("Plazo interno")).toHaveTextContent("No puedo calcular: falta la fecha de inicio del hito 3.");
    expect(within(relojes).getByLabelText("Plazo del oficio")).toHaveTextContent("No hay un plazo de oficio registrado.");
    const chip = within(normativo).getByRole("button", { name: /Fuente: RGT/ });
    await userEvent.click(chip);
    expect(chip).toHaveAttribute("aria-expanded", "true");
    expect(within(normativo).getByRole("link", { name: /Abrir Compendio del RGT/ })).toHaveAttribute("href", "https://cdn.www.gob.pe/uploads/document/file/4388328/");
  });

  it("línea de tiempo con pasaporte, la IA leyó (confirmar y corregir) y mini ruta con «pendiente»", async () => {
    const f = apiBandeja();
    render(<ConSesion sesion={sesionPrueba()}><ToastProvider><MemoryRouter><Bandeja /></MemoryRouter></ToastProvider></ConSesion>);
    const linea = await screen.findByRole("list", { name: "Línea de tiempo del expediente" });
    expect(within(linea).getByText("declarado, no verificado")).toBeInTheDocument();
    expect(within(linea).getByRole("button", { name: "Fuente: MEM-2026-0007" })).toBeInTheDocument();
    const ia = screen.getByRole("region", { name: "La IA leyó el documento" });
    expect(ia).toHaveTextContent("Por confirmar (2)");
    expect(ia.textContent!.indexOf("Prórroga: 2 DH")).toBeLessThan(ia.textContent!.indexOf("Oficio"));  // plazos primero
    expect(within(ia).getByText("«dos (2) días hábiles adicionales»")).toBeInTheDocument();
    await userEvent.click(within(ia).getAllByRole("button", { name: "Confirmar" })[0]);
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("/eventos/3/confirmar"))).toBe(true));
    expect(await screen.findByText("Confirmado. Quedó en la bitácora.")).toBeInTheDocument();
    await userEvent.click(within(ia).getAllByRole("button", { name: "Corregir" })[0]);
    const dialogo = screen.getByRole("dialog", { name: "Corregir la transcripción" });
    await userEvent.clear(within(dialogo).getByLabelText("Días hábiles del plazo"));
    await userEvent.type(within(dialogo).getByLabelText("Días hábiles del plazo"), "3");
    await userEvent.type(within(dialogo).getByLabelText(/Motivo de la corrección/), "El oficio dice tres días");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar corrección" }));
    const [, init] = f.mock.calls.find(([u]) => String(u).includes("/eventos/3/corregir"))!;
    expect(JSON.parse(String(init?.body))).toEqual({ motivo: "El oficio dice tres días", dias_dh: 3 });
    const ruta = screen.getByRole("region", { name: "Ruta del dinero" });
    expect(ruta).toHaveTextContent("Autorizado");
    expect(ruta).toHaveTextContent("Pendiente");
    expect(ruta).toHaveTextContent("No puedo determinar");
    expect(ruta).toHaveTextContent("S/ 139 000,00");
  });

  it("pide la bandeja a la fecha de corte de la sesión", async () => {
    const f = apiBandeja();
    render(<ConSesion sesion={sesionPrueba("especialista_srt", { corte: "2026-09-10" })}><ToastProvider><MemoryRouter><Bandeja /></MemoryRouter></ToastProvider></ConSesion>);
    await screen.findByRole("list", { name: "Expedientes ordenados por plazo restante" });
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

describe("Tablero de dirección", () => {
  it("la fecha de corte mueve los indicadores y muestra el cambio", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
      respuesta(String(url).includes("fecha_corte=2026-09-23") ? tablero("2026-09-23", 0) : tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    const panel = await screen.findByRole("region", { name: "Fecha de corte" });
    await screen.findByRole("button", { name: /Vencido\s*1/ });
    await userEvent.click(within(panel).getByRole("button", { name: "− 1 semana" }));
    await waitFor(() => expect(f.mock.calls.some(([u]) => String(u).includes("fecha_corte=2026-09-23"))).toBe(true));
    expect(await screen.findByText("-1 desde la fecha anterior")).toBeInTheDocument();
    expect(within(panel).getByText("23/09/2026")).toBeInTheDocument();
  });

  it("cinco indicadores: el primero destacado y el % que supera el plazo rotulado", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    await screen.findByRole("button", { name: /Vencido\s*1/ });
    const botones = within(screen.getByRole("region", { name: /Indicadores al/ })).getAllByRole("button");
    expect(botones).toHaveLength(5);
    expect(botones[0]).toHaveClass("destacado");
    expect(botones[0]).toHaveTextContent("En trámite32 en plazo");
    expect(botones[4]).toHaveTextContent("18,5 %");
    expect(botones[4]).toHaveTextContent("muestra simulada");
  });

  it("ruta por EPS, alertas que necesitan decisión, pasos y carga del equipo, sin códigos", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    const rpe = await screen.findByRole("region", { name: "Ruta del dinero por EPS" });
    expect(within(rpe).getByRole("img", { name: /EPS02: programado S\/ 970 000,00, ejecutado S\/ 120 000,00/ })).toBeInTheDocument();
    expect(rpe).toHaveTextContent("Señal para revisión: 1 proyectos");
    expect(rpe).toHaveTextContent("no se suman como «solicitado»");
    const alertas = screen.getByRole("region", { name: "Alertas que necesitan decisión" });
    expect(within(alertas).getByRole("link", { name: /Abrir/ })).toHaveAttribute("href", "/expedientes/CPI-2026-0004");
    expect(within(alertas).getByRole("button", { name: /Fuente: RGT/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "¿En qué paso están los 2 expedientes?" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Consejo Directivo: 2/ })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Carga del equipo" })).toHaveTextContent("esp-srt-01");
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });

  it("el simulador sigue disponible y no modifica los datos", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) => String(url).includes("/simulador")
      ? respuesta({ parametros: { fecha_corte: "2026-09-30", fecha_escenario: "2026-10-14", dias_sin_accion: 10 },
          base: tablero("2026-09-30", 1).indicadores, escenario: tablero("2026-09-30", 3).indicadores,
          cambios: [{ id_expediente: "CPI-2026-0003", antes: "en_plazo", despues: "vencido" }],
          carga_base: { desbalance: 11 }, carga_escenario: { desbalance: 2 },
          rotulo: "Escenario simulado: no modifica los datos reales", supuestos: ["s"] })
      : respuesta(tablero("2026-09-30", 1)));
    render(<TableroConFecha />);
    await userEvent.click(await screen.findByRole("button", { name: "Simular" }));
    expect(await screen.findByText(/Escenario simulado: no modifica los datos reales/)).toBeInTheDocument();
    const [, init] = f.mock.calls.find(([u]) => String(u).includes("/simulador"))!;
    expect(JSON.parse(String(init?.body))).toMatchObject({ fecha_corte: "2026-09-30", dias_sin_accion: 10 });
  });
});

// ================================================================ portal EPS
const pendiente = {
  id_expediente: "CPI-2026-0004", tipo_procedimiento: "cambio_programa_inversiones", hito: "informacion_ep",
  accion: "Enviar la información adicional que pidió Sunass.", fecha_limite: "2026-09-02", dias_restantes: 4, estado: "por_vencer",
  detalle: "", documento: "OF-2026-0018", fuente: "RGT, art. 93.7", suspende_plazo: true,
};
const miEps = {
  cod_eps: "EPS02", fecha_corte: "2026-08-27", siguiente_accion: pendiente, pendientes: [pendiente],
  tramites: [{ id_expediente: "CPI-2026-0004", tipo_procedimiento: "cambio_programa_inversiones", fecha_inicio: "2026-07-27",
    hito_al_corte: "informacion_ep", le_toca_a_la_eps: true, en_que_va: "Le toca a su EPS.", pasos: { ...pasosCpi, actual: 2 } },
  { id_expediente: "RPI-2026-0006", tipo_procedimiento: "reporte_periodico", fecha_inicio: "2026-07-15",
    hito_al_corte: "revision", le_toca_a_la_eps: false, en_que_va: "Está en la Sunass (Equipo SRT).", pasos: null }],
  concluidos: [{ id_expediente: "CPI-2025-0009", tipo_procedimiento: "cambio_programa_inversiones", fecha_conclusion: "2025-04-10", resultado: "aprobado",
    pasos: { ...pasosCpi, terminado: true, actual: 6 } }],
  fondo: [], usos_autorizados: [],
  resumen_fondo: { programado: 1000000, depositado: 800000, autorizado: 0, usado: 300000, aviso: "Lleva depositado el 80 % de lo programado.",
    definiciones: { programado: "a", depositado: "b", autorizado: "c", usado: "d" }, fuente: "DS05 y DS02", hasta: "2026-08" },
  proyectos: [{ cod_proyecto: "EPS02-P014", nombre_proyecto: "Medidores" }],
  aviso_correo: { asunto: "Pendiente: Información adicional de la EP (CPI-2026-0004)", cuerpo: "Estimado equipo…", aviso: "Vista previa: este aviso no se envía." },
  fuente: "DS02",
};
const via = {
  ruta: "solo_comunicacion_art_94", titulo: "Solo comunicación (art. 94, numeral 5)", regla_aplicada: "RGT art. 94, numeral 5",
  explicacion: "El cambio de nombre se comunica.", texto_citado: [{ ubicacion: "RGT art. 94, numeral 5", texto: "En caso existan cambios en el nombre" }],
  advertencias: [], faltantes: [], supuestos: [], documentos: [{ texto: "Oficio dirigido al Gerente General de la Sunass que comunica el cambio", fuente: "RGT art. 94 (encabezado)" }],
  documentos_pendientes: { texto: "Requisitos del TUPA de Sunass: no están en la muestra (por validar, DRE-27).", pregunta_dre: "DRE-27" },
  decision: "Es una orientación. La decisión final siempre es de Sunass.",
};

function apiEps() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    const u = String(url);
    if (u.includes("/prechequeo")) return respuesta(via);
    if (u.includes("/documentos")) return respuesta({ id: 99 }, 201);
    return respuesta(miEps);
  });
}

function montarEps() {
  return render(<ConSesion sesion={sesionPrueba("eps", { usuario: usuarioPrueba("eps", { permisos: ["registrar_documento", "prechequeo"] }) })}>
    <ToastProvider><MemoryRouter><MiEps /></MemoryRouter></ToastProvider></ConSesion>);
}

describe("Portal EPS", () => {
  it("«Sunass te pidió algo»: qué, en qué trámite, con qué oficio, cuántos DH y la pausa del plazo", async () => {
    apiEps();
    montarEps();
    expect(await screen.findByRole("heading", { level: 1, name: "Hola, equipo de Manantial." })).toBeInTheDocument();
    const pedido = screen.getByRole("region", { name: "Enviar la información adicional que pidió Sunass" });
    expect(pedido).toHaveTextContent("Sunass te pidió algo");
    expect(pedido).toHaveTextContent("Trámite CPI-2026-0004");
    expect(within(pedido).getByRole("button", { name: "Fuente: OF-2026-0018" })).toBeInTheDocument();
    expect(pedido).toHaveTextContent("4días hábiles");
    expect(pedido).toHaveTextContent("Tienes hasta el 02/09/2026");
    expect(pedido).toHaveTextContent("Mientras no respondas, el plazo de Sunass está en pausa.");
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });

  it("sin suspensión, no dice que el plazo está en pausa", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta({ ...miEps, siguiente_accion: { ...pendiente, suspende_plazo: false } }));
    montarEps();
    await screen.findByText("Sunass te pidió algo");
    expect(screen.queryByText(/plazo de Sunass está en pausa/)).not.toBeInTheDocument();
  });

  it("Responder registra la respuesta como propuesta", async () => {
    const f = apiEps();
    montarEps();
    await userEvent.click(await screen.findByRole("button", { name: "Responder" }));
    const d = screen.getByRole("dialog", { name: /Responder/ });
    await userEvent.type(within(d).getByLabelText("Número de tu oficio o carta"), "OF-EP-77");
    await userEvent.type(within(d).getByLabelText("Fecha de envío"), "2026-08-26");
    await userEvent.click(within(d).getByRole("button", { name: "Enviar respuesta" }));
    const [, init] = f.mock.calls.find(([u]) => String(u).includes("/expedientes/CPI-2026-0004/documentos"))!;
    expect(JSON.parse(String(init?.body))).toMatchObject({ tipo: "OF", hito: "informacion_ep", numero: "OF-EP-77", canal: "mesa_partes" });
    expect(await screen.findByText(/quedó registrada como «propuesta»/)).toBeInTheDocument();
  });

  it("«¿Qué vía te corresponde?» con preguntas Sí/No, regla aplicada y documentos de la norma", async () => {
    const f = apiEps();
    montarEps();
    const viaSec = await screen.findByRole("region", { name: "¿Qué vía te corresponde?" });
    for (let i = 0; i < 5; i++) {
      const grupos = within(viaSec).getAllByRole("group");
      await userEvent.click(within(grupos[grupos.length - 1]).getByRole("button", { name: "No" }));
    }
    const grupos = within(viaSec).getAllByRole("group");
    await userEvent.click(within(grupos[grupos.length - 1]).getByRole("button", { name: "Sí" }));
    expect(viaSec).toHaveTextContent("Tu caso: Cambio de nombre aprobado en el SNPMGI (art. 94, numeral 5)");
    await userEvent.click(within(viaSec).getByRole("button", { name: "Ver la vía sugerida" }));
    expect(await within(viaSec).findByText(/Solo comunicación/)).toBeInTheDocument();
    const [, init] = f.mock.calls.find(([u]) => String(u).includes("/prechequeo"))!;
    expect(JSON.parse(String(init?.body))).toMatchObject({ cod_eps: "EPS02", tipo_cambio: "cambio_nombre_94_5" });
    expect(within(viaSec).getByRole("checkbox")).not.toBeChecked();
    expect(viaSec).toHaveTextContent("Oficio dirigido al Gerente General de la Sunass");
    expect(viaSec).toHaveTextContent("DRE-27");
    expect(viaSec).toHaveTextContent("Es una orientación. La decisión final siempre es de Sunass.");
  });

  it("Mis trámites con pasos y estado, y Mi fondo con cuatro recuadros", async () => {
    apiEps();
    montarEps();
    const tram = await screen.findByRole("region", { name: "Mis trámites" });
    expect(tram).toHaveTextContent("Te toca a ti");
    expect(tram).toHaveTextContent("Sunass evalúa");
    expect(tram).toHaveTextContent("Aprobado");
    expect(within(tram).getByRole("list", { name: "Paso 3 de 7: Evaluación" })).toBeInTheDocument();
    const fondo = screen.getByRole("region", { name: "Mi fondo de inversiones" });
    for (const x of ["Programado", "Depositado", "Autorizado", "Usado"]) expect(fondo).toHaveTextContent(x);
    expect(fondo).toHaveTextContent("Lleva depositado el 80 % de lo programado.");
  });
});

// =========================================================== vista ciudadana
const ubicaciones = [{ departamento: "LORETO", provincias: [{ provincia: "MAYNAS", distritos: [
  { distrito: "BELEN", ubigeo: "160112", localidad: "Belén" }, { distrito: "IQUITOS", ubigeo: "160101", localidad: "Iquitos" }] }] }];
const etapas = [1, 2, 3, 4, 5, 6].map((n) => ({ n, clave: ["programada", "aprobada", "en_preparacion", "en_obra", "terminada", "beneficio_verificado"][n - 1],
  nombre: ["Programada", "Aprobada", "En preparación", "En obra", "Terminada", "Beneficio verificado"][n - 1], detalle: `Detalle ${n}` }));
const obra = (cod: string, nombre: string, n: number, detenida = false) => ({
  cod_proyecto: cod, nombre_proyecto: nombre, componente: "alcantarillado", poblacion_beneficiaria: 6962, monto_programado_original: 2322000,
  meta_asociada: "MG02", decisiones: [], etapa_ciudadana: { n, de: 6, clave: etapas[n - 1].clave, nombre: etapas[n - 1].nombre, detenida } });
const localidad = (quechua: { texto: string; estado: string } | null) => ({
  localidad: { localidad: "Belén", ubigeo: "160112", departamento: "LORETO", provincia: "MAYNAS", distrito: "BELEN", cod_eps: "EPS06",
    nombre_eps: "EPS Fuente Clara S.A.", poblacion_servida: 71421 },
  fecha_corte: "2026-09-30", etapas,
  agregados: { proyectos: 2, por_etapa: { en_ejecucion: 1, concluido: 1 }, monto_programado_original: 5156000 },
  proyectos: [obra("EPS06-P002", "Rehabilitación de cámara de bombeo", 4, true), obra("EPS06-P003", "Renovación de colectores", 5)],
  audiencias: [{ id_expediente: "RP-2025-0001", hito: "audiencia_publica", fecha_inicio: "2026-04-09", fecha_fin: "2026-05-11", estado: "realizada", plazo_referencial_dh: 30 }],
  resumen_quechua: quechua, avisos: ["La población beneficiaria es una estimación."], fuente: "DS01",
});

function apiCiudadana(quechua: { texto: string; estado: string } | null = null) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    const u = String(url);
    if (u.includes("/publico/ubicaciones")) return respuesta(ubicaciones);
    if (u.includes("/publico/mapa")) return respuesta({ aviso: "Mapa esquemático: DS01 no trae coordenadas.", distritos: [
      { distrito: "BELEN", ubigeo: "160112", localidad: "Belén", obras: [{ cod_proyecto: "EPS06-P002", nombre_proyecto: "R", etapa_ciudadana: obra("x", "x", 4, true).etapa_ciudadana }] }] });
    return respuesta(localidad(quechua));
  });
}

function montarCiudadana() {
  return render(<ConSesion sesion={sesionPrueba("ciudadania")}><MemoryRouter initialEntries={["/ciudadania?ubigeo=160112"]}><VistaCiudadana /></MemoryRouter></ConSesion>);
}

describe("Vista ciudadana", () => {
  it("selectores de ubicación, filtros en píldoras y tarjetas con etapa N de 6", async () => {
    apiCiudadana();
    montarCiudadana();
    expect(screen.getByRole("heading", { level: 1, name: "¿Qué obras de agua hay en tu distrito?" })).toBeInTheDocument();
    const obras = await screen.findByRole("list", { name: "Obras del distrito" });
    expect(screen.getByLabelText("Distrito")).toHaveValue("160112");
    expect(screen.getByRole("option", { name: "Belen" })).toBeInTheDocument();
    expect(within(obras).getAllByRole("button")).toHaveLength(2);
    expect(within(obras).getAllByRole("button")[0]).toHaveTextContent("Obra detenida");
    expect(within(obras).getAllByRole("button")[0]).toHaveTextContent("Etapa 4 de 6");
    await userEvent.click(screen.getByRole("button", { name: "Detenidas" }));
    expect(within(screen.getByRole("list", { name: "Obras del distrito" })).getAllByRole("button")).toHaveLength(1);
    expect(document.body.textContent).not.toMatch(SIN_CODIGOS);
  });

  it("la ficha de obra muestra las seis etapas sin afirmar «en funcionamiento»", async () => {
    apiCiudadana();
    montarCiudadana();
    await userEvent.click(await screen.findByRole("button", { name: /Renovación de colectores/ }));
    const etapasL = screen.getByRole("heading", { name: "¿En qué etapa está?" }).parentElement!;
    const items = within(etapasL).getAllByRole("listitem");
    expect(items).toHaveLength(6);
    expect(items[4]).toHaveAttribute("aria-current", "step");
    expect(items[5]).toHaveTextContent("Beneficio verificado");
    expect(document.body.textContent).not.toMatch(/en funcionamiento/i);
  });

  it("Runasimi: sin validación, muestra «pendiente de validación»", async () => {
    apiCiudadana(null);
    montarCiudadana();
    await screen.findByRole("list", { name: "Obras del distrito" });
    await userEvent.click(screen.getByRole("button", { name: "Runasimi" }));
    expect(screen.getByRole("status")).toHaveTextContent("Resumen en quechua pendiente de validación");
  });

  it("Runasimi: con validación humana, muestra el resumen en quechua", async () => {
    apiCiudadana({ texto: "Kay llaqtapi yaku llamkaykuna.", estado: "validado por una persona" });
    montarCiudadana();
    await screen.findByRole("list", { name: "Obras del distrito" });
    await userEvent.click(screen.getByRole("button", { name: "Runasimi" }));
    const res = screen.getByRole("region", { name: "Resumen en quechua" });
    expect(res).toHaveAttribute("lang", "qu");
    expect(res).toHaveTextContent("Kay llaqtapi yaku llamkaykuna.");
  });

  it("audio: avisa si el navegador no lo soporta y lee en español si lo soporta", async () => {
    apiCiudadana();
    montarCiudadana();
    await screen.findByRole("list", { name: "Obras del distrito" });
    await userEvent.click(screen.getByRole("button", { name: "▶ Escuchar resumen en español" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Tu navegador no permite la lectura en voz alta");
  });

  it("audio con síntesis de voz: usa español (es-PE)", async () => {
    const speak = vi.fn();
    const w = window as unknown as Record<string, unknown>;
    w.speechSynthesis = { speak, cancel: vi.fn() };
    w.SpeechSynthesisUtterance = function (this: Record<string, unknown>, texto: string) { this.text = texto; } as unknown;
    try {
      apiCiudadana();
      montarCiudadana();
      await screen.findByRole("list", { name: "Obras del distrito" });
      await userEvent.click(screen.getByRole("button", { name: "▶ Escuchar resumen en español" }));
      expect(speak).toHaveBeenCalledTimes(1);
      expect(speak.mock.calls[0][0].lang).toBe("es-PE");
      expect(speak.mock.calls[0][0].text).toContain("Belén");
    } finally {
      delete w.speechSynthesis;
      delete w.SpeechSynthesisUtterance;
    }
  });

  it("mapa esquemático y pestaña Participa", async () => {
    apiCiudadana();
    montarCiudadana();
    await screen.findByRole("list", { name: "Obras del distrito" });
    await userEvent.click(screen.getByRole("button", { name: /Mapa/ }));
    expect(await screen.findByRole("heading", { name: "Mapa esquemático" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "BELEN: 1 obras" })).toHaveTextContent("4");
    await userEvent.click(screen.getByRole("button", { name: /Participa/ }));
    expect(screen.getByRole("heading", { name: "Audiencia pública" })).toBeInTheDocument();
  });
});

// ============================================================ componentes
function Disparador() {
  const toast = useToast();
  return <button type="button" onClick={() => toast("Listo.")}>Avisar</button>;
}

describe("Componentes del sistema visual", () => {
  it("píldora de plazo: ícono y texto, nunca solo color", () => {
    const { container } = render(<><PildoraPlazo estado="vencido" dias={-1} /><PildoraPlazo estado="en_plazo" dias={2} enPausa />
      <PildoraPlazo estado="no_calculable" /></>);
    expect(container).toHaveTextContent("⛔Vencido 1 DH");
    expect(container).toHaveTextContent("⏸En pausa");
    expect(container).toHaveTextContent("?No puedo calcular");
  });

  it("toast al confirmar una acción", async () => {
    render(<ToastProvider><Disparador /></ToastProvider>);
    await userEvent.click(screen.getByRole("button", { name: "Avisar" }));
    expect(screen.getByText("Listo.")).toHaveClass("toast");
  });

  it("chip de fuente: abre y se cierra con Escape", async () => {
    render(<ChipFuente texto="OF-2026-0031, pág. 1" detalle="Oficio de la DRT" />);
    const chip = screen.getByRole("button", { name: "Fuente: OF-2026-0031, pág. 1" });
    await userEvent.click(chip);
    expect(screen.getByRole("note")).toHaveTextContent("Oficio de la DRT");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("avatar con iniciales", () => {
    expect(iniciales("Especialista SRT 1 (ficticia)")).toBe("ES1");
    expect(iniciales("EPS Manantial S.A.")).toBe("EM");
  });

  it("prefers-reduced-motion: desplazamiento sin animación y CSS sin animaciones", () => {
    const scroll = vi.fn();
    const el = { scrollIntoView: scroll } as unknown as Element;
    const original = window.matchMedia;
    window.matchMedia = ((q: string) => ({ matches: q.includes("reduce"), media: q })) as unknown as typeof window.matchMedia;
    irA(el);
    expect(scroll).toHaveBeenLastCalledWith({ behavior: "auto", block: "start" });
    window.matchMedia = ((q: string) => ({ matches: false, media: q })) as unknown as typeof window.matchMedia;
    irA(el);
    expect(scroll).toHaveBeenLastCalledWith({ behavior: "smooth", block: "start" });
    window.matchMedia = original;
    const bloque = css.slice(css.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(bloque).toMatch(/animation: none !important/);
    expect(bloque).toMatch(/transition: none !important/);
    expect(bloque).toMatch(/scroll-behavior: auto/);
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
const token = (n: string) => css.match(new RegExp(`--${n}:\\s*(#[0-9A-Fa-f]{6})`))![1];
const BLANCO = "#FFFFFF";

describe("Contraste WCAG AA de la paleta", () => {
  it("cada par de texto usado cumple 4,5:1", () => {
    const pares: [string, string][] = [
      [token("ink"), BLANCO], [token("ink"), token("bg")], [token("mut"), BLANCO], [token("mut"), token("bg")],
      [token("n9"), BLANCO], [token("b7"), BLANCO], [token("b7"), token("bg")], [BLANCO, token("b7")], [BLANCO, token("n8")], [BLANCO, token("n9")],
      [token("ok-tx"), token("ok-bg")], [token("warn-tx"), token("warn-bg")], [token("bad-tx"), token("bad-bg")],
      [token("vio-tx"), token("vio-bg")], [token("info-tx"), token("info-bg")], [token("neu-tx"), token("neu-bg")],
      [token("demo-tx"), token("demo-bg")], [BLANCO, token("bad-tx")], [BLANCO, token("ok-tx")], [token("vio-tx"), BLANCO],
    ];
    for (const [a, b] of pares) expect(contraste(a, b), `${a} sobre ${b}`).toBeGreaterThanOrEqual(4.5);
  });

  it("el texto blanco no va sobre los azules claros; el degradado con texto termina en --b7", () => {
    expect(contraste(BLANCO, token("b5"))).toBeLessThan(4.5);   // 3,77:1: no se usa con texto blanco
    expect(contraste(BLANCO, token("c4"))).toBeLessThan(3);     // 2,70:1: solo decorativo
    const gradTexto = css.match(/--grad-texto:\s*linear-gradient\(([^;]+)\);/)![1];
    for (const c of gradTexto.match(/#[0-9A-Fa-f]{6}/g)!) expect(contraste(BLANCO, c)).toBeGreaterThanOrEqual(4.5);
    // Ninguna regla pone texto blanco sobre el degradado decorativo (--grad).
    for (const regla of css.split("}")) {
      if (/background:\s*var\(--grad\)/.test(regla)) expect(regla).not.toMatch(/(^|[^-])color:\s*#fff/);
    }
    for (const t of ["ok", "warn", "bad"]) expect(contraste(token(t), BLANCO)).toBeLessThan(4.5);  // solo íconos y bordes
    expect(css).not.toMatch(/(^|[^-])color:\s*var\(--(ok|warn|bad|b5|c4)\)/m);
  });

  it("usa Poppins para títulos e Inter para el texto, instaladas en el proyecto", () => {
    expect(css).toMatch(/--f-titulo:\s*"Poppins"/);
    expect(css).toMatch(/--f-texto:\s*"Inter"/);
    const main = readFileSync("src/main.tsx", "utf-8");
    expect(main).toMatch(/@fontsource\/poppins/);
    expect(main).toMatch(/@fontsource\/inter/);
    expect(main).not.toMatch(/fonts\.googleapis/);
  });
});
