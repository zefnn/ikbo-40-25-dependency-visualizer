#!/usr/bin/env bash
# Демонстрация Этапа 4: обратные зависимости в тестовом репозитории.
# Работает без сети. Запуск: ./examples/demo_reverse.sh
set -uo pipefail
cd "$(dirname "$0")/.."

CASES="diamond chain cycle cycles filter no_dependents missing missing_root"

run_case() {
    echo "\$ ./run.sh -c $1"
    ./run.sh -c "$1"
    echo "[код завершения: $?]"
    echo
}

show_repository() {
    local repository
    repository="$(sed -n 's/^repository *= *//p' "$1")"
    echo "--- $repository:"
    cat "$repository"
}

echo "===== Обратные зависимости (тестовый репозиторий) ====="
for name in $CASES; do
    show_repository "examples/reverse/$name.ini"
    run_case "examples/reverse/$name.ini"
done

echo "===== Обратный режим без тестового репозитория ====="
run_case examples/errors/reverse_without_test_mode.ini
