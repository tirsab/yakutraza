# Tareas con Docker. En Windows sin `make`, usa: .\scripts\tareas.ps1 <tarea>
.PHONY: up down seed calidad reporte test cobertura logs

up:
	docker compose up -d --build db api

down:
	docker compose down

seed: up
	docker compose run --rm api python -m app.cli seed

calidad:
	docker compose run --rm api python -m app.cli calidad

reporte:
	docker compose run --rm api python -m app.cli reporte

test:
	docker compose run --rm api python -m pytest -q

cobertura:
	docker compose run --rm api python -m pytest -q --cov=app.calidad --cov=app.ingesta --cov-report=term-missing

logs:
	docker compose logs -f api
