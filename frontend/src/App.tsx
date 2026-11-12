import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { api, type UsuarioDemo } from "./api";
import { DetalleProyecto, TableroRutaDelDinero } from "./dinero";
import { ExpedienteVivo, ListaExpedientes } from "./paginas";

export default function App() {
  const [usuarios, setUsuarios] = useState<UsuarioDemo[]>([]);
  const [usuarioId, setUsuarioId] = useState<string>("esp-srt-01");
  useEffect(() => {
    api.usuarios().then(setUsuarios).catch(() => setUsuarios([]));
  }, []);
  const usuario = usuarios.find((u) => u.id === usuarioId) ?? null;
  return (
    <>
      <header className="encabezado">
        <div className="pagina">
          <Link to="/">YakuTraza</Link>
          <nav aria-label="Secciones">
            <Link to="/">Expedientes</Link>{" · "}<Link to="/ruta-del-dinero">Ruta del dinero</Link>
          </nav>
          <span className="corte">Prototipo · datos de muestra (DS01–DS08 sintéticos)</span>
          <label>
            Usuario de demostración (ficticio):
            <select value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)} aria-label="Usuario de demostración">
              {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre}</option>)}
            </select>
          </label>
        </div>
      </header>
      <main className="pagina">
        <Routes>
          <Route path="/" element={<ListaExpedientes />} />
          <Route path="/expedientes/:id" element={<ExpedienteVivo usuario={usuario} />} />
          <Route path="/ruta-del-dinero" element={<TableroRutaDelDinero />} />
          <Route path="/proyectos/:cod" element={<DetalleProyecto />} />
        </Routes>
        <footer className="pie">
          Ninguna salida es una decisión regulatoria: las decisiones son de Sunass. Las reglas de plazo están «por validar».
          Código abierto (MIT).
        </footer>
      </main>
    </>
  );
}
