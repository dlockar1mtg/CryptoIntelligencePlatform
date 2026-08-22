from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v2_native_context_holdout_evaluation.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import os\nimport sys\nfrom pathlib import Path\n",
        "import os\nimport shutil\nimport sys\nimport tempfile\nfrom pathlib import Path\n",
        "imports",
    )

    old = '''    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")\n    os.environ["CRYPTO_DATABASE_PATH"] = str(source)\n    try:\n        from crypto_platform.platform import load_all, connect\n        settings, _ = load_all()\n        conn = connect(settings)\n'''
    new = '''    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")\n    with tempfile.TemporaryDirectory(prefix="crypto_v2_holdout_") as tmp:\n        temp_db = Path(tmp) / source.name\n        shutil.copy2(source, temp_db)\n        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)\n        try:\n            from crypto_platform.platform import load_all, connect\n            settings, _ = load_all()\n            conn = connect(settings)\n'''
    text = replace_once(text, old, new, "disposable database setup")

    # The source body is still at the original try indentation immediately
    # after setup replacement. Move that body one level deeper so it remains
    # inside the new TemporaryDirectory + try scope.
    start_anchor = '        runner = object.__new__(Module38Runner)\n'
    end_anchor = '        conn.close()\n    finally:\n'
    if text.count(start_anchor) != 1:
        raise RuntimeError(
            f"evaluation body start: expected exactly one source anchor, found {text.count(start_anchor)}"
        )
    if text.count(end_anchor) != 1:
        raise RuntimeError(
            f"evaluation body end: expected exactly one source anchor, found {text.count(end_anchor)}"
        )
    start = text.index(start_anchor)
    end = text.index(end_anchor, start)
    body = text[start:end]
    body = ''.join('    ' + line if line.strip() else line for line in body.splitlines(True))
    text = text[:start] + body + text[end:]

    text = replace_once(
        text,
        '        conn.close()\n    finally:\n        if prior_env is None:\n            os.environ.pop("CRYPTO_DATABASE_PATH", None)\n        else:\n            os.environ["CRYPTO_DATABASE_PATH"] = prior_env\n',
        '            conn.close()\n        finally:\n            if prior_env is None:\n                os.environ.pop("CRYPTO_DATABASE_PATH", None)\n            else:\n                os.environ["CRYPTO_DATABASE_PATH"] = prior_env\n',
        "disposable database cleanup",
    )

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("CRYPTO_V2_EVALUATOR_DISPOSABLE_DATABASE_FIX=PASS")
    print(f"UPDATED_FILE={TARGET}")
    print("SOURCE_DATABASE_OPENED_BY_EVALUATOR=FALSE")
    print("DISPOSABLE_DATABASE_COPY_USED=TRUE")
    print("NEXT_GATE=VALIDATE_V2_EVALUATOR_DISPOSABLE_DATABASE_SOURCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
