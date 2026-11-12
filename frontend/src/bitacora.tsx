import { useEffect, useState } from "react";
import { pedir, type EntradaBitacora } from "./api";
import { Bitacora } from "./componentes";
import { useSesion } from "./sesion";

// Bitácora global (solo Sunass): cada cambio con quién, cuándo y por qué; cada entrada encadena el hash de la anterior.
export function PaginaBitacora() {
  const { usuario } = useSesion();
  const [entradas, setEntradas] = useState<EntradaBitacora[] | null>(null);
  const [integra, setIntegra] = useState<{ integra: boolean; entradas?: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    pedir<EntradaBitacora[]>("/bitacora").then((xs) => setEntradas([...xs].reverse())).catch((e) => setError(e.message));
    pedir<{ integra: boolean; entradas?: number }>("/bitacora/verificacion").then(setIntegra).catch(() => setIntegra(null));
  }, [usuario.id]);
  if (error) return <p className="mensaje mensaje-error" role="alert">No se pudo leer la bitácora: {error}</p>;
  if (!entradas) return <p className="cargando">Cargando la bitácora…</p>;
  return (
    <>
      <h1>Bitácora de cambios</h1>
      <p className="sub">Solo se agregan entradas: nadie puede modificarlas ni borrarlas. Cada una encadena el hash de la anterior.</p>
      {integra && (
        <p className={`mensaje ${integra.integra ? "mensaje-ok" : "mensaje-error"}`} role="status">
          {integra.integra ? "✓ La cadena de hashes está íntegra." : "✗ La cadena de hashes no coincide: revise la bitácora."}
        </p>
      )}
      <section className="tarjeta"><Bitacora entradas={entradas} /></section>
    </>
  );
}
