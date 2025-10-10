# Модуль validate_config

Модуль для валидации конфигураций.

## def validate_path:
#### Проверяет, что путь безопасен и корректен.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `path` | `Path` | Путь для проверки. |

```python
def validate_path(path: Path) -> None:
    """Проверяет, что путь безопасен и корректен.

    Args:
        path (Path): Путь для проверки.
    """
    if not re.match(r"^[a-zA-Z0-9_/.-]+$", str(path)):
        raise ValueError(f"Небезопасный путь: {path}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Путь {path} не является директорией")
```
---
## def validate_project_dirs:
#### Проверяет список директорий проекта.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `dirs` | `List[Path]` | Список директорий проекта. |

```python
def validate_project_dirs(dirs: List[Path]) -> None:
    """Проверяет список директорий проекта.

    Args:
        dirs (List[Path]): Список директорий проекта.
    """
    for dir_path in dirs:
        validate_path(dir_path)
        if not dir_path.exists():
            raise ValueError(f"Директория {dir_path} не существует")
```
---
## def validate_exclude_dirs:
#### Проверяет список исключаемых директорий.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `dirs` | `List[Path]` | Список исключаемых директорий. |

```python
def validate_exclude_dirs(dirs: List[Path]) -> None:
    """Проверяет список исключаемых директорий.

    Args:
        dirs (List[Path]): Список исключаемых директорий.
    """
    if not isinstance(dirs, list):
        raise ValueError("EXCLUDE_DIRS должен быть списком")
    for dir_path in dirs:
        if not isinstance(dir_path, (str, Path)):
            raise ValueError(f"Некорректный путь в EXCLUDE_DIRS: {dir_path}")
        validate_path(Path(dir_path))
```
---
## def validate_docs_dir:
#### Проверяет директорию для документации.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `docs_dir` | `Path` | Директория для документации. |

```python
def validate_docs_dir(docs_dir: Path) -> None:
    """Проверяет директорию для документации.

    Args:
        docs_dir (Path): Директория для документации.
    """
    validate_path(docs_dir)
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Не удалось создать директорию {docs_dir}: {e}")
```
---
## def validate_supported_ext:
#### Проверяет список поддерживаемых расширений.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `extensions` | `List[str]` | Список расширений. |

```python
def validate_supported_ext(extensions: List[str]) -> None:
    """Проверяет список поддерживаемых расширений.

    Args:
        extensions (List[str]): Список расширений.
    """
    for ext in extensions:
        if not isinstance(ext, str) or not ext.startswith("."):
            raise ValueError(f"Некорректное расширение: {ext}")
```
---
## def validate_wiki_repo:
#### Проверяет URL репозитория Wiki.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `url` | `str` | URL репозитория Wiki. |

```python
def validate_wiki_repo(url: str) -> None:
    """Проверяет URL репозитория Wiki.

    Args:
        url (str): URL репозитория Wiki.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            raise ValueError(f"URL {url} должен использовать схему http или https")
        if not parsed.netloc or not parsed.path:
            raise ValueError(f"Некорректный URL репозитория: {url}")
        if not parsed.netloc.endswith("github.com") or not url.endswith(".wiki.git"):
            raise ValueError(f"URL {url} не является валидным GitHub Wiki URL")
    except Exception as e:
        raise ValueError(f"Ошибка валидации URL {url}: {e}")
```
---
## def validate_config:
#### Проверяет все конфигурационные переменные.

#### Аргументы
| Аргумент | Тип | Описание |
|----------|-----|----------|
| `config` | `dict` | Конфигурационный словарь. |
| `config_path` | `str | Path, optional` | Путь к конфигурационному файлу. Defaults to None. |

```python
def validate_config(config: dict, config_path: Optional[str | Path] = None) -> None:
    """Проверяет все конфигурационные переменные.

    Args:
        config (dict): Конфигурационный словарь.
        config_path (str | Path, optional): Путь к конфигурационному файлу. Defaults to None.
    """
    if config_path:
        config_path = Path(config_path)
        if (
            config_path.name != "pyproject.toml"
            and config_path.name.split(".")[0] != "gutarik"
        ):
            raise ValueError(
                f"Файл конфигурации должен начинаться с 'gutarik' или быть 'pyproject.toml', получено: {config_path.name}"
            )
        if config_path.suffix.lower() not in {".yml", ".yaml", ".toml", ".py"}:
            raise ValueError(f"Формат {config_path.suffix} не поддерживается")
    validate_config_keys(config)
    validate_project_dirs([Path(p) for p in config["project_dirs"]])
    validate_docs_dir(Path(config["docs_dir"]))
    validate_supported_ext(config["supported_ext"])
    validate_wiki_repo(config["wiki_repo"])
    validate_path(Path(config["local_wiki_dir"]))
    validate_exclude_dirs([Path(p) for p in config["exclude_dirs"]])
```
---