.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

DC            ?= docker-compose
COMPOSE_FILE  ?= compose.yaml

KEYS_DIR         ?= ./config/keys
LOG_DIR          ?= ./logs
IMAGES_DIR       ?= ./images
LTI_CONFIG_PATH  ?= ./lti_config.json
BACKEND_ENV_FILE ?= ./.env
PORT             ?= 3162

USE_OWN_REDIS    ?= auto
REDIS_URL        ?=

-include .makerc

HOST_REDIS_AVAILABLE := $(shell \
  if command -v redis-cli >/dev/null 2>&1; then \
    redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null | grep -q PONG && echo yes || echo no; \
  else \
    (exec 3<>/dev/tcp/127.0.0.1/6379) 2>/dev/null && { echo yes; exec 3<&- 3>&-; } || echo no; \
  fi)

ifeq ($(USE_OWN_REDIS),auto)
  ifeq ($(HOST_REDIS_AVAILABLE),yes)
    RESOLVED_USE_OWN_REDIS := n
  else
    RESOLVED_USE_OWN_REDIS := y
  endif
else
  RESOLVED_USE_OWN_REDIS := $(USE_OWN_REDIS)
endif

ifeq ($(strip $(REDIS_URL)),)
  ifeq ($(RESOLVED_USE_OWN_REDIS),y)
    REDIS_URL := redis://redis:6379/0
  else
    REDIS_URL := redis://host.docker.internal:6379/0
  endif
endif

ifeq ($(RESOLVED_USE_OWN_REDIS),y)
  COMPOSE_PROFILES_FLAG := --profile with-redis
else
  COMPOSE_PROFILES_FLAG :=
endif

export KEYS_DIR LOG_DIR IMAGES_DIR LTI_CONFIG_PATH BACKEND_ENV_FILE PORT REDIS_URL

DC_RUN := $(DC) -f $(COMPOSE_FILE) $(COMPOSE_PROFILES_FLAG)

.PHONY: help setup reconfigure clean-setup \
        build rebuild up down restart ps \
        logs backend-logs worker-logs nginx-logs redis-logs \
        migrate shell-backend shell-worker \
        check-port doctor

help:
	@echo "Команды:"
	@echo "  make setup            интерактивная настройка"
	@echo "  make reconfigure      запустить setup заново"
	@echo "  make clean-setup      удалить .makerc"
	@echo ""
	@echo "  make build            собрать образы"
	@echo "  make rebuild          собрать без кеша"
	@echo "  make up               поднять сервисы"
	@echo "  make down             остановить"
	@echo "  make restart          перезапустить backend и worker"
	@echo "  make ps               статус"
	@echo ""
	@echo "  make logs | backend-logs | worker-logs | nginx-logs | redis-logs"
	@echo "  make migrate          alembic upgrade head"
	@echo "  make shell-backend | shell-worker"
	@echo ""
	@echo "  make check-port       проверить порт $(PORT)"
	@echo "  make doctor           проверить окружение"
	@echo ""
	@echo "Текущая конфигурация:"
	@echo "  KEYS_DIR             = $(KEYS_DIR)"
	@echo "  LOG_DIR              = $(LOG_DIR)"
	@echo "  IMAGES_DIR           = $(IMAGES_DIR)"
	@echo "  LTI_CONFIG_PATH      = $(LTI_CONFIG_PATH)"
	@echo "  BACKEND_ENV_FILE     = $(BACKEND_ENV_FILE)"
	@echo "  PORT                 = $(PORT)"
	@echo "  USE_OWN_REDIS        = $(USE_OWN_REDIS) (resolved: $(RESOLVED_USE_OWN_REDIS))"
	@echo "  HOST_REDIS_AVAILABLE = $(HOST_REDIS_AVAILABLE)"
	@echo "  REDIS_URL            = $(REDIS_URL)"


define SETUP_SCRIPT
set -euo pipefail

ask() {
  local var="$$1" prompt="$$2" def="$$3" ans
  if [ -n "$$def" ]; then
    read -e -r -p "$$prompt [$$def]: " ans || true
    ans="$${ans:-$$def}"
  else
    read -e -r -p "$$prompt: " ans || true
  fi
  printf -v "$$var" '%s' "$$ans"
}

ask_yn() {
  local var="$$1" prompt="$$2" def="$$3" ans
  while true; do
    read -r -p "$$prompt [$$def]: " ans || true
    ans="$${ans:-$$def}"
    case "$$ans" in
      y|Y|yes) printf -v "$$var" 'y'; return;;
      n|N|no)  printf -v "$$var" 'n'; return;;
      *) echo "Введите y или n.";;
    esac
  done
}

ask_choice() {
  local var="$$1" prompt="$$2" def="$$3" ans
  while true; do
    read -r -p "$$prompt [$$def]: " ans || true
    ans="$${ans:-$$def}"
    case "$$ans" in
      auto|y|n) printf -v "$$var" '%s' "$$ans"; return;;
      *) echo "Введите auto, y или n.";;
    esac
  done
}

pick_editor() {
  if [ -n "$${EDITOR:-}" ] && command -v "$${EDITOR%% *}" >/dev/null 2>&1; then
    echo "$$EDITOR"; return
  fi
  if [ -n "$${VISUAL:-}" ] && command -v "$${VISUAL%% *}" >/dev/null 2>&1; then
    echo "$$VISUAL"; return
  fi
  for e in nano micro vim vi nvim code; do
    if command -v "$$e" >/dev/null 2>&1; then
      [ "$$e" = "code" ] && echo "code --wait" || echo "$$e"
      return
    fi
  done
  echo ""
}

edit_file() {
  local file="$$1" ed
  ed="$$(pick_editor)"
  if [ -z "$$ed" ]; then
    echo "Редактор не найден. Отредактируйте $$file и нажмите Enter."
    read -r _ || true
    return
  fi
  echo "Открываю $$file в $$ed. Закройте редактор для продолжения."
  $$ed "$$file"
}

copy_example() {
  local src="$$1" dst="$$2"
  if [ -f "$$dst" ] && [ -f "$$src" ]; then
    local ow
    while true; do
      read -r -p "$$dst уже существует. Перезаписать из $$src? [n]: " ow || true
      ow="$${ow:-n}"
      case "$$ow" in
        y|Y|yes) cp -f "$$src" "$$dst"; echo "$$dst перезаписан из $$src."; return;;
        n|N|no)  echo "Оставляю существующий $$dst."; return;;
        *) echo "Введите y или n.";;
      esac
    done
  elif [ -f "$$src" ]; then
    mkdir -p "$$(dirname "$$dst")"
    cp "$$src" "$$dst"
    echo "$$src скопирован в $$dst."
  elif [ -f "$$dst" ]; then
    echo "$$dst уже существует, $$src отсутствует — пропускаю."
  else
    echo "Внимание: ни $$src, ни $$dst не найдены."
    return 1
  fi
}

check_env_vars() {
  local file="$$1"; shift
  local missing=()
  for v in "$$@"; do
    grep -qE "^$$v=.+" "$$file" || missing+=("$$v")
  done
  if [ $${#missing[@]} -eq 0 ]; then
    echo "OK: все обязательные переменные заполнены."
    return 0
  fi
  echo "Не заполнены: $${missing[*]}"
  return 1
}

set_env_var() {
  local file="$$1" key="$$2" value="$$3"
  if grep -q "^$$key=" "$$file"; then
    sed -i.bak "s|^$$key=.*|$$key=$$value|" "$$file" && rm -f "$$file.bak"
  else
    echo "$$key=$$value" >> "$$file"
  fi
}

detect_host_redis() {
  if command -v redis-cli >/dev/null 2>&1; then
    redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null | grep -q PONG && return 0 || return 1
  fi
  (exec 3<>/dev/tcp/127.0.0.1/6379) 2>/dev/null && { exec 3<&- 3>&-; return 0; } || return 1
}


echo "[1/6] Каталог логов"
ask LOG_DIR "Куда складывать логи" "$(LOG_DIR)"
mkdir -p "$$LOG_DIR"
echo "Создан $$LOG_DIR"
echo

echo "[2/6] Каталог изображений"
ask IMAGES_DIR "Куда складывать изображения" "$(IMAGES_DIR)"
mkdir -p "$$IMAGES_DIR"
echo "Создан $$IMAGES_DIR"
echo

echo "[3/6] Каталог JWT-ключей"
ask KEYS_DIR "Куда положить JWT-ключи" "$(KEYS_DIR)"
mkdir -p "$$KEYS_DIR"
if [ ! -f "$$KEYS_DIR/jwtRS256.key" ]; then
  ssh-keygen -t rsa -b 4096 -m PEM -f "$$KEYS_DIR/jwtRS256.key" -N "" >/dev/null 2>&1
  echo "Создан $$KEYS_DIR/jwtRS256.key"
else
  echo "Приватный ключ уже существует."
fi
if [ ! -f "$$KEYS_DIR/jwtRS256.key.pub" ]; then
  openssl rsa -in "$$KEYS_DIR/jwtRS256.key" -pubout -outform PEM \
    -out "$$KEYS_DIR/jwtRS256.key.pub" >/dev/null 2>&1
  echo "Создан $$KEYS_DIR/jwtRS256.key.pub"
else
  echo "Публичный ключ уже существует."
fi
echo

echo "[4/6] .env"
ask BACKEND_ENV_FILE "Куда положить .env" "$(BACKEND_ENV_FILE)"
copy_example backend/.env.example "$$BACKEND_ENV_FILE" || true

[ -f "$$BACKEND_ENV_FILE" ] || { mkdir -p "$$(dirname "$$BACKEND_ENV_FILE")"; : > "$$BACKEND_ENV_FILE"; }

if ! grep -qE '^JWT_SECRET_KEY=.+' "$$BACKEND_ENV_FILE"; then
  SECRET="$$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 64)"
  set_env_var "$$BACKEND_ENV_FILE" JWT_SECRET_KEY "$$SECRET"
  echo "JWT_SECRET_KEY сгенерирован."
fi

echo
echo "Redis"
if detect_host_redis; then
  echo "Обнаружен Redis/Valkey на хосте (127.0.0.1:6379)."
  HOST_REDIS_FOUND=y
else
  echo "Redis на хосте не найден."
  HOST_REDIS_FOUND=n
fi

echo "Режимы:"
echo "  auto — определять автоматически при каждом make-вызове"
echo "  y    — всегда поднимать собственный Redis в docker-compose"
echo "  n    — всегда использовать внешний Redis"
DEFAULT_MODE=auto
ask_choice USE_OWN_REDIS "Режим" "$$DEFAULT_MODE"

case "$$USE_OWN_REDIS" in
  y) RESOLVED=y ;;
  n) RESOLVED=n ;;
  auto)
    if [ "$$HOST_REDIS_FOUND" = "y" ]; then RESOLVED=n; else RESOLVED=y; fi
    ;;
esac

if [ "$$RESOLVED" = "y" ]; then
  REDIS_URL="redis://redis:6379/0"
  echo "Будет поднят контейнер redis. URL: $$REDIS_URL"
else
  echo "Будет использоваться внешний Redis."
  ask REDIS_URL "REDIS_URL" "redis://host.docker.internal:6379/0"
fi

set_env_var "$$BACKEND_ENV_FILE" REDIS_URL "$$REDIS_URL"
echo "REDIS_URL=$$REDIS_URL записан в $$BACKEND_ENV_FILE."

ask_yn EDIT_ENV "Открыть $$BACKEND_ENV_FILE в редакторе?" "y"
[ "$$EDIT_ENV" = "y" ] && edit_file "$$BACKEND_ENV_FILE"

REQUIRED=(JWT_SECRET_KEY DATABASE_URL REDIS_URL FRONTEND_URL PUBLIC_BACKEND_URL LLM_BASE_URL LLM_API_KEY LLM_MODEL)
while ! check_env_vars "$$BACKEND_ENV_FILE" "$${REQUIRED[@]}"; do
  ask_yn REOPEN "Открыть ещё раз?" "y"
  if [ "$$REOPEN" = "y" ]; then
    edit_file "$$BACKEND_ENV_FILE"
  else
    break
  fi
done
echo

echo "[5/6] LTI config"
ask LTI_CONFIG_PATH "Куда положить lti_config.json" "$(LTI_CONFIG_PATH)"
copy_example backend/config/lti_config.json.example "$$LTI_CONFIG_PATH" || {
  mkdir -p "$$(dirname "$$LTI_CONFIG_PATH")"
  echo '{}' > "$$LTI_CONFIG_PATH"
  echo "Создан пустой $$LTI_CONFIG_PATH."
}

ask_yn EDIT_LTI "Открыть $$LTI_CONFIG_PATH в редакторе?" "y"
if [ "$$EDIT_LTI" = "y" ]; then
  while true; do
    edit_file "$$LTI_CONFIG_PATH"
    if command -v python3 >/dev/null 2>&1; then
      if python3 -c "import json; json.load(open('$$LTI_CONFIG_PATH'))" 2>/dev/null; then
        echo "JSON валиден."
        break
      else
        echo "Внимание: невалидный JSON."
        ask_yn REOPEN_LTI "Открыть ещё раз?" "y"
        [ "$$REOPEN_LTI" = "y" ] || break
      fi
    else
      break
    fi
  done
fi
echo

echo "[6/6] Порт"
ask PORT "Внешний порт nginx" "$(PORT)"
echo

cat > .makerc <<EOF
KEYS_DIR         := $$KEYS_DIR
LOG_DIR          := $$LOG_DIR
IMAGES_DIR       := $$IMAGES_DIR
LTI_CONFIG_PATH  := $$LTI_CONFIG_PATH
BACKEND_ENV_FILE := $$BACKEND_ENV_FILE
PORT             := $$PORT
USE_OWN_REDIS    := $$USE_OWN_REDIS
REDIS_URL        := $$REDIS_URL
EOF
echo ".makerc сохранён."
echo
echo "Готово. Дальше: make build && make up"
endef
export SETUP_SCRIPT

setup:
	@bash -c "$$SETUP_SCRIPT"

reconfigure:
	@rm -f .makerc
	@$(MAKE) setup

clean-setup:
	@rm -f .makerc
	@echo "Удалён .makerc."

build:          ; $(DC_RUN) build
rebuild:        ; $(DC_RUN) build --no-cache
up:             ; $(DC_RUN) up -d
down:           ; $(DC_RUN) down
restart:        ; $(DC_RUN) restart backend worker
ps:             ; $(DC_RUN) ps

logs:           ; $(DC_RUN) logs -f
backend-logs:   ; $(DC_RUN) logs -f backend
worker-logs:    ; $(DC_RUN) logs -f worker
nginx-logs:     ; $(DC_RUN) logs -f nginx

redis-logs:
ifeq ($(RESOLVED_USE_OWN_REDIS),y)
	$(DC_RUN) logs -f redis
else
	@echo "Используется внешний Redis ($(REDIS_URL))."
	@echo "Логи смотри на хосте, например: sudo journalctl -u valkey-server -f"
	@echo "                          или: sudo journalctl -u redis-server -f"
endif

migrate:        ; $(DC_RUN) exec -T backend uv run alembic upgrade head
shell-backend:  ; $(DC_RUN) exec backend sh
shell-worker:   ; $(DC_RUN) exec worker sh

check-port:
	@if command -v ss >/dev/null 2>&1; then \
		ss -tulpn 2>/dev/null | grep -q ":$(PORT) " \
			&& echo "Порт $(PORT) занят" || echo "Порт $(PORT) свободен"; \
	elif command -v netstat >/dev/null 2>&1; then \
		netstat -tulpn 2>/dev/null | grep -q ":$(PORT) " \
			&& echo "Порт $(PORT) занят" || echo "Порт $(PORT) свободен"; \
	else \
		echo "Не найдено ss/netstat"; \
	fi

doctor:
	@echo "Проверка окружения"
	@command -v docker-compose >/dev/null 2>&1 && echo "docker-compose: OK"  || echo "docker-compose: НЕТ"
	@docker info >/dev/null 2>&1                && echo "docker daemon: OK"  || echo "docker daemon: НЕТ"
	@[ -d $(LOG_DIR) ]                    && echo "$(LOG_DIR): OK"           || echo "$(LOG_DIR): НЕТ"
	@[ -d $(IMAGES_DIR) ]                 && echo "$(IMAGES_DIR): OK"        || echo "$(IMAGES_DIR): НЕТ"
	@[ -f $(BACKEND_ENV_FILE) ]           && echo "$(BACKEND_ENV_FILE): OK"  || echo "$(BACKEND_ENV_FILE): НЕТ"
	@[ -f $(LTI_CONFIG_PATH) ]            && echo "$(LTI_CONFIG_PATH): OK"   || echo "$(LTI_CONFIG_PATH): НЕТ"
	@[ -f $(KEYS_DIR)/jwtRS256.key ] && [ -f $(KEYS_DIR)/jwtRS256.key.pub ] \
		&& echo "JWT-ключи: OK" || echo "JWT-ключи: НЕТ"
	@echo "Redis режим: USE_OWN_REDIS=$(USE_OWN_REDIS) → $(RESOLVED_USE_OWN_REDIS)"
	@echo "Redis на хосте: $(HOST_REDIS_AVAILABLE)"
	@echo "REDIS_URL: $(REDIS_URL)"
	@if [ -f $(BACKEND_ENV_FILE) ]; then \
		for v in JWT_SECRET_KEY DATABASE_URL REDIS_URL FRONTEND_URL PUBLIC_BACKEND_URL LLM_BASE_URL LLM_API_KEY LLM_MODEL; do \
			if grep -qE "^$$v=.+" $(BACKEND_ENV_FILE); then echo "$$v: OK"; else echo "$$v: НЕТ"; fi; \
		done; \
	fi