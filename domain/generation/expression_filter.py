"""AI 상투 표현 감지 및 대체.

④ 문장 표현 변이의 핵심 모듈.
"""

from __future__ import annotations

import re

# AI 상투 표현 블랙리스트
BLACKLIST: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r".{0,20}하는 것이 중요합니다\.?"),
        "핵심입니다",
    ),
    (
        re.compile(r".{0,20}에 대해 알아보겠습니다\.?"),
        "살펴보겠습니다",
    ),
    (
        re.compile(r".{0,20}것을 추천드립니다\.?"),
        "권해 드립니다",
    ),
    (
        re.compile(r"그렇다면 .{0,20}는 어떨까요\??"),
        "",
    ),
    (
        re.compile(r".{0,20}라고 할 수 있습니다\.?"),
        "입니다",
    ),
    (
        re.compile(r"오늘은 .{2,20}에 대해 이야기해 보려고 합니다\.?"),
        "",
    ),
    (
        re.compile(r"많은 분들이 궁금해하시는"),
        "자주 묻는",
    ),
    (
        re.compile(r"결론적으로 말씀드리자면"),
        "정리하면",
    ),
    (
        re.compile(r"이번 포스팅에서는"),
        "이 글에서는",
    ),
    (
        re.compile(r"도움이 되셨으면 좋겠습니다"),
        "참고해 주세요",
    ),
]


def filter_expressions(text: str) -> tuple[str, list[str]]:
    """AI 상투 표현을 감지하고 대체한다.

    Args:
        text: 원본 텍스트

    Returns:
        (수정된 텍스트, 감지된 표현 목록)
    """
    detected: list[str] = []
    result = text

    for pattern, replacement in BLACKLIST:
        matches = pattern.findall(result)
        if matches:
            detected.extend(matches)
            if replacement:
                result = pattern.sub(replacement, result)
            else:
                # 대체 없이 제거 (문장 재구성 필요 시 그대로 유지)
                pass

    # 리스트 항목 정규화: 번호/불릿 → `- ` 통일
    result = normalize_list_items(result)

    # 연속 빈 줄 정리 (3줄 이상 → 2줄로)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result, detected


def normalize_list_items(text: str) -> str:
    """번호/불릿 리스트를 `- ` 형식으로 통일한다."""
    # "1. ", "1) ", "① ", "• ", "· " → "- "
    result = re.sub(r"^(\d+)[.)]\s+", "- ", text, flags=re.MULTILINE)
    result = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "- ", result, flags=re.MULTILINE)
    result = re.sub(r"^[•·]\s+", "- ", result, flags=re.MULTILINE)
    return result


def count_cliches(text: str) -> int:
    """AI 상투 표현 수를 카운트한다."""
    count = 0
    for pattern, _ in BLACKLIST:
        count += len(pattern.findall(text))
    return count
