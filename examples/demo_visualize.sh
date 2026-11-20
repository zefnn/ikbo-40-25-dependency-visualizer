#!/usr/bin/env bash
# Демонстрация Этапа 5: Mermaid, ASCII-дерево и PNG для трёх пакетов
# с PyPI и для тестового репозитория. Нужен интернет (PyPI и
# mermaid.ink). Запуск: ./examples/demo_visualize.sh
set -uo pipefail
cd "$(dirname "$0")/.."

CASES="requests flask pytest cycles"

run_case() {
    echo "\$ ./run.sh -c $1"
    ./run.sh -c "$1"
    echo "[код завершения: $?]"
    echo
}

for name in $CASES; do
    echo "===== $name ====="
    run_case "examples/visualize/$name.ini"
done

echo "===== Созданные изображения ====="
ls -l examples/visualize/*.png
