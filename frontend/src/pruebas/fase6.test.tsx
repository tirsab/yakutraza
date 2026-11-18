// Fase 6: «Leer un documento con IA». Texto sintético; nada entra al expediente sin confirmación.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LeerConIA } from "../extraccion";
import { respuesta } from "./sesion";

const ESTADO = { proveedor: "ollama", modelo: "qwen3.5:4b", disponible: true, detalle: "Ollama listo.", parte_privada: true,
  lista_privada: true };
const RESULTADO = {
  alias: "TACNA-02", proveedor: "ollama", modelo: "qwen3.5:4b", segundos: 42.5, reemplazos: {}, aviso: "Propuesto por IA: nada entra al expediente hasta que una persona lo confirme.",
  campos: {
    numero_documento: { valor: "OFICIO N.° 999-2099-PRUEBA", cita: "OFICIO N.° 999-2099-PRUEBA", pagina: 1 },
    fecha: { valor: "2099-08-14", cita: "14 de agosto de 2099", pagina: 1 },
    remitente: null,
    plazo: { dias_habiles: 2, tipo: "prorroga", cita: "prórroga de dos (2) días hábiles", pagina: 1 },
    requerimientos: [],
  },
  descartados: [{ campo: "remitente", motivo: "la cita no aparece literalmente en la página 1" }],
};

function api(estado = ESTADO) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((url, init) => {
    const u = String(url);
    if (u.endsWith("/extraccion/estado")) return respuesta(estado);
    if (u.includes("/extraccion/documentos?")) return respuesta([{ alias: "TACNA-02", id_expediente: "REAL-TACNA-2026", huella: "abc", procesado: false }]);
    if (u.endsWith("/confirmar")) return respuesta({ documento_id: 1, evento_id: 2, corregidos: JSON.parse(String(init?.body)).motivo_correccion ? ["plazo"] : [] }, 201);
    if (u.endsWith("/extraccion/documentos/TACNA-02") && init?.method === "POST") return respuesta(RESULTADO);
    return respuesta({ detail: "no encontrado" }, 404);
  });
}

function montar() {
  const onConfirmado = vi.fn();
  const onError = vi.fn();
  render(<LeerConIA idExpediente="REAL-TACNA-2026" hitos={["solicitud", "informacion_ep"]} usuarioId="coord-srt-01"
                    onConfirmado={onConfirmado} onError={onError} />);
  return { onConfirmado, onError };
}

afterEach(() => vi.restoreAllMocks());

describe("Leer un documento con IA", () => {
  it("propone cada dato con su cita y su página, y descarta lo que no se valida", async () => {
    api();
    montar();
    const tarjeta = await screen.findByRole("region", { name: "Leer un documento con IA" });
    expect(within(tarjeta).getByRole("combobox", { name: "Documento del caso" })).toHaveValue("TACNA-02");
    expect(tarjeta.textContent).not.toMatch(/\.pdf/);
    await userEvent.click(within(tarjeta).getByRole("button", { name: "Leer con IA" }));
    expect(await within(tarjeta).findByText("Propuesto por IA")).toBeInTheDocument();
    expect(within(tarjeta).getByLabelText("Número del documento")).toHaveValue("OFICIO N.° 999-2099-PRUEBA");
    expect(within(tarjeta).getByLabelText("Plazo en días hábiles")).toHaveValue(2);
    expect(within(tarjeta).getByText("«prórroga de dos (2) días hábiles»", { exact: false })).toBeInTheDocument();
    expect(within(tarjeta).getAllByRole("button", { name: /Fuente: TACNA-02, pág\. 1/ }).length).toBeGreaterThan(0);
    expect(tarjeta).toHaveTextContent("Descartados por la validación: Remitente");
    expect(within(tarjeta).getByLabelText("Hito del expediente")).toHaveValue("informacion_ep");
  });

  it("confirmar sin cambios; corregir exige motivo", async () => {
    const f = api();
    const { onConfirmado } = montar();
    const tarjeta = await screen.findByRole("region", { name: "Leer un documento con IA" });
    await userEvent.click(within(tarjeta).getByRole("button", { name: "Leer con IA" }));
    const plazo = await within(tarjeta).findByLabelText("Plazo en días hábiles");
    await userEvent.clear(plazo);
    await userEvent.type(plazo, "3");
    const boton = within(tarjeta).getByRole("button", { name: "Corregir y confirmar" });
    expect(boton).toBeDisabled();
    await userEvent.type(within(tarjeta).getByLabelText(/Motivo de la corrección/), "El oficio dice tres días.");
    expect(boton).toBeEnabled();
    await userEvent.click(boton);
    const pedido = f.mock.calls.find(([u]) => String(u).endsWith("/confirmar"))!;
    const cuerpo = JSON.parse(String(pedido[1]!.body));
    expect(cuerpo.plazo).toEqual({ dias_habiles: 3, tipo: "prorroga" });
    expect(cuerpo.motivo_correccion).toBe("El oficio dice tres días.");
    expect(onConfirmado).toHaveBeenCalledWith(expect.stringMatching(/con correcciones/));
  });

  it("sin el modelo disponible, explica qué falta y no deja leer", async () => {
    api({ ...ESTADO, disponible: false, detalle: "Ollama no responde en http://localhost:11434. ¿Está instalado y abierto?" });
    montar();
    const tarjeta = await screen.findByRole("region", { name: "Leer un documento con IA" });
    expect(tarjeta).toHaveTextContent("¿Está instalado y abierto?");
    expect(within(tarjeta).getByRole("button", { name: "Leer con IA" })).toBeDisabled();
  });
});
