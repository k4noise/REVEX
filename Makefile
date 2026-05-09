.DEFAULT_GOAL := help

DC ?= docker compose
COMPOSE_FILE ?= docker-compose.yml
KEYS_DIR ?= config/keys
PORT ?= 3162

.PHONY: help prepare init-dirs init-config init-env gen-keys \
        build rebuild up up-with-redis down restart ps logs backend-logs worker-logs nginx-logs redis-logs \
        migrate shell-backend shell-worker check-port doctor redis-check

help:
	@echo "Доступные команды:"
	@echo "  make prepare             - подготовить проект (.env, config, ключи, директории)"
	@echo "  make build               - собрать все образы"
	@echo "  make rebuild             - пересобрать образы без кеша"
	@echo "  make up                  - поднять сервисы без локального redis"
	@echo "  make up-with-redis       - поднять сервисы со встроенным redis-контейнером"
	@echo "  make down                - остановить и удалить контейнеры"
	@echo "  make restart             - перезапустить backend и worker"
	@echo "  make ps                  - показать состояние контейнеров"
	@echo "  make logs                - показать логи всех сервисов"
	@echo "  make backend-logs        - показать логи backend"
	@echo "  make worker-logs         - показать логи worker"
	@echo "  make nginx-logs          - показать логи nginx"
	@echo "  make redis-logs          - показать логи redis"
	@echo "  make migrate             - выполнить alembic upgrade head внутри backend"
	@echo "  make shell-backend       - открыть shell внутри backend-контейнера"
	@echo "  make shell-worker        - открыть shell внутри worker-контейнера"
	@echo "  make check-port          - проверить, свободен ли порт $(PORT) на хосте"
	@echo "  make redis-check         - проверить доступность redis/valkey на хосте"
	@echo "  make doctor              - выполнить базовую проверку конфигурации"
	@echo ""
	@echo "Параметры:"
	@echo "  KEYS_DIR=<path>          - путь к директории ключей (по умолчанию: config/keys)"
	@echo "  PORT=<number>            - внешний порт nginx (по умолчанию: 3162)"
	@echo "  COMPOSE_FILE=<file>      - путь к compose-файлу (по умолчанию: docker-compose.yml)"

init-dirs:
	@mkdir -p logs
	@mkdir -p $(KEYS_DIR)

init-config:
	@if [ ! -f config/lti_config.json ]; then \
		if [ -f config/lti_config.json.example ]; then \
			cp config/lti_config.json.example config/lti_config.json; \
			echo "Создан config/lti_config.json из config/lti_config.json.example"; \
		else \
			echo "Внимание: config/lti_config.json.example не найден. Создайте config/lti_config.json вручную."; \
		fi \
	else \
		echo "config/lti_config.json уже существует."; \
	fi

init-env:
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "Создан .env из .env.example. Проверьте и отредактируйте переменные."; \
		else \
			echo "Внимание: .env.example не найден. Создайте .env вручную."; \
		fi \
	else \
		echo ".env уже существует."; \
	fi

gen-keys:
	@echo "Проверяю JWT ключи в $(KEYS_DIR)..."
	@if [ ! -f "$(KEYS_DIR)/jwtRS256.key" ]; then \
		ssh-keygen -t rsa -b 4096 -m PEM -f "$(KEYS_DIR)/jwtRS256.key" -N "" >/dev/null 2>&1 && \
		echo "Создан приватный ключ: $(KEYS_DIR)/jwtRS256.key"; \
	else \
		echo "Приватный ключ уже существует: $(KEYS_DIR)/jwtRS256.key"; \
	fi
	@if [ ! -f "$(KEYS_DIR)/jwtRS256.key.pub" ]; then \
		openssl rsa -in "$(KEYS_DIR)/jwtRS256.key" -pubout -outform PEM -out "$(KEYS_DIR)/jwtRS256.key.pub" >/dev/null 2>&1 && \
		echo "Создан публичный ключ: $(KEYS_DIR)/jwtRS256.key.pub"; \
	else \
		echo "Публичный ключ уже существует: $(KEYS_DIR)/jwtRS256.key.pub"; \
	fi

prepare: init-dirs init-config init-env gen-keys
	@echo ""
	@echo "Подготовка завершена."
	@echo "Проверьте .env, особенно:"
	@echo "  JWT_SECRET_KEY"
	@echo "  DATABASE_URL"
	@echo "  REDIS_URL"
	@echo "  FRONTEND_URL"
	@echo "  PUBLIC_BACKEND_URL"
	@echo "  LLM_BASE_URL / LLM_API_KEY / LLM_MODEL"
	@echo ""
	@echo "Варианты REDIS_URL:"
	@echo "  Хостовый Redis/Valkey: REDIS_URL=redis://host.docker.internal:6379/0"
	@echo "  Контейнерный Redis:    REDIS_URL=redis://redis:6379/0"
	@echo ""
	@echo "Если нужен встроенный redis-контейнер — запускайте make up-with-redis"

build:
	$(DC) -f $(COMPOSE_FILE) build

rebuild:
	$(DC) -f $(COMPOSE_FILE) build --no-cache

up:
	$(DC) -f $(COMPOSE_FILE) up -d

up-with-redis:
	$(DC) -f $(COMPOSE_FILE) --profile local-redis up -d

down:
	$(DC) -f $(COMPOSE_FILE) down

restart:
	$(DC) -f $(COMPOSE_FILE) restart backend worker

ps:
	$(DC) -f $(COMPOSE_FILE) ps

logs:
	$(DC) -f $(COMPOSE_FILE) logs -f

backend-logs:
	$(DC) -f $(COMPOSE_FILE) logs -f backend

worker-logs:
	$(DC) -f $(COMPOSE_FILE) logs -f worker

nginx-logs:
	$(DC) -f $(COMPOSE_FILE) logs -f nginx

redis-logs:
	$(DC) -f $(COMPOSE_FILE) logs -f redis

migrate:
	$(DC) -f $(COMPOSE_FILE) exec -T backend uv run alembic upgrade head

shell-backend:
	$(DC) -f $(COMPOSE_FILE) exec backend sh

shell-worker:
	$(DC) -f $(COMPOSE_FILE) exec worker sh

check-port:
	@echo "Проверяю, свободен ли порт $(PORT) на хосте..."
	@if command -v ss >/dev/null 2>&1; then \
		if ss -tulpn | grep -q ":$(PORT) "; then \
			echo "Порт $(PORT) уже занят."; \
		else \
			echo "Порт $(PORT) свободен."; \
		fi \
	elif command -v netstat >/dev/null 2>&1; then \
		if netstat -tulpn 2>/dev/null | grep -q ":$(PORT) "; then \
			echo "Порт $(PORT) уже занят."; \
		else \
			echo "Порт $(PORT) свободен."; \
		fi \
	else \
		echo "Не удалось найти ss или netstat. Проверьте порт $(PORT) вручную."; \
	fi

redis-check:
	@echo "Проверяю доступность Redis/Valkey на host.docker.internal:6379 ..."
	@if command -v redis-cli >/dev/null 2>&1; then \
		if redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; then \
			echo "Redis/Valkey доступен на хосте: 127.0.0.1:6379"; \
		else \
			echo "Redis/Valkey на хосте недоступен на 127.0.0.1:6379"; \
		fi \
	else \
		echo "redis-cli не найден, проверка пропущена."; \
	fi

doctor:
	@echo "Базовая проверка окружения..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "Docker найден."; \
	else \
		echo "Внимание: docker не найден."; \
	fi
	@if docker info >/dev/null 2>&1; then \
		echo "Docker daemon доступен."; \
	else \
		echo "Внимание: Docker daemon недоступен."; \
	fi
	@if [ -f .env ]; then \
		echo ".env найден."; \
	else \
		echo "Внимание: .env не найден."; \
	fi
	@if [ -f config/lti_config.json ]; then \
		echo "config/lti_config.json найден."; \
	else \
		echo "Внимание: config/lti_config.json не найден."; \
	fi
	@if [ -f "$(KEYS_DIR)/jwtRS256.key" ] && [ -f "$(KEYS_DIR)/jwtRS256.key.pub" ]; then \
		echo "JWT ключи найдены."; \
	else \
		echo "Внимание: JWT ключи не найдены в $(KEYS_DIR)."; \
	fi
	@if [ -f .env ]; then \
		if grep -q '^JWT_SECRET_KEY=' .env; then \
			echo "JWT_SECRET_KEY задан."; \
		else \
			echo "Внимание: JWT_SECRET_KEY не найден."; \
		fi; \
		if grep -q '^DATABASE_URL=' .env; then \
			echo "DATABASE_URL задан."; \
		else \
			echo "Внимание: DATABASE_URL не найден."; \
		fi; \
		if grep -q '^REDIS_URL=' .env; then \
			echo "REDIS_URL задан."; \
		else \
			echo "Внимание: REDIS_URL не найден."; \
		fi; \
		if grep -q '^FRONTEND_URL=' .env; then \
			echo "FRONTEND_URL задан."; \
		else \
			echo "Внимание: FRONTEND_URL не найден."; \
		fi; \
		if grep -q '^PUBLIC_BACKEND_URL=' .env; then \
			echo "PUBLIC_BACKEND_URL задан."; \
		else \
			echo "Внимание: PUBLIC_BACKEND_URL не найден."; \
		fi; \
		if grep -q '^LLM_BASE_URL=' .env; then \
			echo "LLM_BASE_URL задан."; \
		else \
			echo "Внимание: LLM_BASE_URL не найден."; \
		fi; \
		if grep -q '^LLM_API_KEY=' .env; then \
			echo "LLM_API_KEY задан."; \
		else \
			echo "Внимание: LLM_API_KEY не найден."; \
		fi; \
		if grep -q '^LLM_MODEL=' .env; then \
			echo "LLM_MODEL задан."; \
		else \
			echo "Внимание: LLM_MODEL не найден."; \
		fi; \
	fi
	@echo ""
	@echo "Подсказка:"
	@echo "  Для хостового Redis/Valkey используйте REDIS_URL=redis://host.docker.internal:6379/0"
	@echo "  Для контейнерного Redis используйте REDIS_URL=redis://redis:6379/0 и make up-with-redis"
	@echo "  Если LLM запущена на хосте, внутри Docker может понадобиться LLM_BASE_URL=http://host.docker.internal:11434/v1"
	@echo "Проверка завершена."
