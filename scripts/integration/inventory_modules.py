from __future__ import annotations

import ast
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "crypto_platform"
OUTPUT_ROOT = ROOT / "docs" / "integration" / "orchestration"

MODULE_MIN = 1
MODULE_MAX = 44


@dataclass(frozen=True)
class ModuleInventory:
    module_number: int
    implementation_path: str | None
    implementation_exists: bool
    expected_callable: str
    callable_exists: bool
    callable_signature: str | None
    is_async: bool | None
    imported_modules: list[str]
    runner_path: str | None
    runner_exists: bool
    runner_invokes_callable: bool
    status: str
    notes: list[str]


def implementation_path(module_number: int) -> Path:
    if module_number == 1:
        return PACKAGE_ROOT / "platform.py"

    return PACKAGE_ROOT / f"module{module_number}.py"


def runner_path(module_number: int) -> Path:
    return ROOT / f"run_module{module_number}.py"


def load_tree(path: Path) -> ast.Module:
    source = path.read_text(encoding="utf-8-sig")
    return ast.parse(source, filename=str(path))


def annotation_text(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None

    return ast.unparse(annotation)


def format_default(default: ast.expr) -> str:
    try:
        return ast.unparse(default)
    except Exception:
        return "<default>"


def format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    arguments = node.args
    pieces: list[str] = []

    positional = list(arguments.posonlyargs) + list(arguments.args)
    positional_defaults = [None] * (
        len(positional) - len(arguments.defaults)
    ) + list(arguments.defaults)

    positional_only_count = len(arguments.posonlyargs)

    for index, (argument, default) in enumerate(
        zip(positional, positional_defaults, strict=True)
    ):
        piece = argument.arg

        annotation = annotation_text(argument.annotation)
        if annotation:
            piece += f": {annotation}"

        if default is not None:
            piece += f" = {format_default(default)}"

        pieces.append(piece)

        if positional_only_count and index + 1 == positional_only_count:
            pieces.append("/")

    if arguments.vararg:
        vararg = f"*{arguments.vararg.arg}"
        annotation = annotation_text(arguments.vararg.annotation)
        if annotation:
            vararg += f": {annotation}"
        pieces.append(vararg)
    elif arguments.kwonlyargs:
        pieces.append("*")

    for argument, default in zip(
        arguments.kwonlyargs,
        arguments.kw_defaults,
        strict=True,
    ):
        piece = argument.arg

        annotation = annotation_text(argument.annotation)
        if annotation:
            piece += f": {annotation}"

        if default is not None:
            piece += f" = {format_default(default)}"

        pieces.append(piece)

    if arguments.kwarg:
        kwarg = f"**{arguments.kwarg.arg}"
        annotation = annotation_text(arguments.kwarg.annotation)
        if annotation:
            kwarg += f": {annotation}"
        pieces.append(kwarg)

    return_annotation = annotation_text(node.returns)
    signature = f"({', '.join(pieces)})"

    if return_annotation:
        signature += f" -> {return_annotation}"

    return signature


def collect_imports(tree: ast.Module) -> list[str]:
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return sorted(imports)


def find_callable(
    tree: ast.Module,
    callable_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == callable_name:
                return node

    return None


def runner_invokes(
    tree: ast.Module,
    callable_name: str,
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if isinstance(function, ast.Name) and function.id == callable_name:
            return True

        if isinstance(function, ast.Attribute):
            if function.attr == callable_name:
                return True

    return False


def relative_path(path: Path | None) -> str | None:
    if path is None:
        return None

    return path.relative_to(ROOT).as_posix()


def inspect_module(module_number: int) -> ModuleInventory:
    implementation = implementation_path(module_number)
    runner = runner_path(module_number)
    callable_name = f"run_module{module_number}"

    notes: list[str] = []
    imported_modules: list[str] = []
    callable_exists = False
    callable_signature: str | None = None
    is_async: bool | None = None
    runner_calls_function = False

    if implementation.is_file():
        try:
            implementation_tree = load_tree(implementation)
            imported_modules = collect_imports(implementation_tree)

            callable_node = find_callable(
                implementation_tree,
                callable_name,
            )

            if callable_node is not None:
                callable_exists = True
                callable_signature = format_signature(callable_node)
                is_async = isinstance(callable_node, ast.AsyncFunctionDef)
            else:
                notes.append(
                    f"{callable_name} was not found in "
                    f"{relative_path(implementation)}."
                )

        except SyntaxError as exc:
            notes.append(
                f"Implementation syntax error: "
                f"{exc.msg} at line {exc.lineno}."
            )
    else:
        notes.append("Implementation file is missing.")

    if runner.is_file():
        try:
            runner_tree = load_tree(runner)
            runner_calls_function = runner_invokes(
                runner_tree,
                callable_name,
            )

            if not runner_calls_function:
                notes.append(
                    f"{relative_path(runner)} does not directly invoke "
                    f"{callable_name}."
                )

        except SyntaxError as exc:
            notes.append(
                f"Runner syntax error: "
                f"{exc.msg} at line {exc.lineno}."
            )
    else:
        notes.append("Root runner file is missing.")

    if (
        implementation.is_file()
        and callable_exists
        and runner.is_file()
        and runner_calls_function
    ):
        status = "ready"
    elif implementation.is_file() and callable_exists:
        status = "callable_available"
    else:
        status = "incomplete"

    return ModuleInventory(
        module_number=module_number,
        implementation_path=(
            relative_path(implementation)
            if implementation.is_file()
            else None
        ),
        implementation_exists=implementation.is_file(),
        expected_callable=callable_name,
        callable_exists=callable_exists,
        callable_signature=callable_signature,
        is_async=is_async,
        imported_modules=imported_modules,
        runner_path=relative_path(runner) if runner.is_file() else None,
        runner_exists=runner.is_file(),
        runner_invokes_callable=runner_calls_function,
        status=status,
        notes=notes,
    )


def write_csv(records: list[ModuleInventory], path: Path) -> None:
    fieldnames = [
        "module_number",
        "implementation_path",
        "implementation_exists",
        "expected_callable",
        "callable_exists",
        "callable_signature",
        "is_async",
        "runner_path",
        "runner_exists",
        "runner_invokes_callable",
        "status",
        "imported_modules",
        "notes",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            row: dict[str, Any] = asdict(record)
            row["imported_modules"] = "; ".join(record.imported_modules)
            row["notes"] = " | ".join(record.notes)
            writer.writerow(row)


def write_markdown(
    records: list[ModuleInventory],
    path: Path,
) -> None:
    ready = [record for record in records if record.status == "ready"]
    callable_only = [
        record
        for record in records
        if record.status == "callable_available"
    ]
    incomplete = [
        record
        for record in records
        if record.status == "incomplete"
    ]

    lines = [
        "# Crypto Module 1–44 Orchestration Inventory",
        "",
        f"- Modules inspected: {len(records)}",
        f"- Ready: {len(ready)}",
        f"- Callable available: {len(callable_only)}",
        f"- Incomplete: {len(incomplete)}",
        "",
        "## Callable signatures",
        "",
        "| Module | Implementation | Callable | Signature | Runner | Status |",
        "|---:|---|---|---|---|---|",
    ]

    for record in records:
        signature = record.callable_signature or "—"
        implementation = record.implementation_path or "—"
        runner = record.runner_path or "—"

        lines.append(
            f"| {record.module_number} "
            f"| `{implementation}` "
            f"| `{record.expected_callable}` "
            f"| `{signature}` "
            f"| `{runner}` "
            f"| {record.status} |"
        )

    lines.extend(
        [
            "",
            "## Findings requiring review",
            "",
        ]
    )

    findings_written = False

    for record in records:
        if not record.notes:
            continue

        findings_written = True
        lines.append(f"### Module {record.module_number}")
        lines.append("")

        for note in record.notes:
            lines.append(f"- {note}")

        lines.append("")

    if not findings_written:
        lines.append("No structural gaps detected.")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    records = [
        inspect_module(module_number)
        for module_number in range(MODULE_MIN, MODULE_MAX + 1)
    ]

    json_path = OUTPUT_ROOT / "module_inventory.json"
    csv_path = OUTPUT_ROOT / "module_inventory.csv"
    markdown_path = OUTPUT_ROOT / "MODULE_ORCHESTRATION_INVENTORY.md"

    json_path.write_text(
        json.dumps(
            [asdict(record) for record in records],
            indent=2,
        ),
        encoding="utf-8",
    )

    write_csv(records, csv_path)
    write_markdown(records, markdown_path)

    print("Crypto Module 1–44 Orchestration Inventory")
    print("=" * 48)
    print(f"Modules inspected: {len(records)}")

    for status in ("ready", "callable_available", "incomplete"):
        count = sum(record.status == status for record in records)
        print(f"{status}: {count}")

    print()
    print(f"JSON: {json_path.relative_to(ROOT)}")
    print(f"CSV: {csv_path.relative_to(ROOT)}")
    print(f"Markdown: {markdown_path.relative_to(ROOT)}")

    incomplete = [
        record.module_number
        for record in records
        if record.status == "incomplete"
    ]

    if incomplete:
        print()
        print(
            "Incomplete modules: "
            + ", ".join(str(number) for number in incomplete)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())