#!/usr/bin/env bash
# Демонстрация Этапа 3: граф зависимостей (BFS, фильтр, циклы).
# Тестовые репозитории работают без сети, Flask читается с PyPI.
set -uo pipefail
cd "$(dirname "$0")/.."

TEST_CASES="levels chain diamond cycle cycles filter missing missing_root
bad_format"

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

echo "===== Тестовый репозиторий ====="
for name in $TEST_CASES; do
    show_repository "examples/test_mode/$name.ini"
    run_case "examples/test_mode/$name.ini"
done

echo "===== Реальный репозиторий (PyPI) ====="
run_case examples/packages/flask.ini
run_case examples/packages/flask_filtered.ini
