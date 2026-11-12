# Визуализатор графа зависимостей (ИКБО-40-25, Вариант №10)

Учебный проект по дисциплине «Конфигурационное управление».
Инструмент визуализации графа зависимостей для менеджера пакетов
Python (pip). Готовые средства получения зависимостей (менеджеры
пакетов, сторонние библиотеки) не используются. Разработка ведётся
поэтапно; текущее состояние соответствует **Этапу 2 (сбор данных)**.

## Общее описание

Приложение — консольная утилита (CLI) на Python 3, написанная только
на стандартной библиотеке. Все параметры, которые настраивает
пользователь, задаются в конфигурационном файле формата INI
(Этап 1). По имени и версии пакета приложение скачивает метаданные
этой версии из репозитория пакетов (PyPI JSON API), само разбирает
строки зависимостей в формате PEP 508 и выводит прямые зависимости
пакета (Этап 2). Ошибки конфигурации и репозитория выводятся
понятными сообщениями, а не трассировками.

## Структура репозитория

```text
config.ini          пример конфигурации (requests 2.32.3 с PyPI)
run.sh              скрипт запуска приложения
requirements.txt    зависимости для запуска тестов (pytest)
pyproject.toml      настройки pytest
src/depvis/         исходный код приложения
tests/              модульные тесты (pytest), работают без сети
examples/           примеры конфигураций и демонстрационные скрипты
```

## Функции и настройки

### Запуск

```text
./run.sh [-h] [-c CONFIG]
```

- `-c CONFIG`, `--config CONFIG` — путь к INI-файлу конфигурации
  (по умолчанию `config.ini` в текущем каталоге);
- `-h`, `--help` — справка.

Других аргументов нет: все настройки берутся из файла конфигурации.

### Этап 1 — конфигурация

Файл в кодировке UTF-8 (допускается BOM) содержит ровно одну секцию
`[settings]` со всеми семью параметрами:

```ini
[settings]
package_name = requests
repository = https://pypi.org/pypi
test_mode = false
version = 2.32.3
output_image = graph.png
ascii_tree = false
filter_substring =
```

- Значение отделяется от имени только знаком `=`.
- Строки, начинающиеся с `;` или `#`, — комментарии.
- Имена параметров не зависят от регистра, имя секции — зависит.
- Символ `%` в значениях не имеет особого смысла (интерполяция
  `configparser` отключена), поэтому URL вида `%20` допустимы.
- Относительные пути отсчитываются от текущего рабочего каталога.

Параметры:

- **`package_name`** — имя анализируемого пакета. В обычном режиме —
  имя pip-пакета по PEP 508: латинские буквы, цифры, `.`, `_`, `-`;
  начинается и заканчивается буквой или цифрой (`requests`,
  `zope.interface`). В тестовом режиме — только заглавные латинские
  буквы (`A`, `B`, `ABC`).
- **`repository`** — в обычном режиме URL-адрес репозитория пакетов:
  схема `http` или `https`, имя хоста, без пробелов
  (`https://pypi.org/pypi`). В тестовом режиме — путь к
  существующему файлу тестового репозитория
  (`examples/repos/basic.txt`).
- **`test_mode`** — режим работы с тестовым репозиторием. Логическое
  значение: `true`/`false`, `yes`/`no`, `on`/`off`, `1`/`0` (регистр
  не важен).
- **`version`** — версия пакета в формате PEP 440: `2.32.3`,
  `1.0rc1`, `2.0.post1`, `1.0.dev3`, `1!2.0`, `1.0+local`.
  Обязательна в обоих режимах.
- **`output_image`** — имя PNG-файла, в который будет сохранено
  изображение графа. Должно оканчиваться на `.png` (регистр не
  важен) и не быть каталогом; каталог, в котором окажется файл,
  должен существовать.
- **`ascii_tree`** — режим вывода зависимостей в формате
  ASCII-дерева. Логическое значение, как у `test_mode`.
- **`filter_substring`** — подстрока для фильтрации пакетов: пакеты,
  имя которых её содержит, не учитываются при анализе. Может быть
  пустой (фильтр выключен); иначе допускаются только латинские
  буквы, цифры, `.`, `_` и `-`.

На Этапе 2 используются `package_name`, `repository` и `version`;
остальные параметры проверяются и понадобятся на следующих этапах.
Вывод всех параметров в формате `ключ=значение` требовался только
на Этапе 1 и больше не выполняется.

Ошибки конфигурации выводятся в stderr: заголовок с именем файла и
список всех найденных проблем, код завершения 1. Проверяются:

- чтение файла: файл не найден, вместо файла указан каталог, другая
  ошибка ОС (например, нет прав доступа), файл не в кодировке UTF-8;
- структура (с номером строки, где это возможно): параметр до
  заголовка секции, строка не является парой `ключ = значение`,
  повтор параметра или секции, неизвестная секция или нет секции
  `[settings]`, неизвестный или недостающий параметр;
- значения — по правилам выше. Пустое значение недопустимо везде,
  кроме `filter_substring`. Все неверные значения перечисляются за
  один запуск. Правила для `package_name` и `repository` зависят от
  режима, поэтому они проверяются, только если `test_mode` задан
  корректно.

### Этап 2 — сбор данных о зависимостях

**Источник данных.** Для заданных пакета и версии приложение
запрашивает JSON API репозитория:

```text
GET {repository}/{package_name}/{version}/json
```

Для PyPI `repository = https://pypi.org/pypi`, так что для
`config.ini` запрашивается
`https://pypi.org/pypi/requests/2.32.3/json`; так же устроен
`https://test.pypi.org/pypi`. Имя пакета в адресе приводится к форме
PEP 503 (нижний регистр, разделители `-`). Запрос выполняется
модулем `urllib` с таймаутом 10 секунд, ответ разбирается модулем
`json`.

**Зависимости.** Прямые зависимости версии берутся из поля
`info.requires_dist` ответа — это строки `Requires-Dist` из
метаданных пакета в формате PEP 508, например
`urllib3<3,>=1.21.1` или `colorama; sys_platform == "win32"`.
Значение `null` означает, что зависимостей нет. Каждая строка
разбирается собственным кодом на имя пакета, extras, ограничение
версии (скобки и пробелы убираются) и маркер окружения после `;`.

**Что считается прямой зависимостью:**

- зависимость с маркером, где есть переменная `extra`
  (`PySocks; extra == "socks"`), — необязательная: pip ставит её,
  только если явно запросить `requests[socks]`. Такие зависимости не
  считаются прямыми и перечисляются отдельной строкой;
- зависимость с маркером окружения (`python_version < "3.11"`,
  `sys_platform == "win32"`) — настоящая зависимость, но не для всех
  платформ. Она выводится вместе со своим условием, поэтому
  результат не зависит от машины, на которой запущено приложение;
- строка, которую не удалось разобрать, пропускается с
  предупреждением в stderr.

**Тестовый режим** (`test_mode = true`) появится на Этапе 3. Сейчас
приложение сообщает `test mode (test_mode = true) is not implemented
yet` и завершается с кодом 1, ничего не скачивая.

**Вывод (только Этап 2).** В stdout выводится заголовок
`Direct dependencies of <пакет> <версия>:` и по одной прямой
зависимости в строке: имя, ограничение версии и, если есть, маркер
после ` ; `. Если зависимостей нет, выводится `(none)`. Последняя
строка перечисляет пропущенные необязательные зависимости (extras).

**Ошибки репозитория** выводятся в stderr, код завершения 3:

- пакет не найден в репозитории;
- у пакета нет заданной версии (в сообщении — последняя версия);
- хост не найден или соединение не установлено;
- нет ответа за 10 секунд;
- ошибка проверки HTTPS-сертификата (с подсказкой, как её
  исправить, см. «Сборка и тесты»);
- HTTP-ошибка, например `HTTP error 500 Internal Server Error`;
- ответ не в формате JSON (например, указан адрес HTML-страницы);
- в ответе нет `info.requires_dist` или это не список строк.

Коды завершения:

- `0` — зависимости получены;
- `1` — ошибка в файле конфигурации (или включён тестовый режим);
- `2` — неверные аргументы командной строки (поведение `argparse`);
- `3` — ошибка репозитория.

### Модули и функции

`depvis.cli` — интерфейс командной строки:

- `parse_arguments(argv)` — разбирает аргументы командной строки;
- `describe_requirement(requirement)` — текст одной зависимости:
  имя, ограничение версии, маркер;
- `format_optional(requirements)` — строка с именами пропущенных
  необязательных зависимостей (с переносом по ширине 79);
- `format_dependencies(name, version, dependencies)` — полный текст
  вывода Этапа 2;
- `report_config_error(error)` — печатает ошибки конфигурации;
- `show_direct_dependencies(settings)` — получает и печатает прямые
  зависимости, возвращает код завершения;
- `main(argv)` — точка входа, возвращает код завершения.

`depvis.config` — чтение файла конфигурации:

- `Settings` — неизменяемый dataclass с проверенными параметрами;
- `load_settings(path)` — читает и проверяет файл, возвращает
  `Settings`;
- `read_config_file(path)` — открывает и разбирает INI-файл;
- `describe_syntax_error(error)` — переводит ошибку `configparser`
  в сообщения с номерами строк;
- `check_layout(parser, path)` — проверяет секции и набор
  параметров;
- `find_name_problems(names)` — находит неизвестные и недостающие
  параметры;
- `build_settings(raw_values, path)` — проверяет значения и
  собирает `Settings`;
- `run_check(problems, name, check, *arguments)` — выполняет одну
  проверку и запоминает её ошибку;
- `describe_problems(problems)` — выстраивает сообщения в порядке
  параметров.

`depvis.validation` — проверки значений (каждая возвращает
очищенное значение или бросает `ValidationError`):

- `require_text(value)` — непустая строка без пробелов по краям;
- `parse_flag(value)` — логическое значение;
- `check_package_name(value, test_mode)` — имя пакета;
- `check_repository(value, test_mode)` — URL или путь к файлу;
- `check_repository_url(url)` — http(s)-URL с именем хоста;
- `check_test_repository(location)` — существующий файл;
- `check_version(value)` — версия по PEP 440;
- `check_output_image(value)` — имя PNG-файла;
- `check_filter(value)` — подстрока фильтра.

`depvis.repository` — запросы к репозиторию (PyPI JSON API):

- `release_url(repository, name, version)` — адрес JSON-описания
  версии (без версии — последней версии пакета);
- `fetch_requires_dist(repository, name, version)` — строки
  `Requires-Dist` заданной версии пакета;
- `fetch_json(url)` — скачивает адрес и разбирает ответ как JSON;
- `http_failure(url, error)` — ошибка по HTTP-статусу (404 — пакет
  или версия не найдены);
- `download_failure(url, reason)` — ошибка соединения, таймаута
  или сертификата;
- `explain_missing_release(repository, name, version)` — уточняет,
  чего нет: пакета или только версии;
- `info_object(data)`, `latest_version(data)` — объект `info` и
  последняя версия из ответа;
- `read_requires_dist(url, data)` — проверяет и возвращает
  `info.requires_dist`;
- `is_string_list(value)` — проверка «список строк».

`depvis.requirements` — разбор строк PEP 508:

- `Requirement` — неизменяемый dataclass: `name`, `extras`,
  `specifier`, `marker`; свойство `key` — имя в форме PEP 503,
  свойство `is_optional` — нужна ли зависимость только для extra;
- `canonical_name(name)` — нормализация имени по PEP 503;
- `parse_requirement(text)` — разбирает строку в `Requirement`;
- `split_extras(text)` — список extras из `[...]`;
- `clean_specifier(text)` — проверяет и нормализует ограничение
  версии;
- `strip_parentheses(text)` — убирает скобки вокруг ограничения.

`depvis.dependencies` — прямые зависимости пакета:

- `DirectDependencies` — dataclass с группами `required`,
  `optional` и `invalid`;
- `get_direct_dependencies(repository, name, version)` — скачивает и
  классифицирует зависимости версии пакета;
- `classify(lines)` — разбирает строки и раскладывает их по группам.

`depvis.errors` — исключения: `ValidationError` (ошибка значения),
`ConfigError` (ошибки файла конфигурации, поля `path` и `messages`),
`RequirementError` (строка не в формате PEP 508), `RepositoryError`
(ошибка репозитория) и его подкласс `PackageNotFoundError` (нет
пакета или версии).

## Сборка и тесты

Нужен Python 3.10 или новее (проверено на 3.13). Приложение не
использует сторонних библиотек и не требует сборки: `run.sh`
добавляет каталог `src` в `PYTHONPATH`. Для тестов нужен pytest:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pytest
```

Тесты не обращаются к сети: вместо `urlopen` в них подставляется
поддельный репозиторий, а любой настоящий запрос делает тест
неудачным.

Запуск без скрипта:

```bash
PYTHONPATH=src python3 -m depvis -c config.ini
```

Демонстрация ошибок конфигурации (Этап 1) и получения зависимостей
с PyPI (Этап 2, нужен интернет):

```bash
./examples/demo_config.sh
./examples/demo_dependencies.sh
```

Если Python установлен с python.org на macOS и при запросе
появляется `CERTIFICATE_VERIFY_FAILED`, нужно один раз запустить
`Install Certificates.command` из папки этого Python в
`/Applications`.

## Примеры использования

Файлы примеров:

- `config.ini` — requests 2.32.3 с PyPI;
- `examples/packages/*.ini` — pytest 8.3.3, Flask 3.0.3, Django 5.1
  и certifi 2024.8.30 (пакет без зависимостей);
- `examples/repository_errors/*.ini` — нет пакета, нет версии,
  несуществующий хост, адрес HTML-страницы вместо JSON API;
- `examples/errors/*.ini` — по одному файлу на каждую ошибку
  конфигурации;
- `examples/config_test_mode.ini` и `examples/repos/basic.txt` —
  тестовый режим (граф из файла будет строиться с Этапа 3);
- `examples/demo_config.sh`, `examples/demo_dependencies.sh` —
  запускают приложение на этих примерах.

Прямые зависимости requests (используется `config.ini` из текущего
каталога):

```text
$ ./run.sh
Direct dependencies of requests 2.32.3:
  charset-normalizer <4,>=2
  idna <4,>=2.5
  urllib3 <3,>=1.21.1
  certifi >=2017.4.17
Skipped optional dependencies (extras): PySocks, chardet
```

Зависимости с условиями на окружение:

```text
$ ./run.sh -c examples/packages/pytest.ini
Direct dependencies of pytest 8.3.3:
  iniconfig
  packaging
  pluggy <2,>=1.5
  exceptiongroup >=1.0.0rc8 ; python_version < "3.11"
  tomli >=1 ; python_version < "3.11"
  colorama ; sys_platform == "win32"
Skipped optional dependencies (extras): argcomplete, attrs, hypothesis, mock,
  pygments, requests, setuptools, xmlschema
```

Пакет без зависимостей:

```text
$ ./run.sh -c examples/packages/certifi.ini
Direct dependencies of certifi 2024.8.30:
  (none)
```

Ошибки репозитория (последняя версия requests указана на момент
написания):

```text
$ ./run.sh -c examples/repository_errors/missing_version.ini
error: package 'requests' has no version '9.9.9' in https://pypi.org/pypi (latest version: 2.34.2)
```

```text
$ ./run.sh -c examples/repository_errors/not_json.ini
error: https://pypi.org/project/requests/2.32.3/json: the answer is not JSON
```

Ошибка конфигурации:

```text
$ ./run.sh -c examples/errors/version.ini
error: cannot use config file 'examples/errors/version.ini':
  version: '2.x' is not a PEP 440 version (e.g. 2.32.3)
```

Тестовый режим пока не поддерживается:

```text
$ ./run.sh -c examples/config_test_mode.ini
error: test mode (test_mode = true) is not implemented yet
```
