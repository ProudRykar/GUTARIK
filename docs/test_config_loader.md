# Модуль test_config_loader

Модуль для тестирования парсинга и валидации конфигураций.

## def tmp_config_dir:
#### Создаёт временную директорию для тестовых конфигураций.

```python
@pytest.fixture
def tmp_config_dir(tmp_path: Path):
    """Создаёт временную директорию для тестовых конфигураций."""
    return tmp_path
```
---
## def test_yaml_config_parser:
#### Тестирует парсинг YAML-конфигурации.

```python
def test_yaml_config_parser(tmp_config_dir: Path):
    """Тестирует парсинг YAML-конфигурации."""
    config_content = """
    gutarik:
      project_dirs:
        - ./gutarik/src
      docs_dir: ./docs
      supported_ext:
        - .py
      wiki_repo: https://github.com/user/repo.wiki.git
      local_wiki_dir: ./wiki_tmp
      exclude_dirs:
        - tests
        - venv
    """
    config_file = tmp_config_dir / "gutarik.yml"
    config_file.write_text(config_content)

    config = __yaml_config_parser__(str(config_file), pointer="gutarik")
    assert config["project_dirs"] == ["./gutarik/src"]
    assert config["docs_dir"] == "./docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert config["local_wiki_dir"] == "./wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_toml_config_parser:
#### Тестирует парсинг TOML-конфигурации.

```python
def test_toml_config_parser(tmp_config_dir: Path):
    """Тестирует парсинг TOML-конфигурации."""
    config_content = """
    [gutarik]
    project_dirs = ["./gutarik/src"]
    docs_dir = "./docs"
    supported_ext = [".py"]
    wiki_repo = "https://github.com/user/repo.wiki.git"
    local_wiki_dir = "./wiki_tmp"
    exclude_dirs = ["tests", "venv"]
    """
    config_file = tmp_config_dir / "gutarik.toml"
    config_file.write_text(config_content)

    config = __toml_config_parser__(str(config_file), pointer="gutarik")
    assert config["project_dirs"] == ["./gutarik/src"]
    assert config["docs_dir"] == "./docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert config["local_wiki_dir"] == "./wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_toml_config_parser_pyproject:
#### Тестирует парсинг конфигурации из pyproject.toml.

```python
def test_toml_config_parser_pyproject(tmp_config_dir: Path):
    """Тестирует парсинг конфигурации из pyproject.toml."""
    config_content = """
    [tool.gutarik]
    project_dirs = ["./gutarik/src"]
    docs_dir = "./docs"
    supported_ext = [".py"]
    wiki_repo = "https://github.com/user/repo.wiki.git"
    local_wiki_dir = "./wiki_tmp"
    exclude_dirs = ["tests", "venv"]
    """
    config_file = tmp_config_dir / "pyproject.toml"
    config_file.write_text(config_content)

    config = __toml_config_parser__(str(config_file), pointer="gutarik")
    assert config["project_dirs"] == ["./gutarik/src"]
    assert config["docs_dir"] == "./docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert config["local_wiki_dir"] == "./wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_python_config_parser:
#### Тестирует парсинг Python-конфигурации.

```python
def test_python_config_parser(tmp_config_dir: Path):
    """Тестирует парсинг Python-конфигурации."""
    config_content = """from pathlib import Path
project_dirs = [Path("./gutarik/src")]
docs_dir = Path("./docs")
supported_ext = [".py"]
wiki_repo = "https://github.com/user/repo.wiki.git"
local_wiki_dir = Path("./wiki_tmp")
exclude_dirs = ["tests", "venv"]
"""
    config_file = tmp_config_dir / "gutarik.py"
    config_file.write_text(config_content)

    config = __python_config_parser__(str(config_file), pointer="gutarik")
    assert str(config["project_dirs"][0]) == "gutarik/src"
    assert str(config["docs_dir"]) == "docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert str(config["local_wiki_dir"]) == "wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_load_config_auto_find_yaml:
#### Тестирует автоматическую загрузку YAML-конфигурации.

```python
def test_load_config_auto_find_yaml(tmp_config_dir: Path, monkeypatch):
    """Тестирует автоматическую загрузку YAML-конфигурации."""
    config_content = """
    gutarik:
      project_dirs:
        - ./gutarik/src
      docs_dir: ./docs
      supported_ext:
        - .py
      wiki_repo: https://github.com/user/repo.wiki.git
      local_wiki_dir: ./wiki_tmp
      exclude_dirs:
        - tests
        - venv
    """
    config_file = tmp_config_dir / "gutarik.yml"
    config_file.write_text(config_content)

    monkeypatch.chdir(tmp_config_dir)
    config = load_config()
    assert config["project_dirs"] == ["./gutarik/src"]
    assert config["docs_dir"] == "./docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert config["local_wiki_dir"] == "./wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_load_config_auto_find_pyproject:
#### Тестирует автоматическую загрузку конфигурации из pyproject.toml.

```python
def test_load_config_auto_find_pyproject(tmp_config_dir: Path, monkeypatch):
    """Тестирует автоматическую загрузку конфигурации из pyproject.toml."""
    config_content = """
    [tool.gutarik]
    project_dirs = ["./gutarik/src"]
    docs_dir = "./docs"
    supported_ext = [".py"]
    wiki_repo = "https://github.com/user/repo.wiki.git"
    local_wiki_dir = "./wiki_tmp"
    exclude_dirs = ["tests", "venv"]
    """
    config_file = tmp_config_dir / "pyproject.toml"
    config_file.write_text(config_content)

    monkeypatch.chdir(tmp_config_dir)
    config = load_config()
    assert config["project_dirs"] == ["./gutarik/src"]
    assert config["docs_dir"] == "./docs"
    assert config["supported_ext"] == [".py"]
    assert config["wiki_repo"] == "https://github.com/user/repo.wiki.git"
    assert config["local_wiki_dir"] == "./wiki_tmp"
    assert config["exclude_dirs"] == ["tests", "venv"]
```
---
## def test_load_config_multiple_files:
#### Тестирует ошибку при наличии нескольких конфигурационных файлов.

```python
def test_load_config_multiple_files(tmp_config_dir: Path, monkeypatch):
    """Тестирует ошибку при наличии нескольких конфигурационных файлов."""
    config_content1 = """
    gutarik:
      project_dirs: []
      docs_dir: ./docs
      supported_ext: [".py"]
      wiki_repo: https://github.com/user/repo.wiki.git
      local_wiki_dir: ./wiki_tmp
      exclude_dirs: []
    """
    config_content2 = """
    [gutarik]
    project_dirs = []
    docs_dir = "./docs"
    supported_ext = [".py"]
    wiki_repo = "https://github.com/user/repo.wiki.git"
    local_wiki_dir = "./wiki_tmp"
    exclude_dirs = []
    """
    config_file1 = tmp_config_dir / "gutarik.yml"
    config_file2 = tmp_config_dir / "gutarik.toml"
    config_file1.write_text(config_content1)
    config_file2.write_text(config_content2)

    monkeypatch.chdir(tmp_config_dir)
    with pytest.raises(ValueError, match="Multiple config files found"):
        load_config()
```
---
## def test_load_config_wrong_name:
#### Тестирует ошибку при неверном имени файла.

```python
def test_load_config_wrong_name(tmp_config_dir: Path):
    """Тестирует ошибку при неверном имени файла."""
    config_content = """
    gutarik:
      project_dirs: []
      docs_dir: ./docs
      supported_ext: [".py"]
      wiki_repo: https://github.com/user/repo.wiki.git
      local_wiki_dir: ./wiki_tmp
      exclude_dirs: []
    """
    config_file = tmp_config_dir / "wrongname.yml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Config file must start with 'gutarik'"):
        load_config(str(config_file))
```
---
## def test_load_config_no_file:
#### Тестирует использование конфигурации по умолчанию, если файл не найден.

```python
def test_load_config_no_file(tmp_config_dir: Path, monkeypatch):
    """Тестирует использование конфигурации по умолчанию, если файл не найден."""
    monkeypatch.chdir(tmp_config_dir)
    config = load_config()
    assert config["PROJECT_DIRS"] == [Path("gutarik/src")]
    assert config["DOCS_DIR"] == Path("docs")
    assert config["SUPPORTED_EXT"] == [".py"]
    assert config["WIKI_REPO"] == "https://github.com/user/repo.wiki.git"
    assert config["LOCAL_WIKI_DIR"] == Path("wiki_tmp")
    assert config["EXCLUDE_DIRS"] == []
```
---