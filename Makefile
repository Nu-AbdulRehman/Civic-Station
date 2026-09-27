# Thin wrappers over the documented Compose commands (README "Quickstart").
.PHONY: up down pull-models

up:
	test -f .env || cp .env.example .env
	docker compose up -d --build --wait

down:
	docker compose down

# One-time: fetch Ollama weights into the ollama_models volume over egress (AD-046, T-M6-010).
pull-models:
	docker compose --profile pull run --rm ollama-pull
