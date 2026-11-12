.PHONY: setup up down logs test migrate discover track score demo
setup:
	@test -f .env || cp .env.example .env
up: setup
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f --tail=100
migrate:
	docker compose run --rm migrate
discover:
	docker compose exec worker python -m app.workers.cli discover
track:
	docker compose exec worker python -m app.workers.cli track
score:
	docker compose exec worker python -m app.workers.cli score
demo:
	docker compose exec worker python -m app.workers.cli demo
test:
	cd apps/api && uv run pytest
	cd apps/web && npm run test && npm run typecheck
recover:
	docker compose exec worker python -m app.workers.cli recover
