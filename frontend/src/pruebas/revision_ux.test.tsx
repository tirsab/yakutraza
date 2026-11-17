// Revisión de UX: datasets legibles, resúmenes cortos, montos abreviados, íconos accesibles y cuellos en lenguaje claro.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { corto, resumenFaltante } from "../bandeja";
import { deTotal, solesCorto } from "../dinero";
import { datasetsLegibles, humanizar } from "../etiquetas";
import { Icono } from "../iconos";
import { fraseCuello } from "../tablero";

describe("Fuentes con datasets legibles", () => {
  it("cambia el nombre del archivo por el nombre del dataset", () => {
    expect(datasetsLegibles("DS05 ds05_fondo_inversiones_reservas, fila 12"))
      .toBe("DS05 · Fondo de inversiones y reservas, fila 12");
    expect(datasetsLegibles("DS02 ds02_hitos_procedimientos (sintético)")).toBe("DS02 · Hitos de los procedimientos (sintético)");
    expect(datasetsLegibles("DS02 fila 3 (sintético)")).toBe("DS02 · Procedimientos, fila 3 (sintético)");
    expect(datasetsLegibles("DS03 filas 4, 5; DS04 fila 9"))
      .toBe("DS03 · Programa de inversiones, filas 4, 5; DS04 · Ejecución de inversiones, fila 9");
    expect(datasetsLegibles("DS02, DS03 y DS05 (sintéticos)")).toBe("DS02, DS03 y DS05 (sintéticos)");
    expect(humanizar("DS05 ds05_fondo_inversiones_reservas, fila 12")).not.toMatch(/ds05_/);
  });
});

describe("Bandeja", () => {
  it("título corto de la próxima acción", () => {
    expect(corto("Hacer seguimiento: está en Gerencia General (GG).")).toBe("Hacer seguimiento");
    expect(corto("Elevar al Consejo Directivo.")).toBe("Elevar al Consejo Directivo");
  });

  it("«¿Qué falta?» como resumen", () => {
    const sin = { tipo: "sin_documento" };
    expect(resumenFaltante(Array(10).fill(sin))).toBe("10 hitos sin documento");
    expect(resumenFaltante([sin, { tipo: "por_confirmar" }, { tipo: "por_confirmar" }])).toBe("1 hito sin documento · 2 por confirmar");
    expect(resumenFaltante([])).toBe("No falta evidencia registrada.");
  });
});

describe("Montos abreviados", () => {
  it("millones y miles con coma decimal, y el porcentaje", () => {
    expect(solesCorto(110_300_000)).toBe("S/ 110,3 M");
    expect(solesCorto(217_313.2)).toBe("S/ 217,3 mil");
    expect(solesCorto(950)).toBe("S/ 950,00");
    expect(deTotal(110_300_000, 135_600_000)).toBe("S/ 110,3 M de 135,6 M · 81 %");
  });
});

describe("Cuellos de botella en lenguaje claro", () => {
  it("sin «mediana», «P90» ni códigos", () => {
    const f = fraseCuello("Elevación al Consejo", { mediana_dh: 12, p90_dh: 25, en_curso: 3 });
    expect(f).toBe("Elevación al Consejo: suele tardar 12 días hábiles; 1 de cada 10 casos pasa de 25. 3 en curso ahora.");
    expect(fraseCuello("Derivación", { mediana_dh: 1, p90_dh: 1, en_curso: 0 })).toBe("Derivación: suele tardar 1 día hábil.");
  });
});

describe("Íconos SVG", () => {
  it("decorativos por defecto y con nombre accesible cuando lo tienen", () => {
    const { container } = render(<><Icono nombre="reloj" /><Icono nombre="info" titulo="Ver la fuente" /></>);
    expect(container.querySelectorAll("svg[aria-hidden='true']")).toHaveLength(1);
    expect(screen.getByRole("img", { name: "Ver la fuente" })).toBeInTheDocument();
  });
});
