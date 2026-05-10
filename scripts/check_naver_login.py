"""Chrome 프로필 → CDP → 네이버 NID_AUT 쿠키 추출 검증.

publish.py 본 흐름과 분리된 단순 진단 도구. 프로필 설정 직후 1회 실행해서
"이 프로필이 정말 네이버에 로그인되어 있는가?" 를 확인.

사용:
    python scripts/check_naver_login.py --profile "Profile 2"

성공 시:
    .sessions/naver_check_<profile>.pkl 에 쿠키 저장됨.
    이후 publish.py 가 같은 프로필을 쓰면 캐시 적중 (재로그인 X).

실패 시:
    1) 해당 프로필이 Chrome 에 존재하는지 확인 (chrome://version 의 Profile Path)
    2) 그 프로필에서 https://blog.naver.com 접속 → 로그인되어 있는지 확인
    3) Chrome 이 모두 종료된 상태에서 재시도 (CDP 가 임시 사본을 띄우지만 일부 프로필 잠금 케이스 안전)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

from domain.publishing.auth import naver_login_cdp
from domain.publishing.session import SessionManager


def _safe_session_name(profile: str) -> str:
    """파일명 안전 변환: 'Profile 2' → 'naver_check_profile_2'."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", profile.strip().lower()).strip("_")
    return f"naver_check_{slug or 'default'}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chrome 프로필 → 네이버 CDP 로그인 검증 (publish.py 와 분리된 진단 도구)",
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Chrome 프로필명. 예: 'Default', 'Profile 1', 'Profile 2'. chrome://version 의 'Profile Path' 마지막 segment",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("scripts.check_naver_login")

    session_name = _safe_session_name(args.profile)
    sm = SessionManager(session_name)

    logger.info("CDP 로그인 시도 — profile=%r session=%s", args.profile, session_name)
    ok = naver_login_cdp(sm.session, chrome_profile=args.profile)

    if not ok:
        logger.error(
            "CDP 실패 — 다음을 확인하세요:\n"
            "  1) chrome://version 에서 Profile Path 마지막 segment 가 %r 인지\n"
            "  2) 해당 프로필로 https://blog.naver.com 접속 시 로그인 상태인지\n"
            "  3) Chrome 모두 종료한 상태에서 재시도",
            args.profile,
        )
        return 1

    if not sm.has_login_cookie():
        logger.error("쿠키는 받았지만 NID_AUT/NID_SES 부재. 프로필이 비로그인 상태입니다.")
        return 1

    sm.save()
    logger.info(
        "성공 — NID_AUT 또는 NID_SES 획득. 캐시 저장: %s",
        sm.cookie_path,
    )
    print(
        "\n다음 단계:\n"
        f"  1. config/.env 에 NAVER_CHROME_PROFILE={args.profile!r} 설정\n"
        "  2. python scripts/publish.py --slug <slug> --channel-id <uuid> "
        "--keyword '<키워드>' --dry-run\n"
        "  3. 출력된 _publish_dryrun.json 확인 후 --dry-run 제거하고 실 발행"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
