#!/usr/bin/env bash
# Запуск визуализатора: ./run.sh [-c путь/к/config.ini]
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m depvis "$@"
