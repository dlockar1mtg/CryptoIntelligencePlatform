from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_tree(relative_path: str) -> ast.Module:
    path = ROOT / relative_path
    source = path.read_text(encoding="utf-8-sig")
    return ast.parse(source, filename=str(path))


def find_class(tree: ast.Module, class_name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node

    raise AssertionError(f"Class {class_name!r} was not found.")


def find_method(
    class_node: ast.ClassDef,
    method_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                return node

    raise AssertionError(
        f"Method {method_name!r} was not found in "
        f"class {class_node.name!r}."
    )


def called_self_methods(
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    calls: set[str] = set()

    for node in ast.walk(method_node):
        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if not isinstance(function, ast.Attribute):
            continue

        if not isinstance(function.value, ast.Name):
            continue

        if function.value.id != "self":
            continue

        calls.add(function.attr)

    return calls


def assert_fold_local_selection_contract(
    *,
    module_path: str,
    class_name: str,
    walk_forward_method: str,
) -> None:
    tree = load_tree(module_path)
    class_node = find_class(tree, class_name)

    selector = find_method(
        class_node,
        "select_features_for_fold",
    )

    argument_names = [
        argument.arg
        for argument in selector.args.args
    ]

    assert "train" in argument_names or "training_frame" in argument_names, (
        "select_features_for_fold must receive the outer-training data "
        "explicitly."
    )

    walk_forward = find_method(
        class_node,
        walk_forward_method,
    )

    calls = called_self_methods(walk_forward)

    assert "select_features_for_fold" in calls, (
        f"{class_name}.{walk_forward_method} must perform feature "
        "selection independently inside each outer fold."
    )


def test_module26_defines_fold_local_feature_selector() -> None:
    tree = load_tree("crypto_platform/module26.py")
    class_node = find_class(tree, "Module26Runner")

    selector = find_method(
        class_node,
        "select_features_for_fold",
    )

    argument_names = [
        argument.arg
        for argument in selector.args.args
    ]

    assert "train" in argument_names or "training_frame" in argument_names


def test_module26_nested_validation_selects_features_per_fold() -> None:
    assert_fold_local_selection_contract(
        module_path="crypto_platform/module26.py",
        class_name="Module26Runner",
        walk_forward_method="nested",
    )


def test_module28_defines_fold_local_feature_selector() -> None:
    tree = load_tree("crypto_platform/module28.py")
    class_node = find_class(tree, "Module28Runner")

    selector = find_method(
        class_node,
        "select_features_for_fold",
    )

    argument_names = [
        argument.arg
        for argument in selector.args.args
    ]

    assert "train" in argument_names or "training_frame" in argument_names


def test_module28_nested_validation_selects_features_per_fold() -> None:
    assert_fold_local_selection_contract(
        module_path="crypto_platform/module28.py",
        class_name="Module28Runner",
        walk_forward_method="nested_run",
    )