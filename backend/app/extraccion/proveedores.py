"""Proveedores del modelo de lenguaje. Solo reciben texto YA anonimizado.

- ollama: modelo local (por defecto qwen3.5:4b) en http://localhost:11434 (desde Docker,
  http://host.docker.internal:11434). Nada sale de la computadora.
- anthropic: API de Anthropic (por defecto claude-opus-5-5), alternativa si el modelo local es lento.
  La clave la pone el equipo en .env (ANTHROPIC_API_KEY); el prototipo nunca la pide ni la guarda.
- ninguno: extracción desactivada.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx


class ErrorProveedor(RuntimeError):
    pass


class Proveedor(Protocol):
    nombre: str
    modelo: str

    def extraer(self, sistema: str, usuario: str, esquema: dict[str, Any]) -> dict[str, Any]: ...


class Ollama:
    nombre = "ollama"

    def __init__(self, url: str, modelo: str, timeout: float = 600.0, cliente: httpx.Client | None = None):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.cliente = cliente or httpx.Client(timeout=timeout)

    def extraer(self, sistema: str, usuario: str, esquema: dict[str, Any]) -> dict[str, Any]:
        cuerpo = {
            "model": self.modelo, "stream": False, "format": esquema, "think": False,
            "options": {"temperature": 0},
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        }
        try:
            r = self.cliente.post(f"{self.url}/api/chat", json=cuerpo)
        except httpx.HTTPError as e:
            raise ErrorProveedor(f"No se pudo conectar con Ollama en {self.url}. ¿Está instalado y abierto? ({e})") from e
        if r.status_code == 404:
            raise ErrorProveedor(f"Ollama no tiene el modelo {self.modelo}. Ejecute: ollama pull {self.modelo}")
        if r.status_code >= 400:
            raise ErrorProveedor(f"Ollama respondió {r.status_code}: {r.text[:200]}")
        contenido = r.json().get("message", {}).get("content", "")
        try:
            return json.loads(contenido)
        except json.JSONDecodeError as e:
            raise ErrorProveedor("El modelo local no devolvió un JSON válido.") from e


class Anthropic:
    nombre = "anthropic"

    def __init__(self, modelo: str, cliente: Any = None):
        import anthropic  # importación diferida: solo si se elige este proveedor
        self.modelo = modelo
        self._sdk = anthropic
        self.cliente = cliente or anthropic.Anthropic()

    def extraer(self, sistema: str, usuario: str, esquema: dict[str, Any]) -> dict[str, Any]:
        a = self._sdk
        try:
            r = self.cliente.messages.create(
                model=self.modelo, max_tokens=16000, system=sistema,
                messages=[{"role": "user", "content": usuario}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": esquema}},
            )
        except a.AuthenticationError as e:
            raise ErrorProveedor("La API de Anthropic rechazó la clave: revise ANTHROPIC_API_KEY en .env.") from e
        except a.RateLimitError as e:
            raise ErrorProveedor("La API de Anthropic pidió esperar (límite de uso). Intente en un minuto.") from e
        except a.APIStatusError as e:
            raise ErrorProveedor(f"La API de Anthropic respondió {e.status_code}.") from e
        except a.APIConnectionError as e:
            raise ErrorProveedor("No se pudo conectar con la API de Anthropic.") from e
        if r.stop_reason == "refusal":
            raise ErrorProveedor("El modelo declinó procesar este texto.")
        texto = next((b.text for b in r.content if b.type == "text"), "")
        try:
            return json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErrorProveedor("La API no devolvió un JSON válido.") from e


def crear(nombre: str, *, ollama_url: str, ollama_modelo: str, anthropic_modelo: str) -> Proveedor | None:
    if nombre == "ollama":
        return Ollama(ollama_url, ollama_modelo)
    if nombre == "anthropic":
        return Anthropic(anthropic_modelo)
    return None
