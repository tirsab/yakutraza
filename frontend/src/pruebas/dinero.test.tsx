import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DetalleProyecto, TableroRutaDelDinero, type Proyecto } from "../dinero";

const fila = (fondo: string, nombre: string, extra: Record<string, unknown> = {}) => ({
  fondo, nombre, solicitado: 0, autorizado: 0, uso_ordinario: 0, uso_excepcional_art_89: 0, uso_emergencia_art_90: 0,
  verificado: null, verificaciones_pendientes: 0, deposito_programado: 0, deposito_efectuado: 0, saldo_final: null,
  saldo_al: null, expedientes: [], ...extra,
});

const peldanos = (autorizadoFondo: string | string[] | null) => [
  { peldano: "solicitado", estado: "cumplido", monto: 50000, fondo: "sin_fondo_indicado", detalle: "", fuente: "DS02 fila 3" },
  { peldano: "autorizado", estado: "cumplido", monto: 40000, fondo: autorizadoFondo, detalle: "", fuente: "DS02 fila 3" },
  { peldano: "usado", estado: "cumplido", monto: 40000, fondo: null, detalle: "", fuente: "DS05 fila 9" },
  { peldano: "verificacion_posterior", estado: "pendiente", monto: null, fondo: null, area: null, detalle: "", fuente: "—" },
  { peldano: "devolucion", estado: "sin_dato", monto: null, fondo: null, detalle: "", fuente: "—" },
];

const resumen = {
  filas: [
    fila("fondo_inversiones", "Fondo de inversiones", { autorizado: 40000, uso_excepcional_art_89: 40000, verificaciones_pendientes: 1,
      expedientes: ["UFI-2024-0001"] }),
    fila("reserva_pcc", "Reserva PCC/PAS"),
    fila("sin_fondo_indicado", "Fondo o reserva no indicado", { solicitado: 50000 }),
  ],
  total: fila("total", "Total", { solicitado: 50000, autorizado: 40000 }),
  notas: ["Verificado: la muestra no registra verificaciones posteriores; se muestra «pendiente», no cero."],
  fuente: "DS05 y DS02",
  visibilidad: { uso_excepcional_autorizado: "publico", uso_emergencia_art_90: "reservado" },
  usos_emergencia: [],
  expedientes_uso: [{ id_expediente: "UFI-2024-0001", cod_eps: "EPS01", naturaleza: "sintético", articulo: "RGT art. 89",
    escalera: peldanos(["fondo_inversiones"]), senal: null }],
  casos_reales: [{ id_expediente: "REAL-EPSSMU-2025", cod_eps: null, empresa: "EPSSMU S.A.", naturaleza: "real",
    articulo: "RGT art. 89", escalera: peldanos("reserva PCC/PAS (no el fondo de inversiones)"), senal: null }],
  filtros: { cod_eps: ["EPS01", "EPS02"], anios: [2025, 2026],
    fondos: { fondo_inversiones: "Fondo de inversiones", reserva_pcc: "Reserva PCC/PAS", sin_fondo_indicado: "Fondo o reserva no indicado" } },
};

const proyecto = (cod: string, extra: Partial<Proyecto> = {}): Proyecto => ({
  cod_proyecto: cod, cod_eps: "EPS04", nombre_proyecto: `Proyecto ${cod}`, localidad: "L", fuente_financiamiento: "fondo_inversiones",
  tipo_periodo: "vigente", meta_asociada: null, poblacion_beneficiaria: 100, monto_programado_original: 1000,
  monto_programado_vigente: 1000, modificado: false, expediente_modificacion: [], ejecucion_financiera: 500,
  ultimo_trimestre: "2026-T2", estado_ejecucion: "en_ejecucion", avance_fisico: 45, avance_financiero: 50,
  avance_financiero_original: null, base_avance_financiero: "programado vigente (S/ 1 000,00)", diferencia_pp: 5,
  senal_revision: false, aviso_ejecucion: null, etapa_escalera: "en_ejecucion", escalera: [], fuente: "DS03 filas [1]; DS04 fila 2",
  conciliacion_mef: null, ...extra,
});

const lista = {
  proyectos: [
    proyecto("EPS04-P004", { modificado: true, monto_programado_original: 1200, monto_programado_vigente: 1000,
      avance_financiero: 74.4, avance_financiero_original: 89.0, expediente_modificacion: ["CPI-2025-0002"] }),
    proyecto("EPS19-P049", { senal_revision: true, diferencia_pp: 31.5 }),
  ],
  total: 2, umbral_senal_pp: 25, base_avance_financiero: "programado vigente", visibilidad: { avance_fisico: "reservado" }, escalera: [],
};

function respuesta(cuerpo: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } }));
}

function api() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    const u = String(url);
    if (u.includes("/ruta-dinero/resumen")) return respuesta(resumen);
    if (u.includes("/ruta-dinero/proyectos/")) return respuesta({ ...proyecto("EPS04-P004"), visibilidad: {},
      anios: [{ anio: 2026, original: 1200, vigente: 1000, id_expediente_modificacion: "CPI-2025-0002", fila: 5 }],
      trimestres: [{ anio_trimestre: "2026-T2", estado: "en_ejecucion", ejecucion_trimestre: 100, ejecucion_acumulada: 500, avance_fisico: 45, fila: 8 }],
      modificado: true, monto_programado_original: 1200, avance_financiero_original: 41.7 });
    if (u.includes("/ruta-dinero/proyectos")) return respuesta(lista);
    return respuesta({ detail: "no encontrado" }, 404);
  });
}

afterEach(() => vi.restoreAllMocks());

describe("Tablero de la ruta del dinero", () => {
  it("muestra totales por fondo con la columna de emergencia (art. 90) y verificado pendiente", async () => {
    api();
    render(<MemoryRouter><TableroRutaDelDinero /></MemoryRouter>);
    const tabla = await screen.findByRole("table", { name: "Totales por fondo o reserva" });
    expect(within(tabla).getByRole("columnheader", { name: /Uso por emergencia \(art\. 90\)/ })).toBeInTheDocument();
    expect(within(tabla).getAllByText(/Pendiente/).length).toBeGreaterThan(0);
    expect(within(tabla).getByText("◷ Pendiente (1)")).toBeInTheDocument();
    // Clic hacia el expediente desde el fondo.
    expect(within(tabla).getByRole("link", { name: "UFI-2024-0001" })).toHaveAttribute("href", "/expedientes/UFI-2024-0001");
    expect(screen.getByText(/La muestra no tiene usos por emergencia/)).toBeInTheDocument();
    // Marcas de visibilidad.
    expect(within(tabla).getAllByText("Público").length).toBeGreaterThan(0);
    expect(within(tabla).getAllByText("Reservado").length).toBeGreaterThan(0);
  });

  it("el caso EPSSMU muestra que se autorizó desde una reserva distinta del fondo", async () => {
    api();
    render(<MemoryRouter><TableroRutaDelDinero /></MemoryRouter>);
    const caso = await screen.findByRole("article", { name: "Ruta del dinero de REAL-EPSSMU-2025" });
    expect(caso).toHaveTextContent("reserva PCC/PAS (no el fondo de inversiones)");
    expect(caso).toHaveTextContent("Verificación posterior · ◷ Pendiente");
    expect(within(caso).getByText("Dato real")).toBeInTheDocument();
  });

  it("indica la base del avance financiero y el original cuando hubo modificación", async () => {
    api();
    render(<MemoryRouter><TableroRutaDelDinero /></MemoryRouter>);
    const tabla = await screen.findByRole("table", { name: "Programado frente a ejecutado por proyecto" });
    const fila = within(tabla).getByRole("link", { name: "EPS04-P004" }).closest("tr")!;
    expect(fila).toHaveTextContent("74,4 %");
    expect(fila).toHaveTextContent("sobre programado vigente");
    expect(fila).toHaveTextContent("89 % sobre el original");
    expect(within(fila).getByRole("img")).toHaveAccessibleName(/Programado .* ejecutado/);
    const otra = within(tabla).getByRole("link", { name: "EPS19-P049" }).closest("tr")!;
    expect(otra).toHaveTextContent("⚠ 31,5 pp");
    expect(otra).not.toHaveTextContent("sobre el original");
  });

  it("los filtros vuelven a consultar la API", async () => {
    const f = api();
    render(<MemoryRouter><TableroRutaDelDinero /></MemoryRouter>);
    const filtros = await screen.findByRole("form", { name: "Filtros de la ruta del dinero" });
    await userEvent.selectOptions(within(filtros).getByLabelText("EPS"), "EPS02");
    await userEvent.click(screen.getByLabelText("Solo señales para revisión"));
    await waitFor(() => {
      const urls = f.mock.calls.map(([u]) => String(u));
      expect(urls.some((u) => u.includes("/ruta-dinero/resumen?cod_eps=EPS02"))).toBe(true);
      expect(urls.some((u) => u.includes("/ruta-dinero/proyectos?cod_eps=EPS02") && u.includes("solo_senales=true"))).toBe(true);
    });
  });

  it("muestra el error de la API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta({ detail: "Todavía no hay datos cargados." }, 404));
    render(<MemoryRouter><TableroRutaDelDinero /></MemoryRouter>);
    expect(await screen.findByText(/Todavía no hay datos cargados/)).toBeInTheDocument();
  });
});

describe("Detalle de proyecto", () => {
  it("muestra base, original, series y fuente", async () => {
    api();
    render(
      <MemoryRouter initialEntries={["/proyectos/EPS04-P004"]}>
        <Routes><Route path="/proyectos/:cod" element={<DetalleProyecto />} /></Routes>
      </MemoryRouter>,
    );
    const avance = (await screen.findByText("Avance financiero")).nextElementSibling!;
    expect(avance).toHaveTextContent("50 % sobre programado vigente · 41,7 % sobre el original");
    expect(screen.getByText("Programado original").nextElementSibling).toHaveTextContent("S/ 1 200,00");
    expect(screen.getByRole("link", { name: "CPI-2025-0002" })).toHaveAttribute("href", "/expedientes/CPI-2025-0002");
    expect(screen.getByText(/Fuente: DS03 filas/)).toBeInTheDocument();
  });
});
