#!/usr/bin/env bash
# Демонстрация Этапа 2: данные о зависимостях пакетов из PyPI
# (с Этапа 3 для каждого пакета выводится полный граф).
# Нужен доступ в интернет. Запуск: ./examples/demo_dependencies.sh
set -uo pipefail
cd "$(dirname "$0")/.."

PACKAGES="config.ini examples/packages/pytest.ini examples/packages/flask.ini
examples/packages/django.ini examples/packages/certifi.ini"
REPOSITORY_ERRORS="missing_package missing_version unknown_host not_json"

run_case() {
    echo "\$ ./run.sh -c $1"
    ./run.sh -c "$1"
    echo "[код завершения: $?]"
    echo
}

echo "===== Зависимости пакетов ====="
for config in $PACKAGES; do
    run_case "$config"
done

echo "===== Ошибки репозитория ====="
for name in $REPOSITORY_ERRORS; do
    run_case "examples/repository_errors/$name.ini"
done
