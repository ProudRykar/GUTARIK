"""Модуль для чтения конфигурационных файлов."""

# Config loader
import importlib
import sys
from pathlib import Path
from typing import Any, Dict, Union, List

GENERIC_POINTER = "gutarik"


def __yaml_config_parser__(path: str, pointer: str = GENERIC_POINTER) -> Dict[str, Any]:
    """Приватный метод для парсинга YML/YAML конфигурации.

    Args:
        path (str): Путь к файлу gutarik.yml или gutarik.yaml.
        pointer (str): Указатель на раздел конфигурации для чтения.

    Raises:
        ImportError: Если PyYAML не установлен.
        FileNotFoundError: Если файл не найден.
        ValueError: Если YAML некорректен или имя файла не начинается с 'gutarik'.

    Returns:
        Dict[str, Any]: Словарь с параметрами конфигурации.
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        raise ImportError(
            "To parse YAML/YML configuration files, you need to install PyYAML: "
            "`pip install pyyaml` or `poetry add pyyaml`"
        )

    path_obj = Path(path)
    if path_obj.name.split(".")[0] != "gutarik":
        raise ValueError(f"Config file must start with 'gutarik', got: {path_obj.name}")

    try:
        with open(path_obj, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        return config.get(pointer, {}) if config else {}
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML config file not found at: {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def __toml_config_parser__(path: str, pointer: str = GENERIC_POINTER) -> Dict[str, Any]:
    """Приватный метод для парсинга TOML конфигурации.

    Args:
        path (str): Путь к файлу gutarik.toml или pyproject.toml.
        pointer (str): Указатель на раздел конфигурации для чтения.

    Raises:
        ImportError: Если toml не установлен (для Python < 3.11).
        FileNotFoundError: Если файл не найден.
        ValueError: Если TOML некорректен или имя файла не начинается с 'gutarik'
                    (кроме pyproject.toml).

    Returns:
        Dict[str, Any]: Словарь с параметрами конфигурации.
    """
    if sys.version_info >= (3, 11):
        import tomllib as toml
    else:
        try:
            import toml
        except ImportError:
            raise ImportError(
                "To parse TOML configuration files, you need to install toml: "
                "`pip install toml` or `poetry add toml`"
            )

    path_obj = Path(path)
    if path_obj.name != "pyproject.toml" and path_obj.name.split(".")[0] != "gutarik":
        raise ValueError(
            f"Config file must start with 'gutarik' or be 'pyproject.toml', got: {path_obj.name}"
        )

    try:
        with open(path_obj, "rb") as file:
            config = toml.load(file)
        if path_obj.name == "pyproject.toml":
            return config.get("tool", {}).get(pointer, {})
        return config.get(pointer, {}) if config else {}
    except FileNotFoundError:
        raise FileNotFoundError(f"TOML config file not found at: {path}")
    except toml.TOMLDecodeError as e:
        raise ValueError(f"Error parsing TOML file: {e}")


def __python_config_parser__(
    path: str, pointer: str = GENERIC_POINTER
) -> Dict[str, Any]:
    """Приватный метод для парсинга конфигурации на Python.

    Args:
        path (str): Путь к файлу gutarik.py.
        pointer (str): Указатель на раздел конфигурации (игнорируется для Python файлов).

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если имя файла не начинается с 'gutarik' или модуль не может быть загружен.

    Returns:
        Dict[str, Any]: Словарь с параметрами конфигурации.
    """
    path_obj = Path(path)
    if path_obj.name.split(".")[0] != "gutarik":
        raise ValueError(f"Config file must start with 'gutarik', got: {path_obj.name}")

    try:
        module_name = path_obj.stem
        spec = importlib.util.spec_from_file_location(module_name, path_obj)  # type: ignore
        if spec is None or spec.loader is None:
            raise ValueError(f"Failed to load module from {path_obj}")

        module = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        config = {
            key: value
            for key, value in module.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }
        return config.get(pointer, {}) if pointer in config else config
    except FileNotFoundError:
        raise FileNotFoundError(f"Python config file not found at: {path}")
    except Exception as e:
        raise ValueError(f"Error loading Python config: {e}")


def __config_maker__(
    config: Union[str, Dict[str, Any]], pointer: str = GENERIC_POINTER
) -> Dict[str, Any]:
    """Базовый парсер конфигурации.

    Args:
        config (Union[str, Dict[str, Any]]): Словарь конфигурации или путь к файлу gutarik.* или pyproject.toml.
        pointer (str): Указатель на раздел конфигурации для чтения.

    Raises:
        ValueError: Если формат файла не поддерживается или имя файла не начинается с 'gutarik'
                    (кроме pyproject.toml).

    Returns:
        Dict[str, Any]: Распарсенная конфигурация.
    """
    if isinstance(config, dict):
        return config.get(pointer, {}) if pointer else config

    if isinstance(config, str):
        path_obj = Path(config)
        ext = path_obj.suffix.lower()
        if ext in (".yml", ".yaml"):
            return __yaml_config_parser__(config, pointer)
        elif ext == ".toml":
            return __toml_config_parser__(config, pointer)
        elif ext == ".py":
            return __python_config_parser__(config, pointer)
        else:
            raise ValueError("Only YML/YAML, TOML, or Python configs are supported!")

    raise TypeError("Config must be a string (file path) or dictionary")


def load_config(
    config: Union[str, Dict[str, Any], None] = None, pointer: str = GENERIC_POINTER
) -> Dict[str, Any]:
    """Загружает конфигурацию из файла, имя которого начинается с 'gutarik' (.yml, .yaml, .toml, .py) или из pyproject.toml.

    Args:
        config (Union[str, Dict[str, Any], None]): Словарь конфигурации или путь к файлу конфигурации.
            Если None, выполняется поиск pyproject.toml или gutarik.* в текущей директории.
        pointer (str): Указатель на раздел конфигурации для чтения.

    Returns:
        Dict[str, Any]: Словарь с параметрами конфигурации.

    Raises:
        ValueError: Если конфигурационный файл не найден, найдено несколько файлов или формат не поддерживается.
    """
    supported_extensions = {".yml", ".yaml", ".toml", ".py"}

    if isinstance(config, dict):
        return __config_maker__(config, pointer)

    if config:
        config_path = Path(config)
        if not config_path.exists():
            raise ValueError(f"Config file {config_path} does not exist")
        return __config_maker__(str(config_path), pointer)

    pyproject_path = Path.cwd() / "pyproject.toml"
    if pyproject_path.exists():
        try:
            config = __toml_config_parser__(str(pyproject_path), pointer)
            if config:
                return config
        except ValueError:
            pass

    config_files: List[Path] = []
    for ext in supported_extensions:
        config_files.extend(Path.cwd().glob(f"gutarik{ext}"))

    if not config_files:
        print(
            "No config file with name 'gutarik.*' or '[tool.gutarik]' in pyproject.toml found, using default configuration"
        )
        return {
            "PROJECT_DIRS": [Path("gutarik/src")],
            "DOCS_DIR": Path("docs"),
            "SUPPORTED_EXT": [".py"],
            "WIKI_REPO": "https://github.com/user/repo.wiki.git",
            "LOCAL_WIKI_DIR": Path("wiki_tmp"),
            "EXCLUDE_DIRS": [],
        }
    if len(config_files) > 1:
        raise ValueError(
            f"Multiple config files found: {config_files}. Specify one file."
        )

    return __config_maker__(str(config_files[0]), pointer)


def validate_config(config: Dict[str, Any]) -> None:
    """Проверяет наличие обязательных ключей конфигурации.

    Args:
        config (Dict[str, Any]): Словарь конфигурации.

    Raises:
        ValueError: Если обязательные ключи отсутствуют.
    """
    required_keys = {
        "project_dirs",
        "docs_dir",
        "supported_ext",
        "wiki_repo",
        "local_wiki_dir",
        "exclude_dirs",
    }
    missing_keys = required_keys - set(config.keys())
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {missing_keys}")
