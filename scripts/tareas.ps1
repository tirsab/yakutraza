<#
.SYNOPSIS
  Equivalente de `make` para Windows (PowerShell 5.1 o superior).

.DESCRIPTION
  Tareas locales (sin Docker), usan backend\.venv:
    instalar   Crea backend\.venv e instala dependencias (Python 3.12 o 3.13).
    seed       Carga DS01-DS09, corre el control de calidad y genera el reporte HTML.
    calidad    Vuelve a correr el control de calidad sobre la última carga.
    reporte    Regenera reportes\calidad.html desde la base de datos.
    test       Corre pytest.
    cobertura  Corre pytest con cobertura de calidad, ingesta y plazos.
    api        Levanta la API en http://localhost:8000 (documentación en /docs).

  Tareas con Docker (equivalen a las del Makefile):
    up, down, docker-seed, docker-test

  Lee las variables de .env (DATA_DIR, FECHA_CORTE, DATABASE_URL) si existe.

.EXAMPLE
  .\scripts\tareas.ps1 instalar
  .\scripts\tareas.ps1 seed
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet('instalar', 'seed', 'calidad', 'reporte', 'test', 'cobertura', 'api', 'up', 'down', 'docker-seed', 'docker-test', 'ayuda')]
  [string]$Tarea = 'ayuda'
)

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Raiz 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

function Cargar-Env {
  $archivo = Join-Path $Raiz '.env'
  if (Test-Path $archivo) {
    foreach ($linea in Get-Content $archivo) {
      if ($linea -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
      }
    }
  }
  if (-not $env:DATABASE_URL) {
    # Sin Docker ni .env: SQLite local para desarrollo y pruebas.
    $env:DATABASE_URL = 'sqlite:///' + ((Join-Path $Raiz 'yakutraza_local.db') -replace '\\', '/')
  }
  if (-not $env:REPORTES_DIR) { $env:REPORTES_DIR = Join-Path $Raiz 'reportes' }
}

function Exigir-Venv {
  if (-not (Test-Path $Python)) { throw 'No existe backend\.venv. Ejecuta primero: .\scripts\tareas.ps1 instalar' }
}

function Py([string[]]$argumentos) {
  Exigir-Venv
  Push-Location $Backend
  try {
    & $Python @argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falló: python $($argumentos -join ' ')" }
  } finally { Pop-Location }
}

switch ($Tarea) {
  'instalar' {
    Push-Location $Backend
    try {
      $lanzador = Get-Command py -ErrorAction SilentlyContinue
      if ($lanzador) { & py -3.12 -m venv .venv 2>$null; if ($LASTEXITCODE -ne 0) { & py -3.13 -m venv .venv } }
      else { & python -m venv .venv }
      & $Python -m pip install --upgrade pip
      & $Python -m pip install -e '.[dev]'
    } finally { Pop-Location }
  }
  'seed'      { Cargar-Env; Py @('-m', 'app.cli', 'seed') }
  'calidad'   { Cargar-Env; Py @('-m', 'app.cli', 'calidad') }
  'reporte'   { Cargar-Env; Py @('-m', 'app.cli', 'reporte') }
  'test'      { Cargar-Env; Py @('-m', 'pytest', '-q') }
  'cobertura' { Cargar-Env; Py @('-m', 'pytest', '-q', '--cov=app.calidad', '--cov=app.ingesta', '--cov=app.plazos', '--cov-report=term-missing') }
  'api'       { Cargar-Env; Py @('-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000') }
  'up'          { docker compose up -d --build db api }
  'down'        { docker compose down }
  'docker-seed' { docker compose up -d --build db api; docker compose run --rm api python -m app.cli seed }
  'docker-test' { docker compose run --rm api python -m pytest -q }
  default { Get-Help $PSCommandPath -Detailed }
}
