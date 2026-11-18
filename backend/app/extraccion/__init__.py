"""Fase 6: extracción asistida de documentos con IA.

Flujo: texto del PDF → limpieza → anonimización → modelo (Ollama local o Anthropic) → validación de citas.
Nada entra al expediente hasta que una persona lo confirma. El texto de los oficios vive solo en DATA_DIR.
"""
