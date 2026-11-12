import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { humanizar, t } from "./etiquetas";

// ---------------------------------------------------------------- movimiento
/** true si la persona pidió reducir el movimiento (prefers-reduced-motion). */
export function movimientoReducido(): boolean {
  try {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  } catch {
    return false;
  }
}

/** Desplazamiento suave, salvo que la persona haya pedido reducir el movimiento. */
export function irA(el: Element | null | undefined) {
  el?.scrollIntoView?.({ behavior: movimientoReducido() ? "auto" : "smooth", block: "start" });
}

// ---------------------------------------------------------------- píldoras
const ICONO: Record<string, string> = {
  vencido: "⛔", por_vencer: "⚠", en_plazo: "◷", no_calculable: "?", cumplido: "✓", incumplido: "✗", pausa: "⏸",
};

export function Pildora({ tono, icono, children }: { tono: string; icono?: string; children: ReactNode }) {
  return (
    <span className={`pildora pil-${tono}`}>
      {icono && <span aria-hidden="true">{icono}</span>}
      {children}
    </span>
  );
}

/** Píldora del plazo: «Vencido 4 DH», «5 DH», «En pausa», «No puedo calcular». Ícono + texto, nunca solo color. */
export function PildoraPlazo({ estado, dias, enPausa }: { estado: string; dias?: number | null; enPausa?: boolean }) {
  if (enPausa && estado !== "vencido") return <Pildora tono="pausa" icono={ICONO.pausa}>En pausa</Pildora>;
  if (estado === "no_calculable") return <Pildora tono="no_calculable" icono={ICONO.no_calculable}>No puedo calcular</Pildora>;
  if (estado === "vencido") {
    return <Pildora tono="vencido" icono={ICONO.vencido}>Vencido{dias != null ? ` ${Math.abs(dias)} DH` : ""}</Pildora>;
  }
  if (dias == null) return <Pildora tono={estado} icono={ICONO[estado]}>{t("estado_reloj", estado)}</Pildora>;
  return <Pildora tono={estado} icono={ICONO[estado]}>{dias === 0 ? "Vence hoy" : `${dias} DH`}</Pildora>;
}

// ---------------------------------------------------------------- chip de fuente
const NORMAS: { patron: RegExp; enlace: string; nombre: string }[] = [
  { patron: /028-2026/, enlace: "https://busquedas.elperuano.pe/dispositivo/NL/2538837-1", nombre: "RCD 028-2026-SUNASS-CD (El Peruano)" },
  { patron: /124-2025/, enlace: "https://www.gob.pe/institucion/sunass/normas-legales/7325221-124-2025-sunass-cd", nombre: "RCD 124-2025-SUNASS-CD" },
  { patron: /\bTUO\b|27444/, enlace: "https://cdn.www.gob.pe/uploads/document/file/5320370/4770872-decreto-supremo-n-004-2019-jus.pdf", nombre: "TUO de la Ley 27444 (DS 004-2019-JUS)" },
  { patron: /\bRGT\b|028-2021/, enlace: "https://cdn.www.gob.pe/uploads/document/file/4388328/", nombre: "Compendio del RGT (RCD 028-2021-SUNASS-CD)" },
];

/** Chip con la fuente de un dato. Al abrirlo muestra el texto completo y, si es una norma, el enlace oficial. */
export function ChipFuente({ texto, etiqueta, detalle, enlace }: {
  texto: string | null | undefined; etiqueta?: string; detalle?: ReactNode; enlace?: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const id = useId();
  const caja = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);
  if (!texto) return null;
  const legible = humanizar(texto);
  const norma = NORMAS.find((n) => n.patron.test(texto));
  const destino = enlace ?? norma?.enlace;
  const corto = etiqueta ?? (legible.length > 34 ? `${legible.slice(0, 32)}…` : legible);
  return (
    <span className="chip-envoltura" ref={caja} onKeyDown={(e) => { if (e.key === "Escape") setAbierto(false); }}>
      <button type="button" className="chip-fuente" aria-expanded={abierto} aria-controls={id}
              aria-label={`Fuente: ${legible}`} onClick={() => setAbierto(!abierto)}>
        <span aria-hidden="true">§</span> {corto}
      </button>
      {abierto && (
        <span className="chip-pop" id={id} role="note">
          <strong>Fuente</strong><br />{legible}
          {detalle && <><br />{detalle}</>}
          {destino && <><br /><a href={destino} target="_blank" rel="noreferrer">Abrir {norma && !enlace ? norma.nombre : "la fuente"} ↗</a></>}
          {/\bDS0\d/.test(texto) && <><br /><span className="detalle">Muestra sintética del Hackathon Sunass.</span></>}
        </span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------- avatar
export function iniciales(nombre: string): string {
  const limpio = nombre.replace(/\(.*?\)/g, "").trim();
  const num = limpio.match(/(\d+)\s*$/);
  const palabras = limpio.replace(/\d+\s*$/, "").split(/\s+/).filter((p) => p.length > 2 || /^[A-Z]{2,}$/.test(p));
  const letras = palabras.slice(0, 2).map((p) => p[0].toUpperCase()).join("");
  return (letras + (num ? num[1] : "")).slice(0, 3) || "?";
}

export function Avatar({ nombre, claro }: { nombre: string; claro?: boolean }) {
  return <span className={`avatar${claro ? " claro" : ""}`} aria-hidden="true">{iniciales(nombre)}</span>;
}

// ---------------------------------------------------------------- barra de pasos
export interface Pasos { pasos: { clave: string; nombre: string }[]; actual: number; n: number; terminado: boolean }

export function BarraPasos({ p, detenido, compacto, titulo }: { p: Pasos | null | undefined; detenido?: boolean; compacto?: boolean; titulo?: string }) {
  if (!p) return null;
  const clases = ["pasos", p.terminado ? "terminado" : "", detenido ? "detenido" : "", compacto ? "compacto" : ""].join(" ");
  return (
    <ol className={clases} aria-label={titulo ?? `Paso ${p.actual + 1} de ${p.n}: ${p.pasos[p.actual]?.nombre}`}>
      {p.pasos.map((x, i) => (
        <li key={x.clave} className={p.terminado || i < p.actual ? "hecho" : i === p.actual ? "actual" : ""}
            aria-current={!p.terminado && i === p.actual ? "step" : undefined}>
          {x.nombre}
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------- toasts
interface Toast { id: number; texto: string; error?: boolean }
const ContextoToast = createContext<(texto: string, error?: boolean) => void>(() => {});

export function useToast() {
  return useContext(ContextoToast);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const mostrar = useCallback((texto: string, error?: boolean) => {
    const id = Date.now() + Math.random();
    setToasts((xs) => [...xs, { id, texto, error }]);
    setTimeout(() => setToasts((xs) => xs.filter((x) => x.id !== id)), 4500);
  }, []);
  return (
    <ContextoToast.Provider value={mostrar}>
      {children}
      <div aria-live="polite" role="status" className="oculto-si-vacio">
        {toasts.map((x) => <div key={x.id} className={`toast${x.error ? " error" : ""}`}>{x.texto}</div>)}
      </div>
    </ContextoToast.Provider>
  );
}

// ---------------------------------------------------------------- diálogo
export function Dialogo({ titulo, children, onCerrar }: { titulo: string; children: ReactNode; onCerrar: () => void }) {
  const id = useId();
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previo = document.activeElement as HTMLElement | null;
    caja.current?.querySelector<HTMLElement>("input, select, textarea, button")?.focus();
    return () => previo?.focus?.();
  }, []);
  return (
    <div className="dialogo" onKeyDown={(e) => { if (e.key === "Escape") onCerrar(); }}>
      <div role="dialog" aria-modal="true" aria-labelledby={id} ref={caja}>
        <h2 id={id} style={{ marginTop: 0 }}>{titulo}</h2>
        {children}
      </div>
    </div>
  );
}
