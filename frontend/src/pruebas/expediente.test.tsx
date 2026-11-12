import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Ficha, UsuarioDemo } from "../api";
import { ExpedienteVivo, ListaExpedientes } from "../paginas";
import { ConSesion, sesionPrueba } from "./sesion";

const especialista: UsuarioDemo = {
  id: "esp-srt-01", nombre: "Especialista SRT 1 (ficticia)", rol: "especialista_srt",
  permisos: ["registrar_documento", "confirmar_registro"], cod_eps: null, rotulo: "Usuario ficticio de demostración",
};
const lectura: UsuarioDemo = { ...especialista, id: "area-01", rol: "otras_areas", permisos: [] };

const ficha: Ficha = {
  expediente: { id_expediente: "CPI-2026-0004", cod_eps: "EPS02", tipo_procedimiento: "cambio_programa_inversiones",
    naturaleza: "sintético", estado: "en_tramite", fecha_inicio: "2026-07-27", fecha_conclusion: null,
    plazo_maximo_dh: 30, base_normativa: "RGT art. 93", fuente: "DS02 ds02_procedimientos, fila 2 (sintético)" },
  fecha_corte: "2026-09-30",
  linea_de_tiempo: [
    { nro: 1, hito: "solicitud", descripcion: null, etapa: "unica", responsable: "EP", fecha_inicio: "2026-07-27",
      fecha_fin: "2026-07-27", plazo_referencial_dh: null, cuenta_plazo: true, estado: "concluido", fila_ds02: 10,
      evidencia: { estado: "declarado, no verificado", referencia: null, codigo_ds02: null, tipo: null, documentos: [] } },
    { nro: 6, hito: "oficio_informacion", descripcion: null, etapa: "unica", responsable: "SRT",
      fecha_inicio: "2026-08-14", fecha_fin: "2026-08-19", plazo_referencial_dh: null, cuenta_plazo: true,
      estado: "concluido", fila_ds02: 15,
      evidencia: { estado: "código en DS02, sin archivo", referencia: "OF-2026-0018", codigo_ds02: "OF-2026-0018", tipo: "OF", documentos: [] } },
    { nro: 11, hito: "elevacion_cd", descripcion: null, etapa: "unica", responsable: "GG", fecha_inicio: "2026-09-11",
      fecha_fin: null, plazo_referencial_dh: null, cuenta_plazo: true, estado: "en curso", fila_ds02: 20,
      evidencia: { estado: "declarado, no verificado", referencia: null, codigo_ds02: null, tipo: null, documentos: [] } },
  ],
  relojes: [
    { expediente: "CPI-2026-0004", reloj: "normativo", estado: "vencido", titulo: "Plazo máximo del procedimiento (30 días hábiles)",
      mensaje: "Vencido hace 7 días hábiles. Vence el 2026-09-21.", regla_id: "PLZ-N-CPI", fuente: "RGT (RCD 028-2021-SUNASS-CD), art. 93.8",
      estado_validacion: "por validar", respaldo: "norma_leida", hito: null, etapa: null, fecha_limite: "2026-09-21",
      dias_restantes: -7, documento_inicio: null, documento_estado: "declarado, no verificado: DS02 no registra el documento de la solicitud",
      discrepancia: null, detalle: {} },
    { expediente: "CPI-2026-0004", reloj: "oficio", estado: "cumplido", titulo: "Plazo del oficio: informacion_ep",
      mensaje: "La EP respondió el 2026-08-28.", regla_id: "PLZ-O-INFORMACION-10", fuente: "RGT, art. 93.7",
      estado_validacion: "por validar", respaldo: "norma_leida", hito: "informacion_ep", etapa: "unica",
      fecha_limite: "2026-09-02", dias_restantes: null, documento_inicio: "OF-2026-0018", documento_estado: "verificado en DS02",
      discrepancia: null, detalle: {} },
  ],
  documentos: [
    { id: 7, clave: "x", hito: "elevacion_cd", tipo: "OF", numero: "Oficio de la EPS (demo)", canal: "enlace_externo",
      fecha_emision: null, fecha_recepcion: "2026-09-16", fecha_notificacion: null, naturaleza: "registrado_demo",
      origen: "manual", estado_registro: "propuesto", fuente: null, cita: null, registrado_por: "eps-02", confirmado_por: null },
  ],
  eventos: [],
  proyectos: [{ cod_proyecto: "EPS02-P014", nombre: "Medidores", localidad: "Tingo María", meta_asociada: "MG09", poblacion_beneficiaria: 100 }],
  prechequeo: { ruta: "solo_comunicacion_art_94", titulo: "Solo comunicación (art. 94, numeral 1)", regla_aplicada: "RGT art. 94, numeral 1",
    texto_citado: [{ ubicacion: "RGT art. 94, numeral 1", texto: "En caso el monto total de los incrementos..." }],
    explicacion: "Incrementos del periodo: 0,33 % del programa.", calculos: {}, advertencias: ["El proyecto impulsa la meta MG09: art. 92."],
    faltantes: [], supuestos: ["DS02 no registra la causal."], estado_validacion: "por validar",
    aviso: "Pre-chequeo orientativo: no es una decisión regulatoria." },
  bitacora: [{ id: 1, cuando: "2026-11-12T10:00:00", usuario: "eps-02", rol: "eps", accion: "registrar_documento",
    entidad: "documento", entidad_id: "7", motivo: null, hash: "abcdef1234567890" }],
};

function respuesta(cuerpo: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } }));
}

function montar(usuario: UsuarioDemo) {
  return render(
    <ConSesion sesion={sesionPrueba(usuario.rol === "otras_areas" ? "otras_areas" : "especialista_srt")}>
      <MemoryRouter initialEntries={["/expedientes/CPI-2026-0004"]}>
        <Routes><Route path="/expedientes/:id" element={<ExpedienteVivo usuario={usuario} />} /></Routes>
      </MemoryRouter>
    </ConSesion>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("Expediente vivo", () => {
  it("responde qué requiere acción, qué evidencia falta y por qué importa", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(ficha));
    montar(especialista);
    // ¿Qué requiere acción? El reloj vencido aparece primero, con ícono + texto y su fuente.
    const alertas = await screen.findAllByRole("article");
    expect(alertas[0]).toHaveTextContent("Vencido");
    expect(alertas[0]).toHaveTextContent("RGT (RCD 028-2021-SUNASS-CD), art. 93.8");
    expect(alertas[0]).toHaveTextContent("por validar");
    // ¿Qué evidencia falta? Los hitos sin documento figuran como «declarado, no verificado».
    const linea = screen.getByRole("list", { name: "Línea de tiempo del expediente" });
    expect(within(linea).getAllByText(/declarado, no verificado/)).toHaveLength(2);
    expect(within(linea).getByText(/OF-2026-0018/)).toBeInTheDocument();
    // ¿Por qué importa? Proyecto afectado y advertencia del art. 92.
    expect(screen.getByText(/EPS02-P014/)).toBeInTheDocument();
    expect(screen.getByText(/art. 92/)).toBeInTheDocument();
    // Rótulos de naturaleza del dato.
    expect(screen.getAllByText("Dato sintético").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Estimado").length).toBeGreaterThan(0);
  });

  it("los plazos cerrados quedan en el historial, no en la acción", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(ficha));
    montar(especialista);
    expect(await screen.findByText(/Plazos ya cerrados \(1\)/)).toBeInTheDocument();
  });

  it("confirma un documento propuesto y vuelve a cargar la ficha", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
      String(url).includes("/confirmar") ? respuesta({ estado_registro: "confirmado" }) : respuesta(ficha));
    montar(especialista);
    await userEvent.click(await screen.findByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Documento confirmado."));
    const llamada = f.mock.calls.find(([u]) => String(u).includes("/documentos/7/confirmar"));
    expect((llamada?.[1]?.headers as Record<string, string>)["X-Usuario"]).toBe("esp-srt-01");
  });

  it("registra un documento llegado por correo", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
      String(url).endsWith("/documentos") ? respuesta({ id: 99 }, 201) : respuesta(ficha));
    montar(especialista);
    const form = await screen.findByRole("form", { name: "Registrar un documento" });
    await userEvent.type(within(form).getByLabelText("Número o descripción"), "Correo de la EP");
    await userEvent.type(within(form).getByLabelText("Fecha de recepción"), "2026-09-15");
    await userEvent.click(within(form).getByRole("button", { name: "Registrar documento" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Documento registrado"));
    const [, init] = f.mock.calls.find(([u]) => String(u).endsWith("/documentos"))!;
    expect(JSON.parse(String(init?.body))).toMatchObject({ tipo: "OF", canal: "correo", numero: "Correo de la EP" });
  });

  it("muestra el error de la API sin ocultarlo", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
      String(url).includes("/confirmar")
        ? respuesta({ detail: "El rol eps no tiene el permiso «confirmar_registro»." }, 403)
        : respuesta(ficha));
    montar(especialista);
    await userEvent.click(await screen.findByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("no tiene el permiso"));
  });

  it("un usuario de solo lectura no ve botones de confirmar ni puede registrar", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta(ficha));
    montar(lectura);
    await screen.findAllByRole("article");
    expect(screen.queryByRole("button", { name: "Confirmar" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar documento" })).toBeDisabled();
  });

  it("informa si el expediente no existe", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta({ detail: "No existe el expediente X." }, 404));
    montar(especialista);
    expect(await screen.findByText(/No existe el expediente X/)).toBeInTheDocument();
  });
});

describe("Lista de expedientes", () => {
  it("filtra por tipo y rotula la naturaleza", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respuesta([
      { id_expediente: "REAL-TACNA-2026", cod_eps: null, empresa: "EPS TACNA S.A.", tipo_procedimiento: "cambio_programa_inversiones",
        estado: "concluido", fecha_inicio: "2026-07-17", hito_actual: null, responsable_actual: null, naturaleza: "real" },
      { id_expediente: "RP-2026-0001", cod_eps: "EPS03", tipo_procedimiento: "revision_periodica", estado: "en_tramite",
        fecha_inicio: "2026-01-02", hito_actual: "x", responsable_actual: "SRT", naturaleza: "sintético" },
    ]));
    render(<ConSesion sesion={sesionPrueba()}><MemoryRouter><ListaExpedientes /></MemoryRouter></ConSesion>);
    expect(await screen.findByText("REAL-TACNA-2026")).toBeInTheDocument();
    expect(screen.getByText("Dato real")).toBeInTheDocument();
    expect(screen.queryByText("RP-2026-0001")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole("combobox"), "");
    expect(screen.getByText("RP-2026-0001")).toBeInTheDocument();
  });
});
