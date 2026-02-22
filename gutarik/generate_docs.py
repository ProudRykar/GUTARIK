"""Модуль для генерации Markdown-документации."""
# GenerateDocs

import textwrap
import argparse
from pathlib import Path
from typing import Any
import ast
import os
import re
import shutil
import subprocess

from gutarik.config_loader import load_config, validate_config

config = load_config(os.getenv("gutarik_config"), pointer="gutarik")
validate_config(config)

PROJECT_DIRS = [Path(p) for p in config["project_dirs"]]
DOCS_DIR = Path(config["docs_dir"])
SUPPORTED_EXT = config["supported_ext"]
WIKI_REPO = config["wiki_repo"]
LOCAL_WIKI_DIR = Path(config["local_wiki_dir"])
EXCLUDE_DIRS = [Path(p) for p in config["exclude_dirs"]]


def parse_google_docstring(docstring: str) -> dict[str, Any]:
    """Парсит Google-style докстринг в структуру словаря.

    Нормализует отступы (textwrap.dedent), сохраняет пустые строки и
    возвращает отдельными секциями первую строчку и остальное описание.
    """
    if not docstring:
        return {
            "first_line": "",
            "rest_description": "",
            "args": "",
            "returns": "",
            "raises": "",
        }

    doc = textwrap.dedent(docstring).rstrip("\n")

    sections: dict[str, Any] = {
        "first_line": "",
        "rest_description": [],
        "args": [],
        "returns": [],
        "raises": [],
    }

    current_section = "description"
    is_first_line = True

    for raw_line in doc.splitlines():
        line = raw_line.rstrip()
        line_strip = line.strip()

        if re.match(r"^(Args|Attributes):", line_strip):
            current_section = "args"
            continue
        elif re.match(r"^Returns:", line_strip):
            current_section = "returns"
            continue
        elif re.match(r"^(Raises|Exceptions):", line_strip):
            current_section = "raises"
            continue

        if current_section == "description":
            if is_first_line and line_strip:
                sections["first_line"] = line_strip
                is_first_line = False
            else:
                sections["rest_description"].append(line)
        else:
            sections[current_section].append(line)

    for key in sections:
        if key == "first_line":
            continue
        sections[key] = "\n".join(sections[key]).strip()
    return sections


def extract_docstrings(file_path: Path) -> dict[Any, Any]:
    """Извлекает докстринги и тела функций/методов из Python-файла.

    Args:
        file_path (Path): Путь к Python-файлу.

    Returns:
        dict: Структура с докстрингами и кодом:
            - module (str): Докстринг модуля.
            - classes (dict): Классы и их методы.
            - functions (dict): Глобальные функции.
    """
    with open(file_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    docstrings: dict[str, Any] = {
        "module": ast.get_docstring(tree),
        "classes": {},
    }

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_doc: dict[str, Any] = parse_google_docstring(
                ast.get_docstring(node) or ""
            )
            class_doc["methods"] = {}
            class_doc["body"] = get_class_body(file_path, node)
            for cnode in node.body:
                if isinstance(cnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_doc = parse_google_docstring(ast.get_docstring(cnode) or "")
                    method_doc["body"] = get_function_body(file_path, cnode)
                    method_doc["routes"] = get_route_metadata(cnode)
                    class_doc["methods"][cnode.name] = method_doc
            docstrings["classes"][node.name] = class_doc
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_doc = parse_google_docstring(ast.get_docstring(node) or "")
            func_doc["body"] = get_function_body(file_path, node)
            func_doc["routes"] = get_route_metadata(node)
            docstrings.setdefault("functions", {})[node.name] = func_doc

    return docstrings


def get_function_body(
    file_path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> str:
    """Извлекает полный исходный код функции или метода, включая сигнатуру и декораторы.

    Args:
        file_path (Path): Путь к файлу с исходным кодом.
        node (ast.AST): AST-узел функции или метода.

    Returns:
        str: Текст исходного кода функции.
    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    start_line = node.lineno - 1
    if hasattr(node, "decorator_list") and node.decorator_list:
        decorator_start = min(decorator.lineno - 1 for decorator in node.decorator_list)
        start_line = decorator_start
        while start_line > 0 and lines[start_line - 1].strip().startswith("@"):
            start_line -= 1

    end_line: int = node.end_lineno or start_line + 1

    while end_line < len(lines):
        line = lines[end_line].strip()
        if line and line.startswith("@"):
            break
        if line and not line.startswith(" "):
            break
        end_line += 1

    body = "".join(lines[start_line:end_line]).rstrip()
    return body


def get_class_body(file_path: Path, node: ast.ClassDef) -> str:
    """
    Извлекает верхнюю часть класса (декораторы, сигнатуру, поля и т.п.)
    до первой функции/декоратора внутри тела класса.

    Возвращает текст среза исходного файла (без последующих методов).
    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    start_line = node.lineno - 1
    if hasattr(node, "decorator_list") and node.decorator_list:
        decorator_start = min(dec.lineno - 1 for dec in node.decorator_list)
        start_line = decorator_start
        while start_line > 0 and lines[start_line - 1].strip().startswith("@"):
            start_line -= 1

    min_inner: int | None = None
    for cnode in node.body:
        if isinstance(cnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if getattr(cnode, "decorator_list", None):
                dec_start = min(dec.lineno - 1 for dec in cnode.decorator_list)
                candidate = dec_start
            else:
                candidate = cnode.lineno - 1
            if min_inner is None or candidate < min_inner:
                min_inner = candidate

    if min_inner is not None:
        end_line = min_inner
    else:
        end_line = (
            node.end_lineno if getattr(node, "end_lineno", None) else start_line + 1
        )

    body = "".join(lines[start_line:end_line]).rstrip()
    return body


def get_route_metadata(node: ast.AST) -> list[dict]:
    """
    Извлекает структурированную информацию из HTTP-декораторов.
    Возвращает список словарей с метаданными маршрута.
    """
    routes: list[dict] = []

    for dec in getattr(node, "decorator_list", []) or []:
        if not isinstance(dec, ast.Call):
            continue

        if isinstance(dec.func, ast.Name):
            method = dec.func.id
        elif isinstance(dec.func, ast.Attribute):
            method = dec.func.attr
        else:
            continue

        route_info = {
            "method": method,
            "path": None,
            "summary": None,
            "description": None,
            "tags": [],
            "status_code": None,
        }

        if dec.args:
            try:
                route_info["path"] = ast.literal_eval(dec.args[0])
            except Exception:
                pass

        for kw in dec.keywords:
            try:
                value = ast.literal_eval(kw.value)
            except Exception:
                continue

            if kw.arg == "summary":
                route_info["summary"] = value
            elif kw.arg == "description":
                route_info["description"] = value
            elif kw.arg == "tags":
                route_info["tags"] = value
            elif kw.arg == "status_code":
                route_info["status_code"] = value

        if route_info["status_code"] is None:
            route_info["status_code"] = 0

        routes.append(route_info)

    return routes


def escape_md_pipe(s: str) -> str:
    """
    Экранирует '|' для использования внутри Markdown-таблицы.
    Используем HTML-entity, т.к. она стабильно безопасно проходит через разные рендереры.
    """
    return s.replace("|", r"\|")


def split_top_level(s: str, sep: str = ",") -> list[str]:
    """
    Разбивает строку `s` по разделителю `sep`, но только те разделители,
    которые находятся на верхнем уровне (не внутри скобок или кавычек).

    Пример:
    split_top_level('Literal[\"a\", \"b\"], optional') -> ['Literal["a", "b"]', ' optional']
    """
    parts: list[str] = []
    buf: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(s):
        ch = s[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                j = i - 1
                esc = False
                while j >= 0 and s[j] == "\\":
                    esc = not esc
                    j -= 1
                if not esc:
                    quote = None
        else:
            if ch in ("'", '"'):
                quote = ch
                buf.append(ch)
            elif ch in "([{":
                stack.append(ch)
                buf.append(ch)
            elif ch in ")]}":
                if stack:
                    stack.pop()
                buf.append(ch)
            elif ch == sep and not stack and not quote:
                parts.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf))
    return [p for p in (p.strip() for p in parts) if p != ""]


def format_args_table_md(args_str: str) -> list[str]:
    md_lines: list[str] = []
    if not args_str or not args_str.strip():
        return md_lines

    md_lines.append("\n#### Аргументы")
    md_lines.append("| Аргумент | Тип | Описание |")
    md_lines.append("|----------|-----|----------|")

    for arg in args_str.split("\n"):
        if not arg.strip():
            continue
        parts = arg.strip().split(":", 1)
        if len(parts) == 2:
            name_type = parts[0].strip()
            desc = parts[1].strip()

            m = re.match(r"^([^\(]+)\s*\((.+)\)$", name_type)
            if m:
                arg_name = m.group(1).strip()
                raw_inside = m.group(2).strip()
                inside_parts = split_top_level(raw_inside, ",")
                arg_type = inside_parts[0] if inside_parts else ""
                flags = [p for p in (part.strip() for part in inside_parts[1:]) if p]
                if flags:
                    flags_text = ", ".join(flags)
                    if flags_text:
                        desc = f"{desc} ({flags_text})"
            else:
                arg_name = name_type
                arg_type = ""

            arg_type = escape_md_pipe(arg_type)
            md_lines.append(f"| `{arg_name}` | `{arg_type}` | {desc} |")
        else:
            md_lines.append(f"| `{arg.strip()}` | | |")

    return md_lines


def format_function_md(name: str, doc: dict[str, Any], is_method: bool = False) -> str:
    """Форматирует функцию или метод в Markdown с таблицами аргументов, возвращаемых значений и исключений.

    Args:
        name (str): Имя функции или метода.
        doc (dict): Докстринг функции, разобранный через parse_google_docstring.
        is_method (bool): Флаг, указывающий, что это метод класса.

    Returns:
        str: Сформатированный Markdown.
    """
    display_name = name.replace("__init__", "init")
    is_async = doc["body"].strip().startswith("async def")
    prefix = "async def" if is_async else "def"
    md = [f"## {prefix} {display_name}:"]

    if doc["first_line"]:
        md.append(f"#### {doc['first_line']}")

    if doc["rest_description"]:
        md.append("")

        rest = doc["rest_description"]
        rest = re.sub(r"(?m)^[\t ]*•[\t ]*", "- ", rest)
        rest = re.sub(r"(?m)^[\t ]*-\s*", "- ", rest)
        md.append(rest)

    routes = doc.get("routes") or []
    if routes:
        md.append("#### Маршрут:")
        for route in routes:
            md.append(f"- **Декоратор:** @{route['method']}")
            if route["path"]:
                md.append(f"- **Маршрут:** `{route['path']}`")
            if route["summary"]:
                md.append(f"- **Заголовок:** {route['summary']}")
            if route["description"]:
                md.append(f"- **Описание:** {route['description']}")
            if route["tags"]:
                md.append(f"- **Теги:** {', '.join(route['tags'])}")
            if route["status_code"]:
                md.append(f"- **Код ответа:** {route['status_code']}")
            md.append("")

    # Аргументы
    if doc["args"]:
        md.append("\n#### Аргументы")
        md.append("| Аргумент | Тип | Описание |")
        md.append("|----------|-----|----------|")

        for arg in doc["args"].split("\n"):
            if not arg.strip():
                continue
            parts = arg.strip().split(":", 1)
            if len(parts) == 2:
                name_type = parts[0].strip()
                desc = parts[1].strip()

                m = re.match(r"^([^\(]+)\s*\((.+)\)$", name_type)
                if m:
                    arg_name = m.group(1).strip()
                    raw_inside = m.group(2).strip()
                    inside_parts = split_top_level(raw_inside, ",")
                    arg_type = inside_parts[0] if inside_parts else ""
                    flags = [
                        p for p in (part.strip() for part in inside_parts[1:]) if p
                    ]
                    if flags:
                        flags_text = ", ".join(flags)
                        if flags_text:
                            desc = f"{desc} ({flags_text})"
                else:
                    arg_name = name_type
                    arg_type = ""

                arg_type = escape_md_pipe(arg_type)
                md.append(f"| `{arg_name}` | `{arg_type}` | {desc} |")
            else:
                md.append(f"| `{arg.strip()}` | | |")

    # Возвращаемое значение
    if doc["returns"] and doc["returns"].strip().lower() != "none":
        md.append("\n#### Возвращает")
        md.append("| Тип | Описание |")
        md.append("|-----|----------|")
        for ret in doc["returns"].split("\n"):
            if ret.strip():
                parts = ret.strip().split(":", 1)
                if len(parts) == 2:
                    ret_type = parts[0].strip()
                    ret_desc = parts[1].strip()
                    md.append(f"| `{ret_type}` | {ret_desc} |")
                else:
                    md.append(f"| `{ret.strip()}` | |")

    # Исключения
    if doc["raises"]:
        md.append("\n#### Исключения")
        md.append("| Исключение | Описание |")
        md.append("|------------|----------|")
        for exc in doc["raises"].split("\n"):
            if exc.strip():
                parts = exc.strip().split(":", 1)
                if len(parts) == 2:
                    exc_type = parts[0].strip()
                    exc_desc = parts[1].strip()
                    md.append(f"| `{exc_type}` | {exc_desc} |")
                else:
                    md.append(f"| `{exc.strip()}` | |")

    md.append("\n```python")
    md.append(doc["body"])
    md.append("```")

    return "\n".join(md)


def write_md(file_path: Path, docstrings: dict[str, Any]) -> str:
    """Генерирует Markdown-файл для модуля или класса.

    Args:
        file_path (Path): Путь к Python-файлу.
        docstrings (dict): Словарь с докстрингами, полученный через extract_docstrings.

    Returns:
        str: Полный Markdown контент для файла.
    """
    md_content = []

    if docstrings.get("module"):
        md_content.append(f"# Модуль {file_path.stem}\n\n{docstrings['module']}\n")

    for cls_name, cls_doc in docstrings.get("classes", {}).items():
        md_content.append(f"## Класс {cls_name}\n")
        if cls_doc.get("first_line"):
            md_content.append(f"**{cls_doc['first_line']}**")
        if cls_doc.get("rest_description"):
            md_content.append("")
            md_content.append(cls_doc["rest_description"])
        if cls_doc.get("args"):
            md_content.extend(format_args_table_md(cls_doc["args"]))

        if cls_doc.get("body"):
            md_content.append("\n```python")
            md_content.append(cls_doc["body"])
            md_content.append("```")

        if cls_doc.get("methods"):
            md_content.append("\n---")
        for method_name, method_doc in cls_doc.get("methods", {}).items():
            md_content.append(
                format_function_md(method_name, method_doc, is_method=True)
            )
            md_content.append("---")

    for func_name, func_doc in docstrings.get("functions", {}).items():
        md_content.append(format_function_md(func_name, func_doc))
        md_content.append("---")

    return "\n".join(md_content)


def create_docs(src_dirs: list[Path], dst_dir: Path, exclude_dirs: list[Path]) -> None:
    """Создает Markdown-документацию для всех Python-файлов из списка директорий.

    Args:
        src_dirs (list[Path]): Список исходных директорий.
        dst_dir (Path): Папка, куда будут сохранены сгенерированные Markdown-файлы.
    """
    for src_dir in src_dirs:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if Path(root) / d not in exclude_dirs]
            rel_path = Path(root).relative_to(src_dir)
            target_dir = dst_dir / rel_path
            target_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                file_path = Path(root) / file
                if (
                    file_path.suffix in SUPPORTED_EXT
                    and file_path.name != "__init__.py"
                ):
                    docstrings = extract_docstrings(file_path)
                    md_content = write_md(file_path, docstrings)
                    md_file = target_dir / f"{file_path.stem}.md"
                    with open(md_file, "w", encoding="utf-8") as f:
                        f.write(md_content)


def rename_wiki_files_by_header(local_wiki_dir: Path, docs_dir: Path) -> None:
    """Переименовывает .md файлы в .wiki_tmp на основании второй строки исходных .py файлов.

    Если вторая строка файла начинается с # , используется её содержимое (без решётки и пробелов) как новое имя Markdown-файла.
    Если такого заголовка нет, имя остаётся прежним.

    Args:
        local_wiki_dir (Path): Локальная директория Wiki (.wiki_tmp)
        docs_dir (Path): Папка с документацией (docs/)
    """
    for root, _, files in os.walk(local_wiki_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            md_path = Path(root) / file
            rel_path = md_path.relative_to(local_wiki_dir)
            py_source = docs_dir / rel_path
            py_source = py_source.with_suffix(".py")

            if not py_source.exists():
                for src_dir in PROJECT_DIRS:
                    possible_py = src_dir / rel_path
                    possible_py = possible_py.with_suffix(".py")
                    if possible_py.exists():
                        py_source = possible_py
                        break

            if not py_source.exists():
                continue

            try:
                with open(py_source, encoding="utf-8") as f:
                    lines = f.readlines()
                if len(lines) < 2:
                    continue
                second_line = lines[1].strip()
                if second_line.startswith("# "):
                    new_name = second_line[2:].strip()
                    if not new_name:
                        continue
                    new_md_name = f"{new_name}.md"
                    new_md_path = md_path.with_name(new_md_name)
                    if new_md_path != md_path:
                        os.rename(md_path, new_md_path)
                        print(f"[Wiki] Переименован: {md_path.name} → {new_md_name}")
            except Exception as e:
                print(f"[Wiki] Ошибка при обработке {md_path}: {e}")


def push_to_wiki(docs_dir: Path) -> None:
    """Копирует Markdown-документы в локальный клон Wiki и пушит изменения в удаленный репозиторий.

    Args:
        docs_dir (Path): Папка с сгенерированной документацией.
    """
    if not LOCAL_WIKI_DIR.exists():
        subprocess.run(["git", "clone", WIKI_REPO, str(LOCAL_WIKI_DIR)], check=True)

    for root, _, files in os.walk(docs_dir):
        rel_path = Path(root).relative_to(docs_dir)
        target_dir = LOCAL_WIKI_DIR / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)
        for file in files:
            if file.endswith(".md"):
                src_file = Path(root) / file
                dst_file = target_dir / file
                shutil.copy2(src_file, dst_file)

    rename_wiki_files_by_header(LOCAL_WIKI_DIR, docs_dir)

    subprocess.run(["git", "-C", str(LOCAL_WIKI_DIR), "add", "."], check=True)
    status = subprocess.run(
        ["git", "-C", str(LOCAL_WIKI_DIR), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout.strip():
        subprocess.run(
            [
                "git",
                "-C",
                str(LOCAL_WIKI_DIR),
                "commit",
                "-m",
                "[Wiki] Обновление документации",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(LOCAL_WIKI_DIR), "push"], check=True)
        print("[Wiki] Документация успешно обновлена и отправлена в Wiki.")
    else:
        print("[Wiki] Нет изменений для коммита.")


def main():
    parser = argparse.ArgumentParser(description="Генерация документации проекта")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Если указан, пушить документацию в GitHub Wiki",
    )
    args = parser.parse_args()

    create_docs(PROJECT_DIRS, DOCS_DIR, EXCLUDE_DIRS)
    print(f"Документация сгенерирована в {DOCS_DIR}")

    if args.push:
        push_to_wiki(DOCS_DIR)
