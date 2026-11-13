#!/usr/bin/env bash
# Демонстрация Этапа 1: обработка ошибок в файле конфигурации.
# Запуск из любого каталога: ./examples/demo_config.sh
set -uo pipefail
cd "$(dirname "$0")/.."

FILE_ERRORS="no_section_header bad_syntax duplicate_parameter
duplicate_section wrong_section unknown_parameter missing_parameters
empty_values"
PARAMETER_ERRORS="package_name test_package_name repository_url
test_repository_missing test_repository_directory test_mode version
output_image output_directory ascii_tree filter_substring
filter_matches_package reverse_dependencies reverse_without_test_mode"

run_case() {
    echo "\$ ./run.sh -c $1"
    ./run.sh -c "$1"
    echo "[код завершения: $?]"
    echo
}

echo "===== Ошибки чтения файла ====="
run_case examples/no_such_config.ini
run_case examples
TMP_ROOT="${TMPDIR:-/tmp}"
NOT_UTF8="$(mktemp "${TMP_ROOT%/}/not_utf8.XXXXXX")"
printf '[settings]\npackage_name = caf\xe9\n' > "$NOT_UTF8"
run_case "$NOT_UTF8"
rm -f "$NOT_UTF8"

echo "===== Ошибки структуры файла ====="
for name in $FILE_ERRORS; do
    run_case "examples/errors/$name.ini"
done

echo "===== Ошибки в значениях параметров ====="
for name in $PARAMETER_ERRORS; do
    run_case "examples/errors/$name.ini"
done
