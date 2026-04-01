"""의료법 검증만 실행.

사용법:
    python scripts/validate.py --file path/to/text.md
    python scripts/validate.py --text "검증할 텍스트"
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("validate")


def main() -> None:
    parser = argparse.ArgumentParser(description="의료광고법 검증")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="검증할 텍스트 파일 경로")
    group.add_argument("--text", help="검증할 텍스트 직접 입력")
    parser.add_argument("--no-llm", action="store_true", help="LLM 2차 검증 스킵")
    parser.add_argument("--fix", action="store_true", help="자동 수정 실행")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = args.text

    from domain.compliance.checker import check_compliance
    from domain.compliance.fixer import fix_and_verify

    report = check_compliance(text, use_llm=not args.no_llm)

    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if args.fix and report.verdict != "pass":
        logger.info("자동 수정 시작...")
        fixed_text, final_report = fix_and_verify(text, report, use_llm_check=not args.no_llm)

        print("\n=== 수정 결과 ===")
        print(json.dumps(final_report.model_dump(mode="json"), ensure_ascii=False, indent=2))

        if final_report.verdict == "pass":
            output_path = Path("_workspace/validated_text.md")
            output_path.parent.mkdir(exist_ok=True)
            output_path.write_text(fixed_text, encoding="utf-8")
            logger.info("수정된 텍스트 저장: %s", output_path)


if __name__ == "__main__":
    main()
