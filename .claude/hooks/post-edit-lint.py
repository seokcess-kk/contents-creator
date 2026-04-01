"""PostToolUse hook: Write|Edit 후 domain/, scripts/ 하위 .py 파일에 ruff 실행."""

import json
import re
import subprocess
import sys

PROJECT_ROOT = "C:/Users/assag/solution/contents-creator"


def main() -> None:
    data = json.load(sys.stdin)

    file_path = data.get("tool_input", {}).get("file_path", "") or data.get(
        "tool_response", {}
    ).get("filePath", "")

    # domain/ 또는 scripts/ 하위 .py 파일만 대상
    if not re.search(r"(domain|scripts)/.*\.py$", file_path):
        return

    messages: list[str] = []

    # ruff check
    r1 = subprocess.run(
        ["ruff", "check", "--quiet", file_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,
    )
    if r1.returncode != 0 and r1.stdout:
        messages.append(f"ruff check:\n{r1.stdout.strip()}")

    # ruff format
    r2 = subprocess.run(
        ["ruff", "format", "--check", "--quiet", file_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,
    )
    if r2.returncode != 0 and r2.stdout:
        messages.append(f"ruff format:\n{r2.stdout.strip()}")

    if messages:
        print(json.dumps({"systemMessage": "\n".join(messages)}))


if __name__ == "__main__":
    main()
